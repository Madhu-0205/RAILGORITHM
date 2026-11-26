import React, { useState } from "react";
import type { StationTrack } from "../types";
import { Badge } from "./ui";

interface StationYardDiagramProps {
  stationName: string;
  stationCode: string;
  tracks: StationTrack[];
  throatStatus: string;
  onSelectTrack?: (track: StationTrack) => void;
}

export function StationYardDiagram({
  stationName,
  stationCode,
  tracks,
  throatStatus,
  onSelectTrack,
}: StationYardDiagramProps) {
  const [selectedTrack, setSelectedTrack] = useState<StationTrack | null>(null);

  const handleTrackClick = (track: StationTrack) => {
    setSelectedTrack(track);
    if (onSelectTrack) onSelectTrack(track);
  };

  // Dimensions for schematic
  const svgWidth = 1080;
  const svgHeight = 320;
  const trackStartX = 140;
  const trackEndX = 920;

  // Track state color mappings conforming to Railway Signalling Standards
  const getTrackColor = (state: string) => {
    switch (state) {
      case "CLEAR":
        return "#10B981"; // Emerald Green
      case "OCCUPIED":
        return "#EF4444"; // Red
      case "RESERVED":
        return "#38BDF8"; // Cyan
      case "RESTRICTED":
      case "OUTAGE":
        return "#F59E0B"; // Amber Warning
      case "BLOCKED":
        return "#991B1B"; // Deep Red
      default:
        return "#64748B"; // Slate
    }
  };

  return (
    <div
      className="station-yard-diagram-container"
      style={{
        background: "#0E1726",
        borderRadius: "8px",
        padding: "18px 20px",
        border: "1px solid #1E293B",
        color: "#F8FAFC",
      }}
    >
      {/* Schematic Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
          borderBottom: "1px solid #1E293B",
          paddingBottom: "12px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "15px", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase", letterSpacing: "1px" }}>
              Yard Working Diagram — {stationName} ({stationCode})
            </span>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "4px",
                background: throatStatus === "CLEAR" ? "rgba(16, 185, 129, 0.2)" : "rgba(245, 158, 11, 0.2)",
                color: throatStatus === "CLEAR" ? "#34D399" : "#FBBF24",
                border: `1px solid ${throatStatus === "CLEAR" ? "#059669" : "#D97706"}`,
              }}
            >
              THROAT: {throatStatus}
            </span>
          </div>
          <p style={{ margin: "3px 0 0", fontSize: "12px", color: "#94A3B8" }}>
            Absolute Block Interlocking Layout · Route Relay / Electronic Interlocking (Human Decision Support Mode)
          </p>
        </div>
        <div style={{ display: "flex", gap: "14px", fontSize: "11px", flexWrap: "wrap" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "10px", height: "10px", backgroundColor: "#10B981", borderRadius: "2px", display: "inline-block" }}></span>
            <span>Line Clear</span>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "10px", height: "10px", backgroundColor: "#EF4444", borderRadius: "2px", display: "inline-block" }}></span>
            <span>Occupied / Berthed</span>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "10px", height: "10px", backgroundColor: "#F59E0B", borderRadius: "2px", display: "inline-block" }}></span>
            <span>Speed Caution</span>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "10px", height: "10px", backgroundColor: "#38BDF8", borderRadius: "2px", display: "inline-block" }}></span>
            <span>Route Locked</span>
          </span>
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{ overflowX: "auto", background: "#080C14", borderRadius: "6px", padding: "12px", border: "1px solid #142136" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", height: "auto", minWidth: "900px" }}>
          <defs>
            <pattern id="hatch-restricted" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="8" stroke="#F59E0B" strokeWidth="2" />
            </pattern>
            {/* Signal Mast definition */}
            <g id="signal-mast">
              <line x1="0" y1="0" x2="0" y2="16" stroke="#94A3B8" strokeWidth="2" />
              <circle cx="0" cy="0" r="4" fill="#10B981" />
            </g>
          </defs>

          {/* Block Section Ingress / Egress Boundary Banners */}
          <g>
            <rect x="10" y="30" width="105" height="40" fill="#0E1726" stroke="#263852" rx="4" />
            <text x="62" y="47" fill="#38BDF8" fontSize="10" fontWeight="700" textAnchor="middle">◄ UP LINE</text>
            <text x="62" y="61" fill="#94A3B8" fontSize="9" textAnchor="middle">From Block Rear</text>

            <rect x="10" y="160" width="105" height="40" fill="#0E1726" stroke="#263852" rx="4" />
            <text x="62" y="177" fill="#38BDF8" fontSize="10" fontWeight="700" textAnchor="middle">DN LINE ►</text>
            <text x="62" y="191" fill="#94A3B8" fontSize="9" textAnchor="middle">From Block Rear</text>

            <rect x="945" y="30" width="125" height="40" fill="#0E1726" stroke="#263852" rx="4" />
            <text x="1007" y="47" fill="#38BDF8" fontSize="10" fontWeight="700" textAnchor="middle">UP ADVANCE ►</text>
            <text x="1007" y="61" fill="#94A3B8" fontSize="9" textAnchor="middle">To Forward Section</text>

            <rect x="945" y="160" width="125" height="40" fill="#0E1726" stroke="#263852" rx="4" />
            <text x="1007" y="177" fill="#38BDF8" fontSize="10" fontWeight="700" textAnchor="middle">◄ DN ADVANCE</text>
            <text x="1007" y="191" fill="#94A3B8" fontSize="9" textAnchor="middle">To Forward Section</text>
          </g>

          {/* Approach & Departure Throat Turnouts */}
          <path d="M 115 50 L 140 50" stroke="#38BDF8" strokeWidth="2.5" />
          <path d="M 115 180 L 140 180" stroke="#38BDF8" strokeWidth="2.5" />
          <path d="M 920 50 L 945 50" stroke="#38BDF8" strokeWidth="2.5" />
          <path d="M 920 180 L 945 180" stroke="#38BDF8" strokeWidth="2.5" />

          {/* Render each track */}
          {tracks.map((track, idx) => {
            const trackY = 48 + idx * 42;
            const strokeColor = getTrackColor(track.state);
            const isSelected = selectedTrack?.track_id === track.track_id;
            const isPlatform = track.category === "PLATFORM";
            const isSiding = track.category === "SIDING" || track.category === "SHUNTING_NECK";

            return (
              <g
                key={track.track_id}
                onClick={() => handleTrackClick(track)}
                style={{ cursor: "pointer" }}
              >
                {/* Track label with Category */}
                <text
                  x={trackStartX - 14}
                  y={trackY + 4}
                  textAnchor="end"
                  fill={isSelected ? "#38BDF8" : "#E2E8F0"}
                  fontSize="11"
                  fontWeight={isSelected ? "700" : "600"}
                  fontFamily="var(--mono)"
                >
                  {track.track_name}
                </text>

                {/* Platform Concrete Island Representation */}
                {isPlatform && (
                  <g>
                    <rect
                      x={trackStartX + 110}
                      y={trackY - 18}
                      width={480}
                      height={34}
                      fill="#142136"
                      rx="4"
                      stroke="#263852"
                      strokeWidth="1"
                    />
                    {/* Platform edge tactile line */}
                    <line
                      x1={trackStartX + 110}
                      y1={trackY - 14}
                      x2={trackStartX + 590}
                      y2={trackY - 14}
                      stroke="#F59E0B"
                      strokeWidth="1"
                      strokeDasharray="4,4"
                      opacity="0.6"
                    />
                    <text
                      x={trackStartX + 120}
                      y={trackY - 4}
                      fill="#94A3B8"
                      fontSize="9"
                      fontWeight="700"
                      letterSpacing="0.05em"
                    >
                      {track.track_name.toUpperCase()} ISLAND BERTH · {track.length_m}M
                    </text>
                  </g>
                )}

                {/* Turnouts / Convergence connecting lines at throat */}
                {idx > 0 && (
                  <line
                    x1={trackStartX + 15}
                    y1={trackY}
                    x2={trackStartX + 65}
                    y2={48 + (idx - 1) * 42}
                    stroke="#3E567A"
                    strokeWidth="1.5"
                    strokeDasharray="3,3"
                  />
                )}
                {idx > 0 && (
                  <line
                    x1={trackEndX - 15}
                    y1={trackY}
                    x2={trackEndX - 65}
                    y2={48 + (idx - 1) * 42}
                    stroke="#3E567A"
                    strokeWidth="1.5"
                    strokeDasharray="3,3"
                  />
                )}

                {/* Point / Turnout Indicator */}
                {idx > 0 && (
                  <text
                    x={trackStartX + 40}
                    y={trackY - 6}
                    fill="#64748B"
                    fontSize="8"
                    fontFamily="var(--mono)"
                  >
                    P-{100 + idx}
                  </text>
                )}

                {/* Track Line */}
                <line
                  x1={trackStartX}
                  y1={trackY}
                  x2={trackEndX}
                  y2={trackY}
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 4 : isPlatform ? 3 : 2}
                  strokeDasharray={isSiding ? "6,4" : track.state === "RESERVED" ? "8,4" : undefined}
                />

                {/* Buffer stop for sidings */}
                {isSiding && (
                  <g transform={`translate(${trackEndX}, ${trackY})`}>
                    <line x1="0" y1="-8" x2="0" y2="8" stroke="#EF4444" strokeWidth="3" />
                    <line x1="-4" y1="-8" x2="-4" y2="8" stroke="#F8FAFC" strokeWidth="1.5" />
                  </g>
                )}

                {/* Home / Starter Signal Symbol */}
                <g transform={`translate(${trackStartX + 85}, ${trackY - 14})`}>
                  <line x1="0" y1="0" x2="0" y2="12" stroke="#64748B" strokeWidth="1.5" />
                  <circle
                    cx="0"
                    cy="0"
                    r="4"
                    fill={track.state === "OCCUPIED" ? "#EF4444" : track.state === "CLEAR" ? "#10B981" : "#F59E0B"}
                    stroke="#080C14"
                    strokeWidth="1"
                  />
                  <text x="-4" y="-6" fill="#64748B" fontSize="8" fontFamily="var(--mono)">S{idx + 1}</text>
                </g>

                {/* Train Occupancy marker */}
                {track.occupied_by && (
                  <g transform={`translate(${trackStartX + 200}, ${trackY - 14})`}>
                    <rect
                      x="0"
                      y="0"
                      width="260"
                      height="26"
                      fill="#7F1D1D"
                      rx="4"
                      stroke="#EF4444"
                      strokeWidth="1.5"
                    />
                    <text x="10" y="17" fill="#FFFFFF" fontSize="11" fontWeight="700">
                      🚆 {track.occupied_by.name} ({track.occupied_by.type})
                    </text>
                    <text x="210" y="17" fill="#FCA5A5" fontSize="10" fontWeight="700" fontFamily="var(--mono)">
                      +{track.occupied_by.delay_min}m
                    </text>
                  </g>
                )}

                {/* Maintenance Outage marker */}
                {track.state === "RESTRICTED" && !track.occupied_by && (
                  <g transform={`translate(${trackStartX + 200}, ${trackY - 12})`}>
                    <rect
                      x="0"
                      y="0"
                      width="250"
                      height="22"
                      fill="url(#hatch-restricted)"
                      stroke="#F59E0B"
                      strokeWidth="1.5"
                      rx="3"
                    />
                    <text x="12" y="15" fill="#FEF08A" fontSize="10" fontWeight="700">
                      ⚠ SPEED RESTRICTION: {track.restrictions || "CAUTION ORDER (30 KM/H)"}
                    </text>
                  </g>
                )}

                {/* Clear / Available status indicator */}
                {track.state === "CLEAR" && !track.occupied_by && (
                  <g transform={`translate(${trackStartX + 340}, ${trackY})`}>
                    <circle cx="0" cy="0" r="4.5" fill="#10B981" />
                    <text x="8" y="3" fill="#34D399" fontSize="9" fontWeight="600" opacity="0.8">
                      BERTH AVAILABLE
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Track Inspection Panel */}
      {selectedTrack && (
        <div
          style={{
            marginTop: "14px",
            background: "#142136",
            padding: "14px 18px",
            borderRadius: "6px",
            border: "1px solid #263852",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <strong style={{ color: "#38BDF8", fontSize: "14px" }}>{selectedTrack.track_name}</strong>
              <Badge tone={selectedTrack.state === "CLEAR" ? "good" : "bad"}>
                {selectedTrack.state}
              </Badge>
              {selectedTrack.electrified && (
                <span style={{ fontSize: "11px", color: "#FBBF24", background: "rgba(245, 158, 11, 0.15)", padding: "2px 6px", borderRadius: "3px" }}>
                  ⚡ 25kV AC Traction
                </span>
              )}
            </div>
            <div style={{ marginTop: "4px", color: "#94A3B8", fontSize: "12px", display: "flex", gap: "16px" }}>
              <span>Category: <strong style={{ color: "#F8FAFC" }}>{selectedTrack.category}</strong></span>
              <span>Berthing Length: <strong style={{ color: "#F8FAFC" }}>{selectedTrack.length_m} m</strong></span>
              <span>Max Yard Speed: <strong style={{ color: "#F8FAFC" }}>{selectedTrack.max_speed_kmph} km/h</strong></span>
              <span>Route Locked: <strong style={{ color: selectedTrack.route_locked ? "#38BDF8" : "#94A3B8" }}>{selectedTrack.route_locked ? "LOCKED" : "FREE"}</strong></span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {selectedTrack.occupied_by && (
              <span style={{ fontSize: "12px", color: "#F8FAFC", background: "#0E1726", padding: "6px 12px", borderRadius: "4px", border: "1px solid #EF4444" }}>
                Occupant: <strong>{selectedTrack.occupied_by.name}</strong> (#{selectedTrack.occupied_by.train_id}) · Delay: +{selectedTrack.occupied_by.delay_min}m
              </span>
            )}
            <button
              onClick={() => setSelectedTrack(null)}
              className="button button-ghost button-small"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
