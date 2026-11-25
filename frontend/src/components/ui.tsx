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
}: {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  tone?: "neutral" | "good" | "watch" | "bad";
}) {
  return (
    <div className={`kpi kpi-${tone}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">
        {value}
        {unit && <span className="kpi-unit">{unit}</span>}
      </span>
      {hint && <span className="kpi-hint">{hint}</span>}
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={severityClass(severity)}>{severity}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={statusClass(status)}>{status.replace(/_/g, " ")}</span>;
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
