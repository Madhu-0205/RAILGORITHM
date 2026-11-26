import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { formatMinutes } from "../lib/format";
import { useSimulation } from "../simulation";
import { FeedHealthBanner } from "./FeedHealthBanner";
import { NewSimulationDialog } from "./NewSimulationDialog";
import { SyntheticBanner } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  roles: string[];
  group?: string;
}

const NAV_ITEMS: NavItem[] = [
  // Core Control Office Workspaces
  { to: "/", label: "Dashboard", icon: "◉", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Core Console" },
  { to: "/station-master", label: "Station Yard Workspace", icon: "🚉", roles: ["STATION_MASTER"], group: "Core Console" },
  { to: "/section-controller", label: "Section Control Console", icon: "🎛️", roles: ["SECTION_MASTER"], group: "Core Console" },
  { to: "/graph", label: "Master Control Graph", icon: "📈", roles: ["SECTION_MASTER"], group: "Core Console" },
  { to: "/stations", label: "Station Control", icon: "🏛", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Core Console" },
  { to: "/blocks", label: "Block Section Board", icon: "⏹", roles: ["SECTION_MASTER"], group: "Core Console" },

  // Traffic Regulation
  { to: "/trains", label: "Train Movements", icon: "▤", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Traffic Regulation" },
  { to: "/crossings", label: "Crossings & Precedence", icon: "⇄", roles: ["SECTION_MASTER"], group: "Traffic Regulation" },
  { to: "/conflicts", label: "Conflict Detection", icon: "⚠", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Traffic Regulation" },
  { to: "/recommendations", label: "AI Recommendations", icon: "✦", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Traffic Regulation" },

  // Operations & Safety
  { to: "/restrictions", label: "Engineering Restrictions", icon: "🚧", roles: ["SECTION_MASTER"], group: "Operations & Safety" },
  { to: "/disruptions", label: "Disruption Management", icon: "⛔", roles: ["SECTION_MASTER"], group: "Operations & Safety" },
  { to: "/incidents", label: "Incident Desk", icon: "🚨", roles: ["SECTION_MASTER"], group: "Operations & Safety" },
  { to: "/network", label: "Railway Network", icon: "⌁", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Operations & Safety" },
  { to: "/what-if", label: "What-if Simulation", icon: "⧉", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Operations & Safety" },
  { to: "/analytics", label: "Analytics", icon: "▥", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Operations & Safety" },

  // Governance & Continuity
  { to: "/handover", label: "Shift Handover", icon: "📋", roles: ["SECTION_MASTER"], group: "Governance" },
  { to: "/audit", label: "Audit Trail", icon: "⛓", roles: ["SECTION_MASTER"], group: "Governance" },
  { to: "/specifications", label: "Assumptions & Constraints", icon: "⚙", roles: ["SECTION_MASTER", "STATION_MASTER"], group: "Governance" },
];

export function Shell() {
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

  if (!user) return null;

  const isSectionMaster = user.role === "SECTION_MASTER" || user.role === "SECTION_CONTROLLER" || user.role === "ADMIN";
  const visibleItems = NAV_ITEMS.filter((item) => {
    const allowed = new Set(item.roles);
    if (allowed.has("SECTION_MASTER")) {
      allowed.add("SECTION_CONTROLLER");
      allowed.add("ADMIN");
    }
    return allowed.has(user.role);
  });

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState<{ text: string; error: boolean } | null>(null);

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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">🚂</span>
          <div>
            <strong>RAILGORITHM</strong>
            <small>Traffic Management System</small>
          </div>
        </div>
        <nav className="nav">
          {visibleItems.map((item, index) => {
            const prevItem = visibleItems[index - 1];
            const showGroup = item.group && (!prevItem || prevItem.group !== item.group);
            return (
              <div key={item.to} className="nav-item-wrap">
                {showGroup && <div className="nav-group-header">{item.group}</div>}
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                >
                  <span className="nav-icon" aria-hidden>
                    {item.icon}
                  </span>
                  {item.label}
                </NavLink>
              </div>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <strong>{user.display_name}</strong>
            <span className="mono small" style={{ color: "#38BDF8" }}>{user.role.replace("_", " ")}</span>
            <span className="small text-muted">{user.zone || "SWR"} · {user.division || "Southern Div"}</span>
            {user.station_id ? (
              <span className="badge badge-accent small" style={{ marginTop: "4px" }}>
                Scope: station {user.station_id}
              </span>
            ) : (
              <span className="badge badge-default small" style={{ marginTop: "4px" }}>
                Area: {user.control_area || "Full Corridor"}
              </span>
            )}
          </div>
          <div className="flex-col gap-2" style={{ marginTop: "8px" }}>
            <button
              type="button"
              className="button button-small button-ghost full"
              onClick={() => setShowPasswordModal(true)}
            >
              Change Password
            </button>
            <button
              type="button"
              className="button button-small button-ghost full"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Password Change Dialog */}
      {showPasswordModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Change Password Modal">
          <div className="modal-card" style={{ maxWidth: "420px", background: "#0F172A", border: "1px solid #1E293B", borderRadius: "8px", padding: "20px" }}>
            <div className="flex-row justify-between items-center" style={{ marginBottom: "14px" }}>
              <h3 style={{ margin: 0, color: "#F8FAFC" }}>Change Account Password</h3>
              <button
                type="button"
                className="button button-small button-ghost"
                onClick={() => setShowPasswordModal(false)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleChangePassword} className="stack" style={{ gap: "12px" }}>
              <label className="field">
                <span className="field-label" style={{ color: "#94A3B8" }}>Current Password</span>
                <input
                  type="password"
                  className="input full"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>
              <label className="field">
                <span className="field-label" style={{ color: "#94A3B8" }}>New Password</span>
                <input
                  type="password"
                  className="input full"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>
              {pwdMsg && (
                <div className={`banner ${pwdMsg.error ? "banner-danger" : "banner-accent"}`}>
                  {pwdMsg.text}
                </div>
              )}
              <div className="flex-row justify-end gap-2" style={{ marginTop: "8px" }}>
                <button
                  type="button"
                  className="button button-ghost"
                  onClick={() => setShowPasswordModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="button button-primary">
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="main">
        <header className="topbar">
          <div className="env-indicator flex-row gap-2 items-center">
            <span className="badge badge-watch" title="Operating environment: Simulation mode with synthetic data">
              ● SIMULATION MODE
            </span>
            <span className="badge badge-default mono small" style={{ background: "#1E293B", color: "#38BDF8", border: "1px solid #334155" }}>
              {user.control_area || (user.station_id ? `STATION ${user.station_id}` : "CORRIDOR")}
            </span>
          </div>
          <div className="simulation-picker">
            <label htmlFor="simulation-select">Simulation</label>
            <select
              id="simulation-select"
              value={selectedId ?? ""}
              onChange={(event) => select(event.target.value)}
              disabled={loading || simulations.length === 0}
            >
              {simulations.length === 0 && <option value="">No simulations</option>}
              {simulations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · v{item.state_version} · {item.status}
                </option>
              ))}
            </select>
          </div>
          {selected && (
            <div className="sim-clock">
              <span className="sim-time">{formatMinutes(selected.sim_time_min)}</span>
              <span className="sim-meta">
                {selected.status} · version {selected.state_version} · seed {selected.seed}
              </span>
            </div>
          )}
          {isSectionMaster && selectedId && (
            <div className="controls">
              {[5, 15, 30].map((minutes) => (
                <button
                  key={minutes}
                  type="button"
                  className="button button-small"
                  disabled={busy !== null}
                  onClick={() =>
                    runControl(
                      `advance-${minutes}`,
                      () => api.advance(selectedId, minutes),
                      `Advanced ${minutes} minutes in simulation.`,
                    )
                  }
                >
                  +{minutes}m
                </button>
              ))}
              <button
                type="button"
                className="button button-small button-ghost"
                disabled={busy !== null}
                onClick={() =>
                  runControl(
                    "pause",
                    () =>
                      api.pause(
                        selectedId,
                        selected?.status !== "PAUSED",
                      ),
                    selected?.status === "PAUSED"
                      ? "Simulation resumed."
                      : "Simulation paused.",
                  )
                }
              >
                {selected?.status === "PAUSED" ? "Resume" : "Pause"}
              </button>
              <button
                type="button"
                className="button button-small button-danger"
                disabled={busy !== null}
                onClick={() =>
                  runControl("reset", () => api.reset(selectedId), "Simulation reset.")
                }
              >
                Reset
              </button>
            </div>
          )}
          {isSectionMaster && (
            <button
              type="button"
              className="button button-primary button-small"
              onClick={() => setCreating(true)}
            >
              New simulation
            </button>
          )}
          <FeedHealthBanner />
        </header>

        {message && (
          <div className="banner banner-info" role="status">
            {message}
          </div>
        )}
        <SyntheticBanner />
        <main className="content">
          <Outlet />
        </main>
      </div>
      {creating && (
        <NewSimulationDialog
          scenarios={scenarios}
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );
}
