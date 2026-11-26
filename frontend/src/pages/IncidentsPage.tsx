import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { Badge, EmptyState, ErrorBanner, Panel, Spinner } from "../components/ui";
import { DisruptionsPage } from "./Disruptions";

interface ControlIncident {
  id: string;
  category: "SIGNALLING" | "OHE_ELECTRICAL" | "TRACK_PWAY" | "ROLLING_STOCK" | "OPERATING";
  location: string;
  timeLogged: string;
  reportedBy: string;
  severity: "CRITICAL" | "MAJOR" | "MINOR";
  status: "ACTIVE" | "UNDER_RESTORATION" | "RESOLVED";
  ert: string;
  description: string;
  actionTaken: string;
}

const SAMPLE_INCIDENTS: ControlIncident[] = [
  {
    id: "INC-2026-101",
    category: "SIGNALLING",
    location: "Malgaon Junction (MLG) Up Home Signal 101A",
    timeLogged: "06:14 IST",
    reportedBy: "Station Master (MLG)",
    severity: "CRITICAL",
    status: "UNDER_RESTORATION",
    ert: "07:00 IST (approx 45 min)",
    description: "Signal lamp failure on Red aspect. Interlocking held in caution mode.",
    actionTaken: "Section S&T Team dispatched under Memo #882. Trains piloted on calling-on signal.",
  },
  {
    id: "INC-2026-094",
    category: "TRACK_PWAY",
    location: "Section S3 (MLG–SRP) km 42/12-14",
    timeLogged: "05:40 IST",
    reportedBy: "Track Patrolman #4",
    severity: "MAJOR",
    status: "ACTIVE",
    ert: "09:30 IST",
    description: "Weld gap expansion observed on Up rail. 30 km/h caution imposed.",
    actionTaken: "TSR imposed via Caution Order #42. Engineering gang on site for clamp fixing.",
  },
  {
    id: "INC-2026-088",
    category: "OHE_ELECTRICAL",
    location: "Karanpur (KRN) Platform 2 Loop",
    timeLogged: "04:15 IST",
    reportedBy: "Traction Power Controller",
    severity: "MINOR",
    status: "RESOLVED",
    ert: "Resolved at 05:10 IST",
    description: "OHE bird nest insulator flashover. Feeder CB-2 tripped momentarily.",
    actionTaken: "Power isolation permit cancelled after insulator cleaning. Normal traction restored.",
  },
];

export function IncidentsPage() {
  const { selectedId, revision } = useSimulation();
  const [activeTab, setActiveTab] = useState<"LOGBOOK" | "INJECT">("LOGBOOK");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const filteredIncidents = SAMPLE_INCIDENTS.filter((inc) => {
    if (categoryFilter !== "ALL" && inc.category !== categoryFilter) return false;
    return true;
  });

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to manage operational incidents and disruptions."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Incident Desk..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Operational Incident & Disruption Management Desk</h1>
            <span className="badge badge-accent">CONTROL OFFICE LOGBOOK</span>
          </div>
          <p className="muted">
            Indian Railways Unusual Occurrence & Accident Relief Protocol · Real-time incident logs, restoration tracking, and disruption injection
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Tab Switcher between Logbook and Injection Simulator */}
      <div
        className="flex-row justify-between items-center"
        style={{
          background: "#0F172A",
          color: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <div className="flex-row items-center gap-2">
          <div className="button-group">
            <button
              type="button"
              className={`button button-small ${activeTab === "LOGBOOK" ? "button-primary" : "button-ghost"}`}
              onClick={() => setActiveTab("LOGBOOK")}
            >
              Control Incident Logbook ({SAMPLE_INCIDENTS.length})
            </button>
            <button
              type="button"
              className={`button button-small ${activeTab === "INJECT" ? "button-primary" : "button-ghost"}`}
              onClick={() => setActiveTab("INJECT")}
            >
              Disruption Injection Simulator ⚡
            </button>
          </div>
        </div>

        {activeTab === "LOGBOOK" && (
          <div className="flex-row items-center gap-2">
            <span style={{ fontSize: "0.80rem", color: "#94A3B8" }}>Department:</span>
            <select
              className="select-small"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{ background: "#1E293B", color: "#F1F5F9", border: "1px solid #334155" }}
            >
              <option value="ALL">All Departments</option>
              <option value="SIGNALLING">S&T (Signalling)</option>
              <option value="TRACK_PWAY">P-Way (Permanent Way)</option>
              <option value="OHE_ELECTRICAL">Electrical (TRD / OHE)</option>
              <option value="ROLLING_STOCK">Mechanical (Loco / C&W)</option>
            </select>
          </div>
        )}
      </div>

      {activeTab === "LOGBOOK" ? (
        <div className="stack">
          {/* Incident Table */}
          <Panel
            title="Active Operational Incidents & Failures"
            subtitle="Logged by Station Masters, Section Controllers, Track Maintainers, and Locomotive Pilots"
          >
            <div className="table-wrapper" tabIndex={0} role="region" aria-label="Incident log table">
              <table className="table">
                <thead>
                  <tr>
                    <th>Incident ID</th>
                    <th>Dept / Type</th>
                    <th>Location</th>
                    <th>Time Logged</th>
                    <th>Reported By</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Expected Restoration</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIncidents.map((inc) => (
                    <tr key={inc.id}>
                      <td className="mono font-bold">{inc.id}</td>
                      <td>
                        <span className="badge badge-muted">{inc.category}</span>
                      </td>
                      <td>
                        <strong>{inc.location}</strong>
                        <p className="muted small" style={{ margin: "2px 0 0" }}>{inc.description}</p>
                      </td>
                      <td className="small">{inc.timeLogged}</td>
                      <td className="small">{inc.reportedBy}</td>
                      <td>
                        <Badge tone={inc.severity === "CRITICAL" ? "bad" : inc.severity === "MAJOR" ? "watch" : "good"}>
                          {inc.severity}
                        </Badge>
                      </td>
                      <td>
                        <span className={`badge ${inc.status === "ACTIVE" ? "badge-danger" : inc.status === "UNDER_RESTORATION" ? "badge-watch" : "badge-success"}`}>
                          {inc.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="small font-mono">{inc.ert}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* Incident Emergency Actions & SOPs */}
          <Panel
            title="Standard Operating Procedure (SOP) Quick Reference"
            subtitle="Immediate regulatory mandates per IR General Rules"
          >
            <div className="grid-two">
              <div className="metric-box" style={{ padding: "12px", background: "#F8FAFC", borderRadius: "6px" }}>
                <strong>Home Signal Failure SOP:</strong>
                <p className="small muted" style={{ margin: "4px 0 0" }}>
                  Issue Calling-on Signal (if provided) or Form T/369(3b) with Caution Order. Speed not to exceed 15 km/h over facing points. Verify point clamp and padlock.
                </p>
              </div>
              <div className="metric-box" style={{ padding: "12px", background: "#F8FAFC", borderRadius: "6px" }}>
                <strong>OHE Breakdown / Tripping SOP:</strong>
                <p className="small muted" style={{ margin: "4px 0 0" }}>
                  Immediately trip substation circuit breakers. Section Controller halts all electric trains in unaffected blocks. Diesel power summoned for rescue if required.
                </p>
              </div>
            </div>
          </Panel>
        </div>
      ) : (
        <DisruptionsPage />
      )}
    </div>
  );
}
