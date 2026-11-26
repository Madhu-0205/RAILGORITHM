import { useMemo, useState } from "react";
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
  const { data: analytics } = useAsync(
    () => (selectedId ? api.decisionAnalytics(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const filteredRecommendations = useMemo(() => {
    if (!data?.recommendations) return [];
    return data.recommendations.filter((item) => {
      if (statusFilter === "PENDING" && item.status !== "PENDING") return false;
      if (statusFilter === "DECIDED" && item.status === "PENDING") return false;
      if (urgencyFilter !== "ALL" && item.urgency_category !== urgencyFilter) return false;
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesAction = item.recommended_label?.toLowerCase().includes(q);
        const matchesHeadline = item.headline?.toLowerCase().includes(q);
        const matchesStation = item.affected_stations?.some((s) => s.toLowerCase().includes(q));
        if (!matchesAction && !matchesHeadline && !matchesStation) return false;
      }
      return true;
    });
  }, [data?.recommendations, statusFilter, urgencyFilter, searchTerm]);

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

      {data?.recommendations.some(
        (r) => r.overall_quality_state && r.overall_quality_state !== "HEALTHY"
      ) && (
        <div className="banner banner-warning" role="alert">
          <strong>Data Quality Gate Advisory:</strong> One or more recommendations were generated
          under impaired or stale telemetry. Recommendations under offline or contradictory telemetry
          are gated from automatic decision support.
        </div>
      )}

      {analytics && analytics.total_decisions > 0 && (
        <Panel
          title="Decision Intelligence & Historical Outcome Review"
          subtitle="Controller feedback tracking, prediction error distribution, and outcome accuracy."
        >
          <div className="kpi-grid kpi-grid-tight">
            <div className="mini-kpi">
              <span>Total decisions</span>
              <strong>{analytics.total_decisions}</strong>
            </div>
            <div className="mini-kpi">
              <span>Acceptance rate</span>
              <strong>{analytics.acceptance_rate_pct}%</strong>
            </div>
            <div className="mini-kpi">
              <span>Avg hold adjustment</span>
              <strong>
                {analytics.modification_patterns.average_hold_adjustment_min > 0 ? "+" : ""}
                {analytics.modification_patterns.average_hold_adjustment_min} min
              </strong>
            </div>
            <div className="mini-kpi">
              <span>Mean delay error</span>
              <strong>{analytics.outcome_accuracy.mean_delay_error_min} min</strong>
            </div>
            <div className="mini-kpi">
              <span>Resolution success</span>
              <strong>{analytics.outcome_accuracy.resolution_success_rate_pct}%</strong>
            </div>
          </div>
        </Panel>
      )}

      <Panel
        title="Decision queue"
        subtitle="A recommendation is evidence, not an instruction. It cannot execute itself."
      >
        {/* Recommendation Filter Toolbar */}
        {data && data.recommendations.length > 0 && (
          <div
            className="flex-row justify-between items-center flex-wrap gap-2"
            style={{ marginBottom: "14px", paddingBottom: "10px", borderBottom: "1px solid var(--border)" }}
          >
            <div className="button-group" role="group" aria-label="Recommendation status filter">
              <button
                type="button"
                className={`button button-small ${statusFilter === "ALL" ? "button-primary" : "button-ghost"}`}
                onClick={() => setStatusFilter("ALL")}
              >
                All ({data.recommendations.length})
              </button>
              <button
                type="button"
                className={`button button-small ${statusFilter === "PENDING" ? "button-primary" : "button-ghost"}`}
                onClick={() => setStatusFilter("PENDING")}
              >
                Pending ({data.recommendations.filter((r) => r.status === "PENDING").length})
              </button>
              <button
                type="button"
                className={`button button-small ${statusFilter === "DECIDED" ? "button-primary" : "button-ghost"}`}
                onClick={() => setStatusFilter("DECIDED")}
              >
                Decided ({data.recommendations.filter((r) => r.status !== "PENDING").length})
              </button>
            </div>

            <div className="flex-row items-center gap-2 flex-wrap">
              <select
                className="input input-small"
                style={{ width: "auto" }}
                value={urgencyFilter}
                onChange={(e) => setUrgencyFilter(e.target.value)}
                aria-label="Filter by urgency"
              >
                <option value="ALL">All Urgencies</option>
                <option value="IMMEDIATE">Immediate (&lt;5m)</option>
                <option value="NEAR_TERM">Near-Term (5–15m)</option>
                <option value="PLANNED">Planned (&gt;15m)</option>
                <option value="MONITORING">Monitoring</option>
              </select>

              <input
                type="search"
                placeholder="Search action or station..."
                className="input input-small"
                style={{ maxWidth: "200px" }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Search recommendations"
              />

              {(statusFilter !== "ALL" || urgencyFilter !== "ALL" || searchTerm) && (
                <button
                  type="button"
                  className="button button-small button-ghost"
                  onClick={() => {
                    setStatusFilter("ALL");
                    setUrgencyFilter("ALL");
                    setSearchTerm("");
                  }}
                  title="Reset filters"
                >
                  ↺ Reset
                </button>
              )}
            </div>
          </div>
        )}

        {!data || data.recommendations.length === 0 ? (
          <EmptyState
            title="No recommendations yet"
            description="Generate one to see validated candidates and their measured simulated outcomes."
          />
        ) : filteredRecommendations.length === 0 ? (
          <EmptyState
            title="No matching recommendations"
            description="No recommendations match the selected status, urgency, or search criteria."
          />
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Suggested action</th>
                  <th>Urgency</th>
                  <th>Evidence</th>
                  <th>Status</th>
                  <th>Scope</th>
                  <th>State</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredRecommendations.map((item) => (
                  <tr key={item.id} className={item.is_stale ? "row-stale" : ""}>
                    <td className="small">{formatDateTime(item.created_at)}</td>
                    <td>
                      <strong>{item.recommended_label ?? "No executable recommendation"}</strong>
                      <div className="muted small">{item.headline}</div>
                    </td>
                    <td>
                      {item.urgency_category === "IMMEDIATE" && (
                        <span className="badge badge-danger">IMMEDIATE (&lt;5m)</span>
                      )}
                      {item.urgency_category === "NEAR_TERM" && (
                        <span className="badge badge-watch">NEAR-TERM (5-15m)</span>
                      )}
                      {item.urgency_category === "PLANNED" && (
                        <span className="badge badge-good">PLANNED (&gt;15m)</span>
                      )}
                      {(!item.urgency_category || item.urgency_category === "MONITORING") && (
                        <span className="badge badge-muted">MONITORING</span>
                      )}
                    </td>
                    <td>
                      <EvidenceBadge status={item.evidence_status} />
                      {item.overall_quality_state && item.overall_quality_state !== "HEALTHY" && (
                        <div className="badge badge-warning">{item.overall_quality_state}</div>
                      )}
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
