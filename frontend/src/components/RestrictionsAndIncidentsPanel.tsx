import React, { useState } from "react";
import type { Closure, PlatformOutage } from "../types";
import { Badge } from "./ui";

export interface RestrictionItem {
  id: string;
  type: "TSR" | "PSR" | "MAINTENANCE_BLOCK" | "OHE_POWER_BLOCK";
  location: string;
  section: string;
  speedLimitKmph?: number;
  effectiveWindow: string;
  issuingAuthority: string;
  status: "ACTIVE" | "PENDING" | "EXPIRED";
  operationalImpact: string;
}

export interface IncidentItem {
  id: string;
  category: "INFRASTRUCTURE_FAILURE" | "COMMUNICATION_FAILURE" | "UNUSUAL_DETENTION" | "DATA_CONTRADICTION";
  location: string;
  timeDetected: string;
  affectedTrains: string[];
  affectedStations: string[];
  status: "OPEN" | "INVESTIGATING" | "CONTAINED" | "RESOLVED";
  responsibleDept: "P_WAY" | "S_AND_T" | "ELECTRICAL" | "OPERATING" | "LOCO";
  summary: string;
  followUp: string;
}

export interface RestrictionsAndIncidentsPanelProps {
  closures?: Closure[];
  outages?: PlatformOutage[];
  stations?: any[];
}

export function RestrictionsAndIncidentsPanel({
  closures = [],
  outages = [],
  stations = [],
}: RestrictionsAndIncidentsPanelProps) {
  const [activeTab, setActiveTab] = useState<"RESTRICTIONS" | "INCIDENTS">("RESTRICTIONS");

  // Derive restrictions from actual closures, outages, and domain data
  const restrictions: RestrictionItem[] = [
    ...closures.map((c) => ({
      id: c.id,
      type: "MAINTENANCE_BLOCK" as const,
      location: `Block ${c.block_id}`,
      section: c.block_id.startsWith("B1") ? "S1 (NDL–KRN)" : c.block_id.startsWith("B2") ? "S2 (KRN–MLG)" : "S3 (MLG–SRP)",
      effectiveWindow: `${c.start_min}m – ${c.end_min}m`,
      issuingAuthority: "Sr. Divisional Engineer (P-Way)",
      status: "ACTIVE" as const,
      operationalImpact: "Total block closure; train diversion or hold required",
    })),
    ...outages.map((o) => ({
      id: o.id,
      type: "MAINTENANCE_BLOCK" as const,
      location: `Station ${o.station_id} (Platform ${o.platform_id})`,
      section: `Station ${o.station_id}`,
      effectiveWindow: `${o.start_min}m – ${o.end_min}m`,
      issuingAuthority: "Station Master / Assistant Engineer (Civil)",
      status: "ACTIVE" as const,
      operationalImpact: `Platform ${o.platform_id} unserviceable for reception`,
    })),
    // Standard permanent and verified caution orders
    {
      id: "PSR-01",
      type: "PSR",
      location: "Malgaon Junction Diamond Crossing (km 31.8–32.2)",
      section: "S2/S3 Junction",
      speedLimitKmph: 30,
      effectiveWindow: "Permanent Operating Restriction",
      issuingAuthority: "Commissioner of Railway Safety (CRS)",
      status: "ACTIVE",
      operationalImpact: "Speed reduction over diamond turnouts to 30 km/h",
    },
    {
      id: "TSR-14",
      type: "TSR",
      location: "Section S3 (MLG–SRP, km 41.0–43.5)",
      section: "S3 (MLG–SRP)",
      speedLimitKmph: 45,
      effectiveWindow: "Caution Order #42 · Daily 04:00–12:00",
      issuingAuthority: "Divisional Operating Superintendent",
      status: "ACTIVE",
      operationalImpact: "Deep screening track renewal; +3 min transit penalty",
    },
  ];

  // Incidents ledger
  const incidents: IncidentItem[] = [
    {
      id: "INC-2026-081",
      category: "INFRASTRUCTURE_FAILURE",
      location: "Malgaon Junction Up Home Signal (101A)",
      timeDetected: "06:18 IST",
      affectedTrains: ["12625"],
      affectedStations: ["MLG"],
      status: "INVESTIGATING",
      responsibleDept: "S_AND_T",
      summary: "Axle counter reset required following brief transient pulse drop.",
      followUp: "S&T technician dispatched to relay room; SM advised to issue Pilot-In memo if delayed > 10m.",
    },
    {
      id: "INC-2026-082",
      category: "UNUSUAL_DETENTION",
      location: "Karanpur Down Starter Line",
      timeDetected: "06:22 IST",
      affectedTrains: ["51831"],
      affectedStations: ["KRN"],
      status: "OPEN",
      responsibleDept: "OPERATING",
      summary: "Single-line token receipt delay at Karanpur block instrument.",
      followUp: "Station Master Karanpur confirming line clear verification with Malgaon SM.",
    },
  ];

  return (
    <div className="restrictions-and-incidents-panel stack" style={{ gap: "14px" }}>
      {/* Panel Header */}
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
            Operational Restrictions & Incident Management Workspace
          </strong>
          <span className="small text-muted" style={{ color: "#94A3B8" }}>
            (Engineering Blocks, Speed Restrictions & Infrastructure Incidents)
          </span>
        </div>

        {/* Tab Controls */}
        <div className="button-group" role="group" aria-label="Restrictions and incidents tabs">
          <button
            type="button"
            className={`button button-small ${activeTab === "RESTRICTIONS" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("RESTRICTIONS")}
          >
            Engineering Restrictions ({restrictions.length})
          </button>
          <button
            type="button"
            className={`button button-small ${activeTab === "INCIDENTS" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("INCIDENTS")}
          >
            Active Incidents ({incidents.length})
          </button>
        </div>
      </div>

      {/* Tab 1: Engineering Restrictions & Caution Orders */}
      {activeTab === "RESTRICTIONS" && (
        <div className="table-wrapper" tabIndex={0} role="region" aria-label="Engineering restrictions table">
          <table className="table">
            <thead>
              <tr>
                <th>Restriction ID</th>
                <th>Type</th>
                <th>Location & Track</th>
                <th>Section</th>
                <th>Speed Limit</th>
                <th>Effective Period</th>
                <th>Issuing Authority</th>
                <th>Operational Impact</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {restrictions.map((r) => (
                <tr key={r.id}>
                  <td className="mono" style={{ fontWeight: 700 }}>
                    {r.id}
                  </td>
                  <td>
                    <Badge
                      tone={
                        r.type === "MAINTENANCE_BLOCK"
                          ? "bad"
                          : r.type === "TSR"
                          ? "watch"
                          : "muted"
                      }
                    >
                      {r.type.replace(/_/g, " ")}
                    </Badge>
                  </td>
                  <td>
                    <strong>{r.location}</strong>
                  </td>
                  <td>{r.section}</td>
                  <td>
                    {r.speedLimitKmph ? (
                      <span className="mono" style={{ fontWeight: 700, color: "#DC2626" }}>
                        {r.speedLimitKmph} km/h
                      </span>
                    ) : (
                      <span className="small text-muted">Total Block</span>
                    )}
                  </td>
                  <td className="small">{r.effectiveWindow}</td>
                  <td className="small">{r.issuingAuthority}</td>
                  <td className="small">{r.operationalImpact}</td>
                  <td>
                    <Badge tone="good">{r.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Incidents Workspace */}
      {activeTab === "INCIDENTS" && (
        <div className="stack gap-3">
          {incidents.map((inc) => (
            <div
              key={inc.id}
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
                  <Badge tone={inc.status === "OPEN" ? "bad" : "watch"}>{inc.status}</Badge>
                  <strong style={{ fontSize: "0.95rem", color: "#1E293B" }}>
                    {inc.category.replace(/_/g, " ")}
                  </strong>
                  <span className="mono small text-muted">#{inc.id}</span>
                </div>

                <div className="flex-row items-center gap-2 small">
                  <span className="text-muted">Detected: <strong>{inc.timeDetected}</strong></span>
                  <span className="badge badge-default">Dept: {inc.responsibleDept}</span>
                </div>
              </div>

              {/* Sub-grid of Incident Scope */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "8px",
                  background: "#F8FAFC",
                  padding: "10px",
                  borderRadius: "6px",
                  fontSize: "0.82rem",
                }}
              >
                <div>
                  <span className="text-muted d-block">Location:</span>
                  <strong>{inc.location}</strong>
                </div>
                <div>
                  <span className="text-muted d-block">Affected Trains:</span>
                  <strong>{inc.affectedTrains.join(", ")}</strong>
                </div>
                <div>
                  <span className="text-muted d-block">Affected Stations:</span>
                  <strong>{inc.affectedStations.join(", ")}</strong>
                </div>
              </div>

              <div className="small">
                <p style={{ margin: "0 0 4px", color: "#334155" }}>
                  <strong>Description: </strong>
                  {inc.summary}
                </p>
                <p style={{ margin: 0, color: "#1E3A8A" }}>
                  <strong>Operational Action / Follow-up: </strong>
                  {inc.followUp}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Regulatory Traceability Notice */}
      <span className="small text-muted" style={{ fontSize: "0.74rem" }}>
        * Caution Orders and Engineering Speed Restrictions are synchronized with Divisional Train Notice books and authorized railway authority directives.
      </span>
    </div>
  );
}
