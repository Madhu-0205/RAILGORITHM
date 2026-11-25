import type { BlockOccupancy, Conflict, Section, Station, Train } from "../types";

export interface RailwayCorridorDiagramProps {
  stations: Station[];
  sections: Section[];
  blockOccupancy: BlockOccupancy[];
  trains: Train[];
  conflicts: Conflict[];
  onSelectStation?: (stationId: string) => void;
  selectedStationId?: string;
}

export function RailwayCorridorDiagram({
  stations,
  sections,
  blockOccupancy,
  trains,
  conflicts,
  onSelectStation,
  selectedStationId,
}: RailwayCorridorDiagramProps) {
  const width = 1000;
  const height = 260;
  const left = 90;
  const right = 90;
  const trackY = 135;
  const stationCount = Math.max(1, stations.length);
  const step = (width - left - right) / Math.max(1, stationCount - 1);

  const xOf = (stationId: string) => {
    const index = stations.findIndex((s) => s.id === stationId);
    return index >= 0 ? left + index * step : left;
  };

  const getSectionState = (sectionId: string) => {
    const blocks = blockOccupancy.filter((b) => b.section_id === sectionId);
    if (blocks.some((b) => b.closure)) return "closure";
    const occupied = blocks.filter((b) => Boolean(b.occupied_by));
    if (occupied.length > 0) return "occupied";
    return "free";
  };

  const getOccupiedBlockTrains = (sectionId: string) => {
    return blockOccupancy
      .filter((b) => b.section_id === sectionId && b.occupied_by)
      .map((b) => {
        const train = trains.find((t) => t.id === b.occupied_by);
        return {
          blockId: b.block_id,
          trainId: b.occupied_by as string,
          direction: train?.direction || b.direction || "UP",
          trainName: train?.name || b.occupied_by,
        };
      });
  };

  return (
    <div className="corridor-diagram-wrapper" style={{ overflowX: "auto" }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="corridor-svg"
        role="img"
        aria-label="Railway corridor diagram showing track blocks and train positions"
        style={{ width: "100%", minWidth: "800px", height: "auto" }}
      >
        <title>Railway Corridor Operational Schematic</title>
        <desc>
          Corridor sections and stations from {stations[0]?.name || "Origin"} to{" "}
          {stations[stations.length - 1]?.name || "Destination"} with real-time block occupancy and train movements.
        </desc>

        {/* Corridor Track Background Grid / Guide */}
        <line
          x1={left - 30}
          y1={trackY}
          x2={width - right + 30}
          y2={trackY}
          stroke="#E2E8F0"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* Section Tracks */}
        {sections.map((section) => {
          const x1 = xOf(section.from_station);
          const x2 = xOf(section.to_station);
          const midX = (x1 + x2) / 2;
          const state = getSectionState(section.id);
          const occupiedTrains = getOccupiedBlockTrains(section.id);

          const strokeColor =
            state === "closure"
              ? "#DC2626"
              : state === "occupied"
              ? "#D97706"
              : "#16A34A";

          const isDouble = section.mode === "DOUBLE";

          // Section conflicts
          const sectionConflicts = conflicts.filter(
            (c) => c.location.section_id === section.id || c.location.block_id?.startsWith(section.id),
          );

          return (
            <g key={section.id} className="corridor-section">
              {/* Double line track: 2 parallel lines */}
              {isDouble ? (
                <>
                  <line
                    x1={x1}
                    y1={trackY - 4}
                    x2={x2}
                    y2={trackY - 4}
                    stroke={strokeColor}
                    strokeWidth={4}
                    strokeDasharray={state === "closure" ? "8 4" : undefined}
                  />
                  <line
                    x1={x1}
                    y1={trackY + 4}
                    x2={x2}
                    y2={trackY + 4}
                    stroke={strokeColor}
                    strokeWidth={4}
                    strokeDasharray={state === "closure" ? "8 4" : undefined}
                  />
                </>
              ) : (
                /* Single line track */
                <line
                  x1={x1}
                  y1={trackY}
                  x2={x2}
                  y2={trackY}
                  stroke={strokeColor}
                  strokeWidth={6}
                  strokeDasharray={state === "closure" ? "8 4" : undefined}
                />
              )}

              {/* Track sleeper ties visualization */}
              <line
                x1={midX - 20}
                y1={trackY - 10}
                x2={midX - 20}
                y2={trackY + 10}
                stroke="#CBD5E1"
                strokeWidth={2}
              />
              <line
                x1={midX + 20}
                y1={trackY - 10}
                x2={midX + 20}
                y2={trackY + 10}
                stroke="#CBD5E1"
                strokeWidth={2}
              />

              {/* Section Labels */}
              <text
                x={midX}
                y={trackY - 26}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill="#334155"
              >
                {section.id} · {section.mode} LINE
              </text>
              <text
                x={midX}
                y={trackY + 34}
                textAnchor="middle"
                fontSize={10}
                fill="#64748B"
              >
                {section.headway_min}m headway · {section.max_speed_kmph} km/h
              </text>

              {/* Conflict indicator on section */}
              {sectionConflicts.length > 0 && (
                <g transform={`translate(${midX - 12}, ${trackY - 50})`}>
                  <rect width={24} height={18} rx={4} fill="#FEE2E2" stroke="#DC2626" />
                  <text x={12} y={13} textAnchor="middle" fontSize={11} fill="#DC2626" fontWeight={700}>
                    ⚠
                  </text>
                </g>
              )}

              {/* Occupying Trains on track */}
              {occupiedTrains.map((ot, idx) => {
                const trainX = midX + (idx * 60 - (occupiedTrains.length - 1) * 30);
                const isUp = ot.direction === "UP";
                return (
                  <g key={`${ot.blockId}-${ot.trainId}`} className="corridor-train-marker">
                    <rect
                      x={trainX - 35}
                      y={trackY - 13}
                      width={70}
                      height={24}
                      rx={4}
                      fill="#1E293B"
                      stroke="#F59E0B"
                      strokeWidth={2}
                    />
                    <text
                      x={trainX}
                      y={trackY + 3}
                      textAnchor="middle"
                      fontSize={10}
                      fontWeight={700}
                      fill="#FFFFFF"
                    >
                      {ot.trainId} {isUp ? "▶" : "◀"}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Stations Nodes */}
        {stations.map((st) => {
          const x = xOf(st.id);
          const isSelected = selectedStationId === st.id;
          const isJunction = st.is_junction;
          const stConflicts = conflicts.filter((c) => c.location.station_id === st.id);

          return (
            <g
              key={st.id}
              className="corridor-station"
              style={{ cursor: onSelectStation ? "pointer" : "default" }}
              onClick={() => onSelectStation?.(st.id)}
            >
              {/* Station Outer Node Circle / Diamond */}
              {isJunction ? (
                /* Diamond crossing for junctions */
                <rect
                  x={x - 18}
                  y={trackY - 18}
                  width={36}
                  height={36}
                  rx={4}
                  transform={`rotate(45 ${x} ${trackY})`}
                  fill={isSelected ? "#2563EB" : "#101B2B"}
                  stroke={isSelected ? "#93C5FD" : "#3B82F6"}
                  strokeWidth={3}
                />
              ) : (
                <circle
                  cx={x}
                  cy={trackY}
                  r={15}
                  fill={isSelected ? "#2563EB" : "#FFFFFF"}
                  stroke={isSelected ? "#1D4ED8" : "#1E293B"}
                  strokeWidth={3}
                />
              )}

              {/* Station Code Text */}
              <text
                x={x}
                y={trackY + 4}
                textAnchor="middle"
                fontSize={10}
                fontWeight={700}
                fill={isJunction || isSelected ? "#FFFFFF" : "#0F172A"}
              >
                {st.id}
              </text>

              {/* Station Full Name Above */}
              <text
                x={x}
                y={trackY - 32}
                textAnchor="middle"
                fontSize={12}
                fontWeight={700}
                fill={isSelected ? "#1D4ED8" : "#0F172A"}
              >
                {st.name}
              </text>

              {/* Station Platforms count below */}
              <text
                x={x}
                y={trackY + 46}
                textAnchor="middle"
                fontSize={10}
                fill="#64748B"
              >
                {st.platforms.length} PFs {isJunction ? "· Junction" : ""}
              </text>

              {/* Conflict indicator at station */}
              {stConflicts.length > 0 && (
                <g transform={`translate(${x - 10}, ${trackY - 56})`}>
                  <rect width={20} height={16} rx={3} fill="#FEE2E2" stroke="#DC2626" />
                  <text x={10} y={12} textAnchor="middle" fontSize={10} fill="#DC2626" fontWeight={700}>
                    !
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend & Summary Footer */}
      <div
        className="corridor-legend flex-row gap-4 items-center justify-between"
        style={{
          marginTop: "8px",
          padding: "8px 14px",
          background: "#F8FAFC",
          borderRadius: "6px",
          fontSize: "0.76rem",
          color: "#475569",
          border: "1px solid #E2E8F0",
        }}
      >
        <div className="flex-row gap-3 items-center">
          <span className="flex-row items-center gap-1">
            <span style={{ display: "inline-block", width: 12, height: 4, background: "#16A34A" }} /> Clear Section
          </span>
          <span className="flex-row items-center gap-1">
            <span style={{ display: "inline-block", width: 12, height: 4, background: "#D97706" }} /> Block Occupied
          </span>
          <span className="flex-row items-center gap-1">
            <span style={{ display: "inline-block", width: 12, height: 4, background: "#DC2626", borderTop: "1px dashed #DC2626" }} /> Closure
          </span>
        </div>
        <div className="flex-row gap-3 items-center">
          <span>◆ Diamond Junction (MLG)</span>
          <span>━ Double Line</span>
          <span>─ Single Line Bottleneck</span>
        </div>
      </div>
    </div>
  );
}
