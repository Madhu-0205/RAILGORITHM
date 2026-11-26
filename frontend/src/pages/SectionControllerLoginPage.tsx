import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const SC_ACCOUNTS = [
  {
    label: "Chief Controller — Full Corridor",
    username: "SC_CORRIDOR_001",
    password: "Section@123",
    note: "NDL–VSN Mainline (km 0.0 to 100.0) — All 5 Stations",
  },
  {
    label: "Section Controller — North Area",
    username: "SC_NORTH_001",
    password: "Section@123",
    note: "Northern Territory (NDL, KRN, MLG) — S1 & S2",
  },
  {
    label: "Section Controller — South Area",
    username: "SC_SOUTH_001",
    password: "Section@123",
    note: "Southern Territory (MLG, SRP, VSN) — S3 & S4",
  },
  {
    label: "Section Master (Demo)",
    username: "section.master",
    password: "Section@123",
    note: "Legacy Demo Account — Full Corridor Controller",
  },
];

export function SectionControllerLoginPage() {
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
      await login(username, password, "SECTION_CONTROLLER");
      navigate("/section-controller/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  function pickAccount(u: string, p: string) {
    setUsername(u);
    setPassword(p);
    setError(null);
  }

  return (
    <div
      className="sc-portal-layout"
      style={{
        minHeight: "100vh",
        background: "radial-gradient(ellipse at top right, #082f49 0%, #0f172a 60%, #020617 100%)",
        color: "#f8fafc",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "32px 16px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "1080px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "36px",
          alignItems: "center",
        }}
      >
        {/* Left: Section Controller Operational Identity */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "32px" }}>🎛️</span>
            <div>
              <span
                style={{
                  display: "inline-block",
                  background: "#0284c7",
                  color: "#f8fafc",
                  fontWeight: 800,
                  fontSize: "12px",
                  padding: "3px 10px",
                  borderRadius: "4px",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                }}
              >
                Section Controller Control Office
              </span>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                Divisional Control Office (Indian Railways Traffic Regulation)
              </div>
            </div>
          </div>

          <h1
            style={{
              fontSize: "clamp(2rem, 3.5vw, 2.75rem)",
              fontWeight: 800,
              lineHeight: 1.15,
              margin: 0,
              color: "#f8fafc",
            }}
          >
            Section Controller Working Console
          </h1>

          <p style={{ fontSize: "1.05rem", color: "#94a3b8", lineHeight: 1.5, margin: 0 }}>
            Unified control office workspace for Section Controllers to supervise corridor traffic,
            evaluate crossings and precedence, resolve single-line bottlenecks, and inspect the Master Control Graph.
          </p>

          <div
            style={{
              background: "rgba(2, 132, 199, 0.1)",
              border: "1px solid rgba(2, 132, 199, 0.4)",
              borderRadius: "8px",
              padding: "16px",
              fontSize: "0.9rem",
              lineHeight: 1.5,
              color: "#38bdf8",
            }}
          >
            <strong>🔒 STRICT ROLE BOUNDARY NOTICE:</strong>
            <p style={{ margin: "6px 0 0", color: "#e0f2fe", fontSize: "0.85rem" }}>
              Only authorized Section Controllers and Chief Dispatchers can authenticate through this gateway.
              Station Master accounts are strictly rejected by server-side verification.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#38bdf8" }}>✓</span> Corridor Linear Topology Strip & Single-Line Bottlenecks
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#38bdf8" }}>✓</span> Master Control Graph (Time-Distance Trajectories)
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#38bdf8" }}>✓</span> Junction & Crossing Precedence Resolution Workspace
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#38bdf8" }}>✓</span> Whole-section train ledger & shift handover diary
            </div>
          </div>

          <div style={{ marginTop: "12px", fontSize: "0.85rem", color: "#94a3b8" }}>
            Need Station Master Local Yard Console instead?{" "}
            <Link
              to="/login/station-master"
              style={{ color: "#f59e0b", fontWeight: 600, textDecoration: "underline" }}
            >
              Switch to Station Master Portal →
            </Link>
          </div>
        </div>

        {/* Right: Dedicated Login Card */}
        <div
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: "12px",
            padding: "32px",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
          }}
        >
          <div style={{ marginBottom: "20px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: "#38bdf8",
                textTransform: "uppercase",
                letterSpacing: "1px",
              }}
            >
              Authorized Access Gateway
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "4px 0 0", color: "#f8fafc" }}>
              Section Controller Login
            </h2>
            <div style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "4px" }}>
              Authenticate with your divisional territory credentials
            </div>
          </div>

          {error && (
            <div
              role="alert"
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                borderRadius: "8px",
                padding: "12px 14px",
                color: "#fca5a5",
                fontSize: "0.88rem",
                lineHeight: 1.4,
                marginBottom: "20px",
              }}
            >
              <strong>Authentication Denied:</strong> {error}
            </div>
          )}

          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label
                htmlFor="sc-username"
                style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}
              >
                Section Controller Username
              </label>
              <input
                id="sc-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. SC_CORRIDOR_001"
                required
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  background: "#0f172a",
                  border: "1px solid #475569",
                  color: "#f8fafc",
                  fontSize: "0.95rem",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div>
              <label
                htmlFor="sc-password"
                style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}
              >
                Password
              </label>
              <input
                id="sc-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  background: "#0f172a",
                  border: "1px solid #475569",
                  color: "#f8fafc",
                  fontSize: "0.95rem",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={busy}
              style={{
                marginTop: "6px",
                padding: "12px",
                borderRadius: "6px",
                background: "#0284c7",
                border: "none",
                color: "#f8fafc",
                fontWeight: 700,
                fontSize: "1rem",
                cursor: busy ? "not-allowed" : "pointer",
                opacity: busy ? 0.7 : 1,
                boxShadow: "0 4px 6px -1px rgba(2, 132, 199, 0.3)",
              }}
            >
              {busy ? "Authenticating Territory Authority..." : "Sign In to Control Office Console"}
            </button>
          </form>

          {/* Section Controller Quick Demo Credentials */}
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid #334155" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>
              Provisioned Section Controller Accounts (Click to Fill):
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "10px" }}>
              {SC_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  onClick={() => pickAccount(acc.username, acc.password)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    cursor: "pointer",
                    textAlign: "left",
                    color: "#f8fafc",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: "0.85rem", color: "#38bdf8" }}>{acc.label}</strong>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{acc.note}</div>
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "monospace" }}>{acc.username}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "32px", fontSize: "0.75rem", color: "#64748b", textAlign: "center", maxWidth: "600px" }}>
        SYNTHETIC DATA — Not real Indian Railways operational data. Recommendations are decision support only; a human operator must decide. No live railway interlocking connected.
      </div>
    </div>
  );
}
