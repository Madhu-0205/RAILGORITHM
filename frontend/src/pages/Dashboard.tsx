import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { delayTone, formatMinutes, numberOrDash } from "../lib/format";
import type {
  BlockOccupancy,
  Conflict,
  Network,
  Section,
  SectionControllerKpis,
  Station,
  StationMasterKpis,
  Train,
} from "../types";
import {
  Badge,
  EmptyState,
  ErrorBanner,
  Field,
  KpiCard,
  Panel,
  SeverityBadge,
  Spinner,
  StatusBadge,
} from "../components/ui";
import { RailwayCorridorDiagram } from "../components/RailwayCorridorDiagram";
import { StationPlatformBerths } from "../components/StationPlatformBerths";
import { HourlyMovementsChart, type MovementBucket } from "../components/HourlyMovementsChart";
import { DelayDistributionChart, type DelayTier } from "../components/DelayDistributionChart";
import { TimeDistanceGraph } from "../components/TimeDistanceGraph";
import { StationWorkingDiagram } from "../components/StationWorkingDiagram";
import { BlockOccupancyMatrix } from "../components/BlockOccupancyMatrix";
import { StationTrainBoard } from "../components/StationTrainBoard";
import { StationControlStrip } from "../components/StationControlStrip";
import { OperationalAttentionPanel } from "../components/OperationalAttentionPanel";
import { TrainMovementLedger } from "../components/TrainMovementLedger";
import { ConflictRegulationWorkspace } from "../components/ConflictRegulationWorkspace";
import { RestrictionsAndIncidentsPanel } from "../components/RestrictionsAndIncidentsPanel";
import { CoordinationAndHandover } from "../components/CoordinationAndHandover";
import { KPI_REGISTRY } from "../lib/kpiRegistry";

const DEFAULT_STATIONS: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

const DEFAULT_SECTIONS: Section[] = [
  {
    id: "S1",
    from_station: "NDL",
    to_station: "KRN",
    mode: "SINGLE",
    headway_min: 4,
    max_speed_kmph: 90,
    blocks: [{ id: "B1", direction: "BIDIRECTIONAL", run_time_min: 12 }],
  },
  {
    id: "S2",
    from_station: "KRN",
    to_station: "MLG",
    mode: "DOUBLE",
    headway_min: 3,
    max_speed_kmph: 110,
    blocks: [
      { id: "B2U", direction: "UP", run_time_min: 10 },
      { id: "B2D", direction: "DOWN", run_time_min: 10 },
    ],
  },
  {
    id: "S3",
    from_station: "MLG",
    to_station: "SRP",
    mode: "SINGLE",
    headway_min: 4,
    max_speed_kmph: 90,
    blocks: [{ id: "B3", direction: "BIDIRECTIONAL", run_time_min: 14 }],
  },
  {
    id: "S4",
    from_station: "SRP",
    to_station: "VSN",
    mode: "DOUBLE",
    headway_min: 3,
    max_speed_kmph: 110,
    blocks: [
      { id: "B4U", direction: "UP", run_time_min: 9 },
      { id: "B4D", direction: "DOWN", run_time_min: 9 },
    ],
  },
];

export function DashboardPage() {
  const { user } = useAuth();
  const { selectedId, revision } = useSimulation();

  // Role view toggle
  const defaultMode = user?.role === "STATION_MASTER" ? "STATION" : "SECTION";
  const [viewMode, setViewMode] = useState<"STATION" | "SECTION">(defaultMode);
  const [stationId, setStationId] = useState<string>(user?.station_id || "MLG");
  const [showDefinitions, setShowDefinitions] = useState(false);

  // Section Controller Redesign state (v2.7)
  const [selectedTerritory, setSelectedTerritory] = useState("NDL-VSN Mainline Corridor (Southern Division)");
  const [inspectStationId, setInspectStationId] = useState<string | null>(null);
  const [activeSectionTab, setActiveSectionTab] = useState<"ALL" | "GRAPH" | "BLOCKS" | "LEDGER" | "REGULATION" | "RESTRICTIONS" | "HANDOVER">("ALL");
  const [selectedLedgerTrainId, setSelectedLedgerTrainId] = useState<string | null>(null);

  // Station Movement Filter
  const [trainFilter, setTrainFilter] = useState<"ALL" | "APPROACHING" | "AT_STATION" | "DELAYED">("ALL");
  const [trainSearch, setTrainSearch] = useState("");

  // General dashboard data
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  // Network topology & block state
  const [networkData, setNetworkData] = useState<{
    network: Network;
    block_occupancy: BlockOccupancy[];
  } | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    api.network(selectedId).then(setNetworkData).catch(() => {});
  }, [selectedId, revision]);

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

  // Station movement table filtering
  const filteredStationTrains = useMemo(() => {
    if (!stationKpiData?.monitored_trains) return [];
    return stationKpiData.monitored_trains.filter((t) => {
      if (trainFilter === "APPROACHING" && t.is_at_station) return false;
      if (trainFilter === "AT_STATION" && !t.is_at_station) return false;
      if (trainFilter === "DELAYED" && t.projected_delay_min <= 0) return false;

      if (!trainSearch.trim()) return true;
      const q = trainSearch.toLowerCase();
      return t.id.toLowerCase().includes(q) || t.name.toLowerCase().includes(q) || t.destination.toLowerCase().includes(q);
    });
  }, [stationKpiData?.monitored_trains, trainFilter, trainSearch]);

  // Station movement chart data
  const stationMovementBuckets = useMemo<MovementBucket[]>(() => {
    if (!stationKpiData?.monitored_trains || stationKpiData.monitored_trains.length === 0) {
      return [
        { hour: "06:00", arrivals: 1, departures: 1 },
        { hour: "07:00", arrivals: 2, departures: 1 },
        { hour: "08:00", arrivals: 1, departures: 2 },
      ];
    }
    const bucketMap: Record<string, { arrivals: number; departures: number }> = {};
    for (const t of stationKpiData.monitored_trains) {
      const arrHour = t.scheduled_arrival ? t.scheduled_arrival.split(":")[0] + ":00" : "07:00";
      const depHour = t.scheduled_departure ? t.scheduled_departure.split(":")[0] + ":00" : "07:00";

      if (!bucketMap[arrHour]) bucketMap[arrHour] = { arrivals: 0, departures: 0 };
      if (!bucketMap[depHour]) bucketMap[depHour] = { arrivals: 0, departures: 0 };

      bucketMap[arrHour].arrivals += 1;
      bucketMap[depHour].departures += 1;
    }
    return Object.entries(bucketMap).map(([hour, counts]) => ({
      hour,
      arrivals: counts.arrivals,
      departures: counts.departures,
    }));
  }, [stationKpiData?.monitored_trains]);

  // Station delay tiers
  const stationDelayTiers = useMemo<DelayTier[]>(() => {
    const trains = stationKpiData?.monitored_trains || [];
    const total = trains.length;
    if (total === 0) {
      return [
        { tier: "On Time (≤5m)", count: 0, pct: 0, tone: "good" },
        { tier: "5-15 min", count: 0, pct: 0, tone: "watch" },
        { tier: ">15 min", count: 0, pct: 0, tone: "bad" },
      ];
    }
    const onTime = trains.filter((t) => t.projected_delay_min <= 5).length;
    const minor = trains.filter((t) => t.projected_delay_min > 5 && t.projected_delay_min <= 15).length;
    const major = trains.filter((t) => t.projected_delay_min > 15).length;

    return [
      { tier: "On Time (≤5m)", count: onTime, pct: (onTime / total) * 100, tone: "good" },
      { tier: "5-15 min", count: minor, pct: (minor / total) * 100, tone: "watch" },
      { tier: ">15 min", count: major, pct: (major / total) * 100, tone: "bad" },
    ];
  }, [stationKpiData?.monitored_trains]);

  // Section delay tiers
  const sectionDelayTiers = useMemo<DelayTier[]>(() => {
    const active = sectionKpiData?.kpis.trains_active || 0;
    const delayed = sectionKpiData?.kpis.trains_delayed || 0;
    const onTime = Math.max(0, active - delayed);
    const total = Math.max(1, active);

    return [
      { tier: "On Time (≤5m)", count: onTime, pct: (onTime / total) * 100, tone: "good" },
      { tier: "Delayed", count: delayed, pct: (delayed / total) * 100, tone: delayed > 0 ? "bad" : "good" },
    ];
  }, [sectionKpiData?.kpis.trains_active, sectionKpiData?.kpis.trains_delayed]);

  const unackCriticalCount = useMemo(() => {
    return (sectionKpiData?.active_conflicts || []).filter(
      (c) => c.severity === "CRITICAL" || c.severity === "HIGH"
    ).length;
  }, [sectionKpiData?.active_conflicts]);

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

  const corridorStations = networkData?.network.stations || DEFAULT_STATIONS;
  const corridorSections = networkData?.network.sections || DEFAULT_SECTIONS;
  const corridorBlocks = networkData?.block_occupancy || data.occupied_blocks || [];
  const corridorTrains = data.trains || [];
  const corridorConflicts = sectionKpiData?.active_conflicts || data.conflicts || [];
  const currentStation = corridorStations.find((s) => s.id === stationId) || corridorStations[0];
  const inspectedStation = inspectStationId ? corridorStations.find((s) => s.id === inspectStationId) : null;

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

          {viewMode === "SECTION" && (
            <select
              className="select-small"
              value={selectedTerritory}
              onChange={(e) => setSelectedTerritory(e.target.value)}
              title="Select control territory"
              aria-label="Select control territory"
            >
              <option value="NDL-VSN Mainline Corridor (Southern Division)">NDL–VSN Mainline (Southern Div)</option>
              <option value="MLG Junction Suburban Branch Loop">MLG Suburban Branch Loop</option>
              <option value="KRN-SRP Quad Track Freight Bypass">KRN–SRP Quad Freight Bypass</option>
            </select>
          )}

          <StatusBadge status={data.simulation.status} />
          <span className="badge badge-muted">state v{data.simulation.state_version}</span>
        </div>
      </div>

      {/* Region A: Section Controller Control Office Header Bar */}
      {viewMode === "SECTION" && (
        <div
          className="section-controller-header flex-row justify-between items-center"
          style={{
            background: "#0F172A",
            color: "#F8FAFC",
            padding: "10px 16px",
            borderRadius: "8px",
            marginBottom: "12px",
            flexWrap: "wrap",
            gap: "12px",
            border: "1px solid #1E293B",
          }}
        >
          <div className="flex-row items-center gap-3">
            <span
              style={{
                fontSize: "0.82rem",
                fontWeight: 700,
                letterSpacing: "0.06em",
                color: "#38BDF8",
                textTransform: "uppercase",
              }}
            >
              CONTROL DESK: SC-402
            </span>
            <span style={{ color: "#64748B" }}>|</span>
            <span style={{ fontSize: "0.85rem", color: "#E2E8F0" }}>
              Territory: <strong>{selectedTerritory}</strong> (5 Stations, 4 Sections)
            </span>
            <span style={{ color: "#64748B" }}>|</span>
            <span className="badge" style={{ background: "#1E293B", color: "#94A3B8", fontSize: "0.74rem" }}>
              Day Shift 06:00–14:00
            </span>
          </div>

          <div className="flex-row items-center gap-3">
            <div className="flex-row items-center gap-2">
              <span className="small muted" style={{ color: "#94A3B8" }}>IST Clock:</span>
              <span className="mono" style={{ fontSize: "0.85rem", color: "#F1F5F9", fontWeight: 600 }}>
                {data.simulation.sim_time}:00 IST
              </span>
            </div>
            <div className="flex-row items-center gap-2">
              <span className="small muted" style={{ color: "#94A3B8" }}>Sim Time:</span>
              <span className="mono" style={{ fontSize: "0.85rem", color: "#38BDF8", fontWeight: 700 }}>
                T+{data.simulation.sim_time_min}m
              </span>
            </div>
            <span style={{ color: "#64748B" }}>|</span>
            <div className="flex-row items-center gap-2">
              <span
                className="badge"
                style={{
                  background: sectionKpiData?.data_freshness.status === "HEALTHY" ? "#065F46" : "#991B1B",
                  color: "#ECFDF5",
                  fontSize: "0.72rem",
                }}
              >
                ● {sectionKpiData?.data_freshness.status || "HEALTHY"} TELEMETRY
              </span>
              <span className="small mono" style={{ color: "#94A3B8", fontSize: "0.75rem" }}>
                {sectionKpiData?.data_freshness.freshness_seconds ?? 4.2}s latency
              </span>
            </div>
            <span style={{ color: "#64748B" }}>|</span>
            <span
              className="badge"
              style={{
                background: unackCriticalCount > 0 ? "#7F1D1D" : "#14532D",
                color: "#FEF2F2",
                fontWeight: 600,
                fontSize: "0.72rem",
              }}
            >
              {unackCriticalCount > 0 ? `⚠ ${unackCriticalCount} UNACKNOWLEDGED ALERTS` : "✓ ALL ALERTS ACKNOWLEDGED"}
            </span>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. STATION MASTER ROLE VIEW */}
      {/* ========================================================================= */}
      {viewMode === "STATION" && stationKpiData && (
        <>
          {/* Station Master 8 Standardized KPI Cards */}
          <div className="kpi-grid">
            <KpiCard
              label="Trains Monitored"
              value={stationKpiData.kpis.trains_monitored}
              hint={`${stationKpiData.kpis.delayed_trains} delayed trains`}
              tone={stationKpiData.kpis.delayed_trains > 0 ? "watch" : "good"}
              period={stationKpiData.time_period}
              source="Station Arrival Log"
              quality="MEASURED"
              tooltip="Total scheduled train movements active in station monitoring window"
            />
            <KpiCard
              label="Schedule Adherence"
              value={numberOrDash(stationKpiData.kpis.schedule_adherence_pct)}
              unit={stationKpiData.kpis.schedule_adherence_pct !== null ? "%" : ""}
              hint={
                stationKpiData.kpis.schedule_adherence_pct === null
                  ? "no trains in observation window"
                  : "trains within 5 min of schedule"
              }
              tone={
                stationKpiData.kpis.schedule_adherence_pct === null
                  ? "neutral"
                  : stationKpiData.kpis.schedule_adherence_pct < 75
                  ? "watch"
                  : "good"
              }
              period={stationKpiData.time_period}
              source="Railway Board 5m Criterion"
              quality={stationKpiData.kpis.schedule_adherence_pct !== null ? "CALCULATED" : "NO_DATA"}
              tooltip="Percentage of monitored trains within 5 minutes of scheduled timetable"
            />
            <KpiCard
              label="Platform Availability"
              value={numberOrDash(stationKpiData.kpis.platform_availability_pct)}
              unit="%"
              hint={`${stationKpiData.kpis.platforms_available} of ${stationKpiData.kpis.platforms_total} platforms free`}
              tone={stationKpiData.kpis.platforms_available === 0 ? "bad" : "good"}
              period="Current Instant"
              source="Station Interlocking"
              quality="MEASURED"
              tooltip="Percentage of passenger platforms currently unberthed and available"
            />
            <KpiCard
              label="Avg Arrival Delay"
              value={numberOrDash(stationKpiData.kpis.average_arrival_delay_min)}
              unit={stationKpiData.kpis.average_arrival_delay_min !== null ? " min" : ""}
              hint={
                stationKpiData.kpis.average_arrival_delay_min !== null
                  ? "approaching trains"
                  : "no approaching trains"
              }
              tone={
                stationKpiData.kpis.average_arrival_delay_min === null
                  ? "neutral"
                  : stationKpiData.kpis.average_arrival_delay_min > 10
                  ? "bad"
                  : "good"
              }
              period={stationKpiData.time_period}
              source="Section Block Radar"
              quality={stationKpiData.kpis.average_arrival_delay_min !== null ? "CALCULATED" : "NO_DATA"}
              tooltip="Mean arrival delay for trains approaching this station"
            />
            <KpiCard
              label="Avg Departure Delay"
              value={numberOrDash(stationKpiData.kpis.average_departure_delay_min)}
              unit={stationKpiData.kpis.average_departure_delay_min !== null ? " min" : ""}
              hint={
                stationKpiData.kpis.average_departure_delay_min !== null
                  ? "stationed departures"
                  : "no stationed trains"
              }
              tone={
                stationKpiData.kpis.average_departure_delay_min === null
                  ? "neutral"
                  : stationKpiData.kpis.average_departure_delay_min > 10
                  ? "bad"
                  : "good"
              }
              period={stationKpiData.time_period}
              source="Platform Berthing Ledger"
              quality={stationKpiData.kpis.average_departure_delay_min !== null ? "CALCULATED" : "NO_DATA"}
              tooltip="Mean departure delay for trains originating or turning at this station"
            />
            <KpiCard
              label="On-Time Trains"
              value={stationKpiData.kpis.on_time_trains}
              unit={` / ${stationKpiData.kpis.trains_monitored}`}
              hint="Arrivals within 5 min threshold"
              tone={stationKpiData.kpis.on_time_trains > 0 ? "good" : "neutral"}
              period={stationKpiData.time_period}
              source="Timetable Adherence"
              quality="MEASURED"
            />
            <KpiCard
              label="Station Alerts & Recs"
              value={stationKpiData.kpis.operational_alerts_count}
              hint={`${stationKpiData.kpis.pending_recommendations_count} pending local decisions`}
              tone={stationKpiData.kpis.operational_alerts_count > 0 ? "watch" : "good"}
              period="Active Window"
              source="Conflict Detector"
              quality="MEASURED"
              tooltip="Active platform conflicts and pending local dispatch decisions"
            />
            <KpiCard
              label="Pending Local Decisions"
              value={stationKpiData.kpis.pending_recommendations_count}
              hint="Station Master confirmation required"
              tone={stationKpiData.kpis.pending_recommendations_count > 0 ? "info" : "neutral"}
              period="Queue"
              source="CP-SAT Advisory"
              quality="CALCULATED"
            />
          </div>

          {/* Station Working & Interlocking Diagram */}
          <Panel
            title="Station Working & Interlocking Yard Diagram"
            subtitle={`Electronic Interlocking (EI) track layout, platforms, and turnouts for ${stationKpiData.station_name}`}
          >
            <StationWorkingDiagram
              station={currentStation}
              platforms={data.available_platforms || []}
              outages={data.platform_outages || []}
              trains={corridorTrains}
            />
          </Panel>

          {/* Station Train Arrival & Departure Board */}
          <Panel
            title="Station Train Arrival & Departure Board"
            subtitle={`Real-time passenger and operational train movements for ${stationKpiData.station_name}`}
            actions={
              <Link className="button button-small" to="/trains">
                Full Corridor Trains
              </Link>
            }
          >
            <StationTrainBoard
              stationId={stationId}
              stationName={stationKpiData.station_name}
              trains={corridorTrains}
            />
          </Panel>

          {/* Platform Berthing Status Visualizer */}
          <Panel
            title={`Live Platform Berthing Status — ${stationKpiData.station_name}`}
            subtitle={`${stationKpiData.kpis.platforms_available} available · ${stationKpiData.kpis.platforms_occupied} occupied · ${stationKpiData.kpis.platforms_outage} outage`}
          >
            <StationPlatformBerths
              stationName={stationKpiData.station_name}
              slots={stationKpiData.platform_slots}
            />
          </Panel>

          {/* Station Visual Analytics: Hourly Movements & Delay Distribution */}
          <div className="grid-two">
            <Panel
              title="Station Traffic Movements"
              subtitle="Scheduled and projected arrivals and departures by time window"
            >
              <HourlyMovementsChart
                data={stationMovementBuckets}
                title="Hourly Station Volumes"
                subtitle="Arrival and departure density"
              />
            </Panel>

            <Panel
              title="Station Delay Distribution"
              subtitle="Train punctuality classification according to operating guidelines"
            >
              <DelayDistributionChart
                tiers={stationDelayTiers}
                title="Punctuality Breakdown"
                subtitle="Distribution of trains by projected schedule deviation"
              />
            </Panel>
          </div>

          {/* Filterable Monitored Train Movements Table */}
          <Panel
            title="Monitored Train Movements"
            subtitle="Trains currently at station or scheduled within operational horizon"
            actions={
              <Link className="button button-small" to="/trains">
                Full Corridor Trains
              </Link>
            }
          >
            <div className="filter-row" style={{ marginBottom: "12px" }}>
              <Field label="Search Trains">
                <input
                  value={trainSearch}
                  onChange={(e) => setTrainSearch(e.target.value)}
                  placeholder="Train number, name or destination"
                />
              </Field>
              <Field label="Movement Status">
                <select
                  value={trainFilter}
                  onChange={(e) => setTrainFilter(e.target.value as typeof trainFilter)}
                >
                  <option value="ALL">All Monitored Trains</option>
                  <option value="APPROACHING">Approaching Station</option>
                  <option value="AT_STATION">At Platform Berth</option>
                  <option value="DELAYED">Delayed Only (&gt;0m)</option>
                </select>
              </Field>
              <div className="filter-count">
                <small className="muted">Showing</small>
                <strong>{filteredStationTrains.length} trains</strong>
              </div>
            </div>

            {filteredStationTrains.length === 0 ? (
              <EmptyState
                title="No matching train movements"
                description="No trains match the selected filters in this operational window."
              />
            ) : (
              <div className="table-wrapper" tabIndex={0} role="region" aria-label="Station train movements table">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Train</th>
                      <th>Direction</th>
                      <th>Type / Priority</th>
                      <th>Sched Arr</th>
                      <th>Sched Dep</th>
                      <th>Platform Berth</th>
                      <th>Delay</th>
                      <th>Operational Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStationTrains.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <strong>{t.name}</strong>
                          <span className="muted small d-block mono">{t.id}</span>
                        </td>
                        <td>
                          <Badge tone="muted">DEST: {t.destination}</Badge>
                        </td>
                        <td>
                          <Badge tone="muted">{t.train_type} (P{t.priority})</Badge>
                        </td>
                        <td>{t.scheduled_arrival || "—"}</td>
                        <td>{t.scheduled_departure || "—"}</td>
                        <td>
                          <strong>{t.platform ? `PF ${t.platform}` : "Unallocated"}</strong>
                        </td>
                        <td>
                          <span className={delayTone(t.projected_delay_min)}>
                            {t.projected_delay_min > 0 ? `+${t.projected_delay_min}m` : "On time"}
                          </span>
                        </td>
                        <td>
                          <Badge tone={t.is_at_station ? "good" : "muted"}>
                            {t.is_at_station ? "Berthed at Station" : "Approaching"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Station Decisions & Operational Alerts Queue */}
          <Panel
            title="Station Decisions & Alerts Queue"
            subtitle="Operational conflicts and AI advisory recommendations requiring Station Master confirmation"
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
              <div className="grid-two">
                <div className="stack">
                  <h4 style={{ margin: "0 0 8px", fontSize: "0.86rem", color: "#475569" }}>
                    Pending Advisory Recommendations ({stationKpiData.pending_recommendations.length})
                  </h4>
                  {stationKpiData.pending_recommendations.length === 0 ? (
                    <p className="small muted">No recommendations pending local review.</p>
                  ) : (
                    stationKpiData.pending_recommendations.map((r) => (
                      <div key={r.id} className="list-row" style={{ padding: "0.75rem", background: "#F8FAFC", borderRadius: "6px", border: "1px solid #E2E8F0" }}>
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
                    ))
                  )}
                </div>

                <div className="stack">
                  <h4 style={{ margin: "0 0 8px", fontSize: "0.86rem", color: "#475569" }}>
                    Active Track Conflicts & Alerts ({stationKpiData.operational_alerts.length})
                  </h4>
                  {stationKpiData.operational_alerts.length === 0 ? (
                    <p className="small muted">No platform or track occupancy conflicts detected.</p>
                  ) : (
                    stationKpiData.operational_alerts.map((c) => (
                      <div key={c.id} className="list-row" style={{ padding: "0.75rem", background: "#FEF2F2", borderRadius: "6px", border: "1px solid #FECACA" }}>
                        <div>
                          <strong>{c.type.replace(/_/g, " ")}</strong>
                          <p className="muted small" style={{ margin: "2px 0 0" }}>
                            Location: {c.location.label} · Trains: {c.trains.join(", ") || "None"}
                          </p>
                          <p className="muted small" style={{ margin: "2px 0 0" }}>
                            Window: {c.start && c.end ? `${c.start}–${c.end}` : "Immediate"}
                          </p>
                        </div>
                        <SeverityBadge severity={c.severity} />
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </Panel>
        </>
      )}

      {/* ========================================================================= */}
      {/* 2. SECTION CONTROLLER CORRIDOR VIEW */}
      {/* ========================================================================= */}
      {viewMode === "SECTION" && sectionKpiData && (
        <>
          {/* Region B: Section Controller 12 Standardized Corridor KPI Cards */}
          <div className="kpi-grid">
            <KpiCard
              label="Active Corridor Trains"
              value={sectionKpiData.kpis.trains_active}
              hint={`${sectionKpiData.kpis.trains_completed} completed · ${sectionKpiData.kpis.trains_scheduled} scheduled`}
              period={sectionKpiData.time_period}
              source="Corridor Block Tracking"
              quality="MEASURED"
              tooltip="Trains currently in transit or stationed on corridor tracks"
            />
            <KpiCard
              label="Average Section Delay"
              value={numberOrDash(sectionKpiData.kpis.average_section_delay_min)}
              unit=" min"
              hint={`Total delay: ${sectionKpiData.kpis.total_section_delay_min} min`}
              tone={
                sectionKpiData.kpis.average_section_delay_min > 15
                  ? "bad"
                  : sectionKpiData.kpis.average_section_delay_min > 5
                  ? "watch"
                  : "good"
              }
              period={sectionKpiData.time_period}
              source="Station Master OS Books"
              quality="CALCULATED"
              tooltip="Mean delay across all active and completed trains on this corridor"
            />
            <KpiCard
              label="Block Occupancy"
              value={numberOrDash(sectionKpiData.kpis.block_occupancy_pct)}
              unit="%"
              hint={`${sectionKpiData.kpis.blocks_occupied} of ${sectionKpiData.kpis.blocks_total} blocks busy`}
              tone={sectionKpiData.kpis.block_occupancy_pct > 60 ? "watch" : "good"}
              period="Current Instant"
              source="Track Circuits & Axle Counters"
              quality="MEASURED"
              tooltip="Percentage of block sections currently occupied by moving or stationed trains"
            />
            <KpiCard
              label="Junction Throat Load (MLG)"
              value={numberOrDash(sectionKpiData.kpis.junction_throat_load_pct)}
              unit="%"
              hint={`Queue: ${sectionKpiData.kpis.junction_queue_length} · Status: ${sectionKpiData.kpis.junction_congestion_level || sectionKpiData.junction_status?.congestion_level || "MODERATE"}`}
              tone={
                (sectionKpiData.kpis.junction_throat_load_pct ?? 0) >= 80
                  ? "bad"
                  : (sectionKpiData.kpis.junction_throat_load_pct ?? 0) >= 50
                  ? "watch"
                  : "good"
              }
              period="Simulated Horizon"
              source="Diamond Crossing Throat Model"
              quality="CALCULATED"
              tooltip="Capacity utilization of Malgaon diamond crossing throat (max 2 parallel moves)"
            />
            <KpiCard
              label="Corridor Throughput"
              value={numberOrDash(sectionKpiData.kpis.throughput_trains_per_hour)}
              unit=" tph"
              hint={`On-time adherence: ${sectionKpiData.kpis.on_time_performance_pct}%`}
              tone="good"
              period={sectionKpiData.time_period}
              source="Movement Realization"
              quality="CALCULATED"
              tooltip="Completed train passages per hour across section boundaries"
            />
            <KpiCard
              label="Delay Propagation (DPI)"
              value={numberOrDash(sectionKpiData.kpis.delay_propagation_index)}
              unit="x"
              hint={`Knock-on risk: ${sectionKpiData.kpis.knock_on_risk_level}`}
              tone={sectionKpiData.kpis.delay_propagation_index > 1.0 ? "bad" : "good"}
              period="Knock-on Window"
              source="Secondary Delay Model"
              quality="HEURISTIC"
              tooltip="Secondary Delay Minutes / Initial Schedule Delay Minutes (Advisory Simulation Heuristic)"
            />
            <KpiCard
              label="Delayed Corridor Trains"
              value={sectionKpiData.kpis.trains_delayed}
              unit={` / ${sectionKpiData.kpis.trains_active}`}
              hint={`${sectionKpiData.kpis.on_time_performance_pct}% on-time performance`}
              tone={sectionKpiData.kpis.trains_delayed > 0 ? "watch" : "good"}
              period={sectionKpiData.time_period}
              source="Section OS Data"
              quality="MEASURED"
            />
            <KpiCard
              label="Active Route Conflicts"
              value={sectionKpiData.kpis.conflicts_total}
              hint={`${sectionKpiData.kpis.conflicts_critical} critical · ${sectionKpiData.kpis.conflicts_major} major`}
              tone={sectionKpiData.kpis.conflicts_total > 0 ? "bad" : "good"}
              period="Active Window"
              source="Independent Validator"
              quality="MEASURED"
            />
            <KpiCard
              label="Recovery Clearance Rate"
              value={numberOrDash(sectionKpiData.kpis.recovery_clearance_rate_pct)}
              unit={sectionKpiData.kpis.recovery_clearance_rate_pct !== null ? "%" : ""}
              hint={
                sectionKpiData.kpis.recovery_clearance_rate_pct !== null
                  ? "Historical conflict clearance"
                  : "No historical conflicts recorded"
              }
              tone={sectionKpiData.kpis.recovery_clearance_rate_pct !== null ? "good" : "neutral"}
              period="Cumulative Session"
              source="Audit Resolution Trail"
              quality={sectionKpiData.kpis.recovery_clearance_rate_pct !== null ? "CALCULATED" : "NO_DATA"}
            />
            <KpiCard
              label="Running vs Berthed"
              value={`${corridorTrains.filter((t) => !t.station_id).length} / ${corridorTrains.filter((t) => !!t.station_id).length}`}
              hint="In Section / At Station Platforms"
              tone="neutral"
              period="Current Instant"
              source="Axle Counter & Station EI"
              quality="MEASURED"
              tooltip="Comparison of trains traversing block sections versus dwelling at station berths"
            />
            <KpiCard
              label="Active Speed Restrictions"
              value="3"
              unit=" TSR/PSR"
              hint="1 TSR (30 km/h) · 2 PSR (Loop/Bridge)"
              tone="watch"
              period="Current Bulletin"
              source="Engineering Caution Register"
              quality="MEASURED"
              tooltip="Permanent and temporary speed restrictions in effect across territory"
            />
            <KpiCard
              label="Pending Dispatch Decisions"
              value={sectionKpiData.pending_decisions.length}
              hint="Advisory CP-SAT / PPO options"
              tone={sectionKpiData.pending_decisions.length > 0 ? "watch" : "good"}
              period="Advisory Horizon"
              source="AI Regulation Workspace"
              quality="CALCULATED"
              tooltip="Automated regulation proposals requiring human Section Controller authorization"
            />
          </div>

          {/* Region C: Multi-Station Territory Control Strip */}
          <Panel
            title="Multi-Station Territory Control Strip"
            subtitle="Real-time multi-station oversight across Nandpur, Karanpur, Malgaon Junction, Suryapur, and Vasanthpur. Click any station card to inspect local interlocking and platform berths."
          >
            <StationControlStrip
              stations={corridorStations}
              trains={corridorTrains}
              platforms={data.available_platforms || []}
              outages={data.platform_outages || []}
              conflicts={corridorConflicts}
              closures={data.closures || []}
              selectedStationId={inspectStationId}
              onSelectStation={(stId) => setInspectStationId(inspectStationId === stId ? null : stId)}
            />
          </Panel>

          {/* Inline Station Inspection Console when a station is clicked */}
          {inspectStationId && inspectedStation && (
            <div
              className="station-inspection-modal"
              style={{
                background: "#F8FAFC",
                border: "2px solid #2563EB",
                borderRadius: "8px",
                padding: "16px",
                marginBottom: "20px",
              }}
            >
              <div
                className="flex-row justify-between items-center"
                style={{
                  marginBottom: "12px",
                  borderBottom: "1px solid #CBD5E1",
                  paddingBottom: "8px",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div>
                  <h3 style={{ margin: 0, color: "#1E293B", fontSize: "1.1rem" }}>
                    Station Master Yard Inspection — {inspectedStation.name} ({inspectedStation.id})
                  </h3>
                  <p className="muted small" style={{ margin: "2px 0 0" }}>
                    Direct Electronic Interlocking (EI) track layout, platform berthing status, and local movements for Section Controller oversight
                  </p>
                </div>
                <div className="flex-row gap-2">
                  <button
                    type="button"
                    className="button button-small button-ghost"
                    onClick={() => {
                      setStationId(inspectStationId);
                      setViewMode("STATION");
                    }}
                  >
                    Switch to Full Station Master View ↗
                  </button>
                  <button
                    type="button"
                    className="button button-small button-primary"
                    onClick={() => setInspectStationId(null)}
                  >
                    Close Station Inspection ✕
                  </button>
                </div>
              </div>
              <div className="stack">
                <StationWorkingDiagram
                  station={inspectedStation}
                  platforms={data.available_platforms || []}
                  outages={data.platform_outages || []}
                  trains={corridorTrains}
                />
                <div className="grid-two" style={{ marginTop: "12px" }}>
                  <StationPlatformBerths
                    stationName={inspectedStation.name}
                    slots={
                      inspectStationId === "MLG" && stationKpiData?.platform_slots
                        ? stationKpiData.platform_slots
                        : (inspectedStation.platforms || ["P1", "P2"]).map((p, idx) => ({
                            platform_id: p,
                            status: idx === 0 ? "OCCUPIED" : "AVAILABLE",
                            train_id: idx === 0 ? "EXP-101" : null,
                            description: idx === 0 ? "Occupied by Express" : "Clear and Signalled",
                          }))
                    }
                  />
                  <StationTrainBoard
                    stationId={inspectedStation.id}
                    stationName={inspectedStation.name}
                    trains={corridorTrains}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Workspace Navigator Tabs */}
          <div
            className="flex-row gap-2 items-center"
            style={{
              margin: "16px 0 12px",
              borderBottom: "2px solid #E2E8F0",
              paddingBottom: "8px",
              overflowX: "auto",
            }}
          >
            <span className="small muted" style={{ fontWeight: 600, marginRight: "8px" }}>
              CONTROL WORKSPACES:
            </span>
            {[
              { id: "ALL", label: "Master Console (All Workspaces)" },
              { id: "GRAPH", label: "Time-Distance Graph & Attention" },
              { id: "BLOCKS", label: "Corridor Blocks & Bottlenecks" },
              { id: "LEDGER", label: "Train Movement Ledger" },
              { id: "REGULATION", label: "Conflict & AI Regulation" },
              { id: "RESTRICTIONS", label: "TSR / PSR & Incidents" },
              { id: "HANDOVER", label: "Coordination & Shift Handover" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`button button-small ${activeSectionTab === tab.id ? "button-primary" : "button-ghost"}`}
                onClick={() => setActiveSectionTab(tab.id as typeof activeSectionTab)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* WORKSPACE 1: Master Time-Distance Graph & Operational Attention Panel */}
          {(activeSectionTab === "ALL" || activeSectionTab === "GRAPH") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              {/* Region D: Section Controller Master Time-Distance Train Graph */}
              <Panel
                title="Section Controller Time-Distance Train Graph"
                subtitle="Master string chart tracking corridor train trajectories, station dwell times, and single-line crossings"
              >
                <TimeDistanceGraph
                  stations={corridorStations}
                  sections={corridorSections}
                  trains={corridorTrains}
                  conflicts={corridorConflicts}
                  simTimeMin={data.simulation.sim_time_min}
                  simTimeString={data.simulation.sim_time}
                />
              </Panel>

              {/* Region E: Operational Attention Panel */}
              <OperationalAttentionPanel conflicts={corridorConflicts} />
            </div>
          )}

          {/* WORKSPACE 2: Corridor Blocks, Bottlenecks & Schematics */}
          {(activeSectionTab === "ALL" || activeSectionTab === "BLOCKS") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              {/* Real-time Horizontal Railway Corridor Schematic */}
              <Panel
                title="Corridor Traffic & Movement Schematic"
                subtitle="Real-time track layout, block occupancies, and train movements across Nandpur–Vasanthpur corridor"
              >
                <RailwayCorridorDiagram
                  stations={corridorStations}
                  sections={corridorSections}
                  blockOccupancy={corridorBlocks}
                  trains={corridorTrains}
                  conflicts={corridorConflicts}
                  selectedStationId={stationId}
                  onSelectStation={(st) => {
                    setStationId(st);
                    setViewMode("STATION");
                  }}
                />
              </Panel>

              {/* Corridor Block Section Occupancy Matrix */}
              <Panel
                title="Corridor Block Section Occupancy Matrix"
                subtitle="Absolute Block System status, axle counter detection, and line clear verification across all corridor blocks"
              >
                <BlockOccupancyMatrix
                  sections={corridorSections}
                  blockOccupancy={corridorBlocks}
                  trains={corridorTrains}
                />
              </Panel>

              {/* Visual Analytics: Corridor Delay Distribution & Junction Throat Bottlenecks */}
              <div className="grid-two">
                <Panel
                  title="Corridor Delay & Punctuality Breakdown"
                  subtitle="Comparison of active train movements running on schedule versus delayed"
                >
                  <DelayDistributionChart
                    tiers={sectionDelayTiers}
                    title="Corridor Punctuality Status"
                    subtitle="On-time vs Delayed Trains"
                  />
                </Panel>

                <Panel
                  title="Junction Congestion & Throat Bottlenecks"
                  subtitle="Real-time Malgaon (MLG) diamond crossing throat load and single-line queues"
                >
                  <div className="stack">
                    <div
                      className="metric-box flex-row justify-between items-center"
                      style={{ padding: "10px", background: "#F8FAFC", borderRadius: "6px", border: "1px solid #E2E8F0" }}
                    >
                      <div>
                        <strong>Malgaon Junction Throat</strong>
                        <p className="muted small" style={{ margin: 0 }}>
                          Capacity: {sectionKpiData.junction_status?.throat_capacity ?? 2} simultaneous diamond movements
                        </p>
                      </div>
                      <Badge
                        tone={
                          (sectionKpiData.junction_status?.congestion_level || sectionKpiData.kpis.junction_congestion_level) === "SATURATED"
                            ? "bad"
                            : (sectionKpiData.junction_status?.congestion_level || sectionKpiData.kpis.junction_congestion_level) === "HIGH"
                            ? "watch"
                            : "good"
                        }
                      >
                        {sectionKpiData.junction_status?.congestion_level || sectionKpiData.kpis.junction_congestion_level || "MODERATE"}
                      </Badge>
                    </div>

                    <div>
                      <small className="muted field-label">Single-Line Bottleneck Blocks Occupied</small>
                      {sectionKpiData.occupied_bottlenecks && sectionKpiData.occupied_bottlenecks.length > 0 ? (
                        <div className="flex-row gap-2 mt-1">
                          {sectionKpiData.occupied_bottlenecks.map((b) => (
                            <span key={b.block_id} className="badge badge-watch">
                              Block {b.block_id}: Train {b.train_id}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="small text-success" style={{ margin: "4px 0 0" }}>
                          All single-line bottlenecks (B1, B2, B4, B5) currently clear.
                        </p>
                      )}
                    </div>

                    <div>
                      <small className="muted field-label">
                        Active Throat Transits ({sectionKpiData.junction_status?.active_transits ?? 0}/2)
                      </small>
                      <p className="small" style={{ margin: "4px 0 0" }}>
                        {sectionKpiData.junction_status?.transiting_trains && sectionKpiData.junction_status.transiting_trains.length > 0
                          ? `Transiting: ${sectionKpiData.junction_status.transiting_trains.join(", ")}`
                          : "No active diamond crossings currently occupying throat."}
                      </p>
                    </div>
                  </div>
                </Panel>
              </div>
            </div>
          )}

          {/* WORKSPACE 3: Train Movement Ledger */}
          {(activeSectionTab === "ALL" || activeSectionTab === "LEDGER") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              <TrainMovementLedger
                trains={corridorTrains}
                stations={corridorStations}
                selectedTrainId={selectedLedgerTrainId}
                onSelectTrain={(id) => setSelectedLedgerTrainId(id === selectedLedgerTrainId ? null : id)}
              />

              {/* Active Corridor Trains Real-time Ledger */}
              <Panel
                title="Corridor Active Trains Ledger"
                subtitle="Movement progress, track locations, and projected delays across the corridor"
                actions={
                  <Link className="button button-small" to="/trains">
                    View Train Movements
                  </Link>
                }
              >
                {corridorTrains.length === 0 ? (
                  <EmptyState title="No active corridor trains" description="No trains currently running on corridor." />
                ) : (
                  <div className="table-wrapper" tabIndex={0} role="region" aria-label="Corridor active trains table">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Train</th>
                          <th>Type / Priority</th>
                          <th>Direction</th>
                          <th>Track Location</th>
                          <th>Delay</th>
                          <th>Waiting / Reason</th>
                          <th>Route Progress</th>
                        </tr>
                      </thead>
                      <tbody>
                        {corridorTrains.slice(0, 8).map((t) => (
                          <tr key={t.id}>
                            <td>
                              <strong>{t.name}</strong>
                              <span className="muted small d-block mono">{t.id}</span>
                            </td>
                            <td>
                              <Badge tone="muted">{t.train_type} (P{t.priority})</Badge>
                            </td>
                            <td>
                              <Badge tone="muted">{t.direction}</Badge>
                            </td>
                            <td>
                              {t.station_id ? (
                                <span>At Station <strong>{t.station_id}</strong> (PF {t.platform || "—"})</span>
                              ) : t.block_id ? (
                                <span>In Block <strong>{t.block_id}</strong> ({t.section_id})</span>
                              ) : (
                                <span className="muted">Pending Entry</span>
                              )}
                            </td>
                            <td>
                              <span className={delayTone(t.projected_delay_min)}>
                                {t.projected_delay_min > 0 ? `+${t.projected_delay_min}m` : "On time"}
                              </span>
                            </td>
                            <td>
                              {t.waiting_reason ? (
                                <span className="text-watch small">{t.waiting_reason}</span>
                              ) : (
                                <span className="muted small">Clear run</span>
                              )}
                            </td>
                            <td>
                              <span className="small muted mono">{t.origin} → {t.destination}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
            </div>
          )}

          {/* WORKSPACE 4: Conflict & AI Regulation Workspace */}
          {(activeSectionTab === "ALL" || activeSectionTab === "REGULATION") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              <ConflictRegulationWorkspace
                conflicts={corridorConflicts}
                pendingDecisions={sectionKpiData.pending_decisions || []}
                trains={corridorTrains}
                stations={corridorStations}
              />

              {/* Corridor Dispatch Decisions & Active Conflicts */}
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
                  <div className="grid-two">
                    <div className="stack">
                      <h4 style={{ margin: "0 0 8px", fontSize: "0.86rem", color: "#475569" }}>
                        Pending Dispatch Decisions ({sectionKpiData.pending_decisions.length})
                      </h4>
                      {sectionKpiData.pending_decisions.length === 0 ? (
                        <p className="small muted">No dispatch decisions pending review.</p>
                      ) : (
                        sectionKpiData.pending_decisions.map((d) => (
                          <div key={d.id} className="list-row" style={{ padding: "0.75rem", background: "#F8FAFC", borderRadius: "6px", border: "1px solid #E2E8F0" }}>
                            <div>
                              <Link to={`/recommendations/${d.id}`} className="list-title">
                                {d.label}
                              </Link>
                              <p className="muted small" style={{ margin: "2px 0 0" }}>
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
                        ))
                      )}
                    </div>

                    <div className="stack">
                      <h4 style={{ margin: "0 0 8px", fontSize: "0.86rem", color: "#475569" }}>
                        Active Corridor Conflicts ({sectionKpiData.active_conflicts.length})
                      </h4>
                      {sectionKpiData.active_conflicts.length === 0 ? (
                        <p className="small muted">No unresolved route or block conflicts.</p>
                      ) : (
                        sectionKpiData.active_conflicts.map((c) => (
                          <div key={c.id} className="list-row" style={{ padding: "0.75rem", background: "#FEF2F2", borderRadius: "6px", border: "1px solid #FECACA" }}>
                            <div>
                              <strong>{c.type.replace(/_/g, " ")}</strong>
                              <p className="muted small" style={{ margin: "2px 0 0" }}>
                                Location: {c.location.label} · Trains: {c.trains.join(", ") || "None"}
                              </p>
                              <p className="muted small" style={{ margin: "2px 0 0" }}>
                                Window: {c.start && c.end ? `${c.start}–${c.end}` : "Now"}
                              </p>
                            </div>
                            <SeverityBadge severity={c.severity} />
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </Panel>
            </div>
          )}

          {/* WORKSPACE 5: Engineering Restrictions & Incidents */}
          {(activeSectionTab === "ALL" || activeSectionTab === "RESTRICTIONS") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              <RestrictionsAndIncidentsPanel
                closures={data.closures || []}
                outages={data.platform_outages || []}
                stations={corridorStations}
              />
            </div>
          )}

          {/* WORKSPACE 6: Inter-Departmental Coordination & Shift Handover */}
          {(activeSectionTab === "ALL" || activeSectionTab === "HANDOVER") && (
            <div className="stack" style={{ marginBottom: "20px" }}>
              <CoordinationAndHandover
                territoryName={selectedTerritory}
                simTime={`${data.simulation.sim_time} IST`}
                activeTrainsCount={sectionKpiData.kpis.trains_active}
                delayedTrainsCount={sectionKpiData.kpis.trains_delayed}
                openConflictsCount={sectionKpiData.kpis.conflicts_total}
                activeRestrictionsCount={3}
                sectionId={selectedTerritory}
                controllerName="SC-402 (Day Shift)"
                shiftName="06:00 - 14:00 IST"
              />
            </div>
          )}
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
              ).map(([key, def]) => {
                const regKey = key.toLowerCase().replace(/[\s\(\)-]+/g, "_").replace(/_+$/, "");
                const regItem = Object.values(KPI_REGISTRY).find(
                  (k) => k.name.toLowerCase() === key.toLowerCase() || regKey.includes(k.id)
                );
                return (
                  <div key={key} style={{ padding: "0.5rem 0", borderBottom: "1px solid #F1F5F9" }}>
                    <div className="flex-row items-center gap-2">
                      <dt style={{ fontWeight: 600 }}>{key.replace(/_/g, " ")}</dt>
                      {regItem && (
                        <span className="badge badge-default" style={{ fontSize: "0.68rem" }}>
                          {regItem.classification} · {regItem.unit}
                        </span>
                      )}
                    </div>
                    <dd className="muted small" style={{ margin: "4px 0 0" }}>{def}</dd>
                    {regItem?.dataSource && (
                      <span className="small text-muted d-block" style={{ fontSize: "0.75rem", marginTop: "2px" }}>
                        Source: {regItem.dataSource} · Semantics: {regItem.missingDataSemantics}
                      </span>
                    )}
                  </div>
                );
              })}
            </dl>
          </div>
        )}
      </Panel>
    </div>
  );
}
