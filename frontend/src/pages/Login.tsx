import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const DEMO_ACCOUNTS = [
  // Quick Demo Logins
  {
    label: "Section Master",
    username: "section.master",
    password: "Section@123",
    note: "Corridor Controller (Default Demo)",
    roleGroup: "Section Controller",
  },
  {
    label: "Station Master",
    username: "station.master",
    password: "Station@123",
    note: "Malgaon SM (Default Demo)",
    roleGroup: "Station Master",
  },
  // Section Controllers
  {
    label: "Chief Controller (Corridor)",
    username: "SC_CORRIDOR_001",
    password: "Section@123",
    note: "NDL–VSN Full Corridor Jurisdiction",
    roleGroup: "Section Controller",
  },
  {
    label: "Section Controller (North)",
    username: "SC_NORTH_001",
    password: "Section@123",
    note: "Northern Area (NDL, KRN, MLG)",
    roleGroup: "Section Controller",
  },
  {
    label: "Section Controller (South)",
    username: "SC_SOUTH_001",
    password: "Section@123",
    note: "Southern Area (MLG, SRP, VSN)",
    roleGroup: "Section Controller",
  },
  // Station Masters
  {
    label: "SM Nandpur (NDL)",
    username: "SM_NDL_001",
    password: "Station@123",
    note: "Nandpur Station (km 0)",
    roleGroup: "Station Master",
  },
  {
    label: "SM Karanpur (KRN)",
    username: "SM_KRN_001",
    password: "Station@123",
    note: "Karanpur Station (km 25)",
    roleGroup: "Station Master",
  },
  {
    label: "SM Malgaon (MLG)",
    username: "SM_MLG_001",
    password: "Station@123",
    note: "Malgaon Junction (km 50)",
    roleGroup: "Station Master",
  },
  {
    label: "SM Suryapur (SRP)",
    username: "SM_SRP_001",
    password: "Station@123",
    note: "Suryapur Station (km 75)",
    roleGroup: "Station Master",
  },
  {
    label: "SM Vasanthpur (VSN)",
    username: "SM_VSN_001",
    password: "Station@123",
    note: "Vasanthpur Station (km 100)",
    roleGroup: "Station Master",
  },
  // Security Administrator
  {
    label: "Security Admin",
    username: "ADMIN_001",
    password: "Admin@123",
    note: "User & Role Access Administration",
    roleGroup: "Administrator",
  },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-layout">
      <section className="login-hero">
        <div className="brand brand-large">
          <span className="brand-mark">R</span>
          <div>
            <strong>RAILGORITHM</strong>
            <small>AI-assisted railway traffic decision support</small>
          </div>
        </div>
        <h1>Human control. Machine evidence.</h1>
        <p>
          A simulation-first decision-support prototype for section controllers.
          Every recommendation is independently validated, explained and ranked —
          but only an authorised human can decide. No live railway system is
          connected.
        </p>
        <ul className="hero-list">
          <li>Deterministic synthetic simulation of a four-section network</li>
          <li>CP-SAT feasibility plus independent constraint validation</li>
          <li>PPO candidate ranking, shown separately from the optimizer</li>
          <li>Append-only decision and audit trail</li>
        </ul>
        <p className="login-disclaimer">
          All data is synthetic. Not for operational use on any real railway.
        </p>
      </section>

      <section className="login-card">
        {/* Dedicated Portals Selector */}
        <div style={{ marginBottom: "20px", display: "flex", flexDirection: "column", gap: "8px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "1px" }}>
            Dedicated Role Portals:
          </span>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
            <button
              type="button"
              onClick={() => navigate("/login/station-master")}
              style={{
                padding: "8px 10px",
                borderRadius: "6px",
                background: "rgba(245, 158, 11, 0.15)",
                border: "1px solid #f59e0b",
                color: "#f59e0b",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              🚉 Station Master Portal →
            </button>
            <button
              type="button"
              onClick={() => navigate("/login/section-controller")}
              style={{
                padding: "8px 10px",
                borderRadius: "6px",
                background: "rgba(2, 132, 199, 0.15)",
                border: "1px solid #0284c7",
                color: "#38bdf8",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              🎛️ Section Controller Portal →
            </button>
          </div>
        </div>

        <h2>Controller sign in</h2>
        <p className="muted">Use a demo role to explore the workflow.</p>
        <form onSubmit={submit} aria-label="Sign in">
          <label className="field">
            <span className="field-label">Username</span>
            <input
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              minLength={3}
            />
          </label>
          <label className="field">
            <span className="field-label">Password</span>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
            />
          </label>
          {error && (
            <div className="banner banner-danger" role="alert">
              {error}
            </div>
          )}
          <button type="submit" className="button button-primary full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="demo-accounts">
          <span className="field-label">Demo accounts</span>
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.username}
              type="button"
              className="demo-account"
              onClick={() => {
                setUsername(account.username);
                setPassword(account.password);
                setError(null);
              }}
            >
              <strong>{account.label}</strong>
              <span>{account.username}</span>
              <small>{account.note}</small>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
