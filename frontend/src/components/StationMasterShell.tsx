import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { FeedHealthBanner } from "../components/FeedHealthBanner";
import { SyntheticBanner } from "../components/ui";

interface StationNavItem {
  to: string;
  label: string;
  icon: string;
}

const STATION_NAV_ITEMS: StationNavItem[] = [
  { to: "/station-master/dashboard", label: "Station Yard Workspace", icon: "🚉" },
  { to: "/station-master/trains", label: "Train Movement Board", icon: "📋" },
  { to: "/station-master/adjacent", label: "Adjacent Block Awareness", icon: "⇄" },
  { to: "/station-master/platforms", label: "Platform & Line Berth", icon: "🏛" },
  { to: "/station-master/alerts", label: "Station Alerts & Local Advisory", icon: "⚠" },
  { to: "/station-master/rules", label: "Assumptions & Station Rules", icon: "⚙" },
];

export function StationMasterShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState<{ text: string; error: boolean } | null>(null);

  if (!user) return null;

  async function handleLogout() {
    await logout();
    navigate("/login/station-master", { replace: true });
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

  const assignedStation = user.station_id || (user.assigned_stations?.[0]) || "NDL";

  return (
    <div className="station-master-app-shell" style={{ display: "flex", minHeight: "100vh", background: "#0b0f19", color: "#f8fafc" }}>
      {/* Station Master Sidebar */}
      <aside
        style={{
          width: "270px",
          background: "#0f172a",
          borderRight: "1px solid #1e293b",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div>
          {/* Brand & Portal Header */}
          <div style={{ padding: "20px 18px", borderBottom: "1px solid #1e293b" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "24px" }}>🚉</span>
              <div>
                <strong style={{ display: "block", fontSize: "16px", letterSpacing: "1px", color: "#f8fafc" }}>
                  RAILGORITHM
                </strong>
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", letterSpacing: "0.5px", textTransform: "uppercase" }}>
                  Station Master Desk
                </span>
              </div>
            </div>

            <div
              style={{
                marginTop: "14px",
                background: "rgba(245, 158, 11, 0.1)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                borderRadius: "6px",
                padding: "8px 10px",
              }}
            >
              <div style={{ fontSize: "10px", textTransform: "uppercase", color: "#f59e0b", fontWeight: 700 }}>
                Designated Station
              </div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "#f8fafc", marginTop: "2px" }}>
                {assignedStation} Station Yard
              </div>
              <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                {user.division || "Southern Division"} (SWR)
              </div>
            </div>
          </div>

          {/* Navigation Items */}
          <nav style={{ padding: "16px 12px", display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ fontSize: "10px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "1px", padding: "6px 8px" }}>
              Station Local Controls
            </div>
            {STATION_NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "10px 12px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "#0f172a" : "#cbd5e1",
                  background: isActive ? "#f59e0b" : "transparent",
                  textDecoration: "none",
                  transition: "background 0.15s ease",
                })}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* User Identity & Logout */}
        <div style={{ padding: "16px", borderTop: "1px solid #1e293b", background: "#090d16" }}>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>
            {user.display_name}
          </div>
          <div style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700 }}>
            STATION MASTER
          </div>
          <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
            Assigned: {assignedStation}
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
            padding: "12px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span
              style={{
                background: "#f59e0b",
                color: "#0f172a",
                fontWeight: 800,
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "4px",
                textTransform: "uppercase",
              }}
            >
              Station Master Console
            </span>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc" }}>
              {assignedStation} Station Operations Desk
            </span>
            <span style={{ fontSize: "12px", color: "#64748b" }}>|</span>
            <span style={{ fontSize: "12px", color: "#94a3b8" }}>
              Absolute Block Territory (G&SR 1976)
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <FeedHealthBanner />
            <div
              style={{
                fontSize: "13px",
                fontWeight: 700,
                color: "#f59e0b",
                background: "rgba(245, 158, 11, 0.1)",
                padding: "4px 10px",
                borderRadius: "4px",
                border: "1px solid rgba(245, 158, 11, 0.3)",
              }}
            >
              YARD CLOCK: 17:50 IST
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
            <h3 style={{ margin: "0 0 16px 0", color: "#f8fafc" }}>Change Station Master Password</h3>
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
                  style={{ padding: "8px 12px", borderRadius: "4px", background: "#f59e0b", border: "none", color: "#0f172a", fontWeight: 700, cursor: "pointer" }}
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
