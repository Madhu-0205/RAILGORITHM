import { Badge } from "./ui";

export interface PlatformSlot {
  platform_id: string;
  status: "OCCUPIED" | "AVAILABLE" | "OUTAGE";
  train_id: string | null;
  description: string;
}

export interface StationPlatformBerthsProps {
  stationName: string;
  slots: PlatformSlot[];
}

export function StationPlatformBerths({ stationName, slots }: StationPlatformBerthsProps) {
  return (
    <div className="platform-berths-container stack" style={{ gap: "10px" }}>
      <div className="platform-tracks-grid" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {slots.map((slot) => {
          const isOccupied = slot.status === "OCCUPIED";
          const isOutage = slot.status === "OUTAGE";

          const trackColor = isOccupied ? "#2563EB" : isOutage ? "#DC2626" : "#16A34A";
          const bgColor = isOccupied ? "#EFF6FF" : isOutage ? "#FEF2F2" : "#F0FDF4";
          const borderColor = isOccupied ? "#BFDBFE" : isOutage ? "#FECACA" : "#BBF7D0";

          return (
            <div
              key={slot.platform_id}
              className={`platform-berth-row status-${slot.status.toLowerCase()}`}
              style={{
                display: "grid",
                gridTemplateColumns: "140px 1fr auto",
                alignItems: "center",
                gap: "16px",
                padding: "12px 16px",
                background: bgColor,
                border: `1px solid ${borderColor}`,
                borderRadius: "6px",
                position: "relative",
              }}
            >
              {/* Platform Label */}
              <div className="flex-row items-center gap-2">
                <span
                  style={{
                    display: "inline-block",
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: trackColor,
                  }}
                  aria-hidden="true"
                />
                <strong>Platform {slot.platform_id}</strong>
              </div>

              {/* Track visualizer & Train Details */}
              <div className="flex-row items-center gap-3" style={{ minWidth: 0 }}>
                {/* Horizontal track line snippet */}
                <div
                  style={{
                    flex: "0 0 40px",
                    height: "4px",
                    background: trackColor,
                    borderRadius: "2px",
                  }}
                  aria-hidden="true"
                />
                <div style={{ minWidth: 0 }}>
                  {slot.train_id ? (
                    <div className="flex-row items-center gap-2">
                      <span className="mono" style={{ fontWeight: 700, color: "#1E293B" }}>
                        Train: {slot.train_id}
                      </span>
                      <span className="small text-muted truncate">({slot.description})</span>
                    </div>
                  ) : (
                    <span className="small" style={{ color: isOutage ? "#991B1B" : "#15803D" }}>
                      {slot.description || (isOutage ? "Maintenance Block" : "Clear for reception")}
                    </span>
                  )}
                </div>
              </div>

              {/* Status Badge */}
              <div>
                <Badge tone={isOccupied ? "default" : isOutage ? "bad" : "good"}>
                  {slot.status}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
