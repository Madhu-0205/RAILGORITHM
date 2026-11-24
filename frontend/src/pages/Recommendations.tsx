import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatDateTime } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  EvidenceBadge,
  Panel,
  Spinner,
  StatusBadge,
} from "../components/ui";

export function RecommendationsPage() {
  const { user } = useAuth();
  const { selectedId, refresh, revision } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.recommendations(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function generate() {
    if (!selectedId) return;
    setBusy(true);
    setMessage(null);
    try {
      const created = await api.generateRecommendation(selectedId);
      await refresh();
      navigate(`/recommendations/${created.recommendation_id}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not generate advice");
    } finally {
      setBusy(false);
    }
  }

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading) return <Spinner label="Loading recommendations" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>AI recommendations</h1>
          <p className="muted">
            Simulation → conflicts → candidates → CP-SAT → independent validation → PPO
            ranking → human decision.
          </p>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={generate}
          disabled={busy || !selectedId}
        >
          {busy ? "Generating…" : "Generate recommendation"}
        </button>
      </div>

      {message && (
        <div className="banner banner-danger" role="alert">
          {message}
        </div>
      )}

      <Panel
        title="Decision queue"
        subtitle="A recommendation is evidence, not an instruction. It cannot execute itself."
      >
        {!data || data.recommendations.length === 0 ? (
          <EmptyState
            title="No recommendations yet"
            description="Generate one to see validated candidates and their measured simulated outcomes."
          />
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Suggested action</th>
                  <th>Evidence</th>
                  <th>Status</th>
                  <th>Scope</th>
                  <th>State</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.recommendations.map((item) => (
                  <tr key={item.id} className={item.is_stale ? "row-stale" : ""}>
                    <td className="small">{formatDateTime(item.created_at)}</td>
                    <td>
                      <strong>{item.recommended_label ?? "No executable recommendation"}</strong>
                      <div className="muted small">{item.headline}</div>
                    </td>
                    <td>
                      <EvidenceBadge status={item.evidence_status} />
                      {item.disagreement && (
                        <div className="badge badge-watch">models disagree</div>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={item.status} />
                      {item.is_stale && <div className="badge badge-danger">STALE</div>}
                    </td>
                    <td className="small">
                      {item.affected_stations.join(", ") || "—"}
                    </td>
                    <td className="small">
                      v{item.state_version}
                      <div className="muted">{item.sim_time}</div>
                    </td>
                    <td>
                      <Link
                        className="button button-small"
                        to={`/recommendations/${item.id}`}
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="How to read this queue">
        <ul className="prose-list">
          <li>
            <strong>Validated</strong> means an independent constraint validator checked the
            action and its simulated outcome. It is not a real-world safety certificate.
          </li>
          <li>
            <strong>Models disagree</strong> means the PPO ranking and the CP-SAT candidate
            point at different options. The disagreement is shown, never hidden.
          </li>
          <li>
            <strong>Stale</strong> means the simulation advanced after the advice was
            generated. It cannot be approved; request fresh alternatives.
          </li>
          <li>
            Only a {user?.role === "STATION_MASTER" ? "Station Master within scope" : "Section Master"}{" "}
            can record the decision, and only an explicit confirmation applies it to the
            synthetic simulation.
          </li>
        </ul>
      </Panel>
    </div>
  );
}
