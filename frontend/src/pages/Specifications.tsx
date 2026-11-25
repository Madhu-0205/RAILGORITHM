import { api } from "../api";
import { useAsync } from "../lib/useAsync";
import { ErrorBanner, Panel, Spinner } from "../components/ui";

export function SpecificationsPage() {
  const assumptions = useAsync(() => api.assumptions(), []);
  const constraints = useAsync(() => api.constraints(), []);
  const versions = useAsync(() => api.systemVersions(), []);

  if (assumptions.loading || constraints.loading || versions.loading) {
    return <Spinner label="Loading assumptions and constraints" />;
  }
  if (assumptions.error) {
    return <ErrorBanner message={assumptions.error} onRetry={assumptions.reload} />;
  }
  if (constraints.error) {
    return <ErrorBanner message={constraints.error} onRetry={constraints.reload} />;
  }
  if (!assumptions.data || !constraints.data) return null;

  const assumptionData = assumptions.data;
  const constraintData = constraints.data;
  const categories = Array.from(
    new Set(assumptionData.assumptions.map((item) => item.category)),
  ).sort();

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <h1>Assumptions &amp; constraints</h1>
          <p className="muted">
            Explicit, configurable synthetic assumptions — not verified Indian
            Railways operating rules.
          </p>
        </div>
        <div className="heading-badges">
          <span className="badge badge-muted">{assumptionData.version}</span>
          <span className="badge badge-muted">{constraintData.version}</span>
        </div>
      </div>

      <div className="banner banner-info">
        {assumptionData.disclaimer} {constraintData.disclaimer}
      </div>

      <Panel
        title="Version register"
        subtitle="What produced this build's evidence."
      >
        <dl className="detail-list">
          {Object.entries(versions.data ?? {}).map(([key, value]) => (
            <div key={key}>
              <dt>{key.replace(/_/g, " ")}</dt>
              <dd>
                {typeof value === "object"
                  ? JSON.stringify(value)
                  : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </Panel>

      <Panel
        title="Constraint specification"
        subtitle={`${constraintData.counts.hard} hard constraints and ${constraintData.counts.soft} soft policies.`}
      >
        <div className="table-scroll">
          <table className="table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>Constraint</th>
                <th>Kind</th>
                <th>Scope</th>
                <th>Statement</th>
                <th>Enforced by</th>
              </tr>
            </thead>
            <tbody>
              {constraintData.constraints.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.name}</td>
                  <td>
                    <span
                      className={
                        item.kind === "HARD" ? "badge badge-good" : "badge badge-watch"
                      }
                    >
                      {item.kind}
                    </span>
                  </td>
                  <td>{item.scope}</td>
                  <td>{item.statement}</td>
                  <td>{item.enforced_by.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {categories.map((category) => (
        <Panel
          key={category}
          title={`${category} assumptions`}
          subtitle="Values are configuration inputs, not railway law."
        >
          <div className="table-scroll">
            <table className="table compact">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Assumption</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Override</th>
                  <th>Affects</th>
                </tr>
              </thead>
              <tbody>
                {assumptionData.assumptions
                  .filter((item) => item.category === category)
                  .map((item) => (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>{item.title}</td>
                      <td>{String(item.value)}</td>
                      <td>{item.unit}</td>
                      <td>{item.configurable_via ?? "—"}</td>
                      <td>{item.affects.join(", ")}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ))}
    </div>
  );
}
