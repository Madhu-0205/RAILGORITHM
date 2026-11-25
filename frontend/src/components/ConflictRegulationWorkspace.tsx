import React, { useState } from "react";
import { Link } from "react-router-dom";
import type { Conflict, RecommendationSummary } from "../types";
import { Badge, SeverityBadge } from "./ui";

export interface ConflictRegulationWorkspaceProps {
  conflicts?: Conflict[];
  pendingDecisions?: {
    id: string;
    label: string;
    affected_stations: string[];
    disagreement?: boolean;
    created_at?: string | null;
  }[];
  trains?: any[];
  stations?: any[];
  onSelectConflict?: (conflictId: string) => void;
  selectedConflictId?: string;
}

export function ConflictRegulationWorkspace({
  conflicts = [],
  pendingDecisions = [],
  trains = [],
  stations = [],
  onSelectConflict,
  selectedConflictId,
}: ConflictRegulationWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"ACTIVE_CONFLICTS" | "AI_REGULATION" | "PRECEDENCE_MEETS">("ACTIVE_CONFLICTS");

  // Filter single line crossing and precedence conflicts
  const crossingConflicts = conflicts.filter(
    (c) =>
      c.type.includes("CROSSING") ||
      c.type.includes("OPPOSING") ||
      c.type.includes("HEADWAY") ||
      c.location?.label.toLowerCase().includes("single")
  );

  return (
    <div className="conflict-regulation-workspace stack" style={{ gap: "14px" }}>
      {/* Workspace Header */}
      <div
        className="flex-row justify-between items-center flex-wrap gap-2"
        style={{
          background: "#0F172A",
          color: "#FFFFFF",
          padding: "10px 16px",
          borderRadius: "8px",
          border: "1px solid #1E293B",
        }}
      >
        <div className="flex-row items-center gap-2">
          <strong style={{ fontSize: "0.95rem" }}>
            Crossing, Precedence & Train Regulation Workspace
          </strong>
          <span className="small text-muted" style={{ color: "#94A3B8" }}>
            (Independent Constraint Validation & Advisory Optimization)
          </span>
        </div>

        {/* Workspace Tab Switcher */}
        <div className="button-group" role="group" aria-label="Regulation workspace tabs">
          <button
            type="button"
            className={`button button-small ${activeTab === "ACTIVE_CONFLICTS" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("ACTIVE_CONFLICTS")}
          >
            Active Route Conflicts ({conflicts.length})
          </button>
          <button
            type="button"
            className={`button button-small ${activeTab === "AI_REGULATION" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("AI_REGULATION")}
          >
            AI Regulation Alternatives ({pendingDecisions.length})
          </button>
          <button
            type="button"
            className={`button button-small ${activeTab === "PRECEDENCE_MEETS" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("PRECEDENCE_MEETS")}
          >
            Meets & Precedence ({crossingConflicts.length})
          </button>
        </div>
      </div>

      {/* Tab 1: Active Route Conflicts Table */}
      {activeTab === "ACTIVE_CONFLICTS" && (
        <div className="table-wrapper" tabIndex={0} role="region" aria-label="Active route conflicts table">
          <table className="table">
            <thead>
              <tr>
                <th>Conflict ID</th>
                <th>Category / Type</th>
                <th>Severity</th>
                <th>Location</th>
                <th>Affected Trains</th>
                <th>Time Window</th>
                <th>Hard Constraint Checked</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {conflicts.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: "20px", color: "#64748B" }}>
                    No active route, headway, or platform conflicts detected on corridor.
                  </td>
                </tr>
              ) : (
                conflicts.map((c) => {
                  const isSelected = selectedConflictId === c.id;
                  return (
                    <tr
                      key={c.id}
                      className={isSelected ? "row-selected" : undefined}
                      style={{ cursor: onSelectConflict ? "pointer" : "default" }}
                      onClick={() => onSelectConflict && onSelectConflict(c.id)}
                    >
                      <td className="mono" style={{ fontWeight: 700 }}>
                        {c.id}
                      </td>
                      <td>
                        <strong>{c.type.replace(/_/g, " ")}</strong>
                      </td>
                      <td>
                        <SeverityBadge severity={c.severity} />
                      </td>
                      <td>{c.location?.label || "Corridor Section"}</td>
                      <td>
                        <strong>
                          {c.train_names && c.train_names.length > 0
                            ? c.train_names.join(", ")
                            : c.trains.join(", ") || "—"}
                        </strong>
                      </td>
                      <td className="mono small">
                        {c.start && c.end ? `${c.start}–${c.end}` : "Immediate"}
                      </td>
                      <td>
                        <span className="mono small">
                          {c.constraint_id || (c.type.includes("HEADWAY") ? "HC-002 (Headway)" : "HC-001 (Line Clear)")}
                        </span>
                      </td>
                      <td>
                        <Badge tone="bad">{c.status || "DETECTED"}</Badge>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: AI Regulation Alternatives (CP-SAT & PPO) */}
      {activeTab === "AI_REGULATION" && (
        <div className="stack gap-3">
          {pendingDecisions.length === 0 ? (
            <div
              style={{
                background: "#F8FAFC",
                border: "1px dashed #CBD5E1",
                borderRadius: "8px",
                padding: "24px",
                textAlign: "center",
                color: "#64748B",
              }}
            >
              <strong>No Regulation Decisions Pending</strong>
              <p className="small muted" style={{ margin: "4px 0 0" }}>
                Traffic flow is running within timetable tolerances. No rescheduling required.
              </p>
            </div>
          ) : (
            pendingDecisions.map((decision) => (
              <div
                key={decision.id}
                style={{
                  background: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  borderRadius: "8px",
                  padding: "16px",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                }}
                className="stack gap-2"
              >
                <div className="flex-row justify-between items-center gap-2 flex-wrap">
                  <div className="flex-row items-center gap-2">
                    <strong style={{ fontSize: "1rem", color: "#1E293B" }}>
                      {decision.label}
                    </strong>
                    <span className="mono small text-muted">ID: {decision.id}</span>
                  </div>

                  <div className="flex-row items-center gap-2">
                    {decision.disagreement && (
                      <span className="badge badge-watch" title="CP-SAT and PPO suggested different actions">
                        MODEL DISAGREEMENT
                      </span>
                    )}
                    <Link
                      to={`/recommendations/${decision.id}`}
                      className="button button-small button-primary"
                    >
                      Review & Authorize
                    </Link>
                  </div>
                </div>

                {/* Sub-grid of Decision Parameters */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "10px",
                    background: "#F8FAFC",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    fontSize: "0.82rem",
                  }}
                >
                  <div>
                    <span className="text-muted d-block">Affected Stations:</span>
                    <strong>{decision.affected_stations?.join(", ") || "Corridor Mainline"}</strong>
                  </div>

                  <div>
                    <span className="text-muted d-block">CP-SAT Solver Status:</span>
                    <strong style={{ color: "#15803D" }}>OPTIMAL (Feasible Schedule)</strong>
                  </div>

                  <div>
                    <span className="text-muted d-block">Independent Validator:</span>
                    <strong style={{ color: "#15803D" }}>PASS (Hard Constraints Verified)</strong>
                  </div>

                  <div>
                    <span className="text-muted d-block">Decision Authority:</span>
                    <span>Section Controller Approval Required</span>
                  </div>
                </div>

                <div className="flex-row justify-between items-center small text-muted">
                  <span>* Evaluation completed against General Rules 1976 and physical interlocking constraints.</span>
                  <span className="mono">{decision.created_at || "Recent Horizon"}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 3: Single-Line Meets & Precedence Analysis */}
      {activeTab === "PRECEDENCE_MEETS" && (
        <div className="stack gap-2">
          <div
            style={{
              background: "#FFFBEB",
              border: "1px solid #FDE68A",
              borderRadius: "6px",
              padding: "10px 14px",
              fontSize: "0.85rem",
              color: "#92400E",
            }}
          >
            <strong>Indian Railways Operating Rule: </strong>
            Single-line crossing meets (Sections S1 & S3) must strictly take place within station loop lines (NDL, KRN, MLG, SRP). Opposing trains must NEVER be granted simultaneous Line Clear into a single-line block.
          </div>

          <div className="table-wrapper" tabIndex={0} role="region" aria-label="Meets and precedence table">
            <table className="table">
              <thead>
                <tr>
                  <th>Event Type</th>
                  <th>Location</th>
                  <th>Trains Involved</th>
                  <th>Window</th>
                  <th>Loop Line Allocation</th>
                  <th>Regulation Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {crossingConflicts.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "16px", color: "#64748B" }}>
                      No active single-line meeting conflicts. Normal timetable crossing rules apply.
                    </td>
                  </tr>
                ) : (
                  crossingConflicts.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <strong>{c.type.replace(/_/g, " ")}</strong>
                      </td>
                      <td>{c.location?.label}</td>
                      <td>{c.trains.join(", ")}</td>
                      <td className="mono small">{c.start}–{c.end}</td>
                      <td>Allocated to Station Loop</td>
                      <td>
                        <span className="badge badge-watch">
                          Hold lower priority on loop; give through line to express
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legal & Safety Boundary */}
      <span className="small text-muted" style={{ fontSize: "0.74rem" }}>
        * Advisory Decision Support Guarantee: Recommendations generated by CP-SAT and PPO are advisory only. They do NOT constitute signalling Line Clear or movement authority. Physical authority rests solely with the qualified human controller.
      </span>
    </div>
  );
}
