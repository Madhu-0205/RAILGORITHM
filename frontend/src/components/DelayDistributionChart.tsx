export interface DelayTier {
  tier: string;
  count: number;
  pct: number;
  tone: "good" | "watch" | "bad" | "neutral";
}

export interface DelayDistributionChartProps {
  tiers: DelayTier[];
  title?: string;
  subtitle?: string;
}

export function DelayDistributionChart({
  tiers,
  title = "Train Delay Distribution",
  subtitle = "Punctuality breakdown by delay classification",
}: DelayDistributionChartProps) {
  const getToneColor = (tone: DelayTier["tone"]) => {
    switch (tone) {
      case "good":
        return "#16A34A";
      case "watch":
        return "#D97706";
      case "bad":
        return "#DC2626";
      default:
        return "#64748B";
    }
  };

  return (
    <div className="delay-distribution-container stack" style={{ gap: "10px" }}>
      <div className="flex-row justify-between items-center">
        <div>
          <h4 style={{ margin: 0, fontSize: "0.86rem", color: "#334155" }}>{title}</h4>
          {subtitle && <p className="muted small" style={{ margin: 0 }}>{subtitle}</p>}
        </div>
      </div>

      <div
        className="delay-bars-list stack"
        role="img"
        aria-label={`${title}: delay distribution chart`}
        style={{ gap: "8px" }}
      >
        {tiers.map((t) => {
          const color = getToneColor(t.tone);
          return (
            <div key={t.tier} className="delay-tier-row">
              <div
                className="flex-row justify-between items-center small"
                style={{ marginBottom: "3px" }}
              >
                <span style={{ fontWeight: 500, color: "#1E293B" }}>{t.tier}</span>
                <span className="mono" style={{ color: "#475569" }}>
                  <strong>{t.count} trains</strong> · <span>{t.pct.toFixed(1)}%</span>
                </span>
              </div>
              <div
                className="progress-track"
                style={{
                  height: "8px",
                  background: "#E2E8F0",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, t.pct))}%`,
                    height: "100%",
                    background: color,
                    borderRadius: "4px",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
