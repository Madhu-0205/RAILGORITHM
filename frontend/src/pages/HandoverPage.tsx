import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { EmptyState, ErrorBanner, Panel, Spinner } from "../components/ui";
import { CoordinationAndHandover } from "../components/CoordinationAndHandover";

export function HandoverPage() {
  const { selectedId, revision } = useSimulation();

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: sectionKpis } = useAsync(
    () => (selectedId ? api.sectionKpis(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to manage shift handover protocols."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Shift Handover Desk..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  const activeTrains = sectionKpis?.kpis.trains_active ?? (data.trains || []).length;
  const delayedTrains = sectionKpis?.kpis.trains_delayed ?? (data.trains || []).filter((t) => t.projected_delay_min > 0).length;
  const openConflicts = sectionKpis?.kpis.conflicts_total ?? (data.conflicts || []).length;
  const closuresCount = (data.closures || []).length;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Section Controller Shift Handover Protocol</h1>
            <span className="badge badge-accent">CONTINUITY OF OPERATIONS</span>
          </div>
          <p className="muted">
            Indian Railways Traffic Operating Code · Formal shift transfer desk, statutory verification checklist, and inter-departmental diary
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Main Coordination and Handover Component */}
      <CoordinationAndHandover
        territoryName="NDL–VSN Mainline Corridor (Southern Division)"
        simTime={`${data.simulation.sim_time} IST`}
        activeTrainsCount={activeTrains}
        delayedTrainsCount={delayedTrains}
        openConflictsCount={openConflicts}
        activeRestrictionsCount={closuresCount + 3}
        sectionId="NDL-VSN"
        controllerName="SC-402 (Day Shift)"
        shiftName="Day Shift 06:00 – 14:00 IST"
      />
    </div>
  );
}
