import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { delayTone, formatMinutes, numberOrDash, titleCase } from "../lib/format";
import {
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
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

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

  const { metrics, model_status: modelStatus } = data;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Section overview</h1>
          <p className="muted">
            {data.simulation.name} · {data.simulation.scenario_key.replace(/_/g, " ")} ·
            simulated clock {data.simulation.sim_time} IST
          </p>
        </div>
        <div className="heading-badges">
          <StatusBadge status={data.simulation.status} />
          <span className="badge badge-muted">state v{data.simulation.state_version}</span>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard
          label="Active trains"
          value={metrics.trains_active}
          hint={`${metrics.trains_completed} completed`}
        />
        <KpiCard
          label="Average delay"
          value={numberOrDash(metrics.average_delay_min)}
          unit=" min"
          tone={metrics.average_delay_min > 15 ? "bad" : metrics.average_delay_min > 5 ? "watch" : "good"}
          hint={`max ${metrics.max_delay_min} min`}
        />
        <KpiCard
          label="On-time performance"
          value={numberOrDash(metrics.on_time_performance_pct)}
          unit="%"
          tone={metrics.on_time_performance_pct < 70 ? "watch" : "good"}
          hint="completed arrivals ≤ 5 min late"
        />
        <KpiCard
          label="Active conflicts"
          value={data.conflict_count}
          tone={data.conflict_count > 0 ? "bad" : "good"}
          hint={`${data.pending_recommendation_count} pending recommendation(s)`}
        />
        <KpiCard
          label="Section utilisation"
          value={numberOrDash(metrics.section_utilization_pct)}
          unit="%"
          hint="block occupancy over elapsed time"
        />
        <KpiCard
          label="Throughput"
          value={numberOrDash(metrics.throughput_trains_per_hour)}
          unit=" tph"
          hint="completed trains per simulated hour"
        />
      </div>

      <div className="grid-two">
        <Panel
          title="Model status"
          subtitle="What produced this evidence, and what did not."
        >
          <div className="model-status">
            <div>
              <span className="field-label">PPO candidate ranker</span>
              <strong>
                {modelStatus.ppo.trained ? "Trained artifact loaded" : "Not trained"}
              </strong>
              <span className="badge badge-muted">{modelStatus.ppo.model_version}</span>
              {modelStatus.ppo.reason && (
                <p className="muted small">{modelStatus.ppo.reason}</p>
              )}
            </div>
            <div>
              <span className="field-label">CP-SAT optimizer</span>
              <strong>Deterministic feasibility solver</strong>
              <span className="badge badge-muted">{modelStatus.cpsat.version}</span>
              <p className="muted small">
                Not a trained model. Schedules are independently re-validated.
              </p>
            </div>
          </div>
          {modelStatus.ppo.trained && modelStatus.ppo.evaluation && (
            <dl className="mini-stats">
              <div>
                <dt>Top-1 matches measured best</dt>
                <dd>
                  {String(
                    modelStatus.ppo.evaluation[
                      "policy_top1_matches_measured_best_pct"
                    ] ?? "—",
                  )}
                  %
                </dd>
              </div>
              <div>
                <dt>Mean regret vs best</dt>
                <dd>
                  {String(modelStatus.ppo.evaluation["mean_regret_vs_best"] ?? "—")}
                </dd>
              </div>
              <div>
                <dt>Baseline mean regret</dt>
                <dd>
                  {String(
                    modelStatus.ppo.evaluation["baseline_mean_regret_vs_best"] ?? "—",
                  )}
                </dd>
              </div>
            </dl>
          )}
        </Panel>

        <Panel
          title="Pending human decisions"
          subtitle="Nothing is applied without explicit controller approval."
          actions={
            <Link className="button button-small" to="/recommendations">
              Open queue
            </Link>
          }
        >
          {data.pending_recommendations.length === 0 ? (
            <EmptyState
              title="No pending recommendations"
              description="Generate advice from the AI Recommendations screen when a conflict needs attention."
            />
          ) : (
            <ul className="list">
              {data.pending_recommendations.map((item) => (
                <li key={item.id} className="list-row">
                  <div>
                    <Link to={`/recommendations/${item.id}`} className="list-title">
                      {item.recommended_label ?? "No executable recommendation"}
                    </Link>
                    <p className="muted small">{item.headline}</p>
                    <span className="muted small">
                      {item.sim_time} · state v{item.state_version} ·{" "}
                      {item.affected_stations.join(", ") || "no station scope"}
                    </span>
                  </div>
                  <div className="list-side">
                    <EvidenceBadge status={item.evidence_status} />
                    {item.is_stale && <span className="badge badge-danger">STALE</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid-two">
        <Panel
          title="Active conflicts"
          subtitle="Projected from the current simulated state, not real signalling."
          actions={
            <Link className="button button-small" to="/conflicts">
              All conflicts
            </Link>
          }
        >
          {data.conflicts.length === 0 ? (
            <EmptyState title="No projected conflicts in the horizon" />
          ) : (
            <ul className="list">
              {data.conflicts.slice(0, 6).map((conflict) => (
                <li key={conflict.id} className="list-row">
                  <div>
                    <div className="row-inline">
                      <SeverityBadge severity={conflict.severity} />
                      <strong>{titleCase(conflict.type)}</strong>
                      <span className="muted small">
                        {conflict.start}–{conflict.end}
                      </span>
                    </div>
                    <p className="small">{conflict.description}</p>
                    <span className="muted small">
                      {conflict.location.label} · {conflict.trains.join(", ")}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Delayed trains"
          subtitle="Projected delay if no intervention is made."
        >
          {data.delayed_trains.length === 0 ? (
            <EmptyState title="No train projected over 5 minutes late" />
          ) : (
            <table className="table compact">
              <thead>
                <tr>
                  <th>Train</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Delay</th>
                </tr>
              </thead>
              <tbody>
                {data.delayed_trains.map((train) => (
                  <tr key={train.id}>
                    <td>
                      <strong>{train.id}</strong>
                      <div className="muted small">{train.name}</div>
                    </td>
                    <td>{train.train_type}</td>
                    <td>
                      <StatusBadge status={train.status} />
                    </td>
                    <td className={delayTone(train.projected_delay_min)}>
                      +{train.projected_delay_min} min
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </div>

      <div className="grid-two">
        <Panel title="Infrastructure status">
          <div className="mini-stats">
            <div>
              <dt>Occupied blocks</dt>
              <dd>{data.occupied_blocks.length}</dd>
            </div>
            <div>
              <dt>Available platforms</dt>
              <dd>{data.available_platforms.length}</dd>
            </div>
            <div>
              <dt>Active closures</dt>
              <dd>{data.active_closures.length}</dd>
            </div>
            <div>
              <dt>Upcoming closures</dt>
              <dd>{data.upcoming_closures.length}</dd>
            </div>
            <div>
              <dt>Active platform outages</dt>
              <dd>{data.active_outages.length}</dd>
            </div>
          </div>
        </Panel>

        <Panel title="Recent simulation events" subtitle="Synthetic event log.">
          {data.metrics ? (
            <ul className="timeline">
              {data.trains
                .filter((train) => train.waiting_reason)
                .slice(0, 5)
                .map((train) => (
                  <li key={train.id}>
                    <span className="timeline-time">{formatMinutes(data.simulation.sim_time_min)}</span>
                    <span>
                      <strong>{train.id}</strong> {train.waiting_reason?.replace(/_/g, " ").toLowerCase()}
                    </span>
                  </li>
                ))}
              {data.active_closures.map((closure) => (
                <li key={closure.id}>
                  <span className="timeline-time">
                    {formatMinutes(closure.start_min)}–{formatMinutes(closure.end_min)}
                  </span>
                  <span>
                    Block <strong>{closure.block_id}</strong> closed: {closure.reason}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
