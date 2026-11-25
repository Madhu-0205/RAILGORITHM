import React, { useMemo, useState } from "react";
import type { Conflict } from "../types";
import { Badge, SeverityBadge } from "./ui";

export interface AlertItem {
  id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "INFORMATIONAL";
  title: string;
  trains: string[];
  location: string;
  detectionTime: string;
  reason: string;
  dataSource: string;
  relatedConstraint: string;
  status: "UNACKNOWLEDGED" | "ACKNOWLEDGED" | "ACTION_PENDING" | "RESOLVED";
  suggestedAction: string;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
}

export type AttentionItem = AlertItem;

export interface OperationalAttentionPanelProps {
  conflicts?: Conflict[];
  onSelectConflict?: (conflictId: string) => void;
  selectedConflictId?: string;
}

export function OperationalAttentionPanel({
  conflicts = [],
  onSelectConflict,
  selectedConflictId,
}: OperationalAttentionPanelProps) {
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [unackOnly, setUnackOnly] = useState<boolean>(false);
  const [acknowledgedMap, setAcknowledgedMap] = useState<Record<string, { by: string; at: string }>>({});

  // Transform conflicts into operational alert cards
  const alerts = useMemo<AlertItem[]>(() => {
    return conflicts.map((c) => {
      let sev: "CRITICAL" | "HIGH" | "MEDIUM" | "INFORMATIONAL" = "MEDIUM";
      if (c.severity === "CRITICAL") sev = "CRITICAL";
      else if (c.severity === "HIGH") sev = "HIGH";
      else if (c.severity === "LOW") sev = "INFORMATIONAL";

      let suggested = "Review regulation alternatives in Decision Queue.";
      if (c.type === "HEADWAY_VIOLATION" || c.type === "HEADWAY") {
        suggested = "Issue hold order at preceding station loop to maintain statutory headway distance.";
      } else if (c.type === "PLATFORM_OCCUPANCY") {
        suggested = "Divert trailing train to secondary platform or hold at outer home signal.";
      } else if (c.type === "OPPOSING_MOVE" || c.type === "SINGLE_LINE_CROSSING") {
        suggested = "Enforce crossing halt at station with loop line; do not issue Line Clear into single line.";
      }

      const ackInfo = acknowledgedMap[c.id];

      return {
        id: c.id,
        severity: sev,
        title: c.type.replace(/_/g, " "),
        trains: c.train_names && c.train_names.length > 0 ? c.train_names : c.trains,
        location: c.location?.label || "Corridor Track",
        detectionTime: c.start || "Current Window",
        reason: c.description || "Operational safety constraint threshold exceeded",
        dataSource: "Independent Constraint Validator & Track Sensors",
        relatedConstraint:
          c.constraint_id || (c.type.includes("HEADWAY") ? "GR 8.01 / HC-002" : "GR 1.02(62) / HC-001"),
        status: ackInfo ? "ACKNOWLEDGED" : "UNACKNOWLEDGED",
        suggestedAction: suggested,
        acknowledgedBy: ackInfo?.by,
        acknowledgedAt: ackInfo?.at,
      };
    });
  }, [conflicts, acknowledgedMap]);

  // Sort by operational urgency: Critical > High > Medium > Informational
  const sortedAlerts = useMemo(() => {
    const weights: Record<string, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MEDIUM: 2,
      INFORMATIONAL: 1,
    };
    return [...alerts].sort((a, b) => {
      const diff = (weights[b.severity] || 0) - (weights[a.severity] || 0);
      if (diff !== 0) return diff;
      return a.id.localeCompare(b.id);
    });
  }, [alerts]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    return sortedAlerts.filter((a) => {
      if (severityFilter !== "ALL" && a.severity !== severityFilter) return false;
      if (unackOnly && a.status === "ACKNOWLEDGED") return false;
      return true;
    });
  }, [sortedAlerts, severityFilter, unackOnly]);

  const handleAcknowledge = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const now = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    setAcknowledgedMap((prev) => ({
      ...prev,
      [id]: { by: "Section Controller", at: `${now} IST` },
    }));
  };

  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL").length;
  const highCount = alerts.filter((a) => a.severity === "HIGH").length;
  const unackCount = alerts.filter((a) => a.status === "UNACKNOWLEDGED").length;

  return (
    <div className="operational-attention-panel stack" style={{ gap: "14px" }}>
      {/* Header & Urgency Tally */}
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
          <strong style={{ fontSize: "0.95rem" }}>Operational Attention & Triage Queue</strong>
          <span className="badge badge-bad" style={{ fontSize: "0.75rem", padding: "2px 7px" }}>
            {unackCount} Unacknowledged
          </span>
        </div>

        {/* Severity Badges */}
        <div className="flex-row items-center gap-2 small">
          {criticalCount > 0 && (
            <span style={{ color: "#FCA5A5", fontWeight: 700 }}>
              ● {criticalCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span style={{ color: "#FCD34D", fontWeight: 700 }}>
              ▲ {highCount} High
            </span>
          )}
          <span style={{ color: "#94A3B8" }}>
            Total: <strong>{alerts.length}</strong>
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex-row justify-between items-center flex-wrap gap-2">
        <div className="button-group" role="group" aria-label="Severity filter">
          <button
            type="button"
            className={`button button-small ${severityFilter === "ALL" ? "button-primary" : "button-ghost"}`}
            onClick={() => setSeverityFilter("ALL")}
          >
            All Alerts ({alerts.length})
          </button>
          <button
            type="button"
            className={`button button-small ${severityFilter === "CRITICAL" ? "button-primary" : "button-ghost"}`}
            onClick={() => setSeverityFilter("CRITICAL")}
          >
            Critical ({criticalCount})
          </button>
          <button
            type="button"
            className={`button button-small ${severityFilter === "HIGH" ? "button-primary" : "button-ghost"}`}
            onClick={() => setSeverityFilter("HIGH")}
          >
            High ({highCount})
          </button>
        </div>

        <label className="flex-row items-center gap-2 small text-muted" style={{ cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={unackOnly}
            onChange={(e) => setUnackOnly(e.target.checked)}
          />
          <span>Unacknowledged Only</span>
        </label>
      </div>

      {/* Alert Cards List */}
      {filteredAlerts.length === 0 ? (
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
          <strong>No active operational alerts matching criteria</strong>
          <p className="small muted" style={{ margin: "4px 0 0" }}>
            All safety boundaries and headways operating within nominal parameters.
          </p>
        </div>
      ) : (
        <div className="stack gap-2" style={{ maxHeight: "480px", overflowY: "auto" }}>
          {filteredAlerts.map((alert) => {
            const isSelected = selectedConflictId === alert.id;
            const isCritical = alert.severity === "CRITICAL";
            const isHigh = alert.severity === "HIGH";

            const cardBorder = isSelected
              ? "#2563EB"
              : isCritical
              ? "#FECACA"
              : isHigh
              ? "#FDE68A"
              : "#E2E8F0";

            const cardBg = isCritical ? "#FEF2F2" : isHigh ? "#FFFBEB" : "#F8FAFC";

            return (
              <div
                key={alert.id}
                className="operational-alert-card"
                style={{
                  background: cardBg,
                  border: `1px solid ${cardBorder}`,
                  borderRadius: "8px",
                  padding: "12px 16px",
                  cursor: onSelectConflict ? "pointer" : "default",
                  boxShadow: isSelected ? "0 4px 12px rgba(37,99,235,0.15)" : "none",
                }}
                onClick={() => onSelectConflict && onSelectConflict(alert.id)}
              >
                {/* Alert Top Row */}
                <div className="flex-row justify-between items-center gap-2 mb-1">
                  <div className="flex-row items-center gap-2">
                    <SeverityBadge severity={alert.severity} />
                    <strong style={{ fontSize: "0.95rem", color: "#0F172A" }}>
                      {alert.title}
                    </strong>
                    <span className="mono small text-muted">ID: {alert.id}</span>
                  </div>

                  <div>
                    {alert.status === "ACKNOWLEDGED" ? (
                      <span className="badge badge-good" style={{ fontSize: "0.72rem" }}>
                        ✓ Acknowledged ({alert.acknowledgedAt})
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="button button-small button-ghost"
                        style={{ fontSize: "0.75rem", padding: "3px 8px", borderColor: "#CBD5E1" }}
                        onClick={(e) => handleAcknowledge(alert.id, e)}
                        aria-label={`Acknowledge alert ${alert.id}`}
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>

                {/* Details Grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "8px",
                    margin: "8px 0",
                    fontSize: "0.82rem",
                  }}
                >
                  <div>
                    <span className="text-muted d-block">Location & Window:</span>
                    <strong>{alert.location}</strong>
                    <span className="mono small text-muted d-block">Time: {alert.detectionTime}</span>
                  </div>

                  <div>
                    <span className="text-muted d-block">Affected Movement(s):</span>
                    <strong>{alert.trains.join(", ") || "Corridor Track"}</strong>
                  </div>

                  <div>
                    <span className="text-muted d-block">Constraint Rule:</span>
                    <span className="mono small">{alert.relatedConstraint}</span>
                    <span className="small text-muted d-block">Sensor: {alert.dataSource}</span>
                  </div>
                </div>

                {/* Reason & Actionable Advice */}
                <div
                  style={{
                    background: "#FFFFFF",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid #E2E8F0",
                    fontSize: "0.8rem",
                  }}
                >
                  <p style={{ margin: "0 0 4px", color: "#334155" }}>
                    <strong>Observation: </strong>
                    {alert.reason}
                  </p>
                  <p style={{ margin: 0, color: "#1E3A8A" }}>
                    <strong>Suggested Action: </strong>
                    {alert.suggestedAction}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Safety Notice */}
      <span className="small text-muted" style={{ fontSize: "0.74rem" }}>
        * Acknowledgement logs that the Section Controller has reviewed the condition. It does NOT authorize train movement or clear signals.
      </span>
    </div>
  );
}
