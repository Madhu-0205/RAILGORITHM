import React from "react";
import type { SectionControllerTopology } from "../types";

interface SectionTopologyStripProps {
  topology: SectionControllerTopology;
}

export function SectionTopologyStrip({ topology }: SectionTopologyStripProps) {
  const { stations, sections, speed_restrictions, corridor_length_km } = topology;

  const svgWidth = 1000;
  const svgHeight = 160;
  const marginX = 60;
  const usableWidth = svgWidth - 2 * marginX;

  const getStationX = (km: number) => {
    return marginX + (km / Math.max(1, corridor_length_km)) * usableWidth;
  };

  return (
    <div
      className="section-topology-strip"
      style={{
        background: "#0f172a",
        borderRadius: "8px",
        padding: "16px",
        border: "1px solid #1e293b",
        color: "#f8fafc",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div>
          <span style={{ fontSize: "14px", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "1px" }}>
            Corridor Topology Strip — Linear Section Layout
          </span>
          <span style={{ marginLeft: "12px", fontSize: "12px", color: "#94a3b8" }}>
            Total Length: {corridor_length_km} km | Signaling: Absolute Block (MACLS)
          </span>
        </div>
        <div style={{ display: "flex", gap: "14px", fontSize: "11px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "16px", height: "3px", backgroundColor: "#38bdf8", display: "inline-block" }}></span> Double Line
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "16px", height: "3px", backgroundColor: "#f59e0b", display: "inline-block" }}></span> Single Line Bottleneck
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "10px", height: "10px", backgroundColor: "#ef4444", borderRadius: "2px", display: "inline-block" }}></span> Block Occupied
          </span>
        </div>
      </div>

      <div style={{ overflowX: "auto" }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: "100%", height: "auto", minWidth: "850px" }}>
          {/* Base track lines for each section */}
          {sections.map((sec) => {
            const fromSt = stations.find((s) => s.station_id === sec.from_station);
            const toSt = stations.find((s) => s.station_id === sec.to_station);
            if (!fromSt || !toSt) return null;

            const x1 = getStationX(fromSt.km);
            const x2 = getStationX(toSt.km);
            const isSingle = sec.mode === "SINGLE";
            const lineColor = isSingle ? "#f59e0b" : "#38bdf8";

            return (
              <g key={sec.section_id}>
                {/* UP Line / Single Line */}
                <line
                  x1={x1}
                  y1={isSingle ? 60 : 50}
                  x2={x2}
                  y2={isSingle ? 60 : 50}
                  stroke={lineColor}
                  strokeWidth={isSingle ? 3 : 2}
                />

                {/* DOWN Line (if double) */}
                {!isSingle && (
                  <line
                    x1={x1}
                    y1={70}
                    x2={x2}
                    y2={70}
                    stroke={lineColor}
                    strokeWidth={2}
                  />
                )}

                {/* Section label & speed */}
                <text
                  x={(x1 + x2) / 2}
                  y={isSingle ? 45 : 38}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                  fontWeight="600"
                >
                  {sec.section_id} ({sec.mode}, {sec.distance_km}km, max {sec.max_speed_kmph}km/h)
                </text>

                {/* Block Occupancy Markers */}
                {sec.blocks.map((blk, bIdx) => {
                  const blkX = x1 + ((bIdx + 0.5) / sec.blocks.length) * (x2 - x1);
                  const blkY = isSingle ? 60 : blk.direction === "UP" ? 50 : 70;

                  return (
                    <g key={blk.block_id} transform={`translate(${blkX}, ${blkY})`}>
                      <circle
                        cx="0"
                        cy="0"
                        r={blk.is_occupied ? 7 : 4}
                        fill={blk.is_occupied ? "#ef4444" : "#10b981"}
                        stroke="#0f172a"
                        strokeWidth="1.5"
                      />
                      {blk.is_occupied && (
                        <text x="0" y="-12" textAnchor="middle" fill="#fca5a5" fontSize="10" fontWeight="700">
                          🚆 {blk.occupant_train}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            );
          })}

          {/* Speed Restrictions along corridor */}
          {speed_restrictions.map((tsr, idx) => {
            const tsrX = getStationX(tsr.km_location);
            return (
              <g key={idx} transform={`translate(${tsrX}, 95)`}>
                <polygon points="0,0 -6,-10 6,-10" fill="#f59e0b" />
                <rect x="-16" y="2" width="32" height="14" fill="#1e293b" rx="2" stroke="#f59e0b" strokeWidth="1" />
                <text x="0" y="12" textAnchor="middle" fill="#fef08a" fontSize="9" fontWeight="700">
                  {tsr.speed_limit_kmph}
                </text>
              </g>
            );
          })}

          {/* Station Nodes */}
          {stations.map((st) => {
            const cx = getStationX(st.km);

            return (
              <g key={st.station_id} transform={`translate(${cx}, 60)`}>
                {/* Station circle */}
                <circle
                  cx="0"
                  cy="0"
                  r={st.is_junction ? 10 : 8}
                  fill={st.is_junction ? "#38bdf8" : "#ffffff"}
                  stroke="#0f172a"
                  strokeWidth="2.5"
                />

                {/* Station Code & Name */}
                <text x="0" y="-18" textAnchor="middle" fill="#ffffff" fontSize="12" fontWeight="700">
                  {st.code}
                </text>
                <text x="0" y="26" textAnchor="middle" fill="#94a3b8" fontSize="10">
                  {st.name}
                </text>
                <text x="0" y="38" textAnchor="middle" fill="#64748b" fontSize="9">
                  km {st.km}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
