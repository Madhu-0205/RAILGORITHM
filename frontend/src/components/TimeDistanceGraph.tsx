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
}

const STATION_KMS: Record<string, number> = {
  NDL: 0.0,
  KRN: 14.0,
  MLG: 32.0,
  SRP: 48.0,
  VSN: 60.0,
};

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
  height = 560,
}: TimeDistanceGraphProps) {
  // Controls
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "UP" | "DOWN">("ALL");
  const [windowDuration, setWindowDuration] = useState<number>(180); // 3 hours window
  const [hoveredTrain, setHoveredTrain] = useState<Train | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [showTable, setShowTable] = useState(false);

  // SVG layout dimensions
  const width = 1000;
  const margin = { top: 40, right: 60, bottom: 50, left: 140 };
  const graphWidth = width - margin.left - margin.right;
  const graphHeight = height - margin.top - margin.bottom;

  // Time window: center roughly around simTimeMin or start slightly earlier
  const timeStart = useMemo(() => {
    const half = Math.floor(windowDuration / 3);
    const start = Math.floor((simTimeMin - half) / 30) * 30;
    return Math.max(0, start);
  }, [simTimeMin, windowDuration]);

  const timeEnd = timeStart + windowDuration;

  // Station vertical scale (chainage km -> Y)
  const maxKm = 60.0;
  const stationChainages: StationChainage[] = useMemo(() => {
    return stations.map((s) => {
      const km = STATION_KMS[s.id] ?? (s.x / 100) * maxKm;
      // Y: NDL (km 0) at top, VSN (km 60) at bottom
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
  }, [stations, graphHeight, margin.top]);

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

      // Stations sequence
      const routeStationIds =
        train.route && train.route.length > 0
          ? train.route
          : dir === "UP"
          ? ["NDL", "KRN", "MLG", "SRP", "VSN"]
          : ["VSN", "SRP", "MLG", "KRN", "NDL"];

      // Generate scheduled points along corridor
      const scheduledPoints: TrajectoryPoint[] = [];
      const projectedPoints: TrajectoryPoint[] = [];

      let currentSchedTime = schedDep;
      let currentProjTime = schedDep + delay;

      routeStationIds.forEach((stId, idx) => {
        const km = STATION_KMS[stId] ?? (dir === "UP" ? idx * 15 : 60 - idx * 15);

        if (idx === 0) {
          // Origin departure
          scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId });
          projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId });
        } else {
          const prevStId = routeStationIds[idx - 1];
          // Section transit time
          let nominalRun = 12;
          if (
            (prevStId === "NDL" && stId === "KRN") ||
            (prevStId === "KRN" && stId === "NDL")
          ) {
            nominalRun = 12;
          } else if (
            (prevStId === "KRN" && stId === "MLG") ||
            (prevStId === "MLG" && stId === "KRN")
          ) {
            nominalRun = 10;
          } else if (
            (prevStId === "MLG" && stId === "SRP") ||
            (prevStId === "SRP" && stId === "MLG")
          ) {
            nominalRun = 14;
          } else if (
            (prevStId === "SRP" && stId === "VSN") ||
            (prevStId === "VSN" && stId === "SRP")
          ) {
            nominalRun = 9;
          }

          const legTime = Math.round(nominalRun * speedFactor);
          currentSchedTime += legTime;
          currentProjTime += legTime;

          // Arrival at station
          scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId });
          projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId });

          // Dwell if not final destination
          if (idx < routeStationIds.length - 1) {
            const dwell = train.train_type === "EXPRESS" ? 1 : 2;
            currentSchedTime += dwell;
            currentProjTime += dwell;
            scheduledPoints.push({ timeMin: currentSchedTime, km, stationId: stId, isDwell: true });
            projectedPoints.push({ timeMin: currentProjTime, km, stationId: stId, isDwell: true });
          }
        }
      });

      // Calculate current km based on status
      let currentKm = 0;
      if (train.station_id) {
        currentKm = STATION_KMS[train.station_id] ?? (dir === "UP" ? 0 : 60);
      } else if (train.block_id) {
        if (train.block_id.startsWith("B1")) currentKm = 7.0;
        else if (train.block_id.startsWith("B2")) currentKm = 23.0;
        else if (train.block_id.startsWith("B3")) currentKm = 40.0;
        else if (train.block_id.startsWith("B4")) currentKm = 54.0;
      } else {
        currentKm = dir === "UP" ? 0 : 60;
      }

      return {
        train,
        color: baseColor,
        direction: dir,
        scheduledPoints,
        projectedPoints,
        delayMin: delay,
        currentKm,
      };
    });
  }, [trains]);

  // Filter trajectories
  const filteredTrajectories = useMemo(() => {
    return trajectories.filter((t) => {
      if (directionFilter === "ALL") return true;
      return t.direction === directionFilter;
    });
  }, [trajectories, directionFilter]);

  // Generate Time Grid Ticks (every 15 min, major every 60 min)
  const timeTicks = useMemo(() => {
    const ticks: { min: number; label: string; isMajor: boolean }[] = [];
    const step = 15;
    for (let t = timeStart; t <= timeEnd; t += step) {
      ticks.push({
        min: t,
        label: formatMinutesToTime(t),
        isMajor: t % 60 === 0,
      });
    }
    return ticks;
  }, [timeStart, timeEnd]);

  // Current simulation time X coordinate
  const currentSimX = timeToX(simTimeMin);
  const isSimTimeVisible = currentSimX >= margin.left && currentSimX <= width - margin.right;

  // Single line section ranges (for bottleneck shading)
  const singleLineSections = [
    { name: "S1 (NDL–KRN)", kmStart: 0.0, kmEnd: 14.0 },
    { name: "S3 (MLG–SRP)", kmStart: 32.0, kmEnd: 48.0 },
  ];

  return (
    <div className="time-distance-graph-card stack" style={{ gap: "16px" }}>
      {/* Controls Bar */}
      <div
        className="time-distance-controls flex-row justify-between items-center flex-wrap gap-3"
        style={{
          background: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          border: "1px solid #E2E8F0",
        }}
      >
        {/* Left: Direction Filter */}
        <div className="flex-row items-center gap-2">
          <span className="small text-muted" style={{ fontWeight: 600 }}>
            Direction:
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
        </div>

        {/* Center: Time Window Duration */}
        <div className="flex-row items-center gap-2">
          <span className="small text-muted" style={{ fontWeight: 600 }}>
            Time Window:
          </span>
          <div className="button-group" role="group" aria-label="Time window">
            <button
              type="button"
              className={`button button-small ${windowDuration === 120 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(120)}
            >
              2 Hours
            </button>
            <button
              type="button"
              className={`button button-small ${windowDuration === 180 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(180)}
            >
              3 Hours
            </button>
            <button
              type="button"
              className={`button button-small ${windowDuration === 360 ? "button-primary" : "button-ghost"}`}
              onClick={() => setWindowDuration(360)}
            >
              6 Hours
            </button>
          </div>
        </div>

        {/* Right: Legend & View Toggle */}
        <div className="flex-row items-center gap-3">
          <div className="flex-row items-center gap-2 small text-muted">
            <span style={{ display: "inline-block", width: "16px", height: "2px", background: "#94A3B8" }} />
            <span>Scheduled</span>
            <span style={{ display: "inline-block", width: "16px", height: "3px", background: "#2563EB" }} />
            <span>Actual</span>
            <span
              style={{
                display: "inline-block",
                width: "16px",
                height: "3px",
                borderTop: "3px dashed #2563EB",
              }}
            />
            <span>Projected</span>
          </div>

          <button
            type="button"
            className="button button-small button-ghost"
            onClick={() => setShowTable(!showTable)}
          >
            {showTable ? "View Graph Chart" : "View Accessible Table"}
          </button>
        </div>
      </div>

      {/* Accessible Table View fallback */}
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
                    <span className="mono small text-muted d-block">{train.id}</span>
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
            border: "1px solid #E2E8F0",
            borderRadius: "8px",
            boxShadow: "inset 0 1px 3px rgba(0,0,0,0.02)",
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

              // Generate SVG path strings
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
              const projectedPathD = makePath(projectedPoints);

              return (
                <g
                  key={`trajectory-${train.id}`}
                  className="train-trajectory-group"
                  style={{ cursor: "pointer" }}
                  onClick={() => onSelectTrain && onSelectTrain(train.id)}
                  onMouseEnter={(e) => {
                    setHoveredTrain(train);
                    const rect = e.currentTarget.getBoundingClientRect();
                    setHoverPos({ x: rect.left, y: rect.top });
                  }}
                  onMouseLeave={() => setHoveredTrain(null)}
                >
                  {/* Scheduled Line (faint baseline) */}
                  <path
                    d={scheduledPathD}
                    fill="none"
                    stroke="#94A3B8"
                    strokeWidth={1.5}
                    strokeOpacity={0.6}
                  />

                  {/* Projected / Actual Line */}
                  <path
                    d={projectedPathD}
                    fill="none"
                    stroke={isSelected ? "#EF4444" : isHovered ? "#2563EB" : color}
                    strokeWidth={isSelected ? 4 : isHovered ? 3.5 : 2.5}
                    strokeDasharray={train.projected_delay_min > 0 ? "6 3" : undefined}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Train Label near middle */}
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
                ? kmToY(STATION_KMS[c.location.station_id] ?? 30)
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
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
