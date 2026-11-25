import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { delayTone, formatMinutes, numberOrDash } from "../lib/format";
import type { SectionControllerKpis, StationMasterKpis } from "../types";
import {
  Badge,
  EmptyState,
  ErrorBanner,
  EvidenceBadge,
  KpiCard,
  Panel,
  SeverityBadge,
  Spinner,
  StatusBadge,
} from "../components/ui";

export function DashboardPage() {
  const { user } = useAuth();
  const { selectedId, revision } = useSimulation();

  // Role view toggle
  const defaultMode = user?.role === "STATION_MASTER" ? "STATION" : "SECTION";
  const [viewMode, setViewMode] = useState<"STATION" | "SECTION">(defaultMode);
  const [stationId, setStationId] = useState<string>(user?.station_id || "MLG");
  const [showDefinitions, setShowDefinitions] = useState(false);

  // General dashboard data
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  // Role-specific KPI data
  const [stationKpiData, setStationKpiData] = useState<StationMasterKpis | null>(null);
  const [sectionKpiData, setSectionKpiData] = useState<SectionControllerKpis | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    if (viewMode === "STATION") {
      api.stationKpis(selectedId, stationId).then(setStationKpiData).catch(() => {});
    } else {
      api.sectionKpis(selectedId).then(setSectionKpiData).catch(() => {});
    }
  }, [selectedId, revision, viewMode, stationId]);

  if (!selectedId)
    return (
      <EmptyState
        title="No simulation selected"
        description={
          user?.role === "SECTION_MASTER"
            ? "Create a synthetic scenario from the simulation picker to begin."
            : "Ask the Section Master to create a simulation."
        }
      />
    );
  if (loading) return <Spinner label="Loading dashboard" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Top Page Heading & Role Mode Switcher */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>
              {viewMode === "STATION"
                ? `Station Master Dashboard — ${stationKpiData?.station_name || stationId}`
                : "Section Controller Corridor Dashboard"}
            </h1>
            <span className="badge badge-accent">
              {viewMode === "STATION" ? "STATION MASTER VIEW" : "CORRIDOR DISPATCH VIEW"}
            </span>
          </div>
          <p className="muted">
            {data.simulation.name} · {data.simulation.scenario_key.replace(/_/g, " ")} · simulated clock{" "}
            {data.simulation.sim_time} IST
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          {/* Role view toggle buttons */}
          <div className="button-group">
            <button
              type="button"
              className={`button button-small ${viewMode === "STATION" ? "button-primary" : "button-ghost"}`}
              onClick={() => setViewMode("STATION")}
            >
              Station View
            </button>
            <button
              type="button"
              className={`button button-small ${viewMode === "SECTION" ? "button-primary" : "button-ghost"}`}
              onClick={() => setViewMode("SECTION")}
            >
              Section View
            </button>
          </div>

          {viewMode === "STATION" && (
            <select
              className="select-small"
              value={stationId}
              onChange={(e) => setStationId(e.target.value)}
              title="Select station to monitor"
            >
              <option value="NDL">NDL — Nandpur</option>
              <option value="KRN">KRN — Karanpur</option>
              <option value="MLG">MLG — Malgaon Junction</option>
              <option value="SRP">SRP — Suryapur</option>
              <option value="VSN">VSN — Vasanthpur</option>
            </select>
          )}

          <StatusBadge status={data.simulation.status} />
          <span className="badge badge-muted">state v{data.simulation.state_version}</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1. STATION MASTER ROLE VIEW */}
      {/* ========================================================================= */}
      {viewMode === "STATION" && stationKpiData && (
        <>
          {/* Station Master KPI Cards */}
          <div className="kpi-grid">
            <KpiCard
              label="Trains Monitored"
              value={stationKpiData.kpis.trains_monitored}
              hint={`${stationKpiData.kpis.delayed_trains} delayed trains`}
              tone={stationKpiData.kpis.delayed_trains > 0 ? "watch" : "good"}
            />
            <KpiCard
              label="Schedule Adherence"
              value={numberOrDash(stationKpiData.kpis.schedule_adherence_pct)}
              unit={stationKpiData.kpis.schedule_adherence_pct !== null ? "%" : ""}
              hint={stationKpiData.kpis.schedule_adherence_pct === null ? "no trains in observation window" : "trains within 5 min of schedule"}
              tone={stationKpiData.kpis.schedule_adherence_pct === null ? "neutral" : stationKpiData.kpis.schedule_adherence_pct < 75 ? "watch" : "good"}
            />
            <KpiCard
              label="Platform Availability"
              value={numberOrDash(stationKpiData.kpis.platform_availability_pct)}
              unit="%"
              hint={`${stationKpiData.kpis.platforms_available} of ${stationKpiData.kpis.platforms_total} platforms free`}
              tone={stationKpiData.kpis.platforms_available === 0 ? "bad" : "good"}
            />
            <KpiCard
              label="Avg Arrival Delay"
              value={numberOrDash(stationKpiData.kpis.average_arrival_delay_min)}
              unit={stationKpiData.kpis.average_arrival_delay_min !== null ? " min" : ""}
              hint={stationKpiData.kpis.average_arrival_delay_min !== null ? "approaching trains" : "no approaching trains"}
              tone={stationKpiData.kpis.average_arrival_delay_min === null ? "neutral" : stationKpiData.kpis.average_arrival_delay_min > 10 ? "bad" : "good"}
            />
            <KpiCard
              label="Avg Departure Delay"
              value={numberOrDash(stationKpiData.kpis.average_departure_delay_min)}
              unit={stationKpiData.kpis.average_departure_delay_min !== null ? " min" : ""}
              hint={stationKpiData.kpis.average_departure_delay_min !== null ? "stationed departures" : "no stationed trains"}
              tone={stationKpiData.kpis.average_departure_delay_min === null ? "neutral" : stationKpiData.kpis.average_departure_delay_min > 10 ? "bad" : "good"}
            />
            <KpiCard
              label="Station Alerts & Recs"
              value={stationKpiData.kpis.operational_alerts_count}
              hint={`${stationKpiData.kpis.pending_recommendations_count} pending local decisions`}
              tone={stationKpiData.kpis.operational_alerts_count > 0 ? "watch" : "good"}
            />
          </div>

          {/* Platform Berthing Status Visualizer */}
          <Panel
            title={`Live Platform Berthing Status — ${stationKpiData.station_name}`}
            subtitle={`${stationKpiData.kpis.platforms_available} available · ${stationKpiData.kpis.platforms_occupied} occupied · ${stationKpiData.kpis.platforms_outage} outage`}
          >
            <div className="grid-3">
              {stationKpiData.platform_slots.map((slot) => (
                <div
                  key={slot.platform_id}
                  className={`platform-berth-card status-${slot.status.toLowerCase()}`}
                  style={{
                    padding: "1rem",
                    border: "1px solid var(--border)",
                    borderRadius: "6px",
                    background:
                      slot.status === "OCCUPIED"
                        ? "rgba(59, 130, 246, 0.08)"
                        : slot.status === "OUTAGE"
                        ? "rgba(239, 68, 68, 0.08)"
                        : "rgba(16, 185, 129, 0.08)",
                  }}
                >
                  <div className="flex-row justify-between items-center">
                    <strong>Platform {slot.platform_id}</strong>
                    <Badge
                      tone={
                        slot.status === "OCCUPIED"
                          ? "default"
                          : slot.status === "OUTAGE"
                          ? "bad"
                          : "good"
                      }
                    >
                      {slot.status}
                    </Badge>
                  </div>
                  <p className="small mt-2" style={{ fontWeight: 500 }}>
                    {slot.train_id ? `Train: ${slot.train_id}` : slot.description}
                  </p>
                </div>
              ))}
            </div>
          </Panel>

          {/* Split View: Approaching/Berthed Trains & Station Decisions */}
          <div className="grid-two">
            <Panel
              title="Monitored Train Movements"
              subtitle="Trains currently at station or scheduled within 60 minutes"
              actions={
                <Link className="button button-small" to="/trains">
                  View all trains
                </Link>
              }
            >
              {stationKpiData.monitored_trains.length === 0 ? (
                <EmptyState
                  title="No trains within window"
                  description="No trains scheduled at this station in the active operational window."
                />
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Train</th>
                      <th>Type</th>
                      <th>Sched Arr</th>
                      <th>Sched Dep</th>
                      <th>Delay</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stationKpiData.monitored_trains.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <strong>{t.name}</strong>
                          <span className="muted small d-block">{t.id}</span>
                        </td>
                        <td>
                          <Badge tone="muted">{t.train_type}</Badge>
                        </td>
                        <td>{t.scheduled_arrival || "—"}</td>
                        <td>{t.scheduled_departure || "—"}</td>
                        <td>
                          <span className={delayTone(t.projected_delay_min)}>
                            {t.projected_delay_min > 0 ? `+${t.projected_delay_min}m` : "On time"}
                          </span>
                        </td>
                        <td>
                          <Badge tone={t.is_at_station ? "good" : "muted"}>
                            {t.is_at_station ? `At PF ${t.platform || "—"}` : "Approaching"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>

            <Panel
              title="Station Pending Decisions & Alerts"
              subtitle="Decisions affecting this station requiring controller review"
              actions={
                <Link className="button button-small" to="/recommendations">
                  Decision Queue
                </Link>
              }
            >
              {stationKpiData.pending_recommendations.length === 0 &&
              stationKpiData.operational_alerts.length === 0 ? (
                <EmptyState
                  title="Station operating normally"
                  description="No pending decisions or track conflicts affecting this station."
                />
              ) : (
                <div className="stack">
                  {stationKpiData.pending_recommendations.map((r) => (
                    <div key={r.id} className="list-row" style={{ padding: "0.75rem 0" }}>
                      <div>
                        <Link to={`/recommendations/${r.id}`} className="list-title">
                          {r.label}
                        </Link>
                        <p className="muted small">Recommendation ID: {r.id}</p>
                      </div>
                      <Link to={`/recommendations/${r.id}`} className="button button-small button-primary">
                        Review & Decide
                      </Link>
                    </div>
                  ))}

                  {stationKpiData.operational_alerts.map((c) => (
                    <div key={c.id} className="list-row" style={{ padding: "0.5rem 0" }}>
                      <div>
                        <strong>{c.type.replace(/_/g, " ")}</strong>
                        <p className="muted small">
                          Trains: {c.trains.join(", ") || "None"} · Window: {c.start && c.end ? `${c.start}–${c.end}` : "Immediate"}
                        </p>
                      </div>
                      <SeverityBadge severity={c.severity} />
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* 2. SECTION CONTROLLER CORRIDOR VIEW */}
      {/* ========================================================================= */}
      {viewMode === "SECTION" && sectionKpiData && (
        <>
          {/* Section Controller KPI Cards */}
          <div className="kpi-grid">
            <KpiCard
              label="Active Corridor Trains"
              value={sectionKpiData.kpis.trains_active}
              hint={`${sectionKpiData.kpis.trains_completed} completed · ${sectionKpiData.kpis.trains_scheduled} scheduled`}
            />
            <KpiCard
              label="Average Section Delay"
              value={numberOrDash(sectionKpiData.kpis.average_section_delay_min)}
              unit=" min"
              hint={`Total delay: ${sectionKpiData.kpis.total_section_delay_min} min`}
              tone={sectionKpiData.kpis.average_section_delay_min > 15 ? "bad" : sectionKpiData.kpis.average_section_delay_min > 5 ? "watch" : "good"}
            />
            <KpiCard
              label="Block Occupancy"
              value={numberOrDash(sectionKpiData.kpis.block_occupancy_pct)}
              unit="%"
              hint={`${sectionKpiData.kpis.blocks_occupied} of ${sectionKpiData.kpis.blocks_total} blocks busy`}
              tone={sectionKpiData.kpis.block_occupancy_pct > 60 ? "watch" : "good"}
            />
            <KpiCard
              label="Junction Throat Load (MLG)"
              value={numberOrDash(sectionKpiData.kpis.junction_throat_load_pct)}
              unit="%"
              hint={`Queue: ${sectionKpiData.kpis.junction_queue_length} · Status: ${sectionKpiData.kpis.junction_congestion_level}`}
              tone={sectionKpiData.kpis.junction_throat_load_pct >= 80 ? "bad" : sectionKpiData.kpis.junction_throat_load_pct >= 50 ? "watch" : "good"}
            />
            <KpiCard
              label="Delay Propagation (DPI)"
              value={numberOrDash(sectionKpiData.kpis.delay_propagation_index)}
              unit="x"
              hint={`Knock-on risk: ${sectionKpiData.kpis.knock_on_risk_level}`}
              tone={sectionKpiData.kpis.delay_propagation_index > 1.0 ? "bad" : "good"}
            />
            <KpiCard
              label="Throughput & Recovery"
              value={numberOrDash(sectionKpiData.kpis.throughput_trains_per_hour)}
              unit=" tph"
              hint={sectionKpiData.kpis.recovery_clearance_rate_pct !== null ? `Recovery clear rate: ${sectionKpiData.kpis.recovery_clearance_rate_pct}%` : "No historical conflicts recorded"}
            />
          </div>

          {/* Junction Congestion & Bottleneck Analysis */}
          <div className="grid-two">
            <Panel
              title="Junction Congestion & Throat Bottlenecks"
              subtitle="Real-time Malgaon (MLG) diamond crossing throat load and single-line queues"
            >
              <div className="stack">
                <div className="metric-box flex-row justify-between items-center">
                  <div>
                    <strong>Malgaon Junction Throat</strong>
                    <p className="muted small">
                      Capacity: {sectionKpiData.junction_status.throat_capacity} simultaneous diamond movements
                    </p>
                  </div>
                  <Badge
                    tone={
                      sectionKpiData.junction_status.congestion_level === "SATURATED"
                        ? "bad"
                        : sectionKpiData.junction_status.congestion_level === "HIGH"
                        ? "watch"
                        : "good"
                    }
                  >
                    {sectionKpiData.junction_status.congestion_level}
                  </Badge>
                </div>

                <div>
                  <small className="muted field-label">Single-Line Bottleneck Blocks Occupied</small>
                  {sectionKpiData.occupied_bottlenecks.length === 0 ? (
                    <p className="small text-success">All single-line bottlenecks (B1, B2, B4, B5) currently clear.</p>
                  ) : (
                    <div className="flex-row gap-2 mt-1">
                      {sectionKpiData.occupied_bottlenecks.map((b) => (
                        <span key={b.block_id} className="badge badge-watch">
                          Block {b.block_id}: Train {b.train_id}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <small className="muted field-label">Active Throat Transits ({sectionKpiData.junction_status.active_transits}/2)</small>
                  <p className="small">
                    {sectionKpiData.junction_status.transiting_trains.length > 0
                      ? `Transiting: ${sectionKpiData.junction_status.transiting_trains.join(", ")}`
                      : "No active diamond crossings currently occupying throat."}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel
              title="Corridor Dispatch Decisions & Conflicts"
              subtitle="Active conflicts requiring dispatcher attention across the section"
              actions={
                <Link className="button button-small" to="/recommendations">
                  Decision Queue
                </Link>
              }
            >
              {sectionKpiData.pending_decisions.length === 0 && sectionKpiData.active_conflicts.length === 0 ? (
                <EmptyState
                  title="Corridor Operating Optimally"
                  description="No unresolved conflicts or pending dispatch decisions."
                />
              ) : (
                <div className="stack">
                  {sectionKpiData.pending_decisions.map((d) => (
                    <div key={d.id} className="list-row" style={{ padding: "0.75rem 0" }}>
                      <div>
                        <Link to={`/recommendations/${d.id}`} className="list-title">
                          {d.label}
                        </Link>
                        <p className="muted small">
                          Scope: {d.affected_stations.join(", ") || "Network"} · ID: {d.id}
                        </p>
                      </div>
                      <div className="flex-row gap-2 items-center">
                        {d.disagreement && <span className="badge badge-watch">DISAGREEMENT</span>}
                        <Link to={`/recommendations/${d.id}`} className="button button-small button-primary">
                          Decide
                        </Link>
                      </div>
                    </div>
                  ))}

                  {sectionKpiData.active_conflicts.map((c) => (
                    <div key={c.id} className="list-row" style={{ padding: "0.5rem 0" }}>
                      <div>
                        <strong>{c.type.replace(/_/g, " ")}</strong>
                        <p className="muted small">
                          Trains: {c.trains.join(", ") || "None"} · Window: {c.start && c.end ? `${c.start}–${c.end}` : "Now"}
                        </p>
                      </div>
                      <SeverityBadge severity={c.severity} />
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </>
      )}

      {/* Expandable Traceable KPI Definitions & Time Periods */}
      <Panel
        title="KPI Traceability & Mathematical Definitions"
        subtitle="Formulas, time periods, and data source citations for all operational metrics"
        actions={
          <button
            type="button"
            className="button button-small button-ghost"
            onClick={() => setShowDefinitions(!showDefinitions)}
          >
            {showDefinitions ? "Hide Definitions" : "View KPI Definitions"}
          </button>
        }
      >
        {showDefinitions && (
          <div className="stack">
            <p className="muted small">
              Time Period:{" "}
              {viewMode === "STATION"
                ? stationKpiData?.time_period || "Active Planning Horizon"
                : sectionKpiData?.time_period || "Corridor Operational Horizon"}
            </p>
            <dl className="grid-2">
              {Object.entries(
                (viewMode === "STATION" ? stationKpiData?.kpi_definitions : sectionKpiData?.kpi_definitions) || {}
              ).map(([key, def]) => (
                <div key={key} style={{ padding: "0.5rem 0" }}>
                  <dt style={{ fontWeight: 600 }}>{key.replace(/_/g, " ")}</dt>
                  <dd className="muted small">{def}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </Panel>
    </div>
  );
}
