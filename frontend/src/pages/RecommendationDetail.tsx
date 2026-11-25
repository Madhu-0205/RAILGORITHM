import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import {
  formatDateTime,
  formatMinutes,
  numberOrDash,
  titleCase,
} from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  EvidenceBadge,
  Panel,
  SeverityBadge,
  Spinner,
  StatusBadge,
} from "../components/ui";
import type { CandidateOutcome, RecommendationDetail } from "../types";

const DECISION_ACTIONS = [
  { key: "APPROVE", label: "Approve and apply", needsConfirm: true, tone: "primary" },
  { key: "MODIFY", label: "Modify and apply", needsConfirm: true, tone: "watch" },
  { key: "REJECT", label: "Reject", needsConfirm: false, tone: "danger" },
  { key: "DEFER", label: "Defer", needsConfirm: false, tone: "ghost" },
  {
    key: "REQUEST_ALTERNATIVES",
    label: "Request alternatives",
    needsConfirm: false,
    tone: "ghost",
  },
];

function labelFor(detail: RecommendationDetail, candidateId: string | null): string {
  if (!candidateId) return "—";
  const match = detail.alternatives.find((item) => item.candidate_id === candidateId);
  return match?.label ?? candidateId;
}

function OutcomeCells({ outcome }: { outcome?: CandidateOutcome }) {
  if (!outcome) {
    return (
      <tr>
        <td colSpan={5} className="muted">
          Not available
        </td>
      </tr>
    );
  }
  return (
    <>
      <td>{numberOrDash(outcome.total_delay_min)}</td>
      <td>{numberOrDash(outcome.weighted_delay)}</td>
      <td>{outcome.conflicts_after}</td>
      <td>{outcome.residual_critical}</td>
      <td>{numberOrDash(outcome.on_time_performance_pct)}%</td>
    </>
  );
}

export function RecommendationDetailPage() {
  const { recommendationId = "" } = useParams();
  const { user } = useAuth();
  const { refresh, revision } = useSimulation();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useAsync(
    () => api.recommendation(recommendationId),
    [recommendationId, revision],
  );
  const [rationale, setRationale] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [modificationText, setModificationText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionNote, setDecisionNote] = useState<string | null>(null);

  useEffect(() => {
    setRationale("");
    setConfirm(false);
    setModificationText("");
    setDecisionError(null);
    setDecisionNote(null);
  }, [recommendationId]);

  const scopeBlocked = useMemo(() => {
    if (!data || !user || user.role !== "STATION_MASTER") return false;
    return data.affected_stations.some((station) => station !== user.station_id);
  }, [data, user]);

  if (loading) return <Spinner label="Loading recommendation" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return <EmptyState title="Recommendation not found" />;

  const decided = data.decision !== null;
  const canDecide = !decided && !scopeBlocked;

  async function submit(action: string) {
    if (!data) return;
    setBusy(action);
    setDecisionError(null);
    setDecisionNote(null);
    try {
      let modifications: Record<string, unknown> | null = null;
      if (action === "MODIFY") {
        try {
          const parsed = JSON.parse(modificationText || "{}");
          if (!parsed.action || typeof parsed.action !== "object") {
            throw new Error('Modification must contain an "action" object.');
          }
          modifications = parsed;
        } catch (err) {
          throw new Error(
            err instanceof Error ? err.message : "Modification JSON is invalid.",
          );
        }
      }
      const result = await api.decide(data.recommendation_id, {
        action,
        rationale: rationale.trim(),
        confirm_apply: confirm,
        modifications,
      });
      setDecisionNote(result.note);
      await refresh();
      if (result.new_recommendation) {
        navigate(`/recommendations/${result.new_recommendation.recommendation_id}`);
      } else {
        reload();
      }
    } catch (err) {
      if (err instanceof ApiError) setDecisionError(err.message);
      else setDecisionError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(null);
    }
  }

  const recommended = data.recommended;
  const outcome = recommended?.expected_outcome;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <Link to="/recommendations" className="back-link">
            ← Back to queue
          </Link>
          <h1>Recommendation review</h1>
          <p className="muted">
            Generated {formatDateTime(data.created_at)} by {data.created_by} · simulated{" "}
            {data.simulation_time} · state v{data.state_version}
          </p>
        </div>
        <div className="heading-badges">
          <EvidenceBadge status={data.evidence_status} />
          <StatusBadge status={data.status} />
          {data.is_stale && <span className="badge badge-danger">STALE</span>}
          {data.disagreement && <span className="badge badge-watch">MODELS DISAGREE</span>}
        </div>
      </div>

      {(data.is_stale || scopeBlocked) && (
        <div className="banner banner-danger">
          {data.is_stale &&
            `This advice was generated for state v${data.state_version}, but the simulation is now at v${data.current_state_version}. It cannot be approved; request alternatives. `}
          {scopeBlocked &&
            "This recommendation affects stations outside your scope. Only the Section Master can decide it."}
        </div>
      )}

      {decisionNote && (
        <div className="banner banner-info" role="status">
          {decisionNote}
        </div>
      )}

      <Panel
        title="Recommended action"
        subtitle="Selected by measured simulated outcome among independently validated candidates."
        tone={data.disagreement ? "warning" : "default"}
      >
        {recommended ? (
          <>
            <div className="recommendation-headline">
              <div>
                <span className="field-label">Suggestion</span>
                <h3>{recommended.description}</h3>
                <p className="muted">
                  Source: {recommended.source} · validation:{" "}
                  {recommended.action_validation_status} · outcome:{" "}
                  {recommended.validation_status}
                </p>
              </div>
              <div className="score-box">
                <span className="field-label">Weighted score</span>
                <strong>{numberOrDash(recommended.score)}</strong>
                <span className="muted small">lower is better</span>
              </div>
            </div>

            <div className="validation-summary">
              <span className="badge badge-good">
                {recommended.validation_summary.checks_passed} checks passed
              </span>
              <span className="badge badge-watch">
                {recommended.validation_summary.checks_warned} warnings
              </span>
              <span className="badge badge-danger">
                {recommended.validation_summary.checks_failed} failed
              </span>
              <span className="badge badge-muted">
                {recommended.validation_summary.validator_version}
              </span>
            </div>

            <div className="kpi-grid kpi-grid-tight">
              <div className="mini-kpi">
                <span>Total delay</span>
                <strong>{numberOrDash(outcome?.total_delay_min)} min</strong>
              </div>
              <div className="mini-kpi">
                <span>Average delay</span>
                <strong>{numberOrDash(outcome?.average_delay_min)} min</strong>
              </div>
              <div className="mini-kpi">
                <span>Conflicts after</span>
                <strong>{outcome?.conflicts_after ?? "—"}</strong>
              </div>
              <div className="mini-kpi">
                <span>Residual critical</span>
                <strong>{outcome?.residual_critical ?? "—"}</strong>
              </div>
              <div className="mini-kpi">
                <span>On-time</span>
                <strong>{numberOrDash(outcome?.on_time_performance_pct)}%</strong>
              </div>
              <div className="mini-kpi">
                <span>Throughput</span>
                <strong>{numberOrDash(outcome?.throughput_trains_per_hour)} tph</strong>
              </div>
            </div>
            <p className="muted small">
              Outcomes are measured on a cloned {outcome?.simulation_minutes ?? 0}-minute
              simulation from the same state. They are estimates, not real-world guarantees.
            </p>
          </>
        ) : (
          <EmptyState
            title="No executable recommendation"
            description="Every candidate failed independent validation or the optimizer found no feasible schedule. The system will not fabricate an action."
          />
        )}
      </Panel>

      <div className="grid-two">
        <Panel title="Conflict evidence" subtitle="Projected from the current simulated state.">
          {data.conflicts.length === 0 ? (
            <p className="muted">No conflicts recorded for this recommendation.</p>
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
                    <span className="muted small">
                      {conflict.start}–{conflict.end} · {conflict.location.label}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Model disagreement" subtitle="Shown explicitly; never auto-resolved.">
          <dl className="detail-list">
            <div>
              <dt>Recommended candidate</dt>
              <dd>{labelFor(data, data.disagreement_detail.recommended_candidate_id)}</dd>
            </div>
            <div>
              <dt>PPO top choice</dt>
              <dd>{labelFor(data, data.disagreement_detail.ppo_top_candidate_id)}</dd>
            </div>
            <div>
              <dt>CP-SAT candidate</dt>
              <dd>{labelFor(data, data.disagreement_detail.cpsat_candidate_id)}</dd>
            </div>
            <div>
              <dt>PPO vs CP-SAT</dt>
              <dd>
                {data.disagreement_detail.ppo_vs_cpsat_disagreement
                  ? "Disagree"
                  : "Agree or not applicable"}
              </dd>
            </div>
          </dl>
          <p className="muted small">{data.disagreement_detail.selection_rule}</p>
        </Panel>
      </div>

      <Panel
        title="Why this recommendation?"
        subtitle="Ten required questions, answered from measured evidence."
      >
        <div className="qa-list">
          {Object.entries(data.explanation.questions).map(([key, answer]) => (
            <details key={key} open={key.startsWith("1_") || key.startsWith("4_")}>
              <summary>{titleCase(key.replace(/^\d+_/, ""))}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </Panel>

      <Panel
        title="Provenance, uncertainty and trade-offs"
        subtitle="Every value is labelled as calculated, predicted or assumed. No confidence percentage is fabricated."
      >
        <div className="grid-two">
          <div>
            <dl className="detail-list">
              <div>
                <dt>Spec versions</dt>
                <dd>
                  assumptions {data.assumption_spec_version ?? "—"} · constraints{" "}
                  {data.constraint_spec_version ?? "—"} · objective{" "}
                  {data.objective_profile ?? "—"}
                </dd>
              </div>
              <div>
                <dt>State version</dt>
                <dd>{data.provenance?.state_version ?? data.state_version}</dd>
              </div>
              <div>
                <dt>Constraint references</dt>
                <dd>{data.provenance?.constraint_ids?.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt>Candidate source</dt>
                <dd>{data.provenance?.candidate_source ?? recommended?.source ?? "—"}</dd>
              </div>
              <div>
                <dt>Solver</dt>
                <dd>
                  {String(data.provenance?.solver?.status ?? data.optimizer.status)} ·{" "}
                  {Boolean(data.provenance?.solver?.is_optimal)
                    ? "optimal for configured objective"
                    : "not claimed optimal"}
                </dd>
              </div>
              <div>
                <dt>PPO role</dt>
                <dd>
                  {data.ppo.available
                    ? `${data.ppo.model_version} ranks validated candidates only`
                    : "unavailable — deterministic baseline used"}
                </dd>
              </div>
            </dl>
            <p className="muted small">{data.uncertainty?.note}</p>
          </div>
          <div>
            <span className="field-label">Measured trade-offs</span>
            {data.trade_offs?.available ? (
              <table className="table compact">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Weighted</th>
                    <th>Residual</th>
                    <th>Delay</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ...(data.trade_offs.selected ? [data.trade_offs.selected] : []),
                    ...(data.trade_offs.eligible_alternatives ?? []),
                  ].map((row) => (
                    <tr key={row.candidate_id} className={row.selected ? "row-selected" : undefined}>
                      <td>{row.label}</td>
                      <td>{numberOrDash(row.weighted_delay)}</td>
                      <td>{row.residual_conflicts}</td>
                      <td>{numberOrDash(row.total_delay_min)} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">{data.trade_offs?.reason ?? "No eligible alternatives."}</p>
            )}
            <p className="muted small">{data.trade_offs?.note}</p>
          </div>
        </div>
      </Panel>

      <Panel title="Candidate alternatives" subtitle="Eligibility is decided by validation, not by ranking.">
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Source</th>
                <th>Eligible</th>
                <th>Validation</th>
                <th>Delay</th>
                <th>Weighted</th>
                <th>Conflicts</th>
                <th>Crit.</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {data.alternatives.map((item) => (
                <tr key={item.candidate_id} className={item.selected ? "row-selected" : ""}>
                  <td>
                    <strong>{item.label}</strong>
                    {item.selected && <span className="badge badge-good">SELECTED</span>}
                    <div className="muted small">{item.description}</div>
                    {item.rejection_reason && (
                      <div className="rejection">{item.rejection_reason}</div>
                    )}
                  </td>
                  <td>{item.source}</td>
                  <td>{item.eligible ? "Yes" : "No"}</td>
                  <td className="small">{item.validation_status}</td>
                  <td>{numberOrDash(item.expected_outcome.total_delay_min)}</td>
                  <td>{numberOrDash(item.weighted_delay)}</td>
                  <td>{item.expected_outcome.conflicts_after}</td>
                  <td>{item.expected_outcome.residual_critical}</td>
                  <td>{item.score === null ? "—" : numberOrDash(item.score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid-two">
        <Panel title="PPO ranking" subtitle="Sampling scores, not calibrated confidence.">
          {data.ppo.available ? (
            <>
              <table className="table compact">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Score</th>
                    <th>Policy probability</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ppo.ranking.map((entry) => (
                    <tr key={entry.candidate_id}>
                      <td>{labelFor(data, entry.candidate_id)}</td>
                      <td>{entry.score.toFixed(4)}</td>
                      <td>{(entry.policy_probability * 100).toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted small">{data.ppo.disclaimer}</p>
            </>
          ) : (
            <>
              <p>{data.ppo.reason}</p>
              <p className="muted small">
                The recommendation uses a clearly labelled deterministic baseline ranking.
              </p>
            </>
          )}
        </Panel>

        <Panel title="CP-SAT optimizer" subtitle="Deterministic feasibility, independently validated.">
          <dl className="detail-list">
            <div>
              <dt>Status</dt>
              <dd>{data.optimizer.status}</dd>
            </div>
            <div>
              <dt>Schedule validation</dt>
              <dd>{data.optimizer.schedule_validation_status ?? "not run"}</dd>
            </div>
            <div>
              <dt>Objective</dt>
              <dd>{numberOrDash(data.optimizer.objective_value, 1)}</dd>
            </div>
            <div>
              <dt>Solve time</dt>
              <dd>{numberOrDash(data.optimizer.solve_time_s, 3)} s</dd>
            </div>
          </dl>
          <p className="muted small">{data.optimizer.message}</p>
          <h4>Baseline ordering</h4>
          <ol className="prose-list">
            {data.baseline_ranking.slice(0, 5).map((entry) => (
              <li key={entry.candidate_id}>{entry.label}</li>
            ))}
          </ol>
        </Panel>
      </div>

      <Panel
        title="Measured comparison"
        subtitle={String(data.comparison.measurement_note ?? "Simulated estimates only.")}
      >
        <table className="table compact">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Total delay (min)</th>
              <th>Weighted score</th>
              <th>Conflicts after</th>
              <th>Residual critical</th>
              <th>On-time %</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>No intervention</td>
              <OutcomeCells outcome={data.comparison.no_intervention} />
            </tr>
            <tr>
              <td>Baseline heuristic</td>
              <OutcomeCells outcome={data.comparison.baseline_heuristic_choice} />
            </tr>
            <tr>
              <td>CP-SAT only</td>
              <OutcomeCells outcome={data.comparison.cpsat_only} />
            </tr>
            <tr className="row-selected">
              <td>Hybrid recommendation</td>
              <OutcomeCells outcome={data.comparison.hybrid_recommended} />
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Human decision"
        subtitle="The controller is the final authority. No action executes automatically."
        tone={canDecide ? "default" : "warning"}
      >
        {decided && data.decision ? (
          <div className="decision-record">
            <div className="row-inline">
              <StatusBadge status={data.decision.action} />
              <strong>{data.decision.decided_by}</strong>
              <span className="muted">
                {data.decision.decided_role.replace("_", " ")} ·{" "}
                {formatDateTime(data.decision.decided_at)}
              </span>
            </div>
            <p>{data.decision.rationale}</p>
            <dl className="detail-list">
              <div>
                <dt>Applied</dt>
                <dd>{data.decision.applied ? "Yes — to synthetic simulation" : "No"}</dd>
              </div>
              <div>
                <dt>Execution mode</dt>
                <dd>{data.decision.execution_mode}</dd>
              </div>
              <div>
                <dt>Validation</dt>
                <dd>{data.decision.validation_status ?? "—"}</dd>
              </div>
              <div>
                <dt>Model / optimizer</dt>
                <dd>
                  {data.decision.model_version} / {data.decision.optimizer_version}
                </dd>
              </div>
            </dl>
            {data.decision.simulation_result && (
              <details>
                <summary>Simulation result</summary>
                <pre className="code-block">
                  {JSON.stringify(data.decision.simulation_result, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ) : (
          <>
            <div className="field">
              <label className="field-label" htmlFor="rationale">
                Decision rationale (required)
              </label>
              <textarea
                id="rationale"
                rows={3}
                value={rationale}
                onChange={(event) => setRationale(event.target.value)}
                placeholder="Explain the operational reason for your decision."
              />
            </div>

            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={confirm}
                onChange={(event) => setConfirm(event.target.checked)}
              />
              I explicitly confirm that any applied action affects only the synthetic
              simulation and has been reviewed by me.
            </label>

            <details className="modify-box">
              <summary>Modification payload (only for Modify)</summary>
              <textarea
                rows={6}
                value={modificationText}
                onChange={(event) => setModificationText(event.target.value)}
                placeholder={'{\n  "action": { "type": "DO_NOTHING" }\n}'}
              />
            </details>

            {decisionError && (
              <div className="banner banner-danger" role="alert">
                {decisionError}
              </div>
            )}

            <div className="decision-buttons">
              {DECISION_ACTIONS.map((item) => {
                const disabled =
                  busy !== null ||
                  !canDecide ||
                  rationale.trim().length < 5 ||
                  (item.needsConfirm && !confirm) ||
                  (item.key === "APPROVE" && !recommended) ||
                  (item.key === "APPROVE" && data.is_stale);
                return (
                  <button
                    key={item.key}
                    type="button"
                    className={`button button-${item.tone}`}
                    disabled={disabled}
                    onClick={() => submit(item.key)}
                  >
                    {busy === item.key ? "Recording…" : item.label}
                  </button>
                );
              })}
            </div>
            <p className="muted small">
              Approval and modification require the confirmation checkbox and a rationale
              of at least five characters. The server re-validates the action before
              applying it.
            </p>
          </>
        )}
      </Panel>

      <Panel title="Limitations" tone="warning">
        <ul className="prose-list">
          {data.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
