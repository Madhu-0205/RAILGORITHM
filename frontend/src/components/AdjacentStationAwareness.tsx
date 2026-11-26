import React from "react";
import type { AdjacentStationInfo, StationMasterAdjacentStations } from "../types";

interface AdjacentStationAwarenessProps {
  data: StationMasterAdjacentStations;
}

export function AdjacentStationAwareness({ data }: AdjacentStationAwarenessProps) {
  const { station_name, upstream_station, downstream_station, junction_branches } = data;

  const renderNeighborCard = (info: AdjacentStationInfo | null, role: "UPSTREAM" | "DOWNSTREAM") => {
    if (!info) {
      return (
        <div style={{ flex: 1, background: "#1e293b", padding: "16px", borderRadius: "8px", border: "1px dashed #475569", textAlign: "center", color: "#94a3b8" }}>
          <p style={{ margin: 0, fontWeight: 600 }}>{role === "UPSTREAM" ? "Corridor Origin Boundary" : "Corridor Terminus Boundary"}</p>
          <span style={{ fontSize: "11px" }}>No further adjacent stations under this section</span>
        </div>
      );
    }

    const hasOccupant = info.blocks.some((b) => b.state === "OCCUPIED");
    const activeTrain = info.blocks.find((b) => b.train)?.train;

    return (
      <div
        style={{
          flex: 1,
          background: "#0E1726",
          border: `1px solid ${hasOccupant ? "#EF4444" : "#1E293B"}`,
          borderRadius: "8px",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          boxShadow: hasOccupant ? "0 0 12px rgba(239, 68, 68, 0.15)" : "none",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #1E293B", paddingBottom: "8px" }}>
          <div>
            <span style={{ fontSize: "10px", color: "#38BDF8", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.08em" }}>
              {info.relative_position} ADJACENT INTERFACING BLOCK
            </span>
            <h4 style={{ margin: "2px 0 0", color: "#F8FAFC", fontSize: "16px", fontWeight: 700 }}>
              {info.station_name} ({info.code})
            </h4>
          </div>
          <span
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 700,
              fontFamily: "var(--mono)",
              background: info.line_clear_status.includes("OCCUPIED") ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
              color: info.line_clear_status.includes("OCCUPIED") ? "#FCA5A5" : "#34D399",
              border: `1px solid ${info.line_clear_status.includes("OCCUPIED") ? "#DC2626" : "#059669"}`,
            }}
          >
            {info.line_clear_status.includes("OCCUPIED") ? "■ TRAIN ON LINE" : "● LINE CLEAR"}
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px", color: "#CBD5E1", background: "#080C14", padding: "10px", borderRadius: "6px", border: "1px solid #142136" }}>
          <div>
            <span style={{ color: "#64748B" }}>Connecting Section:</span> <strong style={{ color: "#38BDF8" }}>{info.section_id}</strong>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>Track Mode:</span> <strong style={{ color: info.section_mode === "SINGLE" ? "#F59E0B" : "#38BDF8" }}>{info.section_mode} LINE</strong>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>Inter-Station Distance:</span> <strong style={{ color: "#F8FAFC" }}>{info.distance_km} km</strong>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>Block Headway:</span> <strong style={{ color: "#F8FAFC" }}>{info.headway_min} min</strong>
          </div>
        </div>

        {/* Block Section Details */}
        <div style={{ background: "#142136", padding: "10px", borderRadius: "6px", border: "1px solid #1E293B" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "11px", color: "#94A3B8", fontWeight: 700, textTransform: "uppercase" }}>Block Instrument State:</span>
            <span style={{ fontSize: "10px", color: "#64748B" }}>Tokenless Neale's Ball / Daido Relay</span>
          </div>
          {info.blocks.map((blk) => (
            <div key={blk.block_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px", fontSize: "11px", padding: "4px 6px", background: "#0E1726", borderRadius: "4px" }}>
              <span>
                Block <strong style={{ color: "#F8FAFC" }}>{blk.block_id}</strong> ({blk.direction}):
              </span>
              <span style={{ color: blk.state === "CLEAR" ? "#10B981" : "#EF4444", fontWeight: 700, fontFamily: "var(--mono)" }}>
                {blk.state === "CLEAR" ? "● LINE CLEAR" : "■ OCCUPIED"}
              </span>
            </div>
          ))}
          {activeTrain && (
            <div style={{ marginTop: "8px", padding: "6px 10px", background: "rgba(2, 132, 199, 0.15)", border: "1px solid #0284C7", borderRadius: "4px", fontSize: "11px", color: "#F8FAFC" }}>
              Approaching: <strong style={{ color: "#38BDF8" }}>{activeTrain.train_name}</strong> ({activeTrain.direction}) · Speed: <strong>{activeTrain.speed_kmph} km/h</strong>
            </div>
          )}
        </div>

        <div style={{ fontSize: "11px", color: "#64748B", display: "flex", justifyContent: "space-between", marginTop: "2px" }}>
          <span>Telemetry Freshness: <strong style={{ color: "#94A3B8" }}>{info.telemetry_freshness_seconds}s ago</strong></span>
          <span>{info.last_movement_event?.message}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="adjacent-station-awareness-panel" style={{ background: "#0b1329", border: "1px solid #1e293b", borderRadius: "8px", padding: "16px", color: "#f8fafc" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "15px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>📡</span> Adjacent Station Operational Awareness
          </h3>
          <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "#94a3b8" }}>
            Real-time Line Clear exchange and approaching train telemetry for bordering block stations
          </p>
        </div>
        <span style={{ fontSize: "11px", background: "#1e293b", color: "#38bdf8", padding: "4px 8px", borderRadius: "4px" }}>
          Local Interlocking Scope
        </span>
      </div>

      <div style={{ display: "flex", gap: "16px", alignItems: "stretch" }}>
        {/* Upstream Station Card */}
        {renderNeighborCard(upstream_station, "UPSTREAM")}

        {/* Center Current Station Node */}
        <div
          style={{
            width: "160px",
            background: "#1e293b",
            border: "2px solid #38bdf8",
            borderRadius: "8px",
            padding: "12px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <span style={{ fontSize: "10px", color: "#38bdf8", fontWeight: 700, textTransform: "uppercase" }}>Your Station</span>
          <h4 style={{ margin: "4px 0", fontSize: "16px", color: "#ffffff" }}>{station_name}</h4>
          <span style={{ fontSize: "11px", color: "#94a3b8" }}>Yard Interlocking</span>
          <span style={{ marginTop: "8px", fontSize: "11px", color: "#10b981", fontWeight: 600 }}>Active Control</span>
        </div>

        {/* Downstream Station Card */}
        {renderNeighborCard(downstream_station, "DOWNSTREAM")}
      </div>

      {/* Junction Branches (if applicable) */}
      {junction_branches && junction_branches.length > 0 && (
        <div style={{ marginTop: "14px", borderTop: "1px solid #1e293b", paddingTop: "10px" }}>
          <span style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 700, textTransform: "uppercase" }}>
            Connected Junction Lines / Sidings:
          </span>
          <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
            {junction_branches.map((br) => (
              <div key={br.branch_id} style={{ background: "#1e293b", padding: "8px 12px", borderRadius: "6px", fontSize: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span>🔀</span>
                <div>
                  <strong>{br.name}</strong> ({br.mode} LINE, {br.length_km} km)
                  <div style={{ fontSize: "10px", color: "#94a3b8" }}>Signaling: {br.signaling} | Status: <span style={{ color: "#10b981" }}>{br.status}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
