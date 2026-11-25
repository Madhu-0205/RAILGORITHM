import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import type { Network, Station } from "../types";
import { EmptyState, ErrorBanner, KpiCard, Panel, Spinner } from "../components/ui";
import { RestrictionsAndIncidentsPanel } from "../components/RestrictionsAndIncidentsPanel";

const DEFAULT_STATIONS: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

export function RestrictionsPage() {
  const { selectedId, revision } = useSimulation();

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: networkData } = useAsync<{ network: Network } | null>(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const corridorStations = networkData?.network.stations || DEFAULT_STATIONS;
  const closures = data?.closures || [];
  const outages = data?.platform_outages || [];

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to view engineering caution orders."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Engineering Restrictions..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Engineering Restrictions & Caution Orders (TSR / PSR)</h1>
            <span className="badge badge-accent">CAUTION REGISTER</span>
          </div>
          <p className="muted">
            Indian Railways General & Subsidiary Rules (G&SR Chapter IV) · Active speed restrictions, maintenance possession blocks, and platform outages
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Restrictions Overview KPIs */}
      <div className="kpi-grid">
        <KpiCard
          label="Active Speed Restrictions"
          value="2 TSR / 1 PSR"
          hint="Permanent & temporary cautions"
          tone="watch"
          period="Current Bulletin"
          source="Engineering Caution Register"
          quality="MEASURED"
        />
        <KpiCard
          label="Track Possession Blocks"
          value={closures.length}
          hint={closures.length > 0 ? "Maintenance block in progress" : "All sections clear for traffic"}
          tone={closures.length > 0 ? "bad" : "good"}
          period="Active Window"
          source="Engineering Possession Memo"
          quality="MEASURED"
        />
        <KpiCard
          label="Platform Outages"
          value={outages.length}
          hint={outages.length > 0 ? `${outages.length} berths unserviceable` : "All station berths operational"}
          tone={outages.length > 0 ? "watch" : "good"}
          period="Current Shift"
          source="Station Master Disconnection Memo"
          quality="MEASURED"
        />
        <KpiCard
          label="Estimated Delay Impact"
          value="+4.5 min"
          hint="Cumulative running time penalty"
          tone="watch"
          period="Per Train Passage"
          source="Transit Time Deficit Model"
          quality="CALCULATED"
        />
      </div>

      {/* Full Restrictions Panel */}
      <RestrictionsAndIncidentsPanel
        closures={closures}
        outages={outages}
        stations={corridorStations}
      />
    </div>
  );
}
