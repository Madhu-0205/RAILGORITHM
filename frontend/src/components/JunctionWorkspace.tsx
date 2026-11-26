import React from "react";
import type { JunctionCrossingScenario, SectionControllerJunctionWorkspace } from "../types";
import { Badge, Panel } from "./ui";

interface JunctionWorkspaceProps {
  data: SectionControllerJunctionWorkspace;
  onSelectScenario?: (scenario: JunctionCrossingScenario) => void;
}

export function JunctionWorkspace({ data, onSelectScenario }: JunctionWorkspaceProps) {
  const { monitored_junctions, active_scenarios, simulation_time } = data;

  return (
    <div className="junction-workspace-container" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>🔀</span> Junction Crossing & Precedence Management Workspace
          </h3>
          <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "#94a3b8" }}>
            Decision-support for convergence bottlenecks and single-line meet-and-cross conflicts
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {monitored_junctions.map((j) => (
            <span key={j} style={{ background: "#1e293b", color: "#38bdf8", padding: "4px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
              Junction: {j}
            </span>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        {active_scenarios.map((scenario) => {
          const rec = scenario.recommended_resolution;
          const alt = scenario.alternative_option;

          return (
            <div
              key={scenario.id}
              style={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
              }}
            >
              {/* Scenario Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: "8px" }}>
                <div>
                  <span style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700, textTransform: "uppercase" }}>
                    {scenario.conflict_type.replace(/_/g, " ")} — {scenario.id}
                  </span>
                  <h4 style={{ margin: "2px 0 0 0", fontSize: "15px", color: "#f8fafc" }}>
                    Location: {scenario.junction_name} ({scenario.junction_id})
                  </h4>
                </div>
                <span style={{ background: "#1e293b", color: "#10b981", padding: "4px 10px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                  Net Saving: {rec.net_corridor_saving_min} min
                </span>
              </div>

              {/* Conflicting Trains Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {/* Train A */}
                <div style={{ background: "#1e293b", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                    <strong style={{ color: "#38bdf8" }}>🚆 Train A: {scenario.train_a.name}</strong>
                    <span style={{ background: "#0f172a", color: "#fdba74", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700 }}>
                      Priority {scenario.train_a.priority} ({scenario.train_a.type})
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", color: "#cbd5e1", marginTop: "4px" }}>
                    Direction: {scenario.train_a.direction} | Current Delay: <strong>+{scenario.train_a.current_delay_min}m</strong>
                  </div>
                </div>

                {/* Train B */}
                <div style={{ background: "#1e293b", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                    <strong style={{ color: "#94a3b8" }}>🚆 Train B: {scenario.train_b.name}</strong>
                    <span style={{ background: "#0f172a", color: "#cbd5e1", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700 }}>
                      Priority {scenario.train_b.priority} ({scenario.train_b.type})
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", color: "#cbd5e1", marginTop: "4px" }}>
                    Direction: {scenario.train_b.direction} | Current Delay: <strong>+{scenario.train_b.current_delay_min}m</strong>
                  </div>
                </div>
              </div>

              {/* Comparison Matrix: AI Recommended vs Alternative */}
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "12px" }}>
                {/* Recommended Option */}
                <div style={{ background: "#064e3b", border: "1px solid #059669", padding: "12px", borderRadius: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#a7f3d0", textTransform: "uppercase" }}>
                      ★ AI Recommended Resolution: {rec.action.replace(/_/g, " ")}
                    </span>
                    <span style={{ fontSize: "11px", color: "#6ee7b7", fontWeight: 700 }}>
                      Train A: +{rec.delay_impact_train_a_min}m | Train B: +{rec.delay_impact_train_b_min}m
                    </span>
                  </div>
                  <p style={{ margin: "6px 0", fontSize: "12px", color: "#ecfdf5" }}>
                    {rec.explanation}
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "10px", color: "#a7f3d0" }}>
                    {rec.safety_constraints_verified.map((sc, i) => (
                      <span key={i} style={{ background: "#065f46", padding: "2px 6px", borderRadius: "3px" }}>
                        ✓ {sc.rule}: {sc.name}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Alternative Option */}
                <div style={{ background: "#1e293b", border: "1px solid #475569", padding: "12px", borderRadius: "6px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#cbd5e1", textTransform: "uppercase" }}>
                      Alternative: {alt.action.replace(/_/g, " ")}
                    </span>
                    <span style={{ fontSize: "11px", color: "#f87171", fontWeight: 700 }}>
                      Penalty: +{alt.net_corridor_penalty_min}m
                    </span>
                  </div>
                  <p style={{ margin: "6px 0", fontSize: "12px", color: "#94a3b8" }}>
                    {alt.explanation}
                  </p>
                  <div style={{ fontSize: "10px", color: "#fca5a5" }}>
                    Train A: +{alt.delay_impact_train_a_min}m | Train B: +{alt.delay_impact_train_b_min}m
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
