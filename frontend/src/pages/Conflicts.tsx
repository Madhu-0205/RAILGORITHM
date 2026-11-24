import { useMemo, useState } from "react";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatMinutes, titleCase } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Field,
  Panel,
  SeverityBadge,
  Spinner,
} from "../components/ui";

const SEVERITIES = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export function ConflictsPage() {
  const { selectedId, revision } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.conflicts(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const [severity, setSeverity] = useState("ALL");
  const [type, setType] = useState("ALL");
  const [selected, setSelected] = useState<string | null>(null);

  const conflicts = useMemo(() => {
    const list = data?.conflicts ?? [];
    return list.filter(
      (conflict) =>
        (severity === "ALL" || conflict.severity === severity) &&
        (type === "ALL" || conflict.type === type),
    );
  }, [data, severity, type]);

  const types = useMemo(
    () => Array.from(new Set((data?.conflicts ?? []).map((item) => item.type))).sort(),
    [data],
  );

  const active = conflicts.find((item) => item.id === selected) ?? conflicts[0] ?? null;

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading) return <Spinner label="Detecting conflicts" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Conflict detection</h1>
          <p className="muted">
            {data?.conflicts.length ?? 0} projected conflicts at {formatMinutes(data?.sim_time)} ·{" "}
            {data?.scope_filtered ? "filtered to your station scope" : "full section scope"}
          </p>
        </div>
      </div>

      <Panel>
        <div className="filter-row">
          <Field label="Severity">
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              {SEVERITIES.map((item) => (
                <option key={item} value={item}>
                  {item === "ALL" ? "All severities" : item}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Conflict type">
            <select value={type} onChange={(event) => setType(event.target.value)}>
              <option value="ALL">All types</option>
              {types.map((item) => (
                <option key={item} value={item}>
                  {titleCase(item)}
                </option>
              ))}
            </select>
          </Field>
          <div className="filter-count">
            <span className="field-label">Shown</span>
            <strong>{conflicts.length}</strong>
          </div>
        </div>

        {conflicts.length === 0 ? (
          <EmptyState
            title="No conflicts in the current horizon"
            description="Conflict detection runs on the projected simulated state."
          />
        ) : (
          <div className="split">
            <ul className="conflict-list">
              {conflicts.map((conflict) => (
                <li key={conflict.id}>
                  <button
                    type="button"
                    className={`conflict-item ${active?.id === conflict.id ? "active" : ""}`}
                    onClick={() => setSelected(conflict.id)}
                  >
                    <div className="row-inline">
                      <SeverityBadge severity={conflict.severity} />
                      <strong>{titleCase(conflict.type)}</strong>
                    </div>
                    <p className="small">{conflict.description}</p>
                    <span className="muted small">
                      {conflict.start}–{conflict.end} · {conflict.location.label}
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            {active && (
              <div className="conflict-detail">
                <div className="row-inline">
                  <SeverityBadge severity={active.severity} />
                  <h3>{titleCase(active.type)}</h3>
                </div>
                <p>{active.description}</p>
                <dl className="detail-list">
                  <div>
                    <dt>Location</dt>
                    <dd>{active.location.label}</dd>
                  </div>
                  <div>
                    <dt>Window</dt>
                    <dd>
                      {formatMinutes(active.start_min)}–{formatMinutes(active.end_min)}
                    </dd>
                  </div>
                  <div>
                    <dt>Trains</dt>
                    <dd>
                      {active.trains
                        .map(
                          (train, index) =>
                            `${train} (${active.train_names[index] ?? "unknown"})`,
                        )
                        .join(", ")}
                    </dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{active.status}</dd>
                  </div>
                </dl>
                <h4>Evidence</h4>
                <pre className="code-block">
                  {JSON.stringify(active.evidence, null, 2)}
                </pre>
                <p className="muted small">
                  Detected against configured synthetic constraints. Not verified
                  signalling data.
                </p>
              </div>
            )}
          </div>
        )}
      </Panel>
    </div>
  );
}
