import { useMemo, useState } from "react";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { delayTone, titleCase } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Field,
  Panel,
  Spinner,
  StatusBadge,
} from "../components/ui";

const STATUSES = ["ALL", "AT_STATION", "RUNNING", "COMPLETED"];

export function TrainsPage() {
  const { selectedId, revision } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.trains(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const [status, setStatus] = useState("ALL");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<"delay" | "id" | "status">("delay");

  const trains = useMemo(() => {
    const list = data?.trains ?? [];
    return list
      .filter((train) => status === "ALL" || train.status === status)
      .filter((train) => {
        const needle = query.trim().toLowerCase();
        if (!needle) return true;
        return (
          train.id.toLowerCase().includes(needle) ||
          train.name.toLowerCase().includes(needle) ||
          train.route.join(" ").toLowerCase().includes(needle)
        );
      })
      .sort((a, b) => {
        if (sort === "delay") return b.projected_delay_min - a.projected_delay_min;
        if (sort === "status") return a.status.localeCompare(b.status);
        return a.id.localeCompare(b.id);
      });
  }, [data, status, query, sort]);

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading) return <Spinner label="Loading train movements" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Train movements</h1>
          <p className="muted">
            {data?.trains.length ?? 0} trains at simulated time {data?.sim_time} · state v
            {data?.state_version}
          </p>
        </div>
      </div>

      <Panel>
        <div className="filter-row">
          <Field label="Search">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Train number, name or station"
            />
          </Field>
          <Field label="Status">
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {item === "ALL" ? "All statuses" : titleCase(item)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Sort by">
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as typeof sort)}
            >
              <option value="delay">Highest projected delay</option>
              <option value="id">Train number</option>
              <option value="status">Status</option>
            </select>
          </Field>
        </div>

        {trains.length === 0 ? (
          <EmptyState title="No trains match the filters" />
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Train</th>
                  <th>Type / priority</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Schedule</th>
                  <th>Delay</th>
                  <th>Waiting</th>
                  <th>Route</th>
                </tr>
              </thead>
              <tbody>
                {trains.map((train) => (
                  <tr key={train.id}>
                    <td>
                      <strong>{train.id}</strong>
                      <div className="muted small">{train.name}</div>
                    </td>
                    <td>
                      {train.train_type}
                      <div className="muted small">
                        priority {train.effective_priority}
                        {train.effective_priority !== train.priority && " (override)"}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={train.status} />
                    </td>
                    <td>
                      {train.station_id ? (
                        <>
                          <strong>{train.station_id}</strong>
                          {train.platform && <span className="muted"> / {train.platform}</span>}
                        </>
                      ) : train.block_id ? (
                        <>
                          Block <strong>{train.block_id}</strong>
                          <div className="muted small">→ {train.next_station}</div>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <div className="small">
                        dep {train.scheduled_departure ?? "—"}
                      </div>
                      <div className="small muted">
                        next arr {train.scheduled_arrival_next ?? "—"}
                      </div>
                    </td>
                    <td className={delayTone(train.projected_delay_min)}>
                      <strong>+{train.projected_delay_min} min</strong>
                      <div className="muted small">actual +{train.delay_min}</div>
                    </td>
                    <td>
                      {train.waiting_reason ? (
                        <>
                          <span className="badge badge-muted">
                            {titleCase(train.waiting_reason)}
                          </span>
                          <div className="muted small">{train.total_wait_min} min total</div>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="small">{train.route.join(" → ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Movement legend" subtitle="Statuses are simulated, not live feeds.">
        <div className="legend">
          <span><StatusBadge status="AT_STATION" /> waiting at a platform</span>
          <span><StatusBadge status="RUNNING" /> occupying a block</span>
          <span><StatusBadge status="COMPLETED" /> journey finished</span>
          <span className="muted">
            All times are simulated clock times on a synthetic scenario date.
          </span>
        </div>
      </Panel>
    </div>
  );
}
