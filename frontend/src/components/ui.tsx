import type { ReactNode } from "react";
import { evidenceLabel, severityClass, statusClass } from "../lib/format";

export function Panel({
  title,
  subtitle,
  actions,
  children,
  tone,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  tone?: "default" | "warning" | "danger" | "success";
  className?: string;
}) {
  return (
    <section className={`panel panel-${tone ?? "default"} ${className}`}>
      {(title || actions) && (
        <header className="panel-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function KpiCard({
  label,
  value,
  unit,
  hint,
  tone = "neutral",
  period,
  source,
  quality,
  tooltip,
}: {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  tone?: "neutral" | "good" | "watch" | "bad" | "info";
  period?: string;
  source?: string;
  quality?: "MEASURED" | "CALCULATED" | "PREDICTED" | "HEURISTIC" | "NO_DATA";
  tooltip?: string;
}) {
  const toneIcon =
    tone === "good" ? "✓" : tone === "watch" ? "⚠" : tone === "bad" ? "✕" : tone === "info" ? "ℹ" : "●";

  return (
    <div className={`kpi kpi-${tone}`} title={tooltip}>
      <div className="kpi-header">
        <span className="kpi-label">{label}</span>
        {quality && (
          <span className={`kpi-quality-badge quality-${quality.toLowerCase()}`} title={`Data classification: ${quality}`}>
            {quality}
          </span>
        )}
      </div>
      <div className="kpi-value-row">
        <span className="kpi-value">
          {value}
          {unit && <span className="kpi-unit">{unit}</span>}
        </span>
        <span className="kpi-tone-indicator" aria-hidden="true">
          {toneIcon}
        </span>
      </div>
      {(hint || period || source) && (
        <div className="kpi-meta-row">
          {hint && <span className="kpi-hint">{hint}</span>}
          {period && <span className="kpi-period">{period}</span>}
          {source && (
            <span className="kpi-source" title={`Source: ${source}`}>
              Src: {source}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const norm = severity.toUpperCase();
  const icon =
    norm === "CRITICAL"
      ? "■ "
      : norm === "HIGH" || norm === "MAJOR"
      ? "▲ "
      : norm === "MEDIUM" || norm === "MODERATE"
      ? "▲ "
      : "● ";
  return (
    <span className={severityClass(severity)} data-severity={severity}>
      <span aria-hidden="true" style={{ marginRight: "3px", fontWeight: 700 }}>{icon}</span>
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const norm = status.toUpperCase();
  const icon =
    norm.includes("CLEAR") || norm.includes("NORMAL") || norm.includes("RUNNING") || norm.includes("APPROVED")
      ? "● "
      : norm.includes("DELAY") || norm.includes("CAUTION") || norm.includes("CONGEST") || norm.includes("REGULAT") || norm.includes("PAUSED")
      ? "▲ "
      : norm.includes("CRIT") || norm.includes("OCCUPIED") || norm.includes("BLOCK") || norm.includes("DEGRAD") || norm.includes("REJECT")
      ? "■ "
      : "◆ ";
  return (
    <span className={statusClass(status)} data-status={status}>
      <span aria-hidden="true" style={{ marginRight: "3px", fontWeight: 700 }}>{icon}</span>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function DataProvenanceBadge({
  provenance,
  freshnessSeconds,
}: {
  provenance: "TELEMETRY" | "CALCULATED" | "PREDICTED" | "HEURISTIC" | "SYNTHETIC" | "NO_DATA";
  freshnessSeconds?: number;
}) {
  const config = {
    TELEMETRY: { label: "TELEMETRY", tone: "good", icon: "📡" },
    CALCULATED: { label: "OPTIMIZER (CP-SAT)", tone: "accent", icon: "⚙" },
    PREDICTED: { label: "PREDICTED (PPO)", tone: "accent", icon: "🧠" },
    HEURISTIC: { label: "HEURISTIC", tone: "watch", icon: "⚖" },
    SYNTHETIC: { label: "SYNTHETIC DATA", tone: "watch", icon: "🧪" },
    NO_DATA: { label: "NO_DATA", tone: "muted", icon: "◌" },
  }[provenance] || { label: provenance, tone: "muted", icon: "●" };

  return (
    <span
      className={`badge badge-${config.tone}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        fontFamily: "var(--mono)",
        fontSize: "0.68rem",
        padding: "2px 6px",
      }}
      title={`Data provenance classification: ${provenance}`}
    >
      <span aria-hidden="true">{config.icon}</span>
      <strong>{config.label}</strong>
      {freshnessSeconds !== undefined && (
        <span style={{ opacity: 0.8, marginLeft: "2px" }}>({freshnessSeconds}s ago)</span>
      )}
    </span>
  );
}

export function Badge({
  children,
  tone = "default",
  className = "",
}: {
  children: ReactNode;
  tone?: "default" | "good" | "watch" | "bad" | "muted" | "accent";
  className?: string;
}) {
  const toneClass =
    tone === "good"
      ? "badge-good"
      : tone === "watch"
      ? "badge-watch"
      : tone === "bad"
      ? "badge-danger"
      : tone === "muted"
      ? "badge-muted"
      : tone === "accent"
      ? "badge-accent"
      : "badge-default";
  return <span className={`badge ${toneClass} ${className}`}>{children}</span>;
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="dialog-backdrop" role="dialog" aria-modal="true">
      <div className="dialog">
        <header className="dialog-header">
          <h3>{title}</h3>
          <button type="button" className="button button-ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>
        <div className="dialog-body">{children}</div>
      </div>
    </div>
  );
}

export function EvidenceBadge({ status }: { status: string }) {
  const tone =
    status === "VALIDATED"
      ? "good"
      : status === "VALIDATED_WITH_ASSUMPTIONS"
        ? "watch"
        : status === "MODEL_DISAGREEMENT"
          ? "watch"
          : "bad";
  return (
    <span className={`evidence evidence-${tone}`} title={status}>
      {evidenceLabel(status)}
    </span>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner-dot" />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="banner banner-danger" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="button button-ghost" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}

export function SyntheticBanner() {
  return (
    <div className="synthetic-banner" role="note">
      <span className="synthetic-dot" />
      SYNTHETIC DATA — not real Indian Railways data. Recommendations are
      decision support only; a human controller must decide. No live railway
      systems are connected.
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}
