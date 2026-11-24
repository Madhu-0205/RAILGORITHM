import { useState } from "react";
import { useSimulation } from "../simulation";
import type { Scenario } from "../types";

export function NewSimulationDialog({
  scenarios,
  onClose,
}: {
  scenarios: Scenario[];
  onClose: () => void;
}) {
  const { create } = useSimulation();
  const [scenarioKey, setScenarioKey] = useState(scenarios[0]?.key ?? "");
  const [seed, setSeed] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = scenarios.find((item) => item.key === scenarioKey);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const parsedSeed = seed.trim() ? Number(seed) : undefined;
      if (parsedSeed !== undefined && (!Number.isInteger(parsedSeed) || parsedSeed < 0)) {
        throw new Error("Seed must be a non-negative integer.");
      }
      await create(scenarioKey, parsedSeed);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create simulation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-simulation-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="new-simulation-title">New synthetic simulation</h2>
        <p className="muted">
          Scenarios are deterministic: the same scenario and seed produce the same starting
          state. All data is synthetic.
        </p>
        <label className="field">
          <span className="field-label">Scenario</span>
          <select
            value={scenarioKey}
            onChange={(event) => setScenarioKey(event.target.value)}
          >
            {scenarios.map((scenario) => (
              <option key={scenario.key} value={scenario.key}>
                {scenario.name}
              </option>
            ))}
          </select>
        </label>
        {selected && (
          <div className="scenario-summary">
            <p>{selected.description}</p>
            <dl className="detail-list">
              <div>
                <dt>Trains</dt>
                <dd>{selected.train_count}</dd>
              </div>
              <div>
                <dt>Default seed</dt>
                <dd>{selected.seed}</dd>
              </div>
              <div>
                <dt>Closures</dt>
                <dd>{selected.closure_count}</dd>
              </div>
              <div>
                <dt>Platform outages</dt>
                <dd>{selected.platform_outage_count}</dd>
              </div>
            </dl>
          </div>
        )}
        <label className="field">
          <span className="field-label">Seed (optional)</span>
          <input
            value={seed}
            onChange={(event) => setSeed(event.target.value)}
            placeholder={String(selected?.seed ?? "default")}
            inputMode="numeric"
          />
          <span className="field-hint">Leave blank to use the scenario's default seed.</span>
        </label>
        {error && (
          <div className="banner banner-danger" role="alert">
            {error}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" className="button button-ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={submit}
            disabled={busy || !scenarioKey}
          >
            {busy ? "Creating…" : "Create simulation"}
          </button>
        </div>
      </div>
    </div>
  );
}
