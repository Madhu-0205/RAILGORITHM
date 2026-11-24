import { useMemo, useState } from "react";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatMinutes, numberOrDash, titleCase } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Field,
  KpiCard,
  Panel,
  SeverityBadge,
  Spinner,
} from "../components/ui";
import type { WhatIfResult } from "../types";

const ACTION_TYPES = [
  { key: "DO_NOTHING", label: "Do nothing" },
  { key: "HOLD", label: "Hold a train" },
  { key: "PRECEDENCE", label: "Give precedence" },
  { key: "PLATFORM_REASSIGN", label: "Reassign platform" },
  { key: "CUSTOM", label: "Custom JSON" },
];

export function WhatIfPage() {
  const { selectedId, revision } = useSimulation();
  const networkQuery = useAsync(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const trainsQuery = useAsync(
    () => (selectedId ? api.trains(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const [actionType, setActionType] = useState("DO_NOTHING");
  const [trainId, setTrainId] = useState("");
  const [holdMinutes, setHoldMinutes] = useState(10);
  const [priority, setPriority] = useState(0);
  const [stationId, setStationId] = useState("");
  const [platformId, setPlatformId] = useState("");
  const [customJson, setCustomJson] = useState('{\n  "type": "DO_NOTHING"\n}');
  const [minutes, setMinutes] = useState(30);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const stationTrains = useMemo(
    () => (trainsQuery.data?.trains ?? []).filter((train) => train.status === "AT_STATION"),
    [trainsQuery.data],
  );
  const stations = networkQuery.data?.network.stations ?? [];

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (networkQuery.loading || trainsQuery.loading)
    return <Spinner label="Loading what-if workspace" />;
  if (networkQuery.error)
    return <ErrorBanner message={networkQuery.error} onRetry={networkQuery.reload} />;

  function buildAction(): Record<string, unknown> {
    if (actionType === "DO_NOTHING") return { type: "DO_NOTHING" };
    if (actionType === "HOLD") {
      return { type: "HOLD", train_id: trainId, hold_min: holdMinutes };
    }
    if (actionType === "PRECEDENCE") {
      return { type: "PRECEDENCE", train_id: trainId, priority_override: priority };
    }
    if (actionType === "PLATFORM_REASSIGN") {
      return {
        type: "PLATFORM_REASSIGN",
        train_id: trainId,
        station_id: stationId,
        platform_id: platformId,
      };
    }
    return JSON.parse(customJson);
  }

  async function run() {
    if (!selectedId) return;
    setBusy(true);
    setFailure(null);
    setResult(null);
    try {
      const action = buildAction();
      const response = await api.whatIf(selectedId, action, minutes);
      setResult(response);
    } catch (err) {
      setFailure(err instanceof Error ? err.message : "What-if run failed");
    } finally {
      setBusy(false);
    }
  }

  const deltas = result?.deltas;

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>What-if simulation</h1>
          <p className="muted">
            Test a hypothetical action on a cloned simulation. Nothing is applied to the live
            simulation; the action is independently validated first.
          </p>
        </div>
      </div>

      <Panel title="Hypothetical action">
        <div className="form-grid">
          <Field label="Action type">
            <select
              value={actionType}
              onChange={(event) => setActionType(event.target.value)}
            >
              {ACTION_TYPES.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </Field>

          {actionType !== "DO_NOTHING" && actionType !== "CUSTOM" && (
            <Field label="Train at station">
              <select value={trainId} onChange={(event) => setTrainId(event.target.value)}>
                <option value="">Select a train…</option>
                {stationTrains.map((train) => (
                  <option key={train.id} value={train.id}>
                    {train.id} · {train.name} · at {train.station_id}
                  </option>
                ))}
              </select>
            </Field>
          )}

          {actionType === "HOLD" && (
            <Field label="Hold (minutes)">
              <input
                type="number"
                min={1}
                max={120}
                value={holdMinutes}
                onChange={(event) => setHoldMinutes(Number(event.target.value))}
              />
            </Field>
          )}

          {actionType === "PRECEDENCE" && (
            <Field label="Priority override" hint="Lower number means higher priority.">
              <input
                type="number"
                min={0}
                max={9}
                value={priority}
                onChange={(event) => setPriority(Number(event.target.value))}
              />
            </Field>
          )}

          {actionType === "PLATFORM_REASSIGN" && (
            <>
              <Field label="Station">
                <select value={stationId} onChange={(event) => setStationId(event.target.value)}>
                  <option value="">Select a station…</option>
                  {stations.map((station) => (
                    <option key={station.id} value={station.id}>
                      {station.id} · {station.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Platform">
                <select
                  value={platformId}
                  onChange={(event) => setPlatformId(event.target.value)}
                >
                  <option value="">Select a platform…</option>
                  {(stations.find((station) => station.id === stationId)?.platforms ?? []).map(
                    (platform) => (
                      <option key={platform} value={platform}>
                        {platform}
                      </option>
                    ),
                  )}
                </select>
              </Field>
            </>
          )}

          {actionType === "CUSTOM" && (
            <Field label="Action JSON">
              <textarea
                rows={6}
                value={customJson}
                onChange={(event) => setCustomJson(event.target.value)}
              />
            </Field>
          )}

          <Field label="Horizon (minutes)" hint="5 to 120 simulated minutes.">
            <input
              type="number"
              min={5}
              max={120}
              value={minutes}
              onChange={(event) => setMinutes(Number(event.target.value))}
            />
          </Field>
        </div>

        {failure && (
          <div className="banner banner-danger" role="alert">
            {failure}
          </div>
        )}

        <button
          type="button"
          className="button button-primary"
          onClick={run}
          disabled={busy}
        >
          {busy ? "Simulating…" : "Run what-if"}
        </button>
      </Panel>

      {result && (
        <>
          {result.status !== "COMPLETED" ? (
            <Panel title="What-if rejected" tone="danger">
              <p>{result.message}</p>
              {result.validation && (
                <pre className="code-block">
                  {JSON.stringify(result.validation, null, 2)}
                </pre>
              )}
            </Panel>
          ) : (
            <>
              <div className="kpi-grid">
                <KpiCard
                  label="Total delay Δ"
                  value={numberOrDash(deltas?.total_delay_min)}
                  unit=" min"
                  tone={
                    (deltas?.total_delay_min ?? 0) < 0
                      ? "good"
                      : (deltas?.total_delay_min ?? 0) > 0
                        ? "bad"
                        : "neutral"
                  }
                  hint="hypothetical minus baseline"
                />
                <KpiCard
                  label="Average delay Δ"
                  value={numberOrDash(deltas?.average_delay_min)}
                  unit=" min"
                  tone={
                    (deltas?.average_delay_min ?? 0) < 0
                      ? "good"
                      : (deltas?.average_delay_min ?? 0) > 0
                        ? "bad"
                        : "neutral"
                  }
                />
                <KpiCard
                  label="On-time Δ"
                  value={numberOrDash(deltas?.on_time_performance_pct)}
                  unit=" pp"
                  tone={(deltas?.on_time_performance_pct ?? 0) >= 0 ? "good" : "watch"}
                />
                <KpiCard
                  label="Conflicts Δ"
                  value={numberOrDash(deltas?.conflicts, 0)}
                  tone={(deltas?.conflicts ?? 0) <= 0 ? "good" : "bad"}
                />
              </div>

              <div className="grid-two">
                <Panel title="Baseline (do nothing)">
                  <MetricTable metrics={result.baseline_metrics} />
                </Panel>
                <Panel title="Hypothetical action">
                  <MetricTable metrics={result.hypothetical_metrics} />
                </Panel>
              </div>

              <div className="grid-two">
                <Panel title="Baseline conflicts" subtitle="After the horizon, no intervention.">
                  <ConflictList conflicts={result.baseline_conflicts ?? []} />
                </Panel>
                <Panel title="Hypothetical conflicts" subtitle="After the horizon, action applied.">
                  <ConflictList conflicts={result.hypothetical_conflicts ?? []} />
                </Panel>
              </div>

              <div className="banner banner-info">
                {result.applied_to_live_simulation
                  ? "Warning: the result claims to have modified the live simulation."
                  : "This comparison was produced on cloned simulations and was not applied to the live simulation."}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function MetricTable({ metrics }: { metrics?: WhatIfResult["baseline_metrics"] }) {
  if (!metrics) return <p className="muted">Not available.</p>;
  const rows: [string, string][] = [
    ["Simulated time", formatMinutes(metrics.sim_time_min)],
    ["Trains active", String(metrics.trains_active)],
    ["Trains completed", String(metrics.trains_completed)],
    ["Total delay", `${numberOrDash(metrics.total_delay_min)} min`],
    ["Average delay", `${numberOrDash(metrics.average_delay_min)} min`],
    ["Max delay", `${numberOrDash(metrics.max_delay_min)} min`],
    ["On-time performance", `${numberOrDash(metrics.on_time_performance_pct)}%`],
    ["Throughput", `${numberOrDash(metrics.throughput_trains_per_hour)} tph`],
  ];
  return (
    <dl className="detail-list">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ConflictList({ conflicts }: { conflicts: WhatIfResult["baseline_conflicts"] }) {
  if (!conflicts || conflicts.length === 0) {
    return <p className="muted">No actionable conflicts projected.</p>;
  }
  return (
    <ul className="list">
      {conflicts.map((conflict) => (
        <li key={conflict.id} className="list-row">
          <div>
            <div className="row-inline">
              <SeverityBadge severity={conflict.severity} />
              <strong>{titleCase(conflict.type)}</strong>
            </div>
            <p className="small">{conflict.description}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
