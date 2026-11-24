import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { delayTone, numberOrDash, titleCase } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  KpiCard,
  Panel,
  SeverityBadge,
  Spinner,
} from "../components/ui";

export function AnalyticsPage() {
  const { selectedId, revision } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.analytics(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading) return <Spinner label="Computing analytics" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  const stats = data.recommendation_stats;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Analytics</h1>
          <p className="muted">
            {data.scenario_name} · simulated {data.simulation_time} · state v{data.state_version}
          </p>
        </div>
        <span className="badge badge-muted">{data.label}</span>
      </div>

      <div className="banner banner-warning">{data.data_disclaimer}</div>

      <div className="kpi-grid">
        <KpiCard
          label="Average delay"
          value={numberOrDash(data.kpis.average_delay_min)}
          unit=" min"
          tone={data.kpis.average_delay_min > 15 ? "bad" : data.kpis.average_delay_min > 5 ? "watch" : "good"}
        />
        <KpiCard
          label="Total delay"
          value={numberOrDash(data.kpis.total_delay_min)}
          unit=" min"
        />
        <KpiCard
          label="On-time performance"
          value={numberOrDash(data.kpis.on_time_performance_pct)}
          unit="%"
          tone={data.kpis.on_time_performance_pct < 70 ? "watch" : "good"}
        />
        <KpiCard
          label="Throughput"
          value={numberOrDash(data.kpis.throughput_trains_per_hour)}
          unit=" tph"
        />
        <KpiCard
          label="Section utilisation"
          value={numberOrDash(data.kpis.section_utilization_pct)}
          unit="%"
        />
        <KpiCard
          label="Active conflicts"
          value={data.kpis.conflict_frequency_active}
          tone={data.kpis.conflict_frequency_active > 0 ? "bad" : "good"}
        />
      </div>

      <div className="grid-two">
        <Panel title="Section utilisation" subtitle="Block busy minutes over elapsed time.">
          <div className="bar-list">
            {data.section_utilization.map((section) => (
              <div key={section.section_id} className="bar-row">
                <span className="bar-label">
                  {section.label} <small className="muted">{section.mode}</small>
                </span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${Math.min(100, section.utilization_pct)}%` }}
                  />
                </div>
                <span className="bar-value">{numberOrDash(section.utilization_pct)}%</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Platform utilisation" subtitle="Platform busy minutes over elapsed time.">
          <div className="bar-list">
            {data.platform_utilization.map((station) => (
              <div key={station.station_id} className="bar-row">
                <span className="bar-label">{station.label}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill bar-fill-alt"
                    style={{ width: `${Math.min(100, station.utilization_pct)}%` }}
                  />
                </div>
                <span className="bar-value">{numberOrDash(station.utilization_pct)}%</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid-two">
        <Panel title="Human decision statistics" subtitle="Recorded controller decisions.">
          <dl className="detail-list">
            <div>
              <dt>Recommendations generated</dt>
              <dd>{stats.total ?? 0}</dd>
            </div>
            <div>
              <dt>Pending</dt>
              <dd>{stats.pending ?? 0}</dd>
            </div>
            <div>
              <dt>Decisions recorded</dt>
              <dd>{stats.decided_count ?? 0}</dd>
            </div>
            <div>
              <dt>Approved</dt>
              <dd>{stats.approved ?? 0}</dd>
            </div>
            <div>
              <dt>Modified</dt>
              <dd>{stats.modified ?? 0}</dd>
            </div>
            <div>
              <dt>Rejected</dt>
              <dd>{stats.rejected ?? 0}</dd>
            </div>
            <div>
              <dt>Acceptance rate</dt>
              <dd>{stats.acceptance_rate_pct === null ? "—" : `${stats.acceptance_rate_pct}%`}</dd>
            </div>
            <div>
              <dt>Modification rate</dt>
              <dd>
                {stats.modification_rate_pct === null ? "—" : `${stats.modification_rate_pct}%`}
              </dd>
            </div>
          </dl>
          <p className="muted small">
            Acceptance rate counts approvals and modifications over decisions that were
            approved, modified or rejected. Deferrals and alternative requests are excluded.
          </p>
        </Panel>

        <Panel title="Active conflicts" subtitle="Non-delay-risk conflicts in the horizon.">
          {data.conflicts.length === 0 ? (
            <p className="muted">No active conflicts.</p>
          ) : (
            <ul className="list">
              {data.conflicts.map((conflict) => (
                <li key={conflict.id} className="list-row">
                  <div>
                    <div className="row-inline">
                      <SeverityBadge severity={conflict.severity} />
                      <strong>{titleCase(conflict.type)}</strong>
                    </div>
                    <p className="small">{conflict.description}</p>
                    <span className="muted small">{conflict.location.label}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title="Train delays" subtitle="Actual and projected delay per train.">
        <div className="table-scroll">
          <table className="table compact">
            <thead>
              <tr>
                <th>Train</th>
                <th>Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Actual delay</th>
                <th>Projected delay</th>
              </tr>
            </thead>
            <tbody>
              {[...data.train_delays]
                .sort((a, b) => b.projected_delay_min - a.projected_delay_min)
                .map((train) => (
                  <tr key={train.train_id}>
                    <td>
                      <strong>{train.train_id}</strong>
                      <div className="muted small">{train.name}</div>
                    </td>
                    <td>{train.train_type}</td>
                    <td>{train.priority}</td>
                    <td>{titleCase(train.status)}</td>
                    <td>+{train.delay_min} min</td>
                    <td className={delayTone(train.projected_delay_min)}>
                      +{train.projected_delay_min} min
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Latest recommendation comparison">
        {data.latest_recommendation_comparison ? (
          <pre className="code-block">
            {JSON.stringify(data.latest_recommendation_comparison, null, 2)}
          </pre>
        ) : (
          <p className="muted">No recommendation has been generated for this simulation yet.</p>
        )}
        <p className="muted small">{data.comparison_note}</p>
      </Panel>
    </div>
  );
}
