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
  DataProvenanceBadge,
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
      <td colSpan={5} className="muted">
        Not available
      </td>
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
  const [feedbackCategory, setFeedbackCategory] = useState<string>("ACCEPTED");
  const [structuredTag, setStructuredTag] = useState<string>("SCHEDULE_PRIORITY");
  const [busy, setBusy] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionNote, setDecisionNote] = useState<string | null>(null);

  useEffect(() => {
    setRationale("");
    setConfirm(false);
    setModificationText("");
    setFeedbackCategory("ACCEPTED");
    setStructuredTag("SCHEDULE_PRIORITY");
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
        feedback_category: feedbackCategory,
        structured_rationale_tag: structuredTag,
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
          {data.predictive_regulation?.decision_urgency?.urgency_category === "IMMEDIATE" && (
            <span className="badge badge-danger">IMMEDIATE (&lt;5m)</span>
          )}
          {data.predictive_regulation?.decision_urgency?.urgency_category === "NEAR_TERM" && (
            <span className="badge badge-watch">NEAR-TERM (5-15m)</span>
          )}
          {data.predictive_regulation?.decision_urgency?.urgency_category === "PLANNED" && (
            <span className="badge badge-good">PLANNED REGULATION</span>
          )}
          {data.data_quality && (
            <span className="badge badge-muted">DATA: {data.data_quality.overall_quality_state}</span>
          )}
          <span className="badge badge-watch">
            {data.confidence_disclosure?.confidence_label ?? "Confidence: Not calibrated"}
          </span>
          <DataProvenanceBadge provenance="CALCULATED" />
          <DataProvenanceBadge provenance="PREDICTED" />
        </div>
      </div>

      {/* LEVEL 1: INCIDENT / CONFLICT OPERATIONAL SUMMARY */}
      <div
        className="incident-summary-card"
        style={{
          background: "linear-gradient(135deg, #0e1726 0%, #172554 100%)",
          border: "1px solid #38bdf8",
          borderRadius: "8px",
          padding: "16px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "1.2rem" }}>⚡</span>
            <span style={{ fontSize: "0.8rem", fontWeight: 800, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Operational Incident & Decision Context
            </span>
            {data.predictive_regulation?.decision_urgency && (
              <span
                style={{
                  background:
                    data.predictive_regulation.decision_urgency.urgency_category === "IMMEDIATE"
                      ? "#ef4444"
                      : "#f59e0b",
                  color: "#080c14",
                  fontWeight: 800,
                  fontSize: "0.75rem",
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                ⏱ URGENCY: {data.predictive_regulation.decision_urgency.urgency_category}
              </span>
            )}
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f8fafc" }}>
            {data.explanation.headline || (recommended ? recommended.description : "Regulation Incident")}
          </div>
          <div style={{ fontSize: "0.85rem", color: "#94a3b8", display: "flex", gap: "16px", flexWrap: "wrap" }}>
            <span>
              Affected Stations: <strong style={{ color: "#f8fafc" }}>{data.affected_stations.join(" ⇄ ")}</strong>
            </span>
            <span>
              Simulation Clock: <strong style={{ color: "#f8fafc" }}>{data.simulation_time} IST</strong> (State v{data.state_version})
            </span>
            {data.predictive_regulation?.decision_urgency?.time_to_act_min !== null && data.predictive_regulation?.decision_urgency?.time_to_act_min !== undefined && (
              <span style={{ color: "#f87171", fontWeight: 700 }}>
                Action Window: {data.predictive_regulation.decision_urgency.time_to_act_min}m remaining
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" }}>Estimated Delay Savings</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#34d399" }}>
              {data.predictive_regulation?.comparative_timeline?.net_delay_savings_min !== undefined
                ? `+${data.predictive_regulation.comparative_timeline.net_delay_savings_min} min`
                : outcome?.total_delay_min !== undefined
                ? `-${outcome.total_delay_min} min`
                : "Evaluated"}
            </div>
          </div>
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

      {data.predictive_regulation && (
        <Panel
          title="Predictive Train Regulation & Forward Impact"
          subtitle="Multi-horizon projections, delay progression trends, and longitudinal comparative trajectory."
        >
          {data.predictive_regulation.decision_urgency && data.predictive_regulation.decision_urgency.action_required && (
            <div className="banner banner-warning mb-4" role="status">
              <strong>Decision Window: </strong>
              {data.predictive_regulation.decision_urgency.decision_window_label}
              {data.predictive_regulation.decision_urgency.time_to_act_min !== null && (
                <span> — {data.predictive_regulation.decision_urgency.time_to_act_min} minutes remaining before conflict becomes unavoidable.</span>
              )}
            </div>
          )}

          {data.predictive_regulation.multi_horizon_projections && (
            <div className="kpi-grid mb-4">
              {data.predictive_regulation.multi_horizon_projections.map((h) => (
                <div key={h.horizon_min} className="mini-kpi">
                  <span>{h.horizon_min}m {h.horizon_label} ({h.target_time})</span>
                  <strong>{h.actionable_conflicts} conflicts · {h.projected_total_delay_min}m delay</strong>
                  <span className="muted small">{h.critical_conflicts} critical</span>
                </div>
              ))}
            </div>
          )}

          {data.predictive_regulation.knock_on_propagation && data.predictive_regulation.knock_on_propagation.affected_train_count > 0 && (
            <div className="mb-4 p-3 bg-slate-900 border border-slate-700 rounded text-sm">
              <strong className="text-amber-400">Downstream Knock-on Propagation: </strong>
              If train {data.predictive_regulation.knock_on_propagation.delayed_train_id} is unmitigated, it will induce{" "}
              <strong>{data.predictive_regulation.knock_on_propagation.total_knock_on_delay_min} min</strong> cumulative knock-on delay across{" "}
              <strong>{data.predictive_regulation.knock_on_propagation.affected_train_count} downstream train(s)</strong>.
              {data.predictive_regulation.knock_on_propagation.bottleneck_locations.length > 0 && (
                <div className="text-xs text-slate-400 mt-1">
                  Bottleneck resource(s): {data.predictive_regulation.knock_on_propagation.bottleneck_locations.join(", ")}
                </div>
              )}
            </div>
          )}

          {data.predictive_regulation.comparative_timeline?.available && data.predictive_regulation.comparative_timeline.stations && (
            <div>
              <h4 className="font-semibold text-sm mb-2 text-slate-200">
                Longitudinal Station Trajectory: {data.predictive_regulation.comparative_timeline.focus_train_name ?? "Focus Train"}
                {data.predictive_regulation.comparative_timeline.net_delay_savings_min !== undefined && (
                  <span className="ml-2 text-emerald-400 font-normal">
                    (Net delay savings: {data.predictive_regulation.comparative_timeline.net_delay_savings_min} min)
                  </span>
                )}
              </h4>
              <div className="table-scroll">
                <table className="table text-xs">
                  <thead>
                    <tr>
                      <th>Station</th>
                      <th>Scheduled</th>
                      <th>No Action (Baseline)</th>
                      <th>Recommended Action</th>
                      <th>Alternative Action</th>
                      <th>Savings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.predictive_regulation.comparative_timeline.stations.map((st) => (
                      <tr key={st.station_id}>
                        <td><strong>{st.station_id}</strong></td>
                        <td>{st.scheduled_arrival}</td>
                        <td className="text-rose-400">{st.no_action_arrival}</td>
                        <td className="text-emerald-400 font-semibold">{st.recommended_arrival}</td>
                        <td className="text-slate-400">{st.alternative_arrival ?? "—"}</td>
                        <td>
                          {st.delay_savings_min > 0 ? (
                            <span className="badge badge-good">+{st.delay_savings_min}m</span>
                          ) : (
                            <span className="badge badge-muted">0m</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Panel>
      )}

      {data.explanation.structured_reasoning && (
        <Panel
          title="Explainable Recommendation Reasoning (10-Point Operational Assessment)"
          subtitle="Formulated from formal solver artifacts, independent validator checks, and verified telemetry."
        >
          <div className="space-y-3 text-sm">
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-indigo-300">1. Operational Situation: </strong>
              <span>{String(data.explanation.structured_reasoning["1_operational_situation"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-amber-300">2. Primary Problem: </strong>
              <span>{String(data.explanation.structured_reasoning["2_primary_problem"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-emerald-300">3. Recommended Action: </strong>
              <span>{String(data.explanation.structured_reasoning["3_recommended_action"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-cyan-300">4. Operational Reasoning: </strong>
              <span>{String(data.explanation.structured_reasoning["4_operational_reasoning"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-purple-300">5. Railway Constraints Evaluated: </strong>
              <div className="flex flex-wrap gap-2 mt-1.5">
                {Array.isArray(data.explanation.structured_reasoning["5_railway_constraints_considered"]) &&
                  data.explanation.structured_reasoning["5_railway_constraints_considered"].map((c: any, idx: number) => (
                    <span key={idx} className="badge badge-good">
                      ✓ {c.constraint_id}: {c.name} ({c.status})
                    </span>
                  ))}
              </div>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-blue-300">6. Alternatives Evaluated: </strong>
              <ul className="list-disc pl-5 mt-1 space-y-1">
                {Array.isArray(data.explanation.structured_reasoning["6_alternative_options_evaluated"]) &&
                  data.explanation.structured_reasoning["6_alternative_options_evaluated"].map((alt: any, idx: number) => (
                    <li key={idx}>
                      <strong>{alt.label}</strong> — <span className="badge badge-muted">{alt.status}</span>: {alt.reason_not_chosen}
                    </li>
                  ))}
              </ul>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-teal-300">7. Expected Consequences: </strong>
              <span>{String(data.explanation.structured_reasoning["7_expected_consequences"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-rose-300">8. Consequences of No Action: </strong>
              <span>{String(data.explanation.structured_reasoning["8_consequences_of_no_action"])}</span>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-yellow-300">9. Verified Evidence: </strong>
              <div className="flex flex-wrap gap-2 mt-1">
                {Array.isArray(data.explanation.structured_reasoning["9_verified_evidence"]) &&
                  data.explanation.structured_reasoning["9_verified_evidence"].map((ev: any, idx: number) => (
                    <span key={idx} className="badge badge-muted">{ev}</span>
                  ))}
              </div>
            </div>
            <div className="p-2.5 bg-slate-800/80 rounded border border-slate-700">
              <strong className="text-orange-300">10. Residual Uncertainty: </strong>
              <span>{String(data.explanation.structured_reasoning["10_residual_uncertainty"])}</span>
            </div>
          </div>
        </Panel>
      )}

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

      {data.predictive_regulation && (data.predictive_regulation.developing_delays || data.predictive_regulation.propagation_graph) && (
        <Panel
          title="Predictive Regulation & Delay Propagation Graph"
          subtitle="Early detection of developing delays, headway dependencies, and cascade chains across the corridor."
        >
          {data.predictive_regulation.developing_delays && data.predictive_regulation.developing_delays.length > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <h4>Developing Corridor Delays</h4>
              <table className="table compact">
                <thead>
                  <tr>
                    <th>Train</th>
                    <th>Category</th>
                    <th>Severity</th>
                    <th>Current</th>
                    <th>Projected Range</th>
                    <th>Primary Driver</th>
                    <th>Location</th>
                    <th>Actionability</th>
                  </tr>
                </thead>
                <tbody>
                  {data.predictive_regulation.developing_delays.map((d) => (
                    <tr key={d.train_id}>
                      <td><strong>{d.train_id}</strong> ({d.train_name})</td>
                      <td><span className="badge badge-muted">{d.category}</span></td>
                      <td>
                        <span className={`badge ${d.severity === "CRITICAL" ? "badge-danger" : d.severity === "HIGH" ? "badge-watch" : "badge-good"}`}>
                          {d.severity}
                        </span>
                      </td>
                      <td>{d.current_delay_min} min</td>
                      <td>{d.projected_delay_range.min_delay_min}–{d.projected_delay_range.max_delay_min} min</td>
                      <td className="small">{d.primary_driver}</td>
                      <td>{d.bottleneck_location}</td>
                      <td>
                        <span className={`badge ${d.actionability === "ACTIONABLE_NOW" ? "badge-danger" : "badge-muted"}`}>
                          {d.actionability}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.predictive_regulation.propagation_graph?.cascade_chains && data.predictive_regulation.propagation_graph.cascade_chains.length > 0 && (
            <div>
              <h4>Delay Cascade Propagation Chains</h4>
              <ul className="prose-list">
                {data.predictive_regulation.propagation_graph.cascade_chains.map((chain, i) => (
                  <li key={i}>
                    <strong>Initiating Train {chain.initiating_train_id}:</strong> Chain length {chain.chain_length} trains,
                    accumulating <strong>+{chain.total_accumulated_delay_min} min</strong> delay.
                    Impacted: {chain.impacted_trains.join(" → ")}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Panel>
      )}

      {data.structured_evidence && (
        <Panel
          title="Structured Operational Evidence (11-Part Schema)"
          subtitle="Factual audit trail connecting field situation, constraint checks, and regulation trade-offs."
        >
          <div className="qa-list">
            {Object.entries(data.structured_evidence).map(([secKey, section]: [string, any]) => (
              <details key={secKey} open={["A_situation", "B_detection", "E_recommended_action", "F_expected_outcome"].includes(secKey)}>
                <summary style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>{section.title || titleCase(secKey)}</span>
                  {section.evidence_class && (
                    <span className="badge badge-muted" style={{ fontSize: "0.75rem" }}>
                      {section.evidence_class}
                    </span>
                  )}
                </summary>
                <div style={{ paddingTop: "8px" }}>
                  {section.content && <p>{section.content}</p>}
                  {secKey === "A_situation" && (
                    <div className="mini-kpi-row" style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
                      <span className="badge badge-good">Posture: {section.operational_posture}</span>
                      <span className="badge badge-muted">Active Trains: {section.active_trains_count}</span>
                      <span className="badge badge-watch">{section.corridor_state}</span>
                    </div>
                  )}
                  {secKey === "C_evidence" && section.items && (
                    <table className="table compact" style={{ marginTop: "8px" }}>
                      <thead>
                        <tr>
                          <th>Fact</th>
                          <th>Category</th>
                          <th>Source</th>
                          <th>Class</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.items.map((item: any) => (
                          <tr key={item.id}>
                            <td>{item.fact}</td>
                            <td>{item.category}</td>
                            <td>{item.source}</td>
                            <td><span className="badge badge-muted">{item.evidence_class}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {secKey === "D_constraints" && (
                    <div style={{ marginTop: "6px" }}>
                      <h5>Hard Safety Constraints Checked</h5>
                      <ul className="prose-list">
                        {(section.hard_constraints_checked || []).map((hc: any) => (
                          <li key={hc.id}>
                            <strong>{hc.id}</strong>: {hc.description} — <span className="badge badge-good">{hc.status}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {secKey === "I_trade_offs" && (
                    <div className="grid-two" style={{ marginTop: "6px" }}>
                      <div>
                        <strong className="text-good">Gained Benefits:</strong>
                        <ul className="prose-list">
                          {(section.gained || []).map((g: string, i: number) => (
                            <li key={i}>{g}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <strong className="text-danger">Sacrifices / Incurred Holds:</strong>
                        <ul className="prose-list">
                          {(section.sacrificed || []).map((s: string, i: number) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                  {secKey === "K_validity" && (
                    <div style={{ marginTop: "6px" }}>
                      <p><strong>Valid Until Sim Time:</strong> {section.valid_until_sim_time} (State v{section.state_version})</p>
                      <strong>Revalidation Triggers:</strong>
                      <ul className="prose-list">
                        {(section.revalidation_triggers || []).map((trig: string, i: number) => (
                          <li key={i}>{trig}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>
        </Panel>
      )}

      {data.comparison_matrix && data.comparison_matrix.length > 0 && (
        <Panel
          title="Multi-Alternative Regulation Comparison Matrix"
          subtitle="Direct operational evaluation: Recommended Action vs Feasible Alternative vs No-Action Baseline."
        >
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Operational Attribute</th>
                  <th>Recommended Action</th>
                  <th>Best Alternative</th>
                  <th>No-Action Baseline</th>
                  <th>Operational Significance</th>
                </tr>
              </thead>
              <tbody>
                {data.comparison_matrix.map((row, idx) => (
                  <tr key={idx}>
                    <td><strong>{row.attribute}</strong></td>
                    <td className="row-selected"><strong>{String(row.recommended)}</strong></td>
                    <td>{String(row.best_alternative)}</td>
                    <td className="muted">{String(row.no_action_baseline)}</td>
                    <td className="small">{row.operational_significance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

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
              <dt>Optimality gap</dt>
              <dd>{String(data.optimizer.optimality_gap_pct ?? "0.0%")}</dd>
            </div>
            <div>
              <dt>Solve time</dt>
              <dd>{numberOrDash(data.optimizer.solve_time_s, 3)} s</dd>
            </div>
          </dl>
          {Boolean(data.optimizer.objective_breakdown) && (
            <div style={{ marginTop: "8px" }}>
              <span className="field-label">Objective breakdown</span>
              <table className="table compact">
                <tbody>
                  <tr>
                    <td>Final delay penalty</td>
                    <td>{String((data.optimizer.objective_breakdown as any)?.final_delay_penalty ?? "—")}</td>
                  </tr>
                  <tr>
                    <td>Hold penalty</td>
                    <td>{String((data.optimizer.objective_breakdown as any)?.hold_penalty ?? "—")}</td>
                  </tr>
                  <tr>
                    <td>Total objective</td>
                    <td><strong>{String((data.optimizer.objective_breakdown as any)?.total_objective ?? "—")}</strong></td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          {Array.isArray(data.optimizer.binding_constraints) && data.optimizer.binding_constraints.length > 0 && (
            <div style={{ marginTop: "8px" }}>
              <span className="field-label">Binding constraints</span>
              <ul className="prose-list">
                {data.optimizer.binding_constraints.map((bc: any, idx: number) => (
                  <li key={idx} className="small">
                    <strong>{bc.type}</strong> at {bc.location}: {bc.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
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
                <dt>Feedback category</dt>
                <dd><span className="badge badge-good">{data.decision.feedback_category ?? "ACCEPTED"}</span></dd>
              </div>
              {data.decision.structured_rationale_tag && (
                <div>
                  <dt>Operational rationale tag</dt>
                  <dd><span className="badge badge-muted">{data.decision.structured_rationale_tag}</span></dd>
                </div>
              )}
              {data.decision.prediction_error && (
                <div>
                  <dt>Outcome accuracy</dt>
                  <dd>
                    Delay error: {data.decision.prediction_error.delay_error_min !== null ? `${data.decision.prediction_error.delay_error_min} min` : "—"} ·{" "}
                    Resolution success: {data.decision.prediction_error.resolution_success ? "Achieved" : "Unresolved"}
                  </dd>
                </div>
              )}
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
            {Boolean(data.decision.three_way_comparison) && (
              <div style={{ marginTop: "14px", borderTop: "1px solid var(--border)", paddingTop: "10px" }}>
                <h4>3-Way Outcome Evaluation (AI vs Human vs Observed)</h4>
                <table className="table compact">
                  <thead>
                    <tr>
                      <th>Evaluated Dimension</th>
                      <th>AI Recommended</th>
                      <th>Human Selected</th>
                      <th>Observed Outcome</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Action</td>
                      <td>{String((data.decision.three_way_comparison as any)?.ai_recommended_action?.type || "—")}</td>
                      <td>{String((data.decision.three_way_comparison as any)?.human_selected_action?.type || data.decision.action)}</td>
                      <td><span className="badge badge-good">OBSERVED</span></td>
                    </tr>
                    <tr>
                      <td>Total Delay</td>
                      <td>{numberOrDash((data.decision.three_way_comparison as any)?.ai_predicted_outcome?.total_delay_min)} min</td>
                      <td>{numberOrDash((data.decision.actual_outcome as any)?.total_delay_min)} min</td>
                      <td>{numberOrDash((data.decision.three_way_comparison as any)?.observed_actual_outcome?.total_delay_min)} min</td>
                    </tr>
                    <tr>
                      <td>Relative Evaluation</td>
                      <td colSpan={3}>
                        <span className="badge badge-watch">
                          {String((data.decision.three_way_comparison as any)?.comparison_metrics?.relative_performance || "MATCHED")}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="grid-two mb-3">
              <div className="field">
                <label className="field-label" htmlFor="feedback-cat">
                  Feedback category
                </label>
                <select
                  id="feedback-cat"
                  value={feedbackCategory}
                  onChange={(e) => setFeedbackCategory(e.target.value)}
                  className="input"
                >
                  <option value="ACCEPTED">ACCEPTED (Follow recommendation)</option>
                  <option value="MODIFIED">MODIFIED (Adjusted parameters)</option>
                  <option value="REJECTED">REJECTED (Controller override)</option>
                  <option value="NOT_APPLICABLE">NOT_APPLICABLE (Situation changed)</option>
                  <option value="SUPERSEDED">SUPERSEDED (Alternative requested)</option>
                </select>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="rationale-tag">
                  Operational rationale tag
                </label>
                <select
                  id="rationale-tag"
                  value={structuredTag}
                  onChange={(e) => setStructuredTag(e.target.value)}
                  className="input"
                >
                  <option value="SCHEDULE_PRIORITY">SCHEDULE_PRIORITY (Standard punctuality)</option>
                  <option value="CREW_DUTY_EXCEEDED">CREW_DUTY_EXCEEDED (Hours of Employment Regulation)</option>
                  <option value="PLATFORM_MAINTENANCE">PLATFORM_MAINTENANCE (Track/platform block)</option>
                  <option value="PASSENGER_CONNECTION">PASSENGER_CONNECTION (Branchline/express link)</option>
                  <option value="STATION_REQUEST">STATION_REQUEST (Station Master coordination)</option>
                  <option value="OTHER">OTHER (Special operational circumstances)</option>
                </select>
              </div>
            </div>

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
