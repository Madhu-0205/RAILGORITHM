import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const SM_ACCOUNTS = [
  {
    label: "SM Nandpur (NDL)",
    username: "SM_NDL_001",
    password: "Station@123",
    note: "Nandpur Junction Yard (km 0.0) — Southern Division",
  },
  {
    label: "SM Karanpur (KRN)",
    username: "SM_KRN_001",
    password: "Station@123",
    note: "Karanpur Station (km 25.0) — Northern Area",
  },
  {
    label: "SM Malgaon Jn (MLG)",
    username: "SM_MLG_001",
    password: "Station@123",
    note: "Malgaon Junction Hub (km 50.0) — Convergence Throat",
  },
  {
    label: "SM Suryapur (SRP)",
    username: "SM_SRP_001",
    password: "Station@123",
    note: "Suryapur Station (km 75.0) — Southern Area",
  },
  {
    label: "SM Vasanthpur (VSN)",
    username: "SM_VSN_001",
    password: "Station@123",
    note: "Vasanthpur Terminal (km 100.0) — Terminal Yard",
  },
  {
    label: "Station Master (Demo)",
    username: "station.master",
    password: "Station@123",
    note: "Legacy Demo Account — Malgaon SM",
  },
];

export function StationMasterLoginPage() {
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
      await login(username, password, "STATION_MASTER");
      navigate("/station-master/dashboard", { replace: true });
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
      className="sm-portal-layout"
      style={{
        minHeight: "100vh",
        background: "radial-gradient(ellipse at top left, #1e1b4b 0%, #0f172a 60%, #020617 100%)",
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
        {/* Left: Station Master Operational Identity */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "32px" }}>🚉</span>
            <div>
              <span
                style={{
                  display: "inline-block",
                  background: "#f59e0b",
                  color: "#0f172a",
                  fontWeight: 800,
                  fontSize: "12px",
                  padding: "3px 10px",
                  borderRadius: "4px",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                }}
              >
                Station Master Operating Portal
              </span>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                Indian Railways Operating Manual (G&SR 1976 / Block Rules)
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
            Station Master Working Console
          </h1>

          <p style={{ fontSize: "1.05rem", color: "#94a3b8", lineHeight: 1.5, margin: 0 }}>
            Dedicated operational environment for Station Masters to control station yard
            movements, track occupancy, platform berthing, and adjacent station block token coordination.
          </p>

          <div
            style={{
              background: "rgba(245, 158, 11, 0.08)",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              borderRadius: "8px",
              padding: "16px",
              fontSize: "0.9rem",
              lineHeight: 1.5,
              color: "#fbbf24",
            }}
          >
            <strong>🔒 STRICT ROLE BOUNDARY NOTICE:</strong>
            <p style={{ margin: "6px 0 0", color: "#fef3c7", fontSize: "0.85rem" }}>
              Only designated Station Master accounts can authenticate through this gateway.
              Section Controller accounts are strictly rejected by server-side verification.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "8px" }}>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#f59e0b" }}>✓</span> Assigned station yard schematic front-and-center
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#f59e0b" }}>✓</span> Arrival, departure, and berthing movement ledger
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#f59e0b" }}>✓</span> Upstream & downstream adjacent block awareness
            </div>
            <div style={{ fontSize: "0.85rem", color: "#cbd5e1", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "#f59e0b" }}>✓</span> Isolated from whole-corridor dispatch controls
            </div>
          </div>

          <div style={{ marginTop: "12px", fontSize: "0.85rem", color: "#94a3b8" }}>
            Need Section Controller Control Office instead?{" "}
            <Link
              to="/login/section-controller"
              style={{ color: "#38bdf8", fontWeight: 600, textDecoration: "underline" }}
            >
              Switch to Section Controller Portal →
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
                color: "#f59e0b",
                textTransform: "uppercase",
                letterSpacing: "1px",
              }}
            >
              Authorized Access Gateway
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "4px 0 0", color: "#f8fafc" }}>
              Station Master Login
            </h2>
            <div style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "4px" }}>
              Authenticate with your assigned Station Master credentials
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
                htmlFor="sm-username"
                style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}
              >
                Station Master Username
              </label>
              <input
                id="sm-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. SM_NDL_001"
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
                htmlFor="sm-password"
                style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "#cbd5e1", marginBottom: "6px" }}
              >
                Password
              </label>
              <input
                id="sm-password"
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
                background: "#f59e0b",
                border: "none",
                color: "#0f172a",
                fontWeight: 700,
                fontSize: "1rem",
                cursor: busy ? "not-allowed" : "pointer",
                opacity: busy ? 0.7 : 1,
                boxShadow: "0 4px 6px -1px rgba(245, 158, 11, 0.3)",
              }}
            >
              {busy ? "Authenticating Yard Authority..." : "Sign In to Station Console"}
            </button>
          </form>

          {/* Station Master Quick Demo Credentials */}
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid #334155" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" }}>
              Provisioned Station Master Accounts (Click to Fill):
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "10px" }}>
              {SM_ACCOUNTS.map((acc) => (
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
                    <strong style={{ fontSize: "0.85rem", color: "#f59e0b" }}>{acc.label}</strong>
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
