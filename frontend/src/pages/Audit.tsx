import { useMemo, useState } from "react";
import { api } from "../api";
import { useAsync } from "../lib/useAsync";
import { formatDateTime, humanise } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Field,
  Panel,
  Spinner,
} from "../components/ui";

export function AuditPage() {
  const { data, error, loading, reload } = useAsync(() => api.audit(200), []);
  const [type, setType] = useState("ALL");
  const [query, setQuery] = useState("");

  const types = useMemo(
    () => Array.from(new Set((data?.events ?? []).map((event) => event.event_type))).sort(),
    [data],
  );

  const events = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (data?.events ?? []).filter((event) => {
      if (type !== "ALL" && event.event_type !== type) return false;
      if (!needle) return true;
      return (
        event.actor.toLowerCase().includes(needle) ||
        event.event_type.toLowerCase().includes(needle) ||
        (event.simulation_id ?? "").toLowerCase().includes(needle) ||
        (event.recommendation_id ?? "").toLowerCase().includes(needle)
      );
    });
  }, [data, type, query]);

  if (loading) return <Spinner label="Loading audit trail" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return <EmptyState title="Audit trail unavailable" />;

  const verification = data.verification;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Audit trail</h1>
          <p className="muted">
            Append-only hash chain of logins, simulations, recommendations, what-if runs and
            human decisions. Section Master only.
          </p>
        </div>
      </div>

      <Panel
        title="Chain integrity"
        tone={verification.valid ? "success" : "danger"}
        actions={
          <button type="button" className="button button-small" onClick={reload}>
            Re-verify
          </button>
        }
      >
        <div className="audit-status">
          <span className={`audit-seal ${verification.valid ? "valid" : "invalid"}`}>
            {verification.valid ? "VALID" : "INVALID"}
          </span>
          <dl className="detail-list">
            <div>
              <dt>Events in chain</dt>
              <dd>{verification.events}</dd>
            </div>
            <div>
              <dt>Database protection</dt>
              <dd>{data.append_only ? "UPDATE/DELETE blocked by triggers" : "Not protected"}</dd>
            </div>
            {verification.head_hash && (
              <div>
                <dt>Head hash</dt>
                <dd className="mono break">{verification.head_hash}</dd>
              </div>
            )}
          </dl>
        </div>
        {!verification.valid && (
          <div className="banner banner-danger" role="alert">
            The hash chain failed verification. Investigate before trusting any record.
          </div>
        )}
      </Panel>

      <Panel>
        <div className="filter-row">
          <Field label="Search">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Actor, event type, simulation or recommendation id"
            />
          </Field>
          <Field label="Event type">
            <select value={type} onChange={(event) => setType(event.target.value)}>
              <option value="ALL">All event types</option>
              {types.map((item) => (
                <option key={item} value={item}>
                  {humanise(item)}
                </option>
              ))}
            </select>
          </Field>
          <div className="filter-count">
            <span className="field-label">Shown</span>
            <strong>{events.length}</strong>
          </div>
        </div>

        {events.length === 0 ? (
          <EmptyState title="No audit events match the filters" />
        ) : (
          <div className="table-scroll">
            <table className="table compact">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Recorded</th>
                  <th>Event</th>
                  <th>Actor</th>
                  <th>Subject</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td>{event.id}</td>
                    <td className="small">{formatDateTime(event.created_at)}</td>
                    <td>
                      <strong>{humanise(event.event_type)}</strong>
                      <details>
                        <summary className="small muted">payload</summary>
                        <pre className="code-block">
                          {JSON.stringify(event.payload, null, 2)}
                        </pre>
                      </details>
                    </td>
                    <td>
                      {event.actor}
                      <div className="muted small">{event.actor_role.replace("_", " ")}</div>
                    </td>
                    <td className="small mono">
                      {event.simulation_id && <div>sim {event.simulation_id.slice(0, 8)}…</div>}
                      {event.recommendation_id && (
                        <div>rec {event.recommendation_id.slice(0, 8)}…</div>
                      )}
                      {!event.simulation_id && !event.recommendation_id && "—"}
                    </td>
                    <td className="mono small break">{event.hash.slice(0, 16)}…</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="How the chain works">
        <ul className="prose-list">
          <li>
            Each event stores the hash of the previous event, plus a SHA-256 hash over its own
            content and that previous hash.
          </li>
          <li>
            Database triggers reject UPDATE and DELETE on audit events and decisions, so history
            cannot be quietly rewritten through the API or SQL.
          </li>
          <li>
            Verification recomputes the whole chain. A single altered payload breaks every hash
            after it.
          </li>
        </ul>
      </Panel>
    </div>
  );
}
