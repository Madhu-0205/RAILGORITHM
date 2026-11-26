import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatMinutes } from "../lib/format";
import type { Network, Section, Station } from "../types";
import { EmptyState, ErrorBanner, Panel, Spinner } from "../components/ui";
import { TimeDistanceGraph } from "../components/TimeDistanceGraph";

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

export function MasterControlGraphPage() {
  const { selectedId, revision } = useSimulation();
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: networkData } = useAsync<{ network: Network } | null>(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const corridorStations = networkData?.network.stations || DEFAULT_STATIONS;
  const corridorSections = networkData?.network.sections || DEFAULT_SECTIONS;
  const rawTrains = data?.trains || [];
  const corridorConflicts = data?.conflicts || [];

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to view the Master Time-Distance Graph."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Master Control Graph..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Master Train Control Graph</h1>
            <span className="badge badge-accent">FULL CORRIDOR STRING CHART</span>
          </div>
          <p className="muted">
            Continuous time-distance trajectory plots across Nandpur (km 0) to Vasanthpur (km 100) · Indian Railways Control Office Standard
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Main Full-Viewport String Chart with Redesigned High-Contrast Filter Toolbar */}
      <Panel
        title="Time-Distance Trajectory Workspace"
        subtitle="Upward sloping lines = UP trains (NDL → VSN). Downward sloping lines = DOWN trains (VSN → NDL). Flat horizontal segments = Station dwell / loop wait."
      >
        <TimeDistanceGraph
          stations={corridorStations}
          sections={corridorSections}
          trains={rawTrains}
          conflicts={corridorConflicts}
          simTimeMin={data.simulation.sim_time_min}
          simTimeString={data.simulation.sim_time}
          onSelectTrain={setSelectedTrainId}
          selectedTrainId={selectedTrainId || undefined}
          onRefresh={reload}
        />
      </Panel>

      {/* Tabular Milestone and Passing Time Fallback Ledger */}
      <Panel
        title="Corridor Train Path & Milestone Schedule Ledger"
        subtitle="Detailed passing times, station dwell durations, and projected delays for active paths"
      >
        <div className="table-wrapper" tabIndex={0} role="region" aria-label="Master graph train ledger">
          <table className="table">
            <thead>
              <tr>
                <th>Train</th>
                <th>Type / Priority</th>
                <th>Direction</th>
                <th>Origin → Dest</th>
                <th>Current Status</th>
                <th>Current Delay</th>
                <th>Waiting Reason</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rawTrains.map((t) => (
                <tr
                  key={t.id}
                  style={selectedTrainId === t.id ? { background: "var(--panel-strong)" } : undefined}
                >
                  <td>
                    <strong>{t.name}</strong>
                    <span className="muted small d-block mono">{t.id}</span>
                  </td>
                  <td>
                    <span className="badge badge-muted">
                      {t.train_type} (P{t.priority})
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${t.direction === "UP" ? "badge-accent" : "badge-default"}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td className="small mono">
                    {t.origin} → {t.destination}
                  </td>
                  <td>
                    {t.station_id ? (
                      <span className="text-success">At {t.station_id} (PF {t.platform || "—"})</span>
                    ) : t.block_id ? (
                      <span>In Block {t.block_id}</span>
                    ) : (
                      <span className="muted">En route</span>
                    )}
                  </td>
                  <td>
                    <span className={t.projected_delay_min > 0 ? "text-danger" : "text-success"}>
                      {t.projected_delay_min > 0 ? `+${t.projected_delay_min} min` : "On time"}
                    </span>
                  </td>
                  <td className="small">
                    {t.waiting_reason ? (
                      <span className="text-watch">{t.waiting_reason}</span>
                    ) : (
                      <span className="muted">Clear run</span>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="button button-small button-ghost"
                      onClick={() => setSelectedTrainId(selectedTrainId === t.id ? null : t.id)}
                    >
                      {selectedTrainId === t.id ? "Deselect" : "Track Path"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
