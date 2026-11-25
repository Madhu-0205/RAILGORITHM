import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { formatMinutes } from "../lib/format";
import { useSimulation } from "../simulation";
import { NewSimulationDialog } from "./NewSimulationDialog";
import { SyntheticBanner } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  roles: string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "◉", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/trains", label: "Train Movements", icon: "▤", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/network", label: "Railway Network", icon: "⌁", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/conflicts", label: "Conflict Detection", icon: "⚠", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/recommendations", label: "AI Recommendations", icon: "✦", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/disruptions", label: "Disruption Management", icon: "⛔", roles: ["SECTION_MASTER"] },
  { to: "/what-if", label: "What-if Simulation", icon: "⧉", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/analytics", label: "Analytics", icon: "▥", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/specifications", label: "Assumptions & Constraints", icon: "⚙", roles: ["SECTION_MASTER", "STATION_MASTER"] },
  { to: "/audit", label: "Audit Trail", icon: "⛓", roles: ["SECTION_MASTER"] },
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

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(user.role));
  const isSectionMaster = user.role === "SECTION_MASTER";

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
          <span className="brand-mark">R</span>
          <div>
            <strong>RAILGORITHM</strong>
            <small>Traffic decision support</small>
          </div>
        </div>
        <nav className="nav">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <span className="nav-icon" aria-hidden>
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <strong>{user.display_name}</strong>
            <span>{user.role.replace("_", " ")}</span>
            {user.station_id && <span>Scope: station {user.station_id}</span>}
          </div>
          <button
            type="button"
            className="button button-ghost full"
            onClick={() => {
              logout();
              navigate("/");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
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
