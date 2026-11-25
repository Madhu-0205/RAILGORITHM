import React, { useMemo } from "react";
import type { Closure, Conflict, Platform, PlatformOutage, Station, Train } from "../types";
import { Badge } from "./ui";

export interface StationControlStripProps {
  stations?: Station[];
  trains?: Train[];
  platforms?: Platform[];
  outages?: PlatformOutage[];
  conflicts?: Conflict[];
  closures?: Closure[];
  selectedStationId?: string | null;
  onSelectStation?: (stationId: string) => void;
}

interface StationSummaryData {
  station: Station;
  approachingCount: number;
  berthedCount: number;
  departedCount: number;
  delayedCount: number;
  totalPlatforms: number;
  availablePlatforms: number;
  occupiedPlatforms: number;
  outagePlatforms: number;
  activeAlertsCount: number;
  activeRestrictionsCount: number;
  berthedTrains: Train[];
  approachingTrains: Train[];
  statusTone: "good" | "watch" | "bad";
}

export function StationControlStrip({
  stations = [],
  trains = [],
  platforms = [],
  outages = [],
  conflicts = [],
  closures = [],
  selectedStationId,
  onSelectStation,
}: StationControlStripProps) {
  // Aggregate station-level metrics dynamically
  const summaries = useMemo<StationSummaryData[]>(() => {
    return stations.map((station) => {
      // 1. Train movements relative to this station
      const berthed = trains.filter((t) => t.station_id === station.id);
      const approaching = trains.filter(
        (t) => t.next_station === station.id && t.station_id !== station.id
      );
      const departed = trains.filter((t) => {
        const route = t.route || [];
        if (!route.includes(station.id)) return false;
        if (t.station_id === station.id || t.next_station === station.id) return false;
        const stIdx = route.indexOf(station.id);
        const currStIdx = t.station_id ? route.indexOf(t.station_id) : -1;
        return currStIdx > stIdx || t.status === "COMPLETED";
      });

      const delayed = trains.filter((t) => {
        const route = t.route || [];
        const isAffecting =
          t.station_id === station.id ||
          t.next_station === station.id ||
          route.includes(station.id);
        return isAffecting && ((t.projected_delay_min ?? 0) > 0 || (t.delay_min ?? 0) > 0);
      });

      // 2. Platforms & Berthing
      const stationPlatforms = platforms.filter((p) => p && p.station_id === station.id);
      const stationOutages = outages.filter((o) => o && o.station_id === station.id);
      const totalPf = station.platforms?.length || stationPlatforms.length || 2;
      const occupiedPf = stationPlatforms.filter((p) => Boolean(p.occupied_by)).length;
      const outagePf = stationOutages.length;
      const availablePf = Math.max(0, totalPf - occupiedPf - outagePf);

      // 3. Alerts & Conflicts
      const localConflicts = conflicts.filter((c) => {
        if (!c || !c.location) return false;
        if (c.location.station_id === station.id) return true;
        const label = (c.location.label || "").toLowerCase();
        return label.includes(station.id.toLowerCase()) || label.includes(station.name.toLowerCase());
      });

      // 4. Restrictions / Closures near station
      const localClosures = closures.filter(
        (cl) => cl && cl.block_id && cl.block_id.includes(station.id)
      );

      // Status tone
      let statusTone: "good" | "watch" | "bad" = "good";
      if (localConflicts.some((c) => c.severity === "CRITICAL") || outagePf > 0) {
        statusTone = "bad";
      } else if (localConflicts.length > 0 || delayed.length > 0 || availablePf === 0) {
        statusTone = "watch";
      }

      return {
        station,
        approachingCount: approaching.length,
        berthedCount: berthed.length,
        departedCount: departed.length,
        delayedCount: delayed.length,
        totalPlatforms: totalPf,
        availablePlatforms: availablePf,
        occupiedPlatforms: occupiedPf,
        outagePlatforms: outagePf,
        activeAlertsCount: localConflicts.length,
        activeRestrictionsCount: localClosures.length + outagePf,
        berthedTrains: berthed,
        approachingTrains: approaching,
        statusTone,
      };
    });
  }, [stations, trains, platforms, outages, conflicts, closures]);

  return (
    <div className="station-control-strip-container stack" style={{ gap: "12px" }}>
      {/* Header */}
      <div className="flex-row justify-between items-center flex-wrap gap-2">
        <div className="flex-row items-center gap-2">
          <strong style={{ fontSize: "0.95rem", color: "#1E293B" }}>
            Multi-Station Territory Operational Strip
          </strong>
          <span className="small text-muted">
            ({stations.length} Configured Stations · Click any station to inspect station working)
          </span>
        </div>
        <div className="flex-row items-center gap-2 small text-muted">
          <span className="flex-row items-center gap-1">
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#16A34A" }} />
            Normal
          </span>
          <span className="flex-row items-center gap-1">
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#D97706" }} />
            Active Alert / Delay
          </span>
          <span className="flex-row items-center gap-1">
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#DC2626" }} />
            Outage / Critical Conflict
          </span>
        </div>
      </div>

      {/* Grid of Station Overview Cards */}
      <div
        className="station-strip-grid"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(auto-fit, minmax(210px, 1fr))`,
          gap: "12px",
        }}
      >
        {summaries.map((s) => {
          const isSelected = selectedStationId === s.station.id;
          const borderColor = isSelected
            ? "#2563EB"
            : s.statusTone === "bad"
            ? "#FECACA"
            : s.statusTone === "watch"
            ? "#FDE68A"
            : "#E2E8F0";

          const bgHeader = isSelected
            ? "#1E3A8A"
            : s.statusTone === "bad"
            ? "#991B1B"
            : s.statusTone === "watch"
            ? "#854D0E"
            : "#0F172A";

          return (
            <div
              key={s.station.id}
              className={`station-control-card ${isSelected ? "selected-station" : ""}`}
              style={{
                background: "#FFFFFF",
                border: `2px solid ${borderColor}`,
                borderRadius: "8px",
                overflow: "hidden",
                cursor: "pointer",
                boxShadow: isSelected ? "0 4px 12px rgba(37,99,235,0.18)" : "0 1px 3px rgba(0,0,0,0.05)",
                transition: "all 0.15s ease-in-out",
              }}
              onClick={() => onSelectStation && onSelectStation(s.station.id)}
              tabIndex={0}
              role="button"
              aria-label={`Inspect ${s.station.name} (${s.station.code}) station working`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onSelectStation && onSelectStation(s.station.id);
                }
              }}
            >
              {/* Station Card Header */}
              <div
                style={{
                  background: bgHeader,
                  color: "#FFFFFF",
                  padding: "8px 12px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div className="flex-row items-center gap-2">
                  <span className="mono" style={{ fontWeight: 800, fontSize: "0.95rem" }}>
                    {s.station.code}
                  </span>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#E2E8F0" }}>
                    {s.station.name.split(" ")[0]}
                  </span>
                </div>
                {s.station.is_junction ? (
                  <span
                    style={{
                      background: "#F59E0B",
                      color: "#0F172A",
                      padding: "1px 5px",
                      borderRadius: "3px",
                      fontSize: "0.68rem",
                      fontWeight: 700,
                    }}
                  >
                    JUNCTION
                  </span>
                ) : (
                  <span style={{ fontSize: "0.72rem", color: "#94A3B8" }}>
                    {s.totalPlatforms} PFs
                  </span>
                )}
              </div>

              {/* Station Card Body */}
              <div style={{ padding: "10px 12px" }} className="stack gap-2">
                {/* Movement Metrics Line */}
                <div
                  className="flex-row justify-between items-center small"
                  style={{ borderBottom: "1px solid #F1F5F9", paddingBottom: "6px" }}
                >
                  <span title="Trains approaching station">
                    Approaching: <strong>{s.approachingCount}</strong>
                  </span>
                  <span title="Trains berthed at platform lines">
                    Berthed: <strong style={{ color: s.berthedCount > 0 ? "#2563EB" : undefined }}>{s.berthedCount}</strong>
                  </span>
                </div>

                {/* Platforms & Lines State */}
                <div className="flex-row justify-between items-center small">
                  <span className="text-muted">Platform Lines:</span>
                  <span
                    style={{
                      fontWeight: 600,
                      color: s.availablePlatforms === 0 ? "#DC2626" : "#16A34A",
                    }}
                  >
                    {s.availablePlatforms} / {s.totalPlatforms} Clear
                  </span>
                </div>

                {/* Delays & Alerts Badge Row */}
                <div className="flex-row justify-between items-center gap-1 mt-1">
                  {s.delayedCount > 0 ? (
                    <span
                      className="badge badge-watch"
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                      title={`${s.delayedCount} trains currently running behind schedule`}
                    >
                      {s.delayedCount} Delayed
                    </span>
                  ) : (
                    <span
                      className="badge badge-good"
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                    >
                      Right Time
                    </span>
                  )}

                  {s.activeAlertsCount > 0 && (
                    <span
                      className="badge badge-bad"
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                      title={`${s.activeAlertsCount} active conflicts or safety alerts`}
                    >
                      ⚠️ {s.activeAlertsCount} Alerts
                    </span>
                  )}

                  {s.activeRestrictionsCount > 0 && (
                    <span
                      className="badge badge-watch"
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                      title="Maintenance outage or caution order"
                    >
                      🚧 Outage
                    </span>
                  )}
                </div>

                {/* Berthed Train Details (if any) */}
                {s.berthedTrains.length > 0 && (
                  <div
                    style={{
                      background: "#EFF6FF",
                      padding: "4px 6px",
                      borderRadius: "4px",
                      border: "1px solid #BFDBFE",
                      fontSize: "0.72rem",
                      color: "#1E3A8A",
                    }}
                    className="truncate mono"
                  >
                    🚆 Berthed: {s.berthedTrains.map((t) => `#${t.id}`).join(", ")}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
