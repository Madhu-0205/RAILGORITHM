import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { formatMinutes } from "../lib/format";
import {
  EmptyState,
  ErrorBanner,
  Panel,
  Spinner,
} from "../components/ui";

export function NetworkPage() {
  const { selectedId, revision } = useSimulation();
  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  if (!selectedId)
    return <EmptyState title="No simulation selected" description="Choose a simulation first." />;
  if (loading) return <Spinner label="Loading network" />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  const stations = data.network.stations;
  const sections = data.network.sections;
  const width = 960;
  const height = 280;
  const left = 70;
  const right = 70;
  const y = 150;
  const step = (width - left - right) / Math.max(1, stations.length - 1);
  const xOf = (stationId: string) => {
    const index = stations.findIndex((station) => station.id === stationId);
    return left + index * step;
  };
  const sectionState = (sectionId: string) => {
    const blocks = data.block_occupancy.filter((block) => block.section_id === sectionId);
    if (blocks.some((block) => block.closure)) return "closure";
    if (blocks.some((block) => block.occupied_by)) return "occupied";
    return "free";
  };

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Railway network</h1>
          <p className="muted">
            {data.network.name} · simulated time {data.sim_time} · state v{data.state_version}
          </p>
        </div>
        <span className="badge badge-muted">{data.network.timezone}</span>
      </div>

      <Panel
        title="Schematic"
        subtitle="Single-line and double-line sections. Colours reflect simulated block occupancy only."
      >
        <div className="network-wrap">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="network-svg"
            role="img"
            aria-label="Synthetic railway network schematic"
          >
            {sections.map((section) => {
              const x1 = xOf(section.from_station);
              const x2 = xOf(section.to_station);
              const state = sectionState(section.id);
              const stroke =
                state === "closure"
                  ? "var(--danger)"
                  : state === "occupied"
                    ? "var(--watch)"
                    : "var(--good)";
              const midX = (x1 + x2) / 2;
              return (
                <g key={section.id}>
                  <line
                    x1={x1}
                    y1={y}
                    x2={x2}
                    y2={y}
                    stroke={stroke}
                    strokeWidth={section.mode === "DOUBLE" ? 10 : 6}
                    strokeDasharray={state === "closure" ? "10 7" : undefined}
                    strokeLinecap="round"
                  />
                  <text x={midX} y={y - 18} textAnchor="middle" className="svg-label">
                    {section.id} · {section.mode}
                  </text>
                  <text x={midX} y={y + 30} textAnchor="middle" className="svg-sub">
                    {section.headway_min} min headway
                  </text>
                </g>
              );
            })}
            {stations.map((station) => {
              const x = xOf(station.id);
              const occupied = data.platforms.filter(
                (platform) => platform.station_id === station.id && platform.occupied_by,
              ).length;
              return (
                <g key={station.id}>
                  <circle
                    cx={x}
                    cy={y}
                    r={station.is_junction ? 16 : 12}
                    fill="var(--panel-strong)"
                    stroke="var(--accent)"
                    strokeWidth={3}
                  />
                  <text x={x} y={y + 5} textAnchor="middle" className="svg-station">
                    {station.id}
                  </text>
                  <text x={x} y={y - 34} textAnchor="middle" className="svg-name">
                    {station.name}
                  </text>
                  <text x={x} y={y + 44} textAnchor="middle" className="svg-sub">
                    {occupied}/{station.platforms.length} platforms busy
                  </text>
                </g>
              );
            })}
          </svg>
          <div className="legend">
            <span><i className="swatch swatch-free" /> free</span>
            <span><i className="swatch swatch-occupied" /> occupied</span>
            <span><i className="swatch swatch-closure" /> closed</span>
          </div>
        </div>
      </Panel>

      <div className="grid-two">
        <Panel title="Block occupancy" subtitle="A block is the simulated track-circuit equivalent.">
          <table className="table compact">
            <thead>
              <tr>
                <th>Block</th>
                <th>Section</th>
                <th>Mode</th>
                <th>Direction</th>
                <th>Occupant</th>
                <th>Window</th>
              </tr>
            </thead>
            <tbody>
              {data.block_occupancy.map((block) => (
                <tr key={block.block_id}>
                  <td><strong>{block.block_id}</strong></td>
                  <td>{block.from_station}–{block.to_station}</td>
                  <td>{block.mode}</td>
                  <td>{block.direction}</td>
                  <td>
                    {block.closure ? (
                      <span className="badge badge-danger">CLOSED</span>
                    ) : block.occupied_by ? (
                      block.occupied_by
                    ) : (
                      <span className="muted">free</span>
                    )}
                  </td>
                  <td className="small">
                    {block.entry_min !== null && block.exit_min !== null
                      ? `${formatMinutes(block.entry_min)}–${formatMinutes(block.exit_min)}`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Platform status" subtitle="Simulated platform occupancy and outages.">
          <div className="platform-grid">
            {stations.map((station) => (
              <div key={station.id} className="platform-station">
                <strong>{station.id}</strong>
                <div className="platform-row">
                  {data.platforms
                    .filter((platform) => platform.station_id === station.id)
                    .map((platform) => (
                      <span
                        key={platform.platform_id}
                        className={`platform platform-${platform.status.toLowerCase()}`}
                        title={
                          platform.occupied_by
                            ? `Occupied by ${platform.occupied_by}`
                            : platform.outage
                              ? `Outage: ${platform.outage.reason}`
                              : "Available"
                        }
                      >
                        {platform.platform_id}
                      </span>
                    ))}
                </div>
              </div>
            ))}
          </div>
          <div className="legend">
            <span><i className="swatch swatch-free" /> available</span>
            <span><i className="swatch swatch-occupied" /> occupied</span>
            <span><i className="swatch swatch-closure" /> outage</span>
          </div>
        </Panel>
      </div>

      {(data.closures.length > 0 || data.platform_outages.length > 0) && (
        <Panel title="Infrastructure restrictions">
          <div className="grid-two">
            <div>
              <h3>Block closures</h3>
              {data.closures.length === 0 ? (
                <p className="muted">None.</p>
              ) : (
                <ul className="list">
                  {data.closures.map((closure) => (
                    <li key={closure.id} className="list-row">
                      <div>
                        <strong>Block {closure.block_id}</strong>
                        <p className="muted small">{closure.reason}</p>
                      </div>
                      <span className="badge badge-muted">
                        {formatMinutes(closure.start_min)}–{formatMinutes(closure.end_min)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3>Platform outages</h3>
              {data.platform_outages.length === 0 ? (
                <p className="muted">None.</p>
              ) : (
                <ul className="list">
                  {data.platform_outages.map((outage) => (
                    <li key={outage.id} className="list-row">
                      <div>
                        <strong>
                          {outage.station_id} / {outage.platform_id}
                        </strong>
                        <p className="muted small">{outage.reason}</p>
                      </div>
                      <span className="badge badge-muted">
                        {formatMinutes(outage.start_min)}–{formatMinutes(outage.end_min)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
