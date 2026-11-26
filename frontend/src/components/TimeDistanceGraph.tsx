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
  onRefresh?: () => void;
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
  SUPERFAST: 0.8,
  EXPRESS: 0.85,
  PASSENGER: 1.0,
  MEMU: 1.0,
  FREIGHT: 1.25,
};

const TRAIN_COLORS: Record<string, string> = {
  SUPERFAST: "#F87171", // Luminous Red / Superfast
  EXPRESS: "#38BDF8", // Luminous Cyan / Mail & Express
  PASSENGER: "#34D399", // Luminous Emerald / Passenger
  MEMU: "#FBBF24", // Luminous Amber / Suburban MEMU
  FREIGHT: "#C084FC", // Luminous Violet / Heavy Freight
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
  onRefresh,
}: TimeDistanceGraphProps) {
  // Movement & Train Filters
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "UP" | "DOWN">("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [stationFilter, setStationFilter] = useState<string>("ALL");
  const [trainSearch, setTrainSearch] = useState<string>("");

  // Viewport & Pan Controls
  const [windowDuration, setWindowDuration] = useState<number>(180); // 3 hours window default
  const [timePanOffset, setTimePanOffset] = useState<number>(0); // manual pan in minutes

  // Trajectory Visibility Toggles
  const [showScheduled, setShowScheduled] = useState<boolean>(true);
  const [showObserved, setShowObserved] = useState<boolean>(true);
  const [showForecast, setShowForecast] = useState<boolean>(true);

  // Operational Overlays Toggles (Clean default display)
  const [showConflicts, setShowConflicts] = useState<boolean>(true);
  const [showCrossings, setShowCrossings] = useState<boolean>(false);
  const [showSingleLine, setShowSingleLine] = useState<boolean>(true);
  const [showRestrictions, setShowRestrictions] = useState<boolean>(false);
  const [showDwell, setShowDwell] = useState<boolean>(true);
  const [showBottlenecks, setShowBottlenecks] = useState<boolean>(false);

  // UI state
  const [showOverlaysPanel, setShowOverlaysPanel] = useState<boolean>(false);
  const [hoveredTrain, setHoveredTrain] = useState<Train | null>(null);
  const [showTable, setShowTable] = useState(false);

  // Reset Filters to pristine default
  const resetFilters = () => {
    setDirectionFilter("ALL");
    setCategoryFilter("ALL");
    setStationFilter("ALL");
    setTrainSearch("");
    setWindowDuration(180);
    setTimePanOffset(0);
    setShowScheduled(true);
    setShowObserved(true);
    setShowForecast(true);
    setShowConflicts(true);
    setShowCrossings(true);
    setShowSingleLine(true);
    setShowRestrictions(true);
    setShowDwell(true);
    setShowBottlenecks(true);
  };

  // SVG layout dimensions
  const width = 1000;
  const margin = { top: 48, right: 60, bottom: 50, left: 140 };
  const graphWidth = width - margin.left - margin.right;
  const graphHeight = height - margin.top - margin.bottom;

  // Dynamic Station Chainage & Corridor Geometry Calculation
  const { stationKms, maxKm, singleLineSections } = useMemo(() => {
    const kms: Record<string, number> = {};
    const singleLines: { name: string; kmStart: number; kmEnd: number; sectionId: string }[] = [];

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
        const sec = sections.find(
          (s) =>
            (s.from_station === prev.id && s.to_station === st.id) ||
            (s.to_station === prev.id && s.from_station === st.id)
        );
        const dist = (sec as any)?.distance_km ?? Math.max(10.0, (st.x - prev.x) * 0.6);
        runningKm += dist;
        kms[st.id] = runningKm;

        if (sec && sec.mode === "SINGLE") {
          singleLines.push({
            name: `${sec.id} (${prev.code || prev.id}–${st.code || st.id})`,
            kmStart: kms[prev.id],
            kmEnd: runningKm,
            sectionId: sec.id,
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

      const sortedStationIds = [...stations].sort((a, b) => a.x - b.x).map((s) => s.id);
      const defaultRoute = dir === "UP" ? sortedStationIds : [...sortedStationIds].reverse();
      const routeStationIds = train.route && train.route.length > 0 ? train.route : defaultRoute;

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

  // Unique supported categories
  const supportedCategories = useMemo(() => {
    const set = new Set(trains.map((t) => t.train_type));
    return Array.from(set);
  }, [trains]);

  // Filter trajectories by direction, category, station, and train search
  const filteredTrajectories = useMemo(() => {
    return trajectories.filter((t) => {
      if (directionFilter !== "ALL" && t.direction !== directionFilter) return false;
      if (categoryFilter !== "ALL" && t.train.train_type !== categoryFilter) return false;
      if (stationFilter !== "ALL") {
        const stopsAtStation =
          t.train.station_id === stationFilter ||
          (t.train.route && t.train.route.includes(stationFilter)) ||
          t.scheduledPoints.some((p) => p.stationId === stationFilter);
        if (!stopsAtStation) return false;
      }
      if (trainSearch.trim()) {
        const q = trainSearch.toLowerCase();
        const match =
          t.train.id.toLowerCase().includes(q) ||
          t.train.name.toLowerCase().includes(q) ||
          t.train.origin.toLowerCase().includes(q) ||
          t.train.destination.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    });
  }, [trajectories, directionFilter, categoryFilter, stationFilter, trainSearch]);

  // Generate Crossing Points between UP and DOWN train trajectories
  const crossingPoints = useMemo(() => {
    if (!showCrossings) return [];
    const points: { x: number; y: number; trainUp: string; trainDown: string; km: number; timeMin: number }[] = [];
    const upTrains = filteredTrajectories.filter((t) => t.direction === "UP");
    const downTrains = filteredTrajectories.filter((t) => t.direction === "DOWN");

    upTrains.forEach((up) => {
      downTrains.forEach((dn) => {
        // Approximate crossing point where time and km intersect
        for (let i = 0; i < up.projectedPoints.length - 1; i++) {
          const p1 = up.projectedPoints[i];
          const p2 = up.projectedPoints[i + 1];
          for (let j = 0; j < dn.projectedPoints.length - 1; j++) {
            const q1 = dn.projectedPoints[j];
            const q2 = dn.projectedPoints[j + 1];

            // Check if time ranges overlap
            const tMinOverlap = Math.max(p1.timeMin, q1.timeMin);
            const tMaxOverlap = Math.min(p2.timeMin, q2.timeMin);
            if (tMinOverlap <= tMaxOverlap) {
              const midTime = (tMinOverlap + tMaxOverlap) / 2;
              const midKm = (p1.km + q1.km) / 2;
              if (midTime >= timeStart && midTime <= timeEnd) {
                points.push({
                  x: timeToX(midTime),
                  y: kmToY(midKm),
                  trainUp: up.train.id,
                  trainDown: dn.train.id,
                  km: midKm,
                  timeMin: midTime,
                });
              }
            }
          }
        }
      });
    });
    return points.slice(0, 8); // Top crossing points to keep display crisp
  }, [filteredTrajectories, showCrossings, timeStart, timeEnd]);

  // Generate Time Grid Ticks
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

  // Active overlay count for toggle badge
  const activeOverlayCount = [
    showConflicts,
    showCrossings,
    showSingleLine,
    showRestrictions,
    showDwell,
    showBottlenecks,
  ].filter(Boolean).length;

  return (
    <div className="time-distance-graph-card stack" style={{ gap: "14px" }}>
      {/* Control Workspace Header & Comprehensive Redesigned Toolbar */}
      <div className="graph-toolbar">
        {/* Row 1: Primary Controls (Direction, Category, Station, Search, Window, Actions) */}
        <div className="flex-row justify-between items-center flex-wrap gap-2">
          {/* Movement Direction Filter */}
          <div className="flex-row items-center gap-2 flex-wrap">
            <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase" }}>
              Movement:
            </span>
            <div className="button-group" role="group" aria-label="Direction filter">
              <button
                type="button"
                className={`graph-btn button-small ${directionFilter === "ALL" ? "button-primary active" : "button-ghost"}`}
                onClick={() => setDirectionFilter("ALL")}
              >
                All Movements ({trajectories.length})
              </button>
              <button
                type="button"
                className={`graph-btn button-small ${directionFilter === "UP" ? "button-primary active" : "button-ghost"}`}
                onClick={() => setDirectionFilter("UP")}
              >
                UP (NDL → VSN)
              </button>
              <button
                type="button"
                className={`graph-btn button-small ${directionFilter === "DOWN" ? "button-primary active" : "button-ghost"}`}
                onClick={() => setDirectionFilter("DOWN")}
              >
                DOWN (VSN → NDL)
              </button>
            </div>
          </div>

          {/* Train Category Filter */}
          <div className="flex-row items-center gap-2">
            <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "#94A3B8" }}>
              Class:
            </span>
            <select
              className="graph-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              aria-label="Filter by train category"
            >
              <option value="ALL">All Categories</option>
              {supportedCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
              {!supportedCategories.includes("EXPRESS") && <option value="EXPRESS">Express / Mail</option>}
              {!supportedCategories.includes("PASSENGER") && <option value="PASSENGER">Ordinary Passenger</option>}
              {!supportedCategories.includes("MEMU") && <option value="MEMU">Suburban MEMU</option>}
              {!supportedCategories.includes("FREIGHT") && <option value="FREIGHT">Freight Goods</option>}
            </select>
          </div>

          {/* Station Filter */}
          <div className="flex-row items-center gap-2">
            <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "#94A3B8" }}>
              Station:
            </span>
            <select
              className="graph-select"
              value={stationFilter}
              onChange={(e) => setStationFilter(e.target.value)}
              aria-label="Filter by station"
            >
              <option value="ALL">All Stations</option>
              {stations.map((st) => (
                <option key={st.id} value={st.id}>
                  {st.code || st.id} — {st.name}
                </option>
              ))}
            </select>
          </div>

          {/* Train Search Input */}
          <div className="flex-row items-center gap-2">
            <input
              type="text"
              className="graph-input"
              style={{ width: "140px" }}
              placeholder="Search train..."
              value={trainSearch}
              onChange={(e) => setTrainSearch(e.target.value)}
              aria-label="Search specific train"
            />
          </div>

          {/* Time Panning Controls */}
          <div className="flex-row items-center gap-1">
            <div className="button-group" role="group" aria-label="Time pan controls">
              <button
                type="button"
                className="graph-btn button-small button-ghost"
                onClick={() => setTimePanOffset((prev) => prev - 30)}
                title="Pan backward 30 minutes"
              >
                ◀ -30m
              </button>
              <button
                type="button"
                className="graph-btn button-small button-ghost"
                onClick={() => setTimePanOffset(0)}
                title="Reset view to current simulation time"
              >
                Center Now ⏱
              </button>
              <button
                type="button"
                className="graph-btn button-small button-ghost"
                onClick={() => setTimePanOffset((prev) => prev + 30)}
                title="Pan forward 30 minutes"
              >
                +30m ▶
              </button>
            </div>
          </div>

          {/* Time Window Buttons */}
          <div className="button-group" role="group" aria-label="Time window">
            {[
              { label: "1h", dur: 60 },
              { label: "3h", dur: 180 },
              { label: "6h", dur: 360 },
              { label: "12h", dur: 720 },
            ].map(({ label, dur }) => (
              <button
                key={label}
                type="button"
                className={`graph-btn button-small ${windowDuration === dur ? "button-primary active" : "button-ghost"}`}
                onClick={() => setWindowDuration(dur)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Reset, Table Toggle, and Overlays Toggle */}
          <div className="flex-row items-center gap-2">
            <button
              type="button"
              className="graph-btn graph-btn-reset button-small"
              onClick={resetFilters}
              title="Reset all filters to default"
            >
              ↺ Reset
            </button>
            {onRefresh && (
              <button
                type="button"
                className="graph-btn button-small button-ghost"
                onClick={onRefresh}
                title="Refresh Telemetry"
              >
                ↻ Refresh
              </button>
            )}
            <button
              type="button"
              className="graph-btn button-small button-ghost"
              style={{ color: "#F59E0B" }}
              onClick={() => setShowTable(!showTable)}
            >
              {showTable ? "View Graph Chart" : "View Accessible Table"}
            </button>
            <button
              type="button"
              className={`graph-btn button-small ${showOverlaysPanel ? "button-primary active" : "button-ghost"}`}
              onClick={() => setShowOverlaysPanel(!showOverlaysPanel)}
              title="Toggle operational overlays panel"
            >
              Overlays ({activeOverlayCount}) {showOverlaysPanel ? "▲" : "▼"}
            </button>
          </div>
        </div>

        {/* Row 2: Expandable Trajectory Visibility & Operational Overlays Toolbar */}
        {showOverlaysPanel && (
          <div
            className="flex-row justify-between items-center flex-wrap gap-4"
            style={{
              paddingTop: "10px",
              borderTop: "1px solid #1E293B",
              animation: "fadeIn 0.2s ease-in-out",
            }}
          >
            {/* Trajectory Visibility */}
            <div className="flex-row items-center gap-3">
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase" }}>
                Trajectories:
              </span>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showScheduled}
                  onChange={(e) => setShowScheduled(e.target.checked)}
                />
                <span>Scheduled (Timetable)</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showObserved}
                  onChange={(e) => setShowObserved(e.target.checked)}
                />
                <span>Observed (Past)</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showForecast}
                  onChange={(e) => setShowForecast(e.target.checked)}
                />
                <span>Projected (Forecast)</span>
              </label>
            </div>

            {/* Operational Overlays */}
            <div className="flex-row items-center gap-3 flex-wrap">
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "#F59E0B", textTransform: "uppercase" }}>
                Overlays:
              </span>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showConflicts}
                  onChange={(e) => setShowConflicts(e.target.checked)}
                />
                <span>Conflicts ({conflicts.length})</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showCrossings}
                  onChange={(e) => setShowCrossings(e.target.checked)}
                />
                <span>Crossing Points</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showSingleLine}
                  onChange={(e) => setShowSingleLine(e.target.checked)}
                />
                <span>Single-Line Sections</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showRestrictions}
                  onChange={(e) => setShowRestrictions(e.target.checked)}
                />
                <span>Speed Restrictions (TSR/PSR)</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showDwell}
                  onChange={(e) => setShowDwell(e.target.checked)}
                />
                <span>Station Dwell</span>
              </label>
              <label className="graph-checkbox-label">
                <input
                  type="checkbox"
                  checked={showBottlenecks}
                  onChange={(e) => setShowBottlenecks(e.target.checked)}
                />
                <span>Bottlenecks</span>
              </label>
            </div>
          </div>
        )}
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
              {filteredTrajectories.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-muted text-center" style={{ padding: "24px" }}>
                    No train trajectories match the selected filters.
                  </td>
                </tr>
              ) : (
                filteredTrajectories.map(({ train, delayMin }) => (
                  <tr key={train.id} style={selectedTrainId === train.id ? { background: "var(--panel-strong)" } : undefined}>
                    <td>
                      <strong>{train.name}</strong>
                      <span className="mono small text-muted d-block">#{train.id}</span>
                    </td>
                    <td>
                      <Badge tone="muted">{train.train_type}</Badge>
                    </td>
                    <td>
                      <Badge tone={train.direction === "UP" ? "accent" : "muted"}>{train.direction}</Badge>
                    </td>
                    <td>{train.origin}</td>
                    <td>{train.destination}</td>
                    <td className="mono">{train.scheduled_departure || "—"}</td>
                    <td>{train.status}</td>
                    <td>
                      <span className={delayMin > 0 ? "text-bad" : "text-good"} style={{ fontWeight: 600 }}>
                        {delayMin > 0 ? `+${delayMin} min` : "On time"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
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
            background: "#080C14",
            border: "1px solid #1E293B",
            borderRadius: "8px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
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

            {/* Pattern for Engineering Restrictions (Hatched Yellow Caution) */}
            <defs>
              <pattern id="restrictionPattern" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                <line x1="0" y1="0" x2="0" y2="10" stroke="#F59E0B" strokeWidth="2.5" opacity="0.6" />
              </pattern>
            </defs>

            {/* Shaded Background for Single-Line Sections */}
            {showSingleLine &&
              singleLineSections.map((sec) => {
                const y1 = kmToY(sec.kmStart);
                const y2 = kmToY(sec.kmEnd);
                return (
                  <g key={sec.name}>
                    <rect
                      x={margin.left}
                      y={y1}
                      width={graphWidth}
                      height={y2 - y1}
                      fill="rgba(245, 158, 11, 0.12)"
                    />
                    <text
                      x={width - margin.right - 8}
                      y={y1 + 16}
                      textAnchor="end"
                      fill="#FBBF24"
                      fontSize={10}
                      fontWeight={700}
                      letterSpacing="0.05em"
                    >
                      SINGLE LINE: {sec.name}
                    </text>
                  </g>
                );
              })}

            {/* Engineering Restrictions Overlay (TSR / PSR Caution Bands) */}
            {showRestrictions && (
              <g className="engineering-restrictions-overlay">
                <rect
                  x={margin.left}
                  y={kmToY(12)}
                  width={graphWidth}
                  height={kmToY(16) - kmToY(12)}
                  fill="url(#restrictionPattern)"
                  opacity={0.4}
                />
                <text
                  x={margin.left + 8}
                  y={kmToY(14) + 4}
                  fill="#FBBF24"
                  fontSize={9}
                  fontWeight={700}
                >
                  🚧 TSR 30 km/h (Track renewal km 12-16)
                </text>
              </g>
            )}

            {/* Bottlenecks Overlay */}
            {showBottlenecks && (
              <g className="bottlenecks-overlay">
                <rect
                  x={margin.left}
                  y={kmToY(48)}
                  width={graphWidth}
                  height={kmToY(52) - kmToY(48)}
                  fill="rgba(239, 68, 68, 0.15)"
                />
                <text
                  x={margin.left + 8}
                  y={kmToY(50) + 4}
                  fill="#F87171"
                  fontSize={9}
                  fontWeight={700}
                >
                  ⚠ BOTTLENECK: Malgaon Junction Junction Layout
                </text>
              </g>
            )}

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
                    stroke={tick.isMajor ? "#263852" : "#142136"}
                    strokeWidth={tick.isMajor ? 1.5 : 1}
                    strokeDasharray={tick.isMajor ? undefined : "3 3"}
                  />
                  <text
                    x={x}
                    y={height - margin.bottom + 20}
                    textAnchor="middle"
                    fontSize={11}
                    fontFamily="monospace"
                    fill={tick.isMajor ? "#E2E8F0" : "#94A3B8"}
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
                    fill={tick.isMajor ? "#E2E8F0" : "#94A3B8"}
                    fontWeight={tick.isMajor ? 700 : 500}
                  >
                    {tick.label}
                  </text>
                </g>
              );
            })}

            {/* Horizontal Station Guideline Rows */}
            {stationChainages.map((station) => {
              const isStationFocused = stationFilter === station.id;
              return (
                <g key={`station-line-${station.id}`}>
                  <line
                    x1={margin.left}
                    y1={station.y}
                    x2={width - margin.right}
                    y2={station.y}
                    stroke={isStationFocused ? "#F59E0B" : station.isJunction ? "#2A4365" : "#1E293B"}
                    strokeWidth={isStationFocused ? 3 : station.isJunction ? 2 : 1.25}
                    strokeDasharray={isStationFocused ? undefined : station.isJunction ? undefined : "4 2"}
                  />

                  {/* Left Station Label */}
                  <text
                    x={margin.left - 12}
                    y={station.y + 4}
                    textAnchor="end"
                    fontSize={12}
                    fontWeight={isStationFocused ? 800 : station.isJunction ? 700 : 600}
                    fill={isStationFocused ? "#F59E0B" : station.isJunction ? "#F8FAFC" : "#CBD5E1"}
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
                    fontWeight={isStationFocused ? 700 : 600}
                    fill={isStationFocused ? "#F59E0B" : "#94A3B8"}
                  >
                    {station.code}
                  </text>
                </g>
              );
            })}

            {/* Trajectories */}
            {filteredTrajectories.map(({ train, color, scheduledPoints, projectedPoints }) => {
              const isSelected = selectedTrainId === train.id;
              const isHovered = hoveredTrain?.id === train.id;

              // Split projected points into past (observed) and future (forecast)
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
                      stroke="#475569"
                      strokeWidth={1.5}
                      strokeOpacity={0.5}
                    />
                  )}

                  {/* Observed Past Movement (solid line) */}
                  {showObserved && observedPathD && (
                    <path
                      d={observedPathD}
                      fill="none"
                      stroke={isSelected ? "#EF4444" : isHovered ? "#38BDF8" : color}
                      strokeWidth={isSelected ? 4 : isHovered ? 3.5 : 2.5}
                      strokeLinecap="round"
                    />
                  )}

                  {/* Forecast / Projected Movement (dashed line) */}
                  {showForecast && forecastPathD && (
                    <path
                      d={forecastPathD}
                      fill="none"
                      stroke={isSelected ? "#EF4444" : isHovered ? "#38BDF8" : color}
                      strokeWidth={isSelected ? 3.5 : isHovered ? 3 : 2}
                      strokeDasharray="6 3"
                      strokeLinecap="round"
                    />
                  )}

                  {/* Station Dwell Horizontal Bars */}
                  {showDwell &&
                    projectedPoints
                      .filter((p) => p.isDwell)
                      .map((p, pIdx) => {
                        const x = timeToX(p.timeMin);
                        const y = kmToY(p.km);
                        return (
                          <line
                            key={`dwell-${train.id}-${pIdx}`}
                            x1={x - 6}
                            y1={y}
                            x2={x}
                            y2={y}
                            stroke={color}
                            strokeWidth={4}
                            strokeLinecap="round"
                          />
                        );
                      })}

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

            {/* Crossing Points Overlay */}
            {showCrossings &&
              crossingPoints.map((pt, idx) => (
                <g key={`crossing-pt-${idx}`} transform={`translate(${pt.x}, ${pt.y})`}>
                  <polygon
                    points="0,-6 6,0 0,6 -6,0"
                    fill="#10B981"
                    stroke="#34D399"
                    strokeWidth={1.5}
                  />
                  <text
                    x={8}
                    y={3}
                    fontSize={9}
                    fontWeight={700}
                    fill="#34D399"
                  >
                    ⇄ {pt.trainUp} ✕ {pt.trainDown}
                  </text>
                </g>
              ))}

            {/* Active Conflicts Markers */}
            {showConflicts &&
              conflicts.map((c) => {
                const startX = timeToX(c.start_min);
                const conflictY = c.location.station_id
                  ? kmToY(stationKms[c.location.station_id] ?? 30)
                  : kmToY(30);

                if (startX < margin.left || startX > width - margin.right) return null;

                return (
                  <g key={`conflict-marker-${c.id}`} transform={`translate(${startX}, ${conflictY})`}>
                    <circle r={9} fill="#EF4444" opacity={0.3} />
                    <circle r={5} fill="#EF4444" />
                    <text
                      x={8}
                      y={-4}
                      fontSize={10}
                      fontWeight={700}
                      fill="#F87171"
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
                  stroke="#EF4444"
                  strokeWidth={2}
                  strokeDasharray="4 2"
                />
                <rect
                  x={currentSimX - 44}
                  y={margin.top - 32}
                  width={88}
                  height={20}
                  fill="#EF4444"
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
              fill="#94A3B8"
            >
              ← Chainage / Stations (km)
            </text>
            <text
              x={width - margin.right}
              y={height - margin.bottom + 40}
              textAnchor="end"
              fontSize={11}
              fontWeight={600}
              fill="#94A3B8"
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
                background: "#0F1726",
                color: "#F8FAFC",
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid #263852",
                boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                pointerEvents: "none",
                maxWidth: "280px",
                fontSize: "0.85rem",
                zIndex: 10,
              }}
            >
              <div className="flex-row justify-between items-center gap-2 mb-1">
                <strong style={{ fontSize: "0.95rem", color: "#38BDF8" }}>
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
                      color: hoveredTrain.projected_delay_min > 0 ? "#F87171" : "#34D399",
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
