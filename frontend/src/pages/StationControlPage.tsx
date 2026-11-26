import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { numberOrDash } from "../lib/format";
import type { Network, Station, StationMasterKpis } from "../types";
import { EmptyState, ErrorBanner, KpiCard, Panel, Spinner } from "../components/ui";
import { StationWorkingDiagram } from "../components/StationWorkingDiagram";
import { StationPlatformBerths } from "../components/StationPlatformBerths";
import { StationTrainBoard } from "../components/StationTrainBoard";

const DEFAULT_STATIONS: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

export function StationControlPage() {
  const { selectedId, revision } = useSimulation();
  const [selectedStationId, setSelectedStationId] = useState<string>("MLG");

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: networkData } = useAsync<{ network: Network } | null>(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const [stationKpis, setStationKpis] = useState<StationMasterKpis | null>(null);

  useEffect(() => {
    if (!selectedId || !selectedStationId) return;
    api.stationKpis(selectedId, selectedStationId).then(setStationKpis).catch(() => {});
  }, [selectedId, revision, selectedStationId]);

  const stations = networkData?.network.stations || DEFAULT_STATIONS;
  const currentStation = stations.find((s) => s.id === selectedStationId) || stations[0];
  const trains = data?.trains || [];

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to inspect station yards and interlocking."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Station Control..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Station Yard Control & Interlocking Desk</h1>
            <span className="badge badge-accent">MULTI-STATION OVERSIGHT</span>
          </div>
          <p className="muted">
            Direct Electronic Interlocking (EI) track layout mirroring, platform berthing lines, and station train boards for all corridor stations
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Station Selector Bar */}
      <div
        className="flex-row justify-between items-center"
        style={{
          background: "#0F172A",
          color: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <div className="flex-row items-center gap-2">
          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase" }}>
            Select Station:
          </span>
          <div className="button-group">
            {stations.map((st) => (
              <button
                key={st.id}
                type="button"
                className={`button button-small ${selectedStationId === st.id ? "button-primary" : "button-ghost"}`}
                onClick={() => setSelectedStationId(st.id)}
              >
                {st.name} ({st.id}) {st.is_junction ? "★ JCN" : ""}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-row items-center gap-3">
          <span className="badge" style={{ background: "#1E293B", color: "#94A3B8" }}>
            Platforms: {(currentStation.platforms || []).length} Lines
          </span>
          <span className="badge" style={{ background: currentStation.is_junction ? "#4C1D95" : "#1E293B", color: "#EDE9FE" }}>
            {currentStation.is_junction ? "Diamond Crossing Junction" : "Way Station"}
          </span>
        </div>
      </div>

      {/* Station Operational KPIs */}
      {stationKpis && (
        <div className="kpi-grid">
          <KpiCard
            label="Trains Monitored"
            value={stationKpis.kpis.trains_monitored}
            hint={`${stationKpis.kpis.delayed_trains} delayed trains`}
            tone={stationKpis.kpis.delayed_trains > 0 ? "watch" : "good"}
            period={stationKpis.time_period}
            source="Station Arrival Log"
            quality="MEASURED"
          />
          <KpiCard
            label="Schedule Adherence"
            value={numberOrDash(stationKpis.kpis.schedule_adherence_pct)}
            unit={stationKpis.kpis.schedule_adherence_pct !== null ? "%" : ""}
            hint={
              stationKpis.kpis.schedule_adherence_pct === null
                ? "no trains in window"
                : "trains within 5 min"
            }
            tone={
              stationKpis.kpis.schedule_adherence_pct === null
                ? "neutral"
                : stationKpis.kpis.schedule_adherence_pct < 75
                ? "watch"
                : "good"
            }
            period={stationKpis.time_period}
            source="Railway Board 5m Criterion"
            quality={stationKpis.kpis.schedule_adherence_pct !== null ? "CALCULATED" : "NO_DATA"}
          />
          <KpiCard
            label="Platform Availability"
            value={numberOrDash(stationKpis.kpis.platform_availability_pct)}
            unit="%"
            hint={`${stationKpis.kpis.platforms_available} of ${stationKpis.kpis.platforms_total} platforms free`}
            tone={stationKpis.kpis.platforms_available > 0 ? "good" : "bad"}
            period="Current Instant"
            source="Station Relay Status"
            quality="MEASURED"
          />
          <KpiCard
            label="Average Arrival Delay"
            value={numberOrDash(stationKpis.kpis.average_arrival_delay_min)}
            unit=" min"
            hint="Scheduled vs actual arrival delay"
            tone="neutral"
            period={stationKpis.time_period}
            source="Station Movement Realization"
            quality="CALCULATED"
          />
        </div>
      )}

      {/* Yard Interlocking Diagram */}
      <Panel
        title={`Electronic Interlocking (EI) Track Layout — ${currentStation.name} (${currentStation.id})`}
        subtitle="Real-time track circuits, berthing lines, point positions, and clearing signals"
      >
        <StationWorkingDiagram
          station={currentStation}
          platforms={data.available_platforms || []}
          outages={data.platform_outages || []}
          trains={trains}
        />
      </Panel>

      {/* Platform Berths and Station Train Board */}
      <div className="grid-two">
        <Panel
          title={`Platform Berthing Status — ${currentStation.name}`}
          subtitle="Berth occupancy, fouling clear indications, and berthing assignments"
        >
          <StationPlatformBerths
            stationName={currentStation.name}
            slots={
              selectedStationId === "MLG" && stationKpis?.platform_slots
                ? stationKpis.platform_slots
                : (currentStation.platforms || ["P1", "P2"]).map((p, idx) => {
                    const occupyingTrain = trains.find((t) => t.station_id === currentStation.id && t.platform === p);
                    return {
                      platform_id: p,
                      status: occupyingTrain ? "OCCUPIED" : "AVAILABLE",
                      train_id: occupyingTrain ? occupyingTrain.id : null,
                      description: occupyingTrain
                        ? `Occupied by ${occupyingTrain.name} (${occupyingTrain.train_type})`
                        : "Clear and Signalled",
                    };
                  })
            }
          />
        </Panel>

        <Panel
          title={`Station Train Board — ${currentStation.name}`}
          subtitle="Live sequencing of approaching, dwelling, and departing trains"
        >
          <StationTrainBoard
            stationId={currentStation.id}
            stationName={currentStation.name}
            trains={trains}
          />
        </Panel>
      </div>
    </div>
  );
}
