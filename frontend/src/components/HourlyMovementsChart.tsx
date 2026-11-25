export interface MovementBucket {
  hour: string;
  arrivals: number;
  departures: number;
}

export interface HourlyMovementsChartProps {
  data: MovementBucket[];
  title?: string;
  subtitle?: string;
}

export function HourlyMovementsChart({
  data,
  title = "Hourly Train Movements",
  subtitle = "Arrival and departure volume across operational time buckets",
}: HourlyMovementsChartProps) {
  const width = 500;
  const height = 220;
  const padLeft = 45;
  const padBottom = 35;
  const padTop = 25;
  const padRight = 20;

  const chartWidth = width - padLeft - padRight;
  const chartHeight = height - padTop - padBottom;

  const maxVal = Math.max(1, ...data.map((d) => Math.max(d.arrivals, d.departures)));
  const yTicks = Array.from(new Set([0, Math.max(1, Math.round(maxVal / 2)), maxVal]));

  const bucketWidth = chartWidth / Math.max(1, data.length);
  const barWidth = Math.min(22, (bucketWidth - 12) / 2);

  return (
    <div className="chart-container" style={{ width: "100%", overflowX: "auto" }}>
      <div className="flex-row justify-between items-center" style={{ marginBottom: "8px" }}>
        <div>
          <h4 style={{ margin: 0, fontSize: "0.86rem", color: "#334155" }}>{title}</h4>
          {subtitle && <p className="muted small" style={{ margin: 0 }}>{subtitle}</p>}
        </div>
        <div className="flex-row gap-3 items-center small">
          <span className="flex-row items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, background: "#2563EB", borderRadius: 2 }} />
            Arrivals
          </span>
          <span className="flex-row items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, background: "#10B981", borderRadius: 2 }} />
            Departures
          </span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="movement-chart-svg"
        role="img"
        aria-label={`${title}: chart of arrivals and departures`}
        style={{ width: "100%", minWidth: "360px", height: "auto" }}
      >
        <title>{title}</title>
        <desc>{subtitle}</desc>

        {/* Y Axis Gridlines */}
        {yTicks.map((tick, idx) => {
          const y = padTop + chartHeight - (tick / maxVal) * chartHeight;
          return (
            <g key={`tick-${tick}-${idx}`} className="gridline">
              <line
                x1={padLeft}
                y1={y}
                x2={width - padRight}
                y2={y}
                stroke="#E2E8F0"
                strokeDasharray="3 3"
              />
              <text
                x={padLeft - 8}
                y={y + 3}
                textAnchor="end"
                fontSize={10}
                fill="#94A3B8"
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* X Axis Baseline */}
        <line
          x1={padLeft}
          y1={padTop + chartHeight}
          x2={width - padRight}
          y2={padTop + chartHeight}
          stroke="#CBD5E1"
          strokeWidth={1}
        />

        {/* Bars */}
        {data.map((d, i) => {
          const centerX = padLeft + i * bucketWidth + bucketWidth / 2;
          const arrHeight = (d.arrivals / maxVal) * chartHeight;
          const depHeight = (d.departures / maxVal) * chartHeight;

          const arrX = centerX - barWidth - 1;
          const depX = centerX + 1;

          const arrY = padTop + chartHeight - arrHeight;
          const depY = padTop + chartHeight - depHeight;

          return (
            <g key={d.hour} className="chart-bar-group">
              {/* Arrivals Bar */}
              <rect
                x={arrX}
                y={arrY}
                width={barWidth}
                height={Math.max(2, arrHeight)}
                rx={2}
                fill="#2563EB"
              >
                <title>{`${d.hour}: ${d.arrivals} arrivals`}</title>
              </rect>
              {d.arrivals > 0 && (
                <text
                  x={arrX + barWidth / 2}
                  y={arrY - 4}
                  textAnchor="middle"
                  fontSize={9}
                  fontWeight={600}
                  fill="#2563EB"
                >
                  {d.arrivals}
                </text>
              )}

              {/* Departures Bar */}
              <rect
                x={depX}
                y={depY}
                width={barWidth}
                height={Math.max(2, depHeight)}
                rx={2}
                fill="#10B981"
              >
                <title>{`${d.hour}: ${d.departures} departures`}</title>
              </rect>
              {d.departures > 0 && (
                <text
                  x={depX + barWidth / 2}
                  y={depY - 4}
                  textAnchor="middle"
                  fontSize={9}
                  fontWeight={600}
                  fill="#10B981"
                >
                  {d.departures}
                </text>
              )}

              {/* X Axis Label */}
              <text
                x={centerX}
                y={padTop + chartHeight + 18}
                textAnchor="middle"
                fontSize={10}
                fill="#64748B"
              >
                {d.hour}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
