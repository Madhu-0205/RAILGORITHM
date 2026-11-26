import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { JunctionWorkspace } from "../components/JunctionWorkspace";
import { SectionTopologyStrip } from "../components/SectionTopologyStrip";
import { TimeDistanceGraph } from "../components/TimeDistanceGraph";
import { Badge, ErrorBanner, KpiCard, Panel, StatusBadge } from "../components/ui";
import type {
  Conflict,
  Dashboard,
  Network,
  Section,
  SectionControllerAlerts,
  SectionControllerBlockBoard,
  SectionControllerJunctionWorkspace,
  SectionControllerOverview,
  SectionControllerTopology,
  SectionControllerTrainLedger,
  Station,
  Train,
} from "../types";

export function SectionControllerWorkspace() {
  const { user } = useAuth();
  const [simId, setSimId] = useState<string | null>(null);
  const [overview, setOverview] = useState<SectionControllerOverview | null>(null);
  const [topology, setTopology] = useState<SectionControllerTopology | null>(null);
  const [trainLedger, setTrainLedger] = useState<SectionControllerTrainLedger | null>(null);
  const [blockBoard, setBlockBoard] = useState<SectionControllerBlockBoard | null>(null);
  const [junctionWs, setJunctionWs] = useState<SectionControllerJunctionWorkspace | null>(null);
  const [alerts, setAlerts] = useState<SectionControllerAlerts | null>(null);
  const [dashboardData, setDashboardData] = useState<Dashboard | null>(null);
  const [networkData, setNetworkData] = useState<Network | null>(null);
  const [activeConsoleTab, setActiveConsoleTab] = useState<"overview" | "mcg" | "blocks" | "junctions" | "ledger">("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch simulation ID
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

  // 2. Fetch Section Controller data
  useEffect(() => {
    if (!simId) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.sectionControllerOverview(simId),
      api.sectionControllerTopology(simId),
      api.sectionControllerTrainLedger(simId),
      api.sectionControllerBlockBoard(simId),
      api.sectionControllerJunctionWorkspace(simId),
      api.sectionControllerAlerts(simId),
      api.dashboard(simId),
      api.network(simId),
    ])
      .then(([ov, top, tl, bb, jw, al, dash, netRes]) => {
        if (!mounted) return;
        setOverview(ov);
        setTopology(top);
        setTrainLedger(tl);
        setBlockBoard(bb);
        setJunctionWs(jw);
        setAlerts(al);
        setDashboardData(dash);
        setNetworkData(netRes.network);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || "Failed to load Section Controller console");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [simId]);

  if (loading && !overview) {
    return (
      <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>
        <h3>Loading Section Controller Console...</h3>
        <p>Aggregating corridor telemetry, block section boards, and junction crossing models</p>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div style={{ padding: "32px" }}>
        <ErrorBanner message={`Failed to load Section Controller console: ${error}`} />
      </div>
    );
  }

  const kpis = overview?.kpis;

  return (
    <div className="section-controller-workspace" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* 1. Header & Operating Banner */}
      <div
        style={{
          background: "linear-gradient(135deg, #0b1329 0%, #1e293b 100%)",
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
            <span style={{ fontSize: "20px" }}>🎛️</span>
            <h1 style={{ margin: 0, fontSize: "22px", color: "#f8fafc", fontWeight: 700 }}>
              {overview?.section_name}
            </h1>
            <span style={{ fontSize: "12px", fontWeight: 700, padding: "4px 10px", borderRadius: "4px", background: "#065f46", color: "#a7f3d0" }}>
              TERRITORY CONTROL
            </span>
          </div>
          <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#94a3b8" }}>
            Boundaries: <strong>{overview?.operating_boundaries}</strong> | Controller:{" "}
            <strong>{user?.display_name || user?.username}</strong> ({overview?.control_area})
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ textAlign: "right", borderLeft: "1px solid #334155", paddingLeft: "16px" }}>
            <div style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>Corridor Clock</div>
            <div style={{ fontSize: "18px", color: "#38bdf8", fontWeight: 700 }}>
              {overview?.simulation_time || "10:00"} IST
            </div>
            <div style={{ fontSize: "11px", color: "#10b981" }}>
              ● Telemetry: {overview?.data_quality.feed_status || "NOMINAL"} ({overview?.data_quality.freshness_seconds}s)
            </div>
          </div>
        </div>
      </div>

      {/* 2. Corridor-wide KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
        <KpiCard
          label="Active Trains"
          value={kpis?.trains_active ?? 0}
          unit="running"
          tone="info"
          hint={`Total in section: ${kpis?.trains_total ?? 0}`}
        />
        <KpiCard
          label="Delayed Trains"
          value={kpis?.trains_delayed ?? 0}
          unit="trains"
          tone={(kpis?.trains_delayed ?? 0) > 2 ? "watch" : "good"}
          hint={`Avg Delay: ${kpis?.average_delay_min ?? 0}m`}
        />
        <KpiCard
          label="Block Occupancy"
          value={`${kpis?.blocks_occupied ?? 0} / ${kpis?.blocks_total ?? 0}`}
          unit={`${kpis?.block_occupancy_pct ?? 0}%`}
          tone={(kpis?.block_occupancy_pct ?? 0) > 60 ? "watch" : "neutral"}
          hint="Corridor track utilization"
        />
        <KpiCard
          label="Single-Line Bottlenecks"
          value={`${kpis?.bottlenecks_occupied_count ?? 0} / ${kpis?.critical_bottlenecks_count ?? 0}`}
          unit="occupied"
          tone={(kpis?.bottlenecks_occupied_count ?? 0) > 0 ? "watch" : "good"}
          hint="S1 & S3 critical sections"
        />
        <KpiCard
          label="Corridor Punctuality"
          value={`${kpis?.punctuality_pct ?? 0}%`}
          tone={(kpis?.punctuality_pct ?? 0) >= 80 ? "good" : "bad"}
          hint="Indian Railways standard (<=5m)"
        />
        <KpiCard
          label="Delay Propagation"
          value={kpis?.delay_propagation_index ?? 0}
          unit="idx"
          tone={(kpis?.delay_propagation_index ?? 0) > 1.0 ? "bad" : "good"}
          hint="Secondary / Primary delay"
        />
      </div>

      {/* 3. Section Topology Strip */}
      {topology && <SectionTopologyStrip topology={topology} />}

      {/* 4. Console Navigation Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #334155", paddingBottom: "10px" }}>
        <button
          onClick={() => setActiveConsoleTab("overview")}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "none",
            background: activeConsoleTab === "overview" ? "#38bdf8" : "#1e293b",
            color: activeConsoleTab === "overview" ? "#0f172a" : "#cbd5e1",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Corridor Summary & Alerts
        </button>
        <button
          onClick={() => setActiveConsoleTab("mcg")}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "none",
            background: activeConsoleTab === "mcg" ? "#38bdf8" : "#1e293b",
            color: activeConsoleTab === "mcg" ? "#0f172a" : "#cbd5e1",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Master Control Graph (Time-Distance Chart)
        </button>
        <button
          onClick={() => setActiveConsoleTab("blocks")}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "none",
            background: activeConsoleTab === "blocks" ? "#38bdf8" : "#1e293b",
            color: activeConsoleTab === "blocks" ? "#0f172a" : "#cbd5e1",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Block Section Board ({blockBoard?.blocks.length || 0} Blocks)
        </button>
        <button
          onClick={() => setActiveConsoleTab("junctions")}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "none",
            background: activeConsoleTab === "junctions" ? "#38bdf8" : "#1e293b",
            color: activeConsoleTab === "junctions" ? "#0f172a" : "#cbd5e1",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Junction & Precedence Workspace ({junctionWs?.active_scenarios.length || 0} Scenarios)
        </button>
        <button
          onClick={() => setActiveConsoleTab("ledger")}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            border: "none",
            background: activeConsoleTab === "ledger" ? "#38bdf8" : "#1e293b",
            color: activeConsoleTab === "ledger" ? "#0f172a" : "#cbd5e1",
            fontWeight: 700,
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Section Train Movement Ledger ({trainLedger?.total_trains || 0} Trains)
        </button>
      </div>

      {/* 5. Tab Content Rendering */}

      {/* TAB: Master Control Graph (Embedded Console View) */}
      {activeConsoleTab === "mcg" && dashboardData && networkData && (
        <Panel
          title="Master Control Graph (Time-Distance Trajectories)"
          subtitle="Integrated distance-time graph with forward projections, direction filters, and speed restrictions"
        >
          <TimeDistanceGraph
            stations={networkData.stations}
            sections={networkData.sections}
            trains={dashboardData.trains}
            conflicts={dashboardData.conflicts || []}
            simTimeMin={overview?.sim_time_min}
            simTimeString={overview?.simulation_time}
            height={520}
          />
        </Panel>
      )}

      {/* TAB: Block Section Board */}
      {activeConsoleTab === "blocks" && blockBoard && (
        <Panel
          title="Corridor Block Section Board"
          subtitle="Real-time multi-station block occupancy, signal aspects, and axle counter telemetry health"
        >
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", color: "#f8fafc" }}>
              <thead>
                <tr style={{ background: "#0f172a", borderBottom: "2px solid #334155", textAlign: "left" }}>
                  <th style={{ padding: "10px 12px" }}>Block ID</th>
                  <th style={{ padding: "10px 12px" }}>Section</th>
                  <th style={{ padding: "10px 12px" }}>Track Mode</th>
                  <th style={{ padding: "10px 12px" }}>Direction</th>
                  <th style={{ padding: "10px 12px" }}>Signal Aspect</th>
                  <th style={{ padding: "10px 12px" }}>Occupancy State</th>
                  <th style={{ padding: "10px 12px" }}>Occupant Train</th>
                  <th style={{ padding: "10px 12px" }}>Headway</th>
                  <th style={{ padding: "10px 12px" }}>Axle Counter</th>
                </tr>
              </thead>
              <tbody>
                {blockBoard.blocks.map((blk) => (
                  <tr key={blk.block_id} style={{ borderBottom: "1px solid #1e293b" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 700, color: "#38bdf8" }}>
                      {blk.block_id}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {blk.from_station} ➔ {blk.to_station} ({blk.section_id})
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          background: blk.mode === "SINGLE" ? "#78350f" : "#1e293b",
                          color: blk.mode === "SINGLE" ? "#fcd34d" : "#cbd5e1",
                        }}
                      >
                        {blk.mode}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94a3b8" }}>{blk.direction}</td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          background: blk.signal_aspect === "RED" ? "#7f1d1d" : "#065f46",
                          color: blk.signal_aspect === "RED" ? "#fecaca" : "#a7f3d0",
                        }}
                      >
                        ● {blk.signal_aspect}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 700, color: blk.state === "OCCUPIED" ? "#ef4444" : "#10b981" }}>
                      {blk.state}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {blk.occupant_train ? (
                        <span style={{ color: "#f8fafc", fontWeight: 600 }}>
                          🚆 {blk.occupant_train.train_name} ({blk.occupant_train.speed_kmph} km/h)
                        </span>
                      ) : (
                        <span style={{ color: "#64748b" }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94a3b8" }}>{blk.headway_min} min</td>
                    <td style={{ padding: "10px 12px", color: "#10b981", fontSize: "11px" }}>
                      ✓ {blk.axle_counter_status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* TAB: Junction Workspace */}
      {activeConsoleTab === "junctions" && junctionWs && (
        <JunctionWorkspace data={junctionWs} />
      )}

      {/* TAB: Train Movement Ledger */}
      {activeConsoleTab === "ledger" && trainLedger && (
        <Panel
          title="Section Train Movement Ledger"
          subtitle="Real-time territory ledger with positions, delays, priority ranking, and projected corridor exit"
        >
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", color: "#f8fafc" }}>
              <thead>
                <tr style={{ background: "#0f172a", borderBottom: "2px solid #334155", textAlign: "left" }}>
                  <th style={{ padding: "10px 12px" }}>Train</th>
                  <th style={{ padding: "10px 12px" }}>Precedence Class</th>
                  <th style={{ padding: "10px 12px" }}>Origin ➔ Destination</th>
                  <th style={{ padding: "10px 12px" }}>Location</th>
                  <th style={{ padding: "10px 12px" }}>Km Position</th>
                  <th style={{ padding: "10px 12px" }}>Speed</th>
                  <th style={{ padding: "10px 12px" }}>Delay (Sched / Proj)</th>
                  <th style={{ padding: "10px 12px" }}>Crew Duty</th>
                  <th style={{ padding: "10px 12px" }}>Est Corridor Exit</th>
                </tr>
              </thead>
              <tbody>
                {trainLedger.trains.map((t) => (
                  <tr key={t.train_id} style={{ borderBottom: "1px solid #1e293b" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 700 }}>
                      <span style={{ color: "#38bdf8" }}>{t.train_name}</span>
                      <div style={{ fontSize: "11px", color: "#94a3b8" }}>#{t.train_id} ({t.direction})</div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          background: t.priority <= 2 ? "#7c2d12" : "#1e293b",
                          color: t.priority <= 2 ? "#fdba74" : "#cbd5e1",
                        }}
                      >
                        {t.precedence_class} (P{t.priority})
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", fontSize: "12px", color: "#cbd5e1" }}>
                      {t.origin} ➔ {t.destination}
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                      {t.current_location}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94a3b8" }}>
                      {t.current_km !== null ? `km ${t.current_km.toFixed(1)}` : "—"}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94a3b8" }}>
                      {t.speed_kmph} km/h
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{ color: t.delay_min > 5 ? "#ef4444" : "#10b981", fontWeight: 600 }}>
                        +{t.delay_min}m
                      </span>
                      <span style={{ color: "#94a3b8", fontSize: "11px", marginLeft: "4px" }}>
                        (proj: +{t.projected_delay_min}m)
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94a3b8" }}>
                      {t.crew_duty_hours} hrs
                    </td>
                    <td style={{ padding: "10px 12px", color: "#a5b4fc" }}>
                      {t.eta_section_exit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* TAB: Overview (Summary & Alert Centre) */}
      {activeConsoleTab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px" }}>
          {/* Station summaries along corridor */}
          <Panel
            title="Monitored Stations Territory Status"
            subtitle="Platform occupancy and throat congestion across all section nodes"
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {overview?.monitored_stations.map((st) => (
                <div
                  key={st.station_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    background: "#0f172a",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    border: "1px solid #1e293b",
                  }}
                >
                  <div>
                    <strong style={{ color: "#38bdf8", fontSize: "14px" }}>
                      {st.station_name} ({st.code})
                    </strong>
                    <span style={{ marginLeft: "8px", fontSize: "11px", color: "#94a3b8" }}>
                      km {st.km_marker.toFixed(0)} {st.is_junction ? "★ JUNCTION" : ""}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "12px" }}>
                    <span>
                      Platforms: <strong>{st.occupied_platforms} / {st.total_platforms}</strong> occupied
                    </span>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "10px",
                        fontWeight: 700,
                        background: st.throat_status === "CLEAR" ? "#065f46" : "#854d0e",
                        color: "#ffffff",
                      }}
                    >
                      Throat: {st.throat_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          {/* Section Conflict & AI Advisory Centre */}
          <Panel
            title="Section Conflict & Advisory Centre"
            subtitle="Corridor-wide regulation proposals and safety-checked crossing decisions"
          >
            {alerts && alerts.recommendations.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {alerts.recommendations.map((rec) => (
                  <div
                    key={rec.id}
                    style={{
                      background: "#0f172a",
                      padding: "12px",
                      borderRadius: "6px",
                      border: "1px solid #334155",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: "#38bdf8", fontSize: "13px" }}>{rec.label}</strong>
                      <span style={{ fontSize: "10px", color: "#10b981", background: "#065f46", padding: "2px 6px", borderRadius: "3px" }}>
                        Confidence: {Math.round(rec.confidence * 100)}%
                      </span>
                    </div>
                    <p style={{ margin: "6px 0", fontSize: "12px", color: "#cbd5e1" }}>{rec.explanation}</p>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                      Affected Trains: {rec.affected_trains.join(", ") || "Corridor-wide"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: "24px", color: "#94a3b8", fontSize: "13px" }}>
                No pending corridor regulation advisories. Traffic operating nominally.
              </div>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
