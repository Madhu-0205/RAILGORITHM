import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { AdjacentStationAwareness } from "../components/AdjacentStationAwareness";
import { StationYardDiagram } from "../components/StationYardDiagram";
import { Badge, ErrorBanner, KpiCard, Panel, StatusBadge } from "../components/ui";
import type {
  StationMasterAdjacentStations,
  StationMasterAlerts,
  StationMasterLayout,
  StationMasterMovementBoard,
  StationMasterOverview,
} from "../types";

export function StationMasterWorkspace() {
  const { user } = useAuth();
  const [simId, setSimId] = useState<string | null>(null);
  const [stationId, setStationId] = useState<string>(user?.station_id || "NDL");
  const [overview, setOverview] = useState<StationMasterOverview | null>(null);
  const [layout, setLayout] = useState<StationMasterLayout | null>(null);
  const [movementBoard, setMovementBoard] = useState<StationMasterMovementBoard | null>(null);
  const [adjacent, setAdjacent] = useState<StationMasterAdjacentStations | null>(null);
  const [alerts, setAlerts] = useState<StationMasterAlerts | null>(null);
  const [activeBoardTab, setActiveBoardTab] = useState<"arriving" | "departing" | "through" | "history">("arriving");
  const [trainSearch, setTrainSearch] = useState<string>("");
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "UP" | "DOWN">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Available stations for switcher (based on user jurisdiction)
  const allowedStations: string[] =
    user?.assigned_stations && user.assigned_stations.length > 0
      ? user.assigned_stations
      : [user?.station_id || "NDL"];

  // 1. Fetch current simulation
  useEffect(() => {
    let mounted = true;
    api
      .simulations()
      .then((res) => {
        if (!mounted) return;
        if (res.simulations.length > 0) {
          setSimId(res.simulations[0].id);
        } else {
          setError("No active simulation found");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || "Failed to load simulation");
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // 2. Fetch Station Master data when simId or stationId changes
  useEffect(() => {
    if (!simId) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.stationMasterOverview(simId, stationId),
      api.stationMasterLayout(simId, stationId),
      api.stationMasterMovementBoard(simId, stationId),
      api.stationMasterAdjacentStations(simId, stationId),
      api.stationMasterAlerts(simId, stationId),
    ])
      .then(([ov, lay, mb, adj, al]) => {
        if (!mounted) return;
        setOverview(ov);
        setLayout(lay);
        setMovementBoard(mb);
        setAdjacent(adj);
        setAlerts(al);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || "Failed to load station master operational workspace");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [simId, stationId]);

  if (loading && !overview) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>
        <h3>Loading Station Master Console...</h3>
        <p>Initializing simulated yard telemetry and block schematic state</p>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div style={{ padding: "32px" }}>
        <ErrorBanner message={`Failed to load Station Master console: ${error}`} />
      </div>
    );
  }

  return (
    <div className="station-master-workspace" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* 1. Header & Operating Banner */}
      <div
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
          padding: "18px 24px",
          borderRadius: "10px",
          border: "1px solid #334155",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "20px" }}>🚉</span>
            <h1 style={{ margin: 0, fontSize: "22px", color: "#f8fafc", fontWeight: 700 }}>
              {overview?.station_name} ({overview?.station_code})
            </h1>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 700,
                padding: "4px 10px",
                borderRadius: "4px",
                background:
                  overview?.operational_status === "NORMAL"
                    ? "#065f46"
                    : overview?.operational_status === "CONGESTED"
                    ? "#854d0e"
                    : overview?.operational_status === "REGULATED"
                    ? "#1e40af"
                    : "#7f1d1d",
                color: "#ffffff",
              }}
            >
              YARD STATUS: {overview?.operational_status}
            </span>
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#94a3b8" }}>
            Southern Railway Division | Absolute Block Territory | Designated Authority:{" "}
            <strong>{user?.display_name || user?.username}</strong>
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Station Switcher (Only if multi-station access or admin) */}
          {allowedStations.length > 1 && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label htmlFor="station-select" style={{ fontSize: "12px", color: "#cbd5e1", fontWeight: 600 }}>
                Station Jurisdiction:
              </label>
              <select
                id="station-select"
                value={stationId}
                onChange={(e) => setStationId(e.target.value)}
                style={{
                  background: "#0f172a",
                  color: "#f8fafc",
                  border: "1px solid #475569",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                {allowedStations.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div style={{ textAlign: "right", borderLeft: "1px solid #334155", paddingLeft: "16px" }}>
            <div style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>Simulation Clock</div>
            <div style={{ fontSize: "18px", color: "#38bdf8", fontWeight: 700 }}>
              {overview?.simulation_time || "10:00"} IST
            </div>
            <div style={{ fontSize: "11px", color: "#10b981" }}>
              ● Feed: {overview?.data_quality.feed_status || "NOMINAL"} ({overview?.data_quality.freshness_seconds}s)
            </div>
          </div>
        </div>
      </div>

      {/* 2. Key Operational Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
        <KpiCard
          label="Arriving Next 30m"
          value={overview?.summary_counts.arriving_next_30m ?? 0}
          unit="trains"
          tone="info"
          hint="Within yard approach blocks"
        />
        <KpiCard
          label="Departing Next 30m"
          value={overview?.summary_counts.departing_next_30m ?? 0}
          unit="trains"
          tone="neutral"
          hint="From berthing platforms"
        />
        <KpiCard
          label="Through / Running"
          value={overview?.summary_counts.through_next_30m ?? 0}
          unit="trains"
          tone="neutral"
          hint="Passing on Main Line"
        />
        <KpiCard
          label="Currently Berthed"
          value={overview?.summary_counts.currently_at_station ?? 0}
          unit="trains"
          tone={(overview?.summary_counts.currently_at_station ?? 0) >= (overview?.platform_summary.total_platforms ?? 3) ? "watch" : "good"}
          hint="Active on station tracks"
        />
        <KpiCard
          label="Schedule Adherence"
          value={
            overview?.adherence.schedule_adherence_pct !== null && overview?.adherence.schedule_adherence_pct !== undefined
              ? `${overview.adherence.schedule_adherence_pct}%`
              : "NO DATA"
          }
          tone={
            overview?.adherence.adherence_status === "NO_DATA"
              ? "neutral"
              : (overview?.adherence.schedule_adherence_pct ?? 0) >= 80
              ? "good"
              : "bad"
          }
          hint={overview?.adherence.explanation}
        />
        <KpiCard
          label="Platforms Available"
          value={`${overview?.platform_summary.available ?? 0} / ${overview?.platform_summary.total_platforms ?? 0}`}
          unit="clear"
          tone={(overview?.platform_summary.available ?? 0) > 0 ? "good" : "bad"}
          hint={`Occupancy: ${overview?.platform_summary.occupancy_pct ?? 0}%`}
        />
      </div>

      {/* 3. Physical Station Yard Layout */}
      {layout && (
        <StationYardDiagram
          stationName={layout.station_name}
          stationCode={layout.station_code}
          tracks={layout.tracks}
          throatStatus={layout.throat_status}
        />
      )}

      {/* 4. Train Movement Board */}
      <Panel
        title={`Electronic Train Movement Board — ${overview?.station_name}`}
        subtitle="Operational timetable board with Indian Railways line clear communication states"
        actions={
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ display: "flex", gap: "4px" }}>
              <button
                type="button"
                onClick={() => setActiveBoardTab("arriving")}
                className={`button button-small ${activeBoardTab === "arriving" ? "button-primary" : "button-ghost"}`}
              >
                Arriving ({movementBoard?.arriving.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setActiveBoardTab("departing")}
                className={`button button-small ${activeBoardTab === "departing" ? "button-primary" : "button-ghost"}`}
              >
                Departing ({movementBoard?.departing.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setActiveBoardTab("through")}
                className={`button button-small ${activeBoardTab === "through" ? "button-primary" : "button-ghost"}`}
              >
                Through ({movementBoard?.through.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setActiveBoardTab("history")}
                className={`button button-small ${activeBoardTab === "history" ? "button-primary" : "button-ghost"}`}
              >
                History ({movementBoard?.history.length || 0})
              </button>
            </div>
            <div style={{ display: "flex", gap: "6px", alignItems: "center", marginLeft: "8px" }}>
              <select
                value={directionFilter}
                onChange={(e) => setDirectionFilter(e.target.value as "ALL" | "UP" | "DOWN")}
                style={{ padding: "4px 8px", fontSize: "11px", width: "auto" }}
                aria-label="Filter movement by direction"
              >
                <option value="ALL">Direction: All</option>
                <option value="UP">▲ UP Line</option>
                <option value="DOWN">▼ DOWN Line</option>
              </select>
              <input
                type="text"
                placeholder="Search train / PF..."
                value={trainSearch}
                onChange={(e) => setTrainSearch(e.target.value)}
                style={{ padding: "4px 8px", fontSize: "11px", width: "130px" }}
                aria-label="Search movement board"
              />
            </div>
          </div>
        }
      >
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Train / Id</th>
                <th>Type / Priority</th>
                <th>Origin ➔ Dest</th>
                <th>Scheduled</th>
                <th>Estimated</th>
                <th>Platform</th>
                <th>Punctuality / Delay</th>
                <th>Speed</th>
                <th>Block Line Clear</th>
              </tr>
            </thead>
            <tbody>
              {movementBoard && movementBoard[activeBoardTab]?.length > 0 ? (
                movementBoard[activeBoardTab]
                  .filter((t) => {
                    if (directionFilter !== "ALL" && t.direction !== directionFilter) return false;
                    if (trainSearch.trim()) {
                      const q = trainSearch.toLowerCase();
                      return (
                        t.train_name.toLowerCase().includes(q) ||
                        t.train_id.toLowerCase().includes(q) ||
                        (t.assigned_platform || "").toLowerCase().includes(q)
                      );
                    }
                    return true;
                  })
                  .map((train) => (
                    <tr key={train.train_id}>
                      <td style={{ fontWeight: 700 }}>
                        <span style={{ color: "#38BDF8" }}>{train.train_name}</span>
                        <div style={{ fontSize: "11px", color: "#94A3B8", fontFamily: "var(--mono)" }}>
                          #{train.train_id} ({train.direction === "UP" ? "▲ UP" : "▼ DOWN"})
                        </div>
                      </td>
                      <td>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: 700,
                            background: train.priority <= 2 ? "rgba(245, 158, 11, 0.2)" : "#142136",
                            color: train.priority <= 2 ? "#FBBF24" : "#CBD5E1",
                            border: `1px solid ${train.priority <= 2 ? "#D97706" : "#263852"}`,
                          }}
                        >
                          {train.train_type} (P{train.priority})
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "#CBD5E1" }}>
                        {train.origin} ➔ {train.destination}
                      </td>
                      <td style={{ fontFamily: "var(--mono)", color: "#94A3B8" }}>
                        {activeBoardTab === "departing" ? train.scheduled_departure || "—" : train.scheduled_arrival || "—"}
                      </td>
                      <td style={{ fontFamily: "var(--mono)", fontWeight: 700, color: train.delay_min > 5 ? "#EF4444" : "#10B981" }}>
                        {activeBoardTab === "departing" ? train.estimated_departure || "—" : train.estimated_arrival || "—"}
                      </td>
                      <td>
                        <span
                          style={{
                            fontFamily: "var(--mono)",
                            fontWeight: 700,
                            color: "#38BDF8",
                            background: "rgba(56, 189, 248, 0.15)",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            border: "1px solid #0284C7",
                          }}
                        >
                          {train.assigned_platform || "TBD"}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: 600,
                            fontFamily: "var(--mono)",
                            background: train.status === "ON_TIME" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.18)",
                            color: train.status === "ON_TIME" ? "#34D399" : "#F87171",
                            border: `1px solid ${train.status === "ON_TIME" ? "#059669" : "#DC2626"}`,
                          }}
                        >
                          {train.status === "ON_TIME" ? "● ON TIME" : `▲ +${train.delay_min}m LATE`}
                        </span>
                      </td>
                      <td style={{ fontFamily: "var(--mono)", color: "#94A3B8" }}>
                        {train.speed_kmph} km/h
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 600,
                            color: train.line_clear_status.includes("OCCUPIED") ? "#F87171" : "#A7F3D0",
                            background: train.line_clear_status.includes("OCCUPIED") ? "rgba(239, 68, 68, 0.12)" : "rgba(16, 185, 129, 0.12)",
                            padding: "2px 6px",
                            borderRadius: "3px",
                          }}
                        >
                          {train.line_clear_status.replace(/_/g, " ")}
                        </span>
                      </td>
                    </tr>
                  ))
              ) : (
                <tr>
                  <td colSpan={9} style={{ padding: "28px", textAlign: "center", color: "#64748B" }}>
                    No {activeBoardTab} trains scheduled in this operational window
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* 5. Adjacent Station Operational Awareness */}
      {adjacent && <AdjacentStationAwareness data={adjacent} />}

      {/* 6. Station Alerts & Advisory AI Recommendations */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        {/* Active Yard & Station Conflicts */}
        <Panel
          title="Station Interlocking Alerts & Conflicts"
          subtitle="Direct safety alerts affecting station yard and adjacent block entries"
          tone={alerts && alerts.active_conflicts.length > 0 ? "warning" : "default"}
        >
          {alerts && alerts.active_conflicts.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {alerts.active_conflicts.map((c, i) => (
                <div key={i} style={{ background: "#1e293b", padding: "12px", borderRadius: "6px", borderLeft: "4px solid #ef4444" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                    <strong style={{ color: "#f87171" }}>{c.type}</strong>
                    <span style={{ color: "#94a3b8" }}>Severity: {c.severity}</span>
                  </div>
                  <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#cbd5e1" }}>{c.description}</p>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "20px", color: "#10b981", fontSize: "13px" }}>
              ✓ All station platforms, lines, and adjacent block entries operating without conflicts
            </div>
          )}
        </Panel>

        {/* Station-Local AI Advisory Recommendations */}
        <Panel
          title="Station Master AI Advisory Proposals"
          subtitle="Validated decision-support recommendations for platform berthing and dispatch"
        >
          {alerts && alerts.pending_recommendations.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {alerts.pending_recommendations.map((rec) => (
                <div key={rec.id} style={{ background: "#1e293b", padding: "12px", borderRadius: "6px", border: "1px solid #334155" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "#38bdf8", fontSize: "14px" }}>{rec.label}</strong>
                    <span style={{ fontSize: "11px", color: "#10b981", background: "#065f46", padding: "2px 6px", borderRadius: "3px" }}>
                      Confidence: {Math.round(rec.confidence * 100)}%
                    </span>
                  </div>
                  <p style={{ margin: "6px 0", fontSize: "12px", color: "#cbd5e1" }}>{rec.explanation}</p>
                  <div style={{ display: "flex", gap: "8px", fontSize: "11px", color: "#94a3b8" }}>
                    <span>Rule Verification:</span>
                    {rec.safety_checks.map((sc, idx) => (
                      <span key={idx} style={{ color: "#10b981" }}>
                        ✓ {sc.rule} ({sc.name})
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "20px", color: "#94a3b8", fontSize: "13px" }}>
              No pending station-local regulation proposals at this time
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
