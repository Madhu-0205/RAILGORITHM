import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const DEMO_ACCOUNTS = [
  {
    label: "Section Master",
    username: "section.master",
    password: "Section@123",
    note: "Full section authority",
  },
  {
    label: "Station Master",
    username: "station.master",
    password: "Station@123",
    note: "Malgaon Junction scope",
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
