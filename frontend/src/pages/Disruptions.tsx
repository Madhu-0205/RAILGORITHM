import { useMemo, useState } from "react";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatMinutes } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Field,
  Panel,
  Spinner,
} from "../components/ui";

const TYPES = [
  {
    key: "BLOCK_CLOSURE",
    label: "Block closure",
    description: "Take one block out of service for a window.",
  },
  {
    key: "SECTION_CLOSURE",
    label: "Section closure",
    description: "Close every block on a section.",
  },
  {
    key: "PLATFORM_OUTAGE",
    label: "Platform outage",
    description: "Mark a station platform unavailable.",
  },
  {
    key: "TRAIN_DELAY",
    label: "Injected train delay",
    description: "Delay a train that is currently at a station.",
  },
  {
    key: "PRIORITY_CHANGE",
    label: "Priority change",
    description: "Override a train's operational priority.",
  },
];

export function DisruptionsPage() {
  const { selectedId, revision, refresh } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );
  const trainsQuery = useAsync(
    () => (selectedId ? api.trains(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const [type, setType] = useState("BLOCK_CLOSURE");
  const [blockId, setBlockId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [stationId, setStationId] = useState("");
  const [platformId, setPlatformId] = useState("");
  const [trainId, setTrainId] = useState("");
  const [duration, setDuration] = useState(30);
  const [delayMinutes, setDelayMinutes] = useState(10);
  const [priority, setPriority] = useState(0);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const stations = data?.network.stations ?? [];
  const blocks = data?.block_occupancy ?? [];
  const stationTrains = useMemo(
    () => (trainsQuery.data?.trains ?? []).filter((train) => train.status === "AT_STATION"),
    [trainsQuery.data],
  );

  const activeType = TYPES.find((item) => item.key === type) ?? TYPES[0];
  const simNow = data?.sim_time
    ? Number(data.sim_time.slice(0, 2)) * 60 + Number(data.sim_time.slice(3, 5))
    : 0;

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading || trainsQuery.loading) return <Spinner label="Loading infrastructure" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  async function submit() {
    if (!selectedId) return;
    setBusy(true);
    setMessage(null);
    setFailure(null);
    try {
      const payload: Record<string, unknown> = {
        start_min: simNow,
        end_min: simNow + duration,
        reason: reason.trim() || undefined,
      };
      if (type === "BLOCK_CLOSURE") payload.block_id = blockId;
      if (type === "SECTION_CLOSURE") payload.section_id = sectionId;
      if (type === "PLATFORM_OUTAGE") {
        payload.station_id = stationId;
        payload.platform_id = platformId;
      }
      if (type === "TRAIN_DELAY") {
        payload.train_id = trainId;
        payload.delay_min = delayMinutes;
      }
      if (type === "PRIORITY_CHANGE") {
        payload.train_id = trainId;
        payload.priority = priority;
      }
      await api.disruption(selectedId, type, payload);
      await refresh();
      setMessage(`${activeType.label} recorded and applied to the synthetic simulation.`);
      reload();
      trainsQuery.reload();
    } catch (err) {
      setFailure(err instanceof Error ? err.message : "Disruption failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Disruption management</h1>
          <p className="muted">
            Inject synthetic disruptions. Every disruption is validated, audited and applied
            only to the simulation — never to real infrastructure.
          </p>
        </div>
      </div>

      <div className="grid-two">
        <Panel title="Inject a disruption" subtitle="Section Master only.">
          <div className="form-grid">
            <Field label="Disruption type" hint={activeType.description}>
              <select value={type} onChange={(event) => setType(event.target.value)}>
                {TYPES.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </Field>

            {type === "BLOCK_CLOSURE" && (
              <Field label="Block">
                <select value={blockId} onChange={(event) => setBlockId(event.target.value)}>
                  <option value="">Select a block…</option>
                  {blocks.map((block) => (
                    <option key={block.block_id} value={block.block_id}>
                      {block.block_id} · {block.from_station}–{block.to_station}
                      {block.occupied_by ? ` · occupied by ${block.occupied_by}` : ""}
                    </option>
                  ))}
                </select>
              </Field>
            )}

            {type === "SECTION_CLOSURE" && (
              <Field label="Section">
                <select value={sectionId} onChange={(event) => setSectionId(event.target.value)}>
                  <option value="">Select a section…</option>
                  {data.network.sections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.id} · {section.from_station}–{section.to_station}
                    </option>
                  ))}
                </select>
              </Field>
            )}

            {type === "PLATFORM_OUTAGE" && (
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

            {(type === "TRAIN_DELAY" || type === "PRIORITY_CHANGE") && (
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

            {type === "TRAIN_DELAY" && (
              <Field label="Delay (minutes)">
                <input
                  type="number"
                  min={1}
                  max={180}
                  value={delayMinutes}
                  onChange={(event) => setDelayMinutes(Number(event.target.value))}
                />
              </Field>
            )}

            {type === "PRIORITY_CHANGE" && (
              <Field label="Priority override" hint="0 is highest priority; 9 is lowest.">
                <input
                  type="number"
                  min={0}
                  max={9}
                  value={priority}
                  onChange={(event) => setPriority(Number(event.target.value))}
                />
              </Field>
            )}

            {(type === "BLOCK_CLOSURE" ||
              type === "SECTION_CLOSURE" ||
              type === "PLATFORM_OUTAGE") && (
              <Field
                label="Duration (minutes)"
                hint={`Window ${formatMinutes(simNow)}–${formatMinutes(simNow + duration)}`}
              >
                <input
                  type="number"
                  min={5}
                  max={240}
                  value={duration}
                  onChange={(event) => setDuration(Number(event.target.value))}
                />
              </Field>
            )}

            <Field label="Reason">
              <input
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Engineering block, signal failure…"
              />
            </Field>
          </div>

          {failure && (
            <div className="banner banner-danger" role="alert">
              {failure}
            </div>
          )}
          {message && (
            <div className="banner banner-info" role="status">
              {message}
            </div>
          )}

          <button
            type="button"
            className="button button-danger"
            onClick={submit}
            disabled={busy}
          >
            {busy ? "Applying…" : "Apply to simulation"}
          </button>
          <p className="muted small">
            Block and platform outages are refused if the asset is currently occupied.
            The server validates all inputs; the UI is not trusted.
          </p>
        </Panel>

        <Panel title="Current restrictions" subtitle="Read from the simulated state.">
          <h3>Block closures</h3>
          {data.closures.length === 0 ? (
            <p className="muted">No block closures recorded.</p>
          ) : (
            <ul className="list">
              {data.closures.map((closure) => (
                <li key={closure.id} className="list-row">
                  <div>
                    <strong>Block {closure.block_id}</strong>
                    <p className="muted small">{closure.reason}</p>
                    <span className="muted small">by {closure.created_by}</span>
                  </div>
                  <span className="badge badge-muted">
                    {formatMinutes(closure.start_min)}–{formatMinutes(closure.end_min)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <h3>Platform outages</h3>
          {data.platform_outages.length === 0 ? (
            <p className="muted">No platform outages recorded.</p>
          ) : (
            <ul className="list">
              {data.platform_outages.map((outage) => (
                <li key={outage.id} className="list-row">
                  <div>
                    <strong>
                      {outage.station_id} / {outage.platform_id}
                    </strong>
                    <p className="muted small">{outage.reason}</p>
                    <span className="muted small">by {outage.created_by}</span>
                  </div>
                  <span className="badge badge-muted">
                    {formatMinutes(outage.start_min)}–{formatMinutes(outage.end_min)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
