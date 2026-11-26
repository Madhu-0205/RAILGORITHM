import React, { useState } from "react";
import { Badge } from "./ui";

export interface CoordinationMessage {
  id: string;
  timestamp: string;
  origin: string;
  recipient: string;
  category: "LINE_CLEAR_VERIFICATION" | "CAUTION_ORDER" | "POWER_BLOCK" | "CREW_STATUS" | "STATION_UPDATE";
  relatedEntity: string;
  content: string;
  status: "CONFIRMED" | "ACKNOWLEDGED" | "PENDING_ACK";
}

export interface CoordinationAndHandoverProps {
  territoryName?: string;
  simTime?: string;
  activeTrainsCount?: number;
  delayedTrainsCount?: number;
  openConflictsCount?: number;
  activeRestrictionsCount?: number;
  sectionId?: string;
  controllerName?: string;
  shiftName?: string;
}

export function CoordinationAndHandover({
  territoryName = "NDL–VSN Mainline Corridor",
  simTime = "07:00 IST",
  activeTrainsCount = 4,
  delayedTrainsCount = 1,
  openConflictsCount = 1,
  activeRestrictionsCount = 3,
  sectionId,
  controllerName,
  shiftName,
}: CoordinationAndHandoverProps) {
  const [activeTab, setActiveTab] = useState<"COORDINATION_LOG" | "SHIFT_HANDOVER">("COORDINATION_LOG");
  const [handoverNote, setHandoverNote] = useState<string>(
    "Track tamping on B1 completed. Train 12625 running right time on platform 1 at Malgaon Junction. Train 51831 approaching Karanpur with +10m token wait. Handing over shift to Relief Section Controller."
  );
  const [handoverSigned, setHandoverSigned] = useState<boolean>(false);
  const [newMsgContent, setNewMsgContent] = useState("");
  const [newMsgRecipient, setNewMsgRecipient] = useState("SM-MLG (Malgaon SM)");

  const [messages, setMessages] = useState<CoordinationMessage[]>([
    {
      id: "MSG-101",
      timestamp: "06:12 IST",
      origin: "Section Controller",
      recipient: "SM-MLG (Malgaon SM)",
      category: "LINE_CLEAR_VERIFICATION",
      relatedEntity: "Train 12625 / Block B2U",
      content: "Verify line clear granted for Up Mail 12625 into Platform 1 at Malgaon.",
      status: "CONFIRMED",
    },
    {
      id: "MSG-102",
      timestamp: "06:16 IST",
      origin: "SM-KRN (Karanpur SM)",
      recipient: "Section Controller",
      category: "STATION_UPDATE",
      relatedEntity: "Train 51831 / Single Line S3",
      content: "Train 51831 holding at Karanpur Down starter awaiting single-line line-clear from Malgaon.",
      status: "ACKNOWLEDGED",
    },
    {
      id: "MSG-103",
      timestamp: "06:20 IST",
      origin: "TPC (Traction Power Controller)",
      recipient: "Section Controller",
      category: "POWER_BLOCK",
      relatedEntity: "Section S3 (MLG–SRP)",
      content: "Scheduled 25kV OHE power block approved from 07:00 to 09:00 IST for mast insulator replacement.",
      status: "CONFIRMED",
    },
  ]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsgContent.trim()) return;

    const newMsg: CoordinationMessage = {
      id: `MSG-${Date.now().toString().slice(-4)}`,
      timestamp: `${simTime} IST`,
      origin: "Section Controller",
      recipient: newMsgRecipient,
      category: "STATION_UPDATE",
      relatedEntity: "Control Section",
      content: newMsgContent.trim(),
      status: "CONFIRMED",
    };

    setMessages((prev) => [newMsg, ...prev]);
    setNewMsgContent("");
  };

  return (
    <div className="coordination-handover-workspace stack" style={{ gap: "14px" }}>
      {/* Header */}
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
            Control Office Coordination & Shift Handover Workspace
          </strong>
          <span className="small text-muted" style={{ color: "#94A3B8" }}>
            (Inter-Departmental Control Diary & Continuous Operations Ledger)
          </span>
        </div>

        {/* Tab Controls */}
        <div className="button-group" role="group" aria-label="Coordination tabs">
          <button
            type="button"
            className={`button button-small ${activeTab === "COORDINATION_LOG" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("COORDINATION_LOG")}
          >
            Coordination Diary ({messages.length})
          </button>
          <button
            type="button"
            className={`button button-small ${activeTab === "SHIFT_HANDOVER" ? "button-primary" : "button-ghost"}`}
            onClick={() => setActiveTab("SHIFT_HANDOVER")}
          >
            Shift Handover Console {handoverSigned ? "✓" : ""}
          </button>
        </div>
      </div>

      {/* Tab 1: Coordination Diary */}
      {activeTab === "COORDINATION_LOG" && (
        <div className="stack gap-3">
          {/* New Message Input Form */}
          <form
            onSubmit={handleSendMessage}
            className="flex-row gap-2 flex-wrap items-center"
            style={{
              background: "#F8FAFC",
              padding: "10px 14px",
              borderRadius: "6px",
              border: "1px solid #E2E8F0",
            }}
          >
            <select
              className="input input-small"
              style={{ width: "auto" }}
              value={newMsgRecipient}
              onChange={(e) => setNewMsgRecipient(e.target.value)}
              aria-label="Select message recipient"
            >
              <option value="SM-NDL (Nandpur SM)">SM-NDL (Nandpur SM)</option>
              <option value="SM-KRN (Karanpur SM)">SM-KRN (Karanpur SM)</option>
              <option value="SM-MLG (Malgaon SM)">SM-MLG (Malgaon SM)</option>
              <option value="SM-SRP (Suryapur SM)">SM-SRP (Suryapur SM)</option>
              <option value="SM-VSN (Vasanthpur SM)">SM-VSN (Vasanthpur SM)</option>
              <option value="TPC (Traction Power Controller)">TPC (Traction Power)</option>
              <option value="S&T (Signal & Telecom Controller)">S&T (Signal & Telecom)</option>
              <option value="P-Way (Permanent Way Control)">P-Way (Engineering)</option>
              <option value="Loco Control">Loco & Crew Controller</option>
            </select>

            <input
              type="text"
              placeholder="Record coordination note or instructions to station..."
              className="input input-small"
              style={{ flex: "1 1 240px" }}
              value={newMsgContent}
              onChange={(e) => setNewMsgContent(e.target.value)}
              aria-label="Message content"
            />

            <button type="submit" className="button button-small button-primary">
              Log Note
            </button>
          </form>

          {/* Messages Table */}
          <div className="table-wrapper" tabIndex={0} role="region" aria-label="Coordination diary table">
            <table className="table">
              <thead>
                <tr>
                  <th>Msg ID</th>
                  <th>Time (IST)</th>
                  <th>Origin</th>
                  <th>Recipient</th>
                  <th>Category</th>
                  <th>Entity / Movement</th>
                  <th>Operational Message</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((m) => (
                  <tr key={m.id}>
                    <td className="mono small font-bold">
                      <strong>{m.id}</strong>
                    </td>
                    <td className="mono small">{m.timestamp}</td>
                    <td><strong>{m.origin}</strong></td>
                    <td>{m.recipient}</td>
                    <td>
                      <Badge tone="muted">{m.category.replace(/_/g, " ")}</Badge>
                    </td>
                    <td className="mono small">{m.relatedEntity}</td>
                    <td style={{ maxWidth: "340px" }}>{m.content}</td>
                    <td>
                      <Badge tone="good">{m.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Shift Handover Console */}
      {activeTab === "SHIFT_HANDOVER" && (
        <div className="stack gap-3">
          {/* Territory Continuity Briefing Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "12px",
              background: "#F8FAFC",
              padding: "16px",
              borderRadius: "8px",
              border: "1px solid #E2E8F0",
            }}
          >
            <div>
              <span className="small text-muted d-block">Territory:</span>
              <strong style={{ fontSize: "1rem" }}>{territoryName}</strong>
              <span className="small text-muted d-block">Time: {simTime} IST</span>
            </div>

            <div>
              <span className="small text-muted d-block">Active Corridor Trains:</span>
              <strong style={{ fontSize: "1.1rem", color: "#2563EB" }}>
                {activeTrainsCount} Running
              </strong>
              <span className="small text-muted d-block">{delayedTrainsCount} Delayed</span>
            </div>

            <div>
              <span className="small text-muted d-block">Unresolved Conflicts:</span>
              <strong style={{ fontSize: "1.1rem", color: openConflictsCount > 0 ? "#DC2626" : "#16A34A" }}>
                {openConflictsCount} Open
              </strong>
              <span className="small text-muted d-block">Requires incoming review</span>
            </div>

            <div>
              <span className="small text-muted d-block">Active Restrictions:</span>
              <strong style={{ fontSize: "1.1rem", color: "#D97706" }}>
                {activeRestrictionsCount} Caution Orders
              </strong>
              <span className="small text-muted d-block">P-Way & OHE blocks</span>
            </div>
          </div>

          {/* Structured Handover Notes Input */}
          <div className="stack gap-2">
            <label htmlFor="handover-notes-textarea" className="small" style={{ fontWeight: 600 }}>
              Outgoing Section Controller Handover Briefing & Log:
            </label>
            <textarea
              id="handover-notes-textarea"
              rows={4}
              className="input"
              style={{ width: "100%", fontFamily: "inherit", fontSize: "0.88rem", padding: "10px" }}
              value={handoverNote}
              onChange={(e) => {
                setHandoverNote(e.target.value);
                setHandoverSigned(false);
              }}
              aria-label="Outgoing controller handover notes"
            />

            <div className="flex-row justify-between items-center flex-wrap gap-2">
              <span className="small text-muted">
                Handover records are cryptographically sealed in the SHA-256 audit ledger. Pending conflicts are never silently discarded.
              </span>

              <button
                type="button"
                className={`button button-small ${handoverSigned ? "button-ghost" : "button-primary"}`}
                onClick={() => setHandoverSigned(true)}
              >
                {handoverSigned ? "✓ Handover Briefing Signed" : "Sign & Transfer Shift"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual coordination notice */}
      <span className="small text-muted" style={{ fontSize: "0.74rem" }}>
        * Manual Control Office Coordination Record. No external telecommunication or signaling integration is active. All communications represent operator control entries.
      </span>
    </div>
  );
}
