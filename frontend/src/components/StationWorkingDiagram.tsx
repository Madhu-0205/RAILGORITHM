import React, { useMemo, useState } from "react";
import type { Platform, PlatformOutage, Station, Train } from "../types";
import { Badge } from "./ui";

export interface StationWorkingDiagramProps {
  station: Station;
  platforms: Platform[];
  outages: PlatformOutage[];
  trains: Train[];
  onSelectTrack?: (trackId: string) => void;
  selectedTrackId?: string;
}

interface TrackLineModel {
  id: string;
  name: string;
  type: "MAIN_UP" | "MAIN_DOWN" | "LOOP_PLATFORM" | "GOODS_SIDING" | "DIAMOND_CROSSING";
  platformId?: string;
  status: "AVAILABLE" | "OCCUPIED" | "OUTAGE" | "ROUTE_SET";
  train?: Train;
  outage?: PlatformOutage;
  y: number;
  lengthM: number;
}

export function StationWorkingDiagram({
  station,
  platforms,
  outages,
  trains,
  onSelectTrack,
  selectedTrackId,
}: StationWorkingDiagramProps) {
  const [selectedTrack, setSelectedTrack] = useState<TrackLineModel | null>(null);

  // SVG canvas dimensions
  const width = 960;
  const height = 320;
  const trackStartX = 140;
  const trackEndX = 820;

  // Station layout track lines
  const trackLines = useMemo<TrackLineModel[]>(() => {
    const list: TrackLineModel[] = [];
    const isJunction = station.is_junction;
    const pfIds = station.platforms || ["P1", "P2"];

    // 1. Up Loop (Platform 1)
    const pf1 = platforms.find((p) => p.station_id === station.id && p.platform_id === "P1");
    const pf1Outage = outages.find((o) => o.station_id === station.id && o.platform_id === "P1");
    const pf1Train = trains.find(
      (t) => t.station_id === station.id && (t.platform === "P1" || pf1?.occupied_by === t.id)
    );
    list.push({
      id: `${station.id}-P1`,
      name: `Platform 1 (Up Loop)`,
      type: "LOOP_PLATFORM",
      platformId: "P1",
      status: pf1Outage ? "OUTAGE" : pf1Train || pf1?.occupied_by ? "OCCUPIED" : "AVAILABLE",
      train: pf1Train,
      outage: pf1Outage,
      y: 70,
      lengthM: 650,
    });

    // 2. Up Main Line (Through Line)
    list.push({
      id: `${station.id}-MAIN-UP`,
      name: `Up Main Line (Through Line)`,
      type: "MAIN_UP",
      status: "AVAILABLE",
      y: 120,
      lengthM: 750,
    });

    // 3. Down Main Line (Platform 2 or Through Line)
    const pf2 = platforms.find((p) => p.station_id === station.id && p.platform_id === "P2");
    const pf2Outage = outages.find((o) => o.station_id === station.id && o.platform_id === "P2");
    const pf2Train = trains.find(
      (t) => t.station_id === station.id && (t.platform === "P2" || pf2?.occupied_by === t.id)
    );
    list.push({
      id: `${station.id}-P2`,
      name: `Platform 2 (Down Main / Platform Line)`,
      type: "LOOP_PLATFORM",
      platformId: "P2",
      status: pf2Outage ? "OUTAGE" : pf2Train || pf2?.occupied_by ? "OCCUPIED" : "AVAILABLE",
      train: pf2Train,
      outage: pf2Outage,
      y: 170,
      lengthM: 600,
    });

    // 4. Platform 3 (if junction or multi-platform)
    if (pfIds.includes("P3")) {
      const pf3 = platforms.find((p) => p.station_id === station.id && p.platform_id === "P3");
      const pf3Outage = outages.find((o) => o.station_id === station.id && o.platform_id === "P3");
      const pf3Train = trains.find(
        (t) => t.station_id === station.id && (t.platform === "P3" || pf3?.occupied_by === t.id)
      );
      list.push({
        id: `${station.id}-P3`,
        name: `Platform 3 (Down Loop)`,
        type: "LOOP_PLATFORM",
        platformId: "P3",
        status: pf3Outage ? "OUTAGE" : pf3Train || pf3?.occupied_by ? "OCCUPIED" : "AVAILABLE",
        train: pf3Train,
        outage: pf3Outage,
        y: 220,
        lengthM: 600,
      });
    }

    // 5. Goods / Shunting Siding (Bottom)
    list.push({
      id: `${station.id}-SIDING`,
      name: `Goods & Stabling Siding`,
      type: "GOODS_SIDING",
      status: "AVAILABLE",
      y: pfIds.includes("P3") ? 270 : 230,
      lengthM: 450,
    });

    return list;
  }, [station, platforms, outages, trains]);

  const activeTrack = selectedTrack || trackLines[0];

  const handleTrackClick = (track: TrackLineModel) => {
    setSelectedTrack(track);
    if (onSelectTrack) onSelectTrack(track.id);
  };

  return (
    <div className="station-working-diagram-card stack" style={{ gap: "16px" }}>
      {/* Station Yard Header & Status Summary */}
      <div
        className="station-yard-header flex-row justify-between items-center flex-wrap gap-2"
        style={{
          background: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          border: "1px solid #E2E8F0",
        }}
      >
        <div className="flex-row items-center gap-3">
          <span
            style={{
              background: "#0F172A",
              color: "#FFFFFF",
              padding: "4px 8px",
              borderRadius: "4px",
              fontFamily: "monospace",
              fontWeight: 700,
              fontSize: "0.85rem",
            }}
          >
            {station.code}
          </span>
          <div>
            <strong style={{ fontSize: "1rem" }}>{station.name} Station Yard Layout</strong>
            <span className="small text-muted d-block">
              Panel Interlocking / Electronic Interlocking (EI) Operational VDU View
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-row items-center gap-3 small text-muted">
          <div className="flex-row items-center gap-1">
            <span style={{ width: "10px", height: "10px", background: "#16A34A", borderRadius: "2px" }} />
            <span>Clear / Available</span>
          </div>
          <div className="flex-row items-center gap-1">
            <span style={{ width: "10px", height: "10px", background: "#2563EB", borderRadius: "2px" }} />
            <span>Berthed / Occupied</span>
          </div>
          <div className="flex-row items-center gap-1">
            <span style={{ width: "10px", height: "10px", background: "#DC2626", borderRadius: "2px" }} />
            <span>Maintenance Block</span>
          </div>
          {station.is_junction && (
            <Badge tone="watch">Diamond Crossing Throat (Cap 2)</Badge>
          )}
        </div>
      </div>

      {/* Main Vector Interlocking SVG Diagram */}
      <div
        className="station-svg-container"
        style={{
          overflowX: "auto",
          background: "#0F172A", // Railway control dark panel background for authenticity
          borderRadius: "8px",
          border: "1px solid #334155",
          padding: "12px",
          position: "relative",
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="station-interlocking-svg"
          role="img"
          aria-label={`Station Working Diagram of ${station.name}`}
          style={{ width: "100%", minWidth: "860px", height: "auto", display: "block" }}
        >
          <title>{`${station.name} Interlocking Track Diagram`}</title>
          <desc>
            Displays reception lines, passenger platforms, main lines, and signals for {station.name}.
          </desc>

          {/* Inbound Block Section Feeds */}
          {/* West / Up Entry */}
          <line x1={20} y1={120} x2={trackStartX - 20} y2={120} stroke="#64748B" strokeWidth={3} />
          <text x={30} y={110} fill="#94A3B8" fontSize={10} fontFamily="monospace" fontWeight={600}>
            ← FROM WEST BLOCK
          </text>

          {/* East / Down Exit */}
          <line x1={trackEndX + 20} y1={120} x2={width - 20} y2={120} stroke="#64748B" strokeWidth={3} />
          <text x={width - 150} y={110} fill="#94A3B8" fontSize={10} fontFamily="monospace" fontWeight={600}>
            TO EAST BLOCK →
          </text>

          {/* West Turnouts / Lead Switches to Platforms & Loops */}
          <path
            d={`M ${trackStartX - 20} 120 L ${trackStartX + 20} 70`}
            stroke="#64748B"
            strokeWidth={2.5}
            fill="none"
          />
          <path
            d={`M ${trackStartX - 20} 120 L ${trackStartX + 20} 170`}
            stroke="#64748B"
            strokeWidth={2.5}
            fill="none"
          />
          {station.platforms.includes("P3") && (
            <path
              d={`M ${trackStartX} 170 L ${trackStartX + 40} 220`}
              stroke="#64748B"
              strokeWidth={2.5}
              fill="none"
            />
          )}

          {/* East Turnouts / Trailing Switches */}
          <path
            d={`M ${trackEndX - 20} 70 L ${trackEndX + 20} 120`}
            stroke="#64748B"
            strokeWidth={2.5}
            fill="none"
          />
          <path
            d={`M ${trackEndX - 20} 170 L ${trackEndX + 20} 120`}
            stroke="#64748B"
            strokeWidth={2.5}
            fill="none"
          />
          {station.platforms.includes("P3") && (
            <path
              d={`M ${trackEndX - 40} 220 L ${trackEndX} 170`}
              stroke="#64748B"
              strokeWidth={2.5}
              fill="none"
            />
          )}

          {/* Diamond Crossing Throat Visualizer for Malgaon Junction */}
          {station.is_junction && (
            <g className="diamond-crossing-throat" transform="translate(480, 145)">
              <rect x={-35} y={-45} width={70} height={90} fill="#1E293B" stroke="#F59E0B" strokeWidth={1.5} strokeDasharray="3 3" rx={4} />
              <line x1={-30} y1={-25} x2={30} y2={25} stroke="#F59E0B" strokeWidth={2} />
              <line x1={-30} y1={25} x2={30} y2={-25} stroke="#F59E0B" strokeWidth={2} />
              <text x={0} y={-32} textAnchor="middle" fill="#F59E0B" fontSize={8} fontWeight={700}>
                DIAMOND THROAT
              </text>
            </g>
          )}

          {/* Station Tracks & Platform Lines */}
          {trackLines.map((track) => {
            const isSelected = activeTrack?.id === track.id;
            const isOccupied = track.status === "OCCUPIED";
            const isOutage = track.status === "OUTAGE";

            const trackColor = isOutage
              ? "#EF4444" // Bright red
              : isOccupied
              ? "#3B82F6" // Bright blue
              : "#22C55E"; // Emerald green

            return (
              <g
                key={track.id}
                className="station-track-row"
                style={{ cursor: "pointer" }}
                onClick={() => handleTrackClick(track)}
              >
                {/* Track Line */}
                <line
                  x1={trackStartX + 20}
                  y1={track.y}
                  x2={trackEndX - 20}
                  y2={track.y}
                  stroke={trackColor}
                  strokeWidth={isSelected ? 6 : 4}
                  strokeDasharray={isOutage ? "8 4" : undefined}
                />

                {/* Platform Island Berth (for passenger platforms) */}
                {track.platformId && (
                  <rect
                    x={trackStartX + 80}
                    y={track.y - 18}
                    width={trackEndX - trackStartX - 160}
                    height={8}
                    fill="#334155"
                    stroke="#475569"
                    strokeWidth={1}
                    rx={2}
                  />
                )}

                {/* Left Track Identifier Label */}
                <text
                  x={trackStartX + 10}
                  y={track.y - 8}
                  fill="#E2E8F0"
                  fontSize={11}
                  fontWeight={600}
                >
                  {track.name}
                </text>

                {/* Track Status Badge in Diagram */}
                <text
                  x={trackEndX - 30}
                  y={track.y - 8}
                  textAnchor="end"
                  fill={trackColor}
                  fontSize={10}
                  fontFamily="monospace"
                  fontWeight={700}
                >
                  {isOutage
                    ? "[BLOCKED]"
                    : isOccupied
                    ? `[OCCUPIED: ${track.train?.id || "TRAIN"}]`
                    : "[CLEAR]"}
                </text>

                {/* Train Box if Berthed */}
                {isOccupied && track.train && (
                  <g transform={`translate(${trackStartX + 260}, ${track.y - 12})`}>
                    <rect
                      x={0}
                      y={0}
                      width={180}
                      height={24}
                      fill="#1E3A8A"
                      stroke="#60A5FA"
                      strokeWidth={1.5}
                      rx={4}
                    />
                    <text
                      x={10}
                      y={16}
                      fill="#FFFFFF"
                      fontSize={11}
                      fontWeight={700}
                      fontFamily="monospace"
                    >
                      🚆 {track.train.id} ({track.train.train_type})
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Starter Signals */}
          <g className="starter-signals">
            {trackLines.map((t) => (
              <g key={`starter-${t.id}`} transform={`translate(${trackEndX - 50}, ${t.y - 14})`}>
                <line x1={0} y1={0} x2={0} y2={14} stroke="#94A3B8" strokeWidth={1.5} />
                <circle cx={4} cy={4} r={3} fill={t.status === "OCCUPIED" ? "#EF4444" : "#22C55E"} />
              </g>
            ))}
          </g>
        </svg>
      </div>

      {/* Selected Track Inspection Popover / Detail Panel */}
      {activeTrack && (
        <div
          className="track-detail-panel"
          style={{
            background: "#F8FAFC",
            border: "1px solid #E2E8F0",
            borderRadius: "8px",
            padding: "14px 18px",
          }}
        >
          <div className="flex-row justify-between items-center flex-wrap gap-2 mb-2">
            <div className="flex-row items-center gap-2">
              <strong style={{ fontSize: "0.95rem" }}>
                Track Inspection: {activeTrack.name}
              </strong>
              <Badge
                tone={
                  activeTrack.status === "OCCUPIED"
                    ? "default"
                    : activeTrack.status === "OUTAGE"
                    ? "bad"
                    : "good"
                }
              >
                {activeTrack.status}
              </Badge>
            </div>
            <span className="small text-muted mono">
              Track ID: {activeTrack.id} · Usable Length: {activeTrack.lengthM}m
            </span>
          </div>

          <div
            className="grid-three"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "12px",
              marginTop: "8px",
            }}
          >
            <div>
              <small className="text-muted d-block">Occupying Movement</small>
              <strong>{activeTrack.train ? activeTrack.train.name : "None (Track Unoccupied)"}</strong>
              {activeTrack.train && (
                <span className="small text-muted d-block mono">
                  Train No: {activeTrack.train.id} ({activeTrack.train.train_type})
                </span>
              )}
            </div>

            <div>
              <small className="text-muted d-block">Schedule & Dwell</small>
              <span>
                {activeTrack.train
                  ? `Sched Dep: ${activeTrack.train.scheduled_departure || "—"} · Delay: +${activeTrack.train.projected_delay_min || 0}m`
                  : "Ready for route setting"}
              </span>
            </div>

            <div>
              <small className="text-muted d-block">Sensors & Interlocking Provenance</small>
              <span className="small text-muted">
                Dual Axle Counters (HASSDAC) & Audio Frequency Track Circuit (AFTC) · <strong>MEASURED</strong>
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
