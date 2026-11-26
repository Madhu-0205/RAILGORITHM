import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { FeedHealthBanner } from "../components/FeedHealthBanner";
import { NewSimulationDialog } from "../components/NewSimulationDialog";
import { SyntheticBanner } from "../components/ui";
import { formatMinutes } from "../lib/format";
import { useSimulation } from "../simulation";

interface SectionNavItem {
  to: string;
  label: string;
  icon: string;
  group?: string;
}

const SECTION_NAV_ITEMS: SectionNavItem[] = [
  // Core Dispatch Console
  { to: "/section-controller/dashboard", label: "Section Control Console", icon: "🎛️", group: "Core Console" },
  { to: "/section-controller/graph", label: "Master Control Graph", icon: "📈", group: "Core Console" },
  { to: "/section-controller/topology", label: "Corridor Topology Strip", icon: "⌁", group: "Core Console" },
  { to: "/section-controller/blocks", label: "Block Section Board", icon: "⏹", group: "Core Console" },

  // Traffic Regulation
  { to: "/section-controller/trains", label: "Corridor Train Ledger", icon: "▤", group: "Traffic Regulation" },
  { to: "/section-controller/crossings", label: "Crossings & Precedence", icon: "⇄", group: "Traffic Regulation" },
  { to: "/section-controller/junctions", label: "Junction Crossing Workspace", icon: "💎", group: "Traffic Regulation" },
  { to: "/section-controller/conflicts", label: "Conflict & AI Regulation", icon: "⚠", group: "Traffic Regulation" },

  // Operations & Safety
  { to: "/section-controller/restrictions", label: "Engineering Restrictions", icon: "🚧", group: "Operations & Safety" },
  { to: "/section-controller/incidents", label: "Incident Desk", icon: "🚨", group: "Operations & Safety" },
  { to: "/section-controller/analytics", label: "Punctuality Analytics", icon: "▥", group: "Operations & Safety" },

  // Governance & Handover
  { to: "/section-controller/handover", label: "Shift Handover Diary", icon: "📋", group: "Governance" },
  { to: "/section-controller/audit", label: "Decision Audit Trail", icon: "⛓", group: "Governance" },
  { to: "/section-controller/rules", label: "Assumptions & Constraints", icon: "⚙", group: "Governance" },
];

export function SectionControllerShell() {
  const { user, logout } = useAuth();
  const {
    simulations,
    selected,
    selectedId,
    select,
    refresh,
    loading,
    scenarios,
  } = useSimulation();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState<{ text: string; error: boolean } | null>(null);

  if (!user) return null;

  async function handleLogout() {
    await logout();
    navigate("/login/section-controller", { replace: true });
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwdMsg(null);
    try {
      const res = await api.changePassword(oldPassword, newPassword);
      setPwdMsg({ text: res.message || "Password updated successfully.", error: false });
      setOldPassword("");
      setNewPassword("");
      setTimeout(() => setShowPasswordModal(false), 1500);
    } catch (err) {
      setPwdMsg({ text: err instanceof Error ? err.message : "Password change failed", error: true });
    }
  }

  async function runControl(
    label: string,
    action: () => Promise<unknown>,
    note: string,
  ) {
    setBusy(label);
    setMessage(null);
    try {
      await action();
      await refresh();
      setMessage(note);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  // Group items by category
  const groups: { [key: string]: SectionNavItem[] } = {};
  for (const item of SECTION_NAV_ITEMS) {
    const g = item.group || "Other";
    if (!groups[g]) groups[g] = [];
    groups[g].push(item);
  }

  return (
    <div className="section-controller-app-shell" style={{ display: "flex", minHeight: "100vh", background: "#0b0f19", color: "#f8fafc" }}>
      {/* Section Controller Sidebar */}
      <aside
        style={{
          width: "280px",
          background: "#0f172a",
          borderRight: "1px solid #1e293b",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ overflowY: "auto" }}>
          {/* Brand & Portal Header */}
          <div style={{ padding: "20px 18px", borderBottom: "1px solid #1e293b" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "24px" }}>🎛️</span>
              <div>
                <strong style={{ display: "block", fontSize: "16px", letterSpacing: "1px", color: "#f8fafc" }}>
                  RAILGORITHM
                </strong>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#38bdf8", letterSpacing: "0.5px", textTransform: "uppercase" }}>
                  Section Control Office
                </span>
              </div>
            </div>

            <div
              style={{
                marginTop: "14px",
                background: "rgba(2, 132, 199, 0.1)",
                border: "1px solid rgba(2, 132, 199, 0.3)",
                borderRadius: "6px",
                padding: "8px 10px",
              }}
            >
              <div style={{ fontSize: "10px", textTransform: "uppercase", color: "#38bdf8", fontWeight: 700 }}>
                Authorized Control Territory
              </div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#f8fafc", marginTop: "2px" }}>
                {user.control_area === "NORTHERN_CONTROL_AREA"
                  ? "Northern Area (NDL-MLG)"
                  : user.control_area === "SOUTHERN_CONTROL_AREA"
                  ? "Southern Area (MLG-VSN)"
                  : "Full Corridor (NDL-VSN)"}
              </div>
              <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                5 Stations | 4 Sections | 60.0 km
              </div>
            </div>
          </div>

          {/* Navigation Groups */}
          <nav style={{ padding: "12px 10px", display: "flex", flexDirection: "column", gap: "16px" }}>
            {Object.entries(groups).map(([groupTitle, items]) => (
              <div key={groupTitle}>
                <div style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", padding: "4px 8px", marginBottom: "4px" }}>
                  {groupTitle}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  {items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      style={({ isActive }) => ({
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "8px 10px",
                        borderRadius: "6px",
                        fontSize: "13px",
                        fontWeight: isActive ? 600 : 500,
                        color: isActive ? "#0f172a" : "#cbd5e1",
                        background: isActive ? "#38bdf8" : "transparent",
                        textDecoration: "none",
                        transition: "background 0.15s ease",
                      })}
                    >
                      <span style={{ fontSize: "14px" }}>{item.icon}</span>
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>
        </div>

        {/* User Identity & Logout */}
        <div style={{ padding: "16px", borderTop: "1px solid #1e293b", background: "#090d16" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>
            {user.display_name}
          </div>
          <div style={{ fontSize: "11px", color: "#38bdf8", fontWeight: 700 }}>
            SECTION CONTROLLER
          </div>
          <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
            Jurisdiction: {user.control_area || "CORRIDOR"}
          </div>

          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            <button
              type="button"
              onClick={() => setShowPasswordModal(true)}
              style={{
                flex: 1,
                padding: "6px 8px",
                borderRadius: "4px",
                background: "#1e293b",
                border: "1px solid #334155",
                color: "#cbd5e1",
                fontSize: "11px",
                cursor: "pointer",
              }}
            >
              Password
            </button>
            <button
              type="button"
              onClick={handleLogout}
              style={{
                flex: 1,
                padding: "6px 8px",
                borderRadius: "4px",
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                color: "#fca5a5",
                fontSize: "11px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Operating Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top Operational Status Bar */}
        <header
          style={{
            background: "#0f172a",
            borderBottom: "1px solid #1e293b",
            padding: "10px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          {/* Left: Simulation & Mode Selector */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <span
              style={{
                background: "#0284c7",
                color: "#f8fafc",
                fontWeight: 800,
                fontSize: "11px",
                padding: "3px 8px",
                borderRadius: "4px",
                textTransform: "uppercase",
              }}
            >
              Control Office
            </span>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <label htmlFor="sc-sim-select" style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase" }}>
                Simulation:
              </label>
              <select
                id="sc-sim-select"
                value={selectedId ?? ""}
                onChange={(e) => select(e.target.value)}
                disabled={loading}
                style={{
                  background: "#1e293b",
                  border: "1px solid #475569",
                  color: "#f8fafc",
                  fontSize: "12px",
                  borderRadius: "4px",
                  padding: "4px 8px",
                }}
              >
                {simulations.map((sim) => (
                  <option key={sim.id} value={sim.id}>
                    {sim.name} · v{sim.state_version} · {sim.status}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Advance Controls */}
            {selected && (
              <div style={{ display: "flex", gap: "4px" }}>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => runControl("advance5", () => api.advance(selected.id, 5), "Advanced 5m")}
                  style={{ padding: "3px 7px", fontSize: "11px", background: "#1e293b", border: "1px solid #475569", color: "#f8fafc", borderRadius: "3px", cursor: "pointer" }}
                >
                  +5m
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => runControl("advance15", () => api.advance(selected.id, 15), "Advanced 15m")}
                  style={{ padding: "3px 7px", fontSize: "11px", background: "#1e293b", border: "1px solid #475569", color: "#f8fafc", borderRadius: "3px", cursor: "pointer" }}
                >
                  +15m
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => runControl("advance30", () => api.advance(selected.id, 30), "Advanced 30m")}
                  style={{ padding: "3px 7px", fontSize: "11px", background: "#1e293b", border: "1px solid #475569", color: "#f8fafc", borderRadius: "3px", cursor: "pointer" }}
                >
                  +30m
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => runControl("pause", () => api.pause(selected.id, selected.status !== "PAUSED"), selected.status === "PAUSED" ? "Simulation resumed" : "Simulation paused")}
                  style={{ padding: "3px 7px", fontSize: "11px", background: "#1e293b", border: "1px solid #475569", color: "#f8fafc", borderRadius: "3px", cursor: "pointer" }}
                >
                  {selected.status === "RUNNING" ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => runControl("reset", () => api.reset(selected.id), "Simulation reset")}
                  style={{ padding: "3px 7px", fontSize: "11px", background: "rgba(239, 68, 68, 0.2)", border: "1px solid #ef4444", color: "#fca5a5", borderRadius: "3px", cursor: "pointer" }}
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={() => setCreating(true)}
                  style={{ padding: "3px 9px", fontSize: "11px", background: "#0284c7", border: "none", color: "#f8fafc", fontWeight: 600, borderRadius: "3px", cursor: "pointer" }}
                >
                  New simulation
                </button>
              </div>
            )}
          </div>

          {/* Right: Clock & Telemetry */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <FeedHealthBanner />
            <div
              style={{
                fontSize: "13px",
                fontWeight: 700,
                color: "#38bdf8",
                background: "rgba(2, 132, 199, 0.15)",
                padding: "4px 10px",
                borderRadius: "4px",
                border: "1px solid rgba(2, 132, 199, 0.3)",
              }}
            >
              DISPATCH CLOCK: {selected ? formatMinutes(selected.sim_time_min) : "17:50"} IST
            </div>
          </div>
        </header>

        {/* Global Safety & Synthetic Disclaimer */}
        <div style={{ padding: "12px 24px 0" }}>
          <SyntheticBanner />
        </div>

        {/* Main Content Viewport */}
        <main style={{ flex: 1, padding: "16px 24px 32px", overflowY: "auto" }}>
          <Outlet />
        </main>
      </div>

      {/* New Simulation Dialog */}
      {creating && (
        <NewSimulationDialog
          scenarios={scenarios}
          onClose={() => setCreating(false)}
        />
      )}

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              padding: "24px",
              maxWidth: "400px",
              width: "100%",
            }}
          >
            <h3 style={{ margin: "0 0 16px 0", color: "#f8fafc" }}>Change Controller Password</h3>
            {pwdMsg && (
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "4px",
                  marginBottom: "12px",
                  fontSize: "12px",
                  background: pwdMsg.error ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                  color: pwdMsg.error ? "#fca5a5" : "#6ee7b7",
                }}
              >
                {pwdMsg.text}
              </div>
            )}
            <form onSubmit={handleChangePassword} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", background: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "#94a3b8", marginBottom: "4px" }}>New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", background: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  style={{ padding: "8px 12px", borderRadius: "4px", background: "#334155", border: "none", color: "#f8fafc", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: "8px 12px", borderRadius: "4px", background: "#0284c7", border: "none", color: "#f8fafc", fontWeight: 700, cursor: "pointer" }}
                >
                  Update
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
