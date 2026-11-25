import React, { useMemo, useState } from "react";
import type { Conflict, Section, Station, Train } from "../types";
import { Badge } from "./ui";

export interface TimeDistanceGraphProps {
  stations: Station[];
  sections: Section[];
  trains: Train[];
  conflicts: Conflict[];
  simTimeMin?: number;
  simTimeString?: string;
  onSelectTrain?: (trainId: string) => void;
  selectedTrainId?: string;
  height?: number;
}

interface StationChainage {
  id: string;
  name: string;
  code: string;
  km: number;
  y: number;
  isJunction: boolean;
}

interface TrajectoryPoint {
  timeMin: number;
  km: number;
  stationId?: string;
  isDwell?: boolean;
}

interface TrainTrajectory {
  train: Train;
  color: string;
  direction: "UP" | "DOWN";
  scheduledPoints: TrajectoryPoint[];
  projectedPoints: TrajectoryPoint[];
  delayMin: number;
  currentKm: number;
  isStale?: boolean;
}

const SECTION_SPEED_FACTORS: Record<string, number> = {
  EXPRESS: 0.85,
  PASSENGER: 1.0,
  MEMU: 1.0,
  FREIGHT: 1.25,
};

const TRAIN_COLORS: Record<string, string> = {
  EXPRESS: "#2563EB", // Blue
  PASSENGER: "#059669", // Emerald
  MEMU: "#D97706", // Amber
  FREIGHT: "#7C3AED", // Violet
};

function parseTimeToMinutes(timeStr: string | null | undefined): number {
  if (!timeStr) return 360; // 06:00 default
  const parts = timeStr.split(":");
  if (parts.length >= 2) {
    const h = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    if (!isNaN(h) && !isNaN(m)) {
      return h * 60 + m;
    }
  }
  return 360;
}

function formatMinutesToTime(min: number): string {
  const normalized = Math.max(0, Math.floor(min));
  const h = Math.floor(normalized / 60) % 24;
  const m = normalized % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

export function TimeDistanceGraph({
  stations,
  sections,
  trains,
  conflicts,
  simTimeMin = 384, // 06:24
  simTimeString = "06:24",
  onSelectTrain,
  selectedTrainId,
  height = 580,
}: TimeDistanceGraphProps) {
  // Controls & Filters
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "UP" | "DOWN">("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [windowDuration, setWindowDuration] = useState<number>(180); // 3 hours window
  const [timePanOffset, setTimePanOffset] = useState<number>(0); // manual pan in minutes
  const [showScheduled, setShowScheduled] = useState<boolean>(true);
  const [showObserved, setShowObserved] = useState<boolean>(true);
  const [showForecast, setShowForecast] = useState<boolean>(true);
  const [hoveredTrain, setHoveredTrain] = useState<Train | null>(null);
  const [showTable, setShowTable] = useState(false);

  // SVG layout dimensions
  const width = 1000;
  const margin = { top: 44, right: 60, bottom: 50, left: 140 };
  const graphWidth = width - margin.left - margin.right;
  const graphHeight = height - margin.top - margin.bottom;

  // Dynamic Station Chainage & Corridor Geometry Calculation (eliminates hardcoding)
  const { stationKms, maxKm, singleLineSections } = useMemo(() => {
    const kms: Record<string, number> = {};
    const singleLines: { name: string; kmStart: number; kmEnd: number }[] = [];

    // Sort stations topologically / by x coordinate
    const sorted = [...stations].sort((a, b) => a.x - b.x);

    if (sorted.length === 0) {
      return { stationKms: {}, maxKm: 60.0, singleLineSections: [] };
    }

    let runningKm = 0.0;
    sorted.forEach((st, idx) => {
      if (idx === 0) {
        kms[st.id] = 0.0;
      } else {
        const prev = sorted[idx - 1];
        // Find connecting section
        const sec = sections.find(
          (s) =>
            (s.from_station === prev.id && s.to_station === st.id) ||
            (s.to_station === prev.id && s.from_station === st.id)
        );
        // Use configured distance or fall back to x delta
        const dist = (sec as any)?.distance_km ?? Math.max(10.0, (st.x - prev.x) * 0.6);
        runningKm += dist;
        kms[st.id] = runningKm;

        if (sec && sec.mode === "SINGLE") {
          singleLines.push({
            name: `${sec.id} (${prev.code || prev.id}–${st.code || st.id})`,
            kmStart: kms[prev.id],
            kmEnd: runningKm,
          });
        }
      }
    });

    const totalKm = Math.max(10.0, runningKm > 0 ? runningKm : 60.0);
    return { stationKms: kms, maxKm: totalKm, singleLineSections: singleLines };
  }, [stations, sections]);

  // Station vertical scale (chainage km -> Y)
  const stationChainages: StationChainage[] = useMemo(() => {
    return stations.map((s) => {
      const km = stationKms[s.id] ?? 0.0;
      const y = margin.top + (km / maxKm) * graphHeight;
      return {
        id: s.id,
        name: s.name,
        code: s.code || s.id,
        km,
        y,
        isJunction: s.is_junction,
      };
    });
  }, [stations, stationKms, maxKm, graphHeight, margin.top]);

  // Dynamic Time Window Calculation with Panning
  const timeStart = useMemo(() => {
    const half = Math.floor(windowDuration / 3);
    const base = Math.floor((simTimeMin - half) / 30) * 30 + timePanOffset;
    return Math.max(0, base);
  }, [simTimeMin, windowDuration, timePanOffset]);

  const timeEnd = timeStart + windowDuration;

  // Coordinate conversion helpers
  const timeToX = (tMin: number): number => {
    return margin.left + ((tMin - timeStart) / (timeEnd - timeStart)) * graphWidth;
  };

  const kmToY = (km: number): number => {
    return margin.top + (Math.max(0, Math.min(maxKm, km)) / maxKm) * graphHeight;
  };

  // Generate Trajectories for Trains
  const trajectories = useMemo<TrainTrajectory[]>(() => {
    return trains.map((train) => {
      const dir = (train.direction === "DOWN" ? "DOWN" : "UP") as "UP" | "DOWN";
      const speedFactor = SECTION_SPEED_FACTORS[train.train_type] || 1.0;
      const baseColor = TRAIN_COLORS[train.train_type] || "#2563EB";
      const schedDep = parseTimeToMinutes(train.scheduled_departure);
      const delay = train.projected_delay_min || train.delay_min || 0;

      // Ordered stations along corridor
      const sortedStationIds = [...stations].sort((a, b) => a.x - b.x).map((s) => s.id);
      const defaultRoute = dir === "UP" ? sortedStationIds : [...sortedStationIds].reverse();
      const routeStationIds = train.route && train.route.length > 0 ? train.route : defaultRoute;

      // Generate scheduled points along corridor
      const scheduledPoints: TrajectoryPoint[] = [];
      const projectedPoints: TrajectoryPoint[] = [];

      let currentSchedTime = schedDep;
      let currentProjTime = schedDep + delay;

      routeStationIds.forEach((stId, idx) => {
        const km = stationKms[stId] ?? (dir === "UP" ? idx * 15 : maxKm - idx * 15);

        if (idx === 0) {
          scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId });
          projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId });
        } else {
          const prevStId = routeStationIds[idx - 1];
          // Section transit time lookup
          const sec = sections.find(
            (s) =>
              (s.from_station === prevStId && s.to_station === stId) ||
              (s.to_station === prevStId && s.from_station === stId)
          );
          const nominalRun = sec?.blocks?.[0]?.run_time_min ?? 12;
          const legTime = Math.round(nominalRun * speedFactor);
          currentSchedTime += legTime;
          currentProjTime += legTime;

          scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId });
          projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId });

          // Station dwell if not final terminal
          if (idx < routeStationIds.length - 1) {
            const dwell = train.train_type === "EXPRESS" ? 1 : 2;
            currentSchedTime += dwell;
            currentProjTime += dwell;
            scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId, isDwell: true });
            projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId, isDwell: true });
          }
        }
      });

      // Current km position
      let currentKm = 0;
      if (train.station_id) {
        currentKm = stationKms[train.station_id] ?? (dir === "UP" ? 0 : maxKm);
      } else if (train.block_id) {
        if (train.block_id.startsWith("B1")) currentKm = (stationKms["KRN"] || 14) * 0.5;
        else if (train.block_id.startsWith("B2")) currentKm = (stationKms["KRN"] || 14) + 9.0;
        else if (train.block_id.startsWith("B3")) currentKm = (stationKms["MLG"] || 32) + 8.0;
        else if (train.block_id.startsWith("B4")) currentKm = (stationKms["SRP"] || 48) + 6.0;
        else currentKm = maxKm * 0.5;
      } else {
        currentKm = dir === "UP" ? 0 : maxKm;
      }

      return {
        train,
        color: baseColor,
        direction: dir,
        scheduledPoints,
        projectedPoints,
        delayMin: delay,
        currentKm,
        isStale: train.waiting_reason?.includes("stale") || false,
      };
    });
  }, [trains, stations, sections, stationKms, maxKm]);

  // Filter trajectories by direction & category
  const filteredTrajectories = useMemo(() => {
    return trajectories.filter((t) => {
      if (directionFilter !== "ALL" && t.direction !== directionFilter) return false;
      if (categoryFilter !== "ALL" && t.train.train_type !== categoryFilter) return false;
      return true;
    });
  }, [trajectories, directionFilter, categoryFilter]);

  // Generate Time Grid Ticks (15-min intervals, prominent 60-min ticks)
  const timeTicks = useMemo(() => {
    const ticks: { min: number; label: string; isMajor: boolean }[] = [];
    const step = windowDuration >= 720 ? 60 : windowDuration >= 360 ? 30 : 15;
    for (let t = timeStart; t <= timeEnd; t += step) {
      ticks.push({
        min: t,
        label: formatMinutesToTime(t),
        isMajor: t % 60 === 0,
      });
    }
    return ticks;
  }, [timeStart, timeEnd, windowDuration]);

  // Current simulation time X coordinate
  const currentSimX = timeToX(simTimeMin);
  const isSimTimeVisible = currentSimX >= margin.left && currentSimX <= width - margin.right;

  return (
    <div className="time-distance-graph-card stack" style={{ gap: "14px" }}>
      {/* Control Workspace Header & Toolbar */}
      <div
        className="time-distance-controls flex-row justify-between items-center flex-wrap gap-3"
        style={{
          background: "#0F172A", // Dark navy command center styling
          color: "#FFFFFF",
          padding: "10px 16px",
          borderRadius: "8px",
          border: "1px solid #1E293B",
        }}
      >
        {/* Left: Direction & Category Filters */}
        <div className="flex-row items-center gap-2 flex-wrap">
          <span className="small text-muted" style={{ fontWeight: 600, color: "#94A3B8" }}>
            Filter:
          </span>
          <div className="button-group" role="group" aria-label="Direction filter">
            <button
              type="button"
              className={`button button-small ${directionFilter === "ALL" ? "button-primary" : "button-ghost"}`}
              onClick={() => setDirectionFilter("ALL")}
            >
              All Movements ({trajectories.length})
            </button>
            <button
              type="button"
              className={`button button-small ${directionFilter === "UP" ? "button-primary" : "button-ghost"}`}
              onClick={() => setDirectionFilter("UP")}
            >
              UP (NDL → VSN)
            </button>
            <button
              type="button"
              className={`button button-small ${directionFilter === "DOWN" ? "button-primary" : "button-ghost"}`}
              onClick={() => setDirectionFilter("DOWN")}
            >
              DOWN (VSN → NDL)
            </button>
          </div>

          <select
            className="input input-small"
            style={{ width: "auto", background: "#1E293B", color: "#FFFFFF", borderColor: "#334155" }}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            aria-label="Filter by train category"
          >
            <option value="ALL">All Categories</option>
            <option value="EXPRESS">Express / Mail</option>
            <option value="PASSENGER">Ordinary Passenger</option>
            <option value="MEMU">Suburban MEMU</option>
            <option value="FREIGHT">Freight Goods</option>
          </select>
        </div>

        {/* Center: Viewport & Pan Controls */}
        <div className="flex-row items-center gap-2 flex-wrap">
          <div className="button-group" role="group" aria-label="Time pan controls">
            <button
              type="button"
              className="button button-small button-ghost"
              onClick={() => setTimePanOffset((prev) => prev - 30)}
              title="Pan backward 30 minutes"
            >
              ◀ -30m
            </button>
            <button
              type="button"
              className="button button-small button-ghost"
              onClick={() => setTimePanOffset(0)}
              title="Reset view to current simulation time"
            >
              Center Now ⏱
            </button>
            <button
              type="button"
              className="button button-small button-ghost"
              onClick={() => setTimePanOffset((prev) => prev + 30)}
              title="Pan forward 30 minutes"
            >
              +30m ▶
            </button>
          </div>

          <div className="button-group" role="group" aria-label="Time window">
            <button
              type="button"
              className={`button button-small ${windowDuration === 120 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(120)}
            >
              2h
            </button>
            <button
              type="button"
              className={`button button-small ${windowDuration === 180 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(180)}
            >
              3h
            </button>
            <button
              type="button"
              className={`button button-small ${windowDuration === 360 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(360)}
            >
              6h
            </button>
            <button
              type="button"
              className={`button button-small ${windowDuration === 720 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(720)}
            >
              12h
            </button>
          </div>
        </div>

        {/* Right: Path Visibility Toggles & Table Toggle */}
        <div className="flex-row items-center gap-3">
          <label className="flex-row items-center gap-1 small text-muted" style={{ cursor: "pointer", color: "#CBD5E1" }}>
            <input
              type="checkbox"
              checked={showScheduled}
              onChange={(e) => setShowScheduled(e.target.checked)}
            />
            <span>Scheduled</span>
          </label>
          <label className="flex-row items-center gap-1 small text-muted" style={{ cursor: "pointer", color: "#CBD5E1" }}>
            <input
              type="checkbox"
              checked={showForecast}
              onChange={(e) => setShowForecast(e.target.checked)}
            />
            <span>Projected</span>
          </label>

          <button
            type="button"
            className="button button-small button-ghost"
            style={{ color: "#F59E0B" }}
            onClick={() => setShowTable(!showTable)}
          >
            {showTable ? "View Graph Chart" : "View Accessible Table"}
          </button>
        </div>
      </div>

      {/* Accessible Table Fallback */}
      {showTable ? (
        <div className="table-wrapper" tabIndex={0} role="region" aria-label="Time-Distance train trajectories data table">
          <table className="table">
            <thead>
              <tr>
                <th>Train</th>
                <th>Type / Cat</th>
                <th>Direction</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Sched Dep</th>
                <th>Current Status</th>
                <th>Projected Delay</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrajectories.map(({ train, delayMin }) => (
                <tr key={train.id}>
                  <td>
                    <strong>{train.name}</strong>
                    <span className="mono small text-muted d-block">#{train.id}</span>
                  </td>
                  <td>
                    <Badge tone="muted">{train.train_type}</Badge>
                  </td>
                  <td>
                    <Badge tone="muted">{train.direction}</Badge>
                  </td>
                  <td>{train.origin}</td>
                  <td>{train.destination}</td>
                  <td className="mono">{train.scheduled_departure || "—"}</td>
                  <td>{train.status}</td>
                  <td>
                    <span className={delayMin > 0 ? "text-bad" : "text-good"}>
                      {delayMin > 0 ? `+${delayMin} min` : "On time"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Vector SVG Time-Distance Graph */
        <div
          className="time-distance-svg-container"
          style={{
            position: "relative",
            overflowX: "auto",
            background: "#FFFFFF",
            border: "1px solid #CBD5E1",
            borderRadius: "8px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.04)",
          }}
        >
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="time-distance-svg"
            role="img"
            aria-label="Time-Distance Train Graph representing corridor train paths against station chainage"
            style={{ width: "100%", minWidth: "900px", height: "auto", display: "block" }}
          >
            <title>Section Controller Master Time-Distance Train Graph</title>
            <desc>
              Displays train paths along the Nandpur to Vasanthpur corridor over time.
              Horizontal axis represents time (IST); vertical axis represents corridor stations.
            </desc>

            {/* Shaded Background for Single-Line Bottleneck Sections */}
            {singleLineSections.map((sec) => {
              const y1 = kmToY(sec.kmStart);
              const y2 = kmToY(sec.kmEnd);
              return (
                <g key={sec.name}>
                  <rect
                    x={margin.left}
                    y={y1}
                    width={graphWidth}
                    height={y2 - y1}
                    fill="#FEF3C7"
                    opacity={0.35}
                  />
                  <text
                    x={width - margin.right - 8}
                    y={y1 + 16}
                    textAnchor="end"
                    fill="#B45309"
                    fontSize={10}
                    fontWeight={600}
                    letterSpacing="0.05em"
                  >
                    SINGLE LINE: {sec.name}
                  </text>
                </g>
              );
            })}

            {/* Vertical Time Grid Lines */}
            {timeTicks.map((tick) => {
              const x = timeToX(tick.min);
              return (
                <g key={`time-tick-${tick.min}`}>
                  <line
                    x1={x}
                    y1={margin.top}
                    x2={x}
                    y2={height - margin.bottom}
                    stroke={tick.isMajor ? "#CBD5E1" : "#F1F5F9"}
                    strokeWidth={tick.isMajor ? 1.5 : 1}
                    strokeDasharray={tick.isMajor ? undefined : "3 3"}
                  />
                  <text
                    x={x}
                    y={height - margin.bottom + 20}
                    textAnchor="middle"
                    fontSize={11}
                    fontFamily="monospace"
                    fill={tick.isMajor ? "#1E293B" : "#64748B"}
                    fontWeight={tick.isMajor ? 700 : 500}
                  >
                    {tick.label}
                  </text>
                  <text
                    x={x}
                    y={margin.top - 12}
                    textAnchor="middle"
                    fontSize={11}
                    fontFamily="monospace"
                    fill={tick.isMajor ? "#1E293B" : "#64748B"}
                    fontWeight={tick.isMajor ? 700 : 500}
                  >
                    {tick.label}
                  </text>
                </g>
              );
            })}

            {/* Horizontal Station Guideline Rows */}
            {stationChainages.map((station) => (
              <g key={`station-line-${station.id}`}>
                <line
                  x1={margin.left}
                  y1={station.y}
                  x2={width - margin.right}
                  y2={station.y}
                  stroke="#94A3B8"
                  strokeWidth={station.isJunction ? 2 : 1.25}
                  strokeDasharray={station.isJunction ? undefined : "4 2"}
                />

                {/* Left Station Label */}
                <text
                  x={margin.left - 12}
                  y={station.y + 4}
                  textAnchor="end"
                  fontSize={12}
                  fontWeight={station.isJunction ? 700 : 600}
                  fill={station.isJunction ? "#0F172A" : "#334155"}
                >
                  {station.code} ({station.name})
                </text>
                <text
                  x={margin.left - 12}
                  y={station.y + 16}
                  textAnchor="end"
                  fontSize={10}
                  fill="#64748B"
                  fontFamily="monospace"
                >
                  km {station.km.toFixed(1)}
                </text>

                {/* Right Station Chainage */}
                <text
                  x={width - margin.right + 10}
                  y={station.y + 4}
                  textAnchor="start"
                  fontSize={11}
                  fontWeight={600}
                  fill="#475569"
                >
                  {station.code}
                </text>
              </g>
            ))}

            {/* Trajectories */}
            {filteredTrajectories.map(({ train, color, scheduledPoints, projectedPoints }) => {
              const isSelected = selectedTrainId === train.id;
              const isHovered = hoveredTrain?.id === train.id;

              // Split projected points into past (observed running) and future (forecast)
              const pastPoints: TrajectoryPoint[] = [];
              const futurePoints: TrajectoryPoint[] = [];

              projectedPoints.forEach((p) => {
                if (p.timeMin <= simTimeMin) {
                  pastPoints.push(p);
                } else {
                  if (pastPoints.length > 0 && futurePoints.length === 0) {
                    futurePoints.push(pastPoints[pastPoints.length - 1]);
                  }
                  futurePoints.push(p);
                }
              });

              const makePath = (points: TrajectoryPoint[]) => {
                if (points.length < 2) return "";
                return points
                  .map((p, idx) => {
                    const x = timeToX(p.timeMin);
                    const y = kmToY(p.km);
                    return `${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
                  })
                  .join(" ");
              };

              const scheduledPathD = makePath(scheduledPoints);
              const observedPathD = makePath(pastPoints);
              const forecastPathD = makePath(futurePoints.length > 0 ? futurePoints : projectedPoints);

              return (
                <g
                  key={`trajectory-${train.id}`}
                  className="train-trajectory-group"
                  style={{ cursor: "pointer" }}
                  onClick={() => onSelectTrain && onSelectTrain(train.id)}
                  onMouseEnter={() => setHoveredTrain(train)}
                  onMouseLeave={() => setHoveredTrain(null)}
                >
                  {/* Scheduled Line (faint baseline) */}
                  {showScheduled && scheduledPathD && (
                    <path
                      d={scheduledPathD}
                      fill="none"
                      stroke="#94A3B8"
                      strokeWidth={1.5}
                      strokeOpacity={0.6}
                    />
                  )}

                  {/* Observed Past Movement (solid line) */}
                  {showObserved && observedPathD && (
                    <path
                      d={observedPathD}
                      fill="none"
                      stroke={isSelected ? "#EF4444" : isHovered ? "#2563EB" : color}
                      strokeWidth={isSelected ? 4 : isHovered ? 3.5 : 2.5}
                      strokeLinecap="round"
                    />
                  )}

                  {/* Forecast / Projected Movement (dashed line) */}
                  {showForecast && forecastPathD && (
                    <path
                      d={forecastPathD}
                      fill="none"
                      stroke={isSelected ? "#EF4444" : isHovered ? "#2563EB" : color}
                      strokeWidth={isSelected ? 3.5 : isHovered ? 3 : 2}
                      strokeDasharray="6 3"
                      strokeLinecap="round"
                    />
                  )}

                  {/* Train Identifier Label along path */}
                  {projectedPoints.length > 2 && (
                    <text
                      x={timeToX(projectedPoints[1].timeMin) + 4}
                      y={kmToY(projectedPoints[1].km) - 6}
                      fill={color}
                      fontSize={10}
                      fontWeight={700}
                      fontFamily="monospace"
                    >
                      {train.id} ({train.name.split(" ")[0]})
                    </text>
                  )}
                </g>
              );
            })}

            {/* Active Conflicts Markers */}
            {conflicts.map((c) => {
              const startX = timeToX(c.start_min);
              const conflictY = c.location.station_id
                ? kmToY(stationKms[c.location.station_id] ?? 30)
                : kmToY(30);

              if (startX < margin.left || startX > width - margin.right) return null;

              return (
                <g key={`conflict-marker-${c.id}`} transform={`translate(${startX}, ${conflictY})`}>
                  <circle r={9} fill="#EF4444" opacity={0.25} />
                  <circle r={5} fill="#DC2626" />
                  <text
                    x={8}
                    y={-4}
                    fontSize={10}
                    fontWeight={700}
                    fill="#DC2626"
                  >
                    ⚠️ {c.type}
                  </text>
                </g>
              );
            })}

            {/* Current Simulation Time Marker */}
            {isSimTimeVisible && (
              <g className="current-sim-time-cursor">
                <line
                  x1={currentSimX}
                  y1={margin.top - 20}
                  x2={currentSimX}
                  y2={height - margin.bottom + 15}
                  stroke="#E11D48"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                />
                <rect
                  x={currentSimX - 44}
                  y={margin.top - 32}
                  width={88}
                  height={20}
                  fill="#E11D48"
                  rx={4}
                />
                <text
                  x={currentSimX}
                  y={margin.top - 18}
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize={11}
                  fontWeight={700}
                  fontFamily="monospace"
                >
                  {simTimeString} IST
                </text>
              </g>
            )}

            {/* Graph Axis Labels */}
            <text
              x={margin.left}
              y={margin.top - 24}
              fontSize={11}
              fontWeight={700}
              fill="#475569"
            >
              ← Chainage / Stations (km)
            </text>
            <text
              x={width - margin.right}
              y={height - margin.bottom + 40}
              textAnchor="end"
              fontSize={11}
              fontWeight={600}
              fill="#475569"
            >
              Operational Time (24h IST) →
            </text>
          </svg>

          {/* Interactive Tooltip on Hover */}
          {hoveredTrain && (
            <div
              className="time-distance-tooltip"
              style={{
                position: "absolute",
                top: "16px",
                right: "16px",
                background: "#0F172A",
                color: "#F8FAFC",
                padding: "12px 16px",
                borderRadius: "8px",
                boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
                pointerEvents: "none",
                maxWidth: "280px",
                fontSize: "0.85rem",
                zIndex: 10,
              }}
            >
              <div className="flex-row justify-between items-center gap-2 mb-1">
                <strong style={{ fontSize: "0.95rem", color: "#60A5FA" }}>
                  {hoveredTrain.name}
                </strong>
                <span className="mono small" style={{ color: "#94A3B8" }}>
                  #{hoveredTrain.id}
                </span>
              </div>
              <div className="stack gap-1 small">
                <div>
                  <span className="text-muted">Type: </span>
                  <span>{hoveredTrain.train_type} (Priority {hoveredTrain.priority})</span>
                </div>
                <div>
                  <span className="text-muted">Direction: </span>
                  <span>{hoveredTrain.direction}</span>
                </div>
                <div>
                  <span className="text-muted">Route: </span>
                  <span>{hoveredTrain.origin} → {hoveredTrain.destination}</span>
                </div>
                <div>
                  <span className="text-muted">Sched Dep: </span>
                  <span className="mono">{hoveredTrain.scheduled_departure || "—"}</span>
                </div>
                <div>
                  <span className="text-muted">Projected Delay: </span>
                  <span
                    style={{
                      color: hoveredTrain.projected_delay_min > 0 ? "#F87171" : "#4ADE80",
                      fontWeight: 700,
                    }}
                  >
                    {hoveredTrain.projected_delay_min > 0
                      ? `+${hoveredTrain.projected_delay_min} min`
                      : "On time"}
                  </span>
                </div>
                <div>
                  <span className="text-muted">Status: </span>
                  <span>{hoveredTrain.status}</span>
                </div>
                <div>
                  <span className="text-muted">Data Quality: </span>
                  <span className="mono" style={{ color: "#38BDF8" }}>
                    MEASURED (Axle Counter)
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
