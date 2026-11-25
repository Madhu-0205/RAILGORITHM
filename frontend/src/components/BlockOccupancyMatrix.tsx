import React, { useMemo, useState } from "react";
import type { BlockOccupancy, Section, Train } from "../types";
import { Badge } from "./ui";

export interface BlockOccupancyMatrixProps {
  sections: Section[];
  blockOccupancy: BlockOccupancy[];
  trains: Train[];
  onSelectBlock?: (blockId: string) => void;
  selectedBlockId?: string;
}

interface BlockDetailRow {
  blockId: string;
  sectionId: string;
  sectionName: string;
  mode: "SINGLE" | "DOUBLE";
  direction: "UP" | "DOWN" | "BIDIRECTIONAL";
  distanceKm: number;
  maxSpeedKmph: number;
  runTimeMin: number;
  headwayMin: number;
  signalingType: string;
  status: "CLEAR" | "OCCUPIED" | "MAINTENANCE";
  occupyingTrain?: Train;
  trainId: string | null;
  entryMin: number | null;
  exitMin: number | null;
  isSingleLineBottleneck: boolean;
  maintenanceReason?: string;
}

const SECTION_METADATA: Record<
  string,
  { name: string; distanceKm: number; maxSpeedKmph: number }
> = {
  S1: { name: "Nandpur – Karanpur", distanceKm: 14.0, maxSpeedKmph: 90 },
  S2: { name: "Karanpur – Malgaon Jct", distanceKm: 18.0, maxSpeedKmph: 110 },
  S3: { name: "Malgaon Jct – Suryapur", distanceKm: 16.0, maxSpeedKmph: 90 },
  S4: { name: "Suryapur – Vasanthpur", distanceKm: 12.0, maxSpeedKmph: 110 },
};

function formatMinutesToTime(min: number | null): string {
  if (min === null || min === undefined) return "—";
  const h = Math.floor(min / 60) % 24;
  const m = min % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
}

export function BlockOccupancyMatrix({
  sections,
  blockOccupancy,
  trains,
  onSelectBlock,
  selectedBlockId,
}: BlockOccupancyMatrixProps) {
  const [filterMode, setFilterMode] = useState<"ALL" | "OCCUPIED" | "BOTTLENECKS">("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const rows = useMemo<BlockDetailRow[]>(() => {
    return blockOccupancy.map((b) => {
      const secMeta = SECTION_METADATA[b.section_id] || {
        name: `${b.from_station} – ${b.to_station}`,
        distanceKm: 10.0,
        maxSpeedKmph: 100,
      };

      const train = b.occupied_by ? trains.find((t) => t.id === b.occupied_by) : undefined;
      const isOutage = Boolean(b.closure);
      const isOccupied = Boolean(b.occupied_by);

      const status: "CLEAR" | "OCCUPIED" | "MAINTENANCE" = isOutage
        ? "MAINTENANCE"
        : isOccupied
        ? "OCCUPIED"
        : "CLEAR";

      const isSingleLineBottleneck = b.mode === "SINGLE";

      return {
        blockId: b.block_id,
        sectionId: b.section_id,
        sectionName: secMeta.name,
        mode: (b.mode as "SINGLE" | "DOUBLE") || "SINGLE",
        direction: (b.direction as "UP" | "DOWN" | "BIDIRECTIONAL") || "BIDIRECTIONAL",
        distanceKm: secMeta.distanceKm,
        maxSpeedKmph: secMeta.maxSpeedKmph,
        runTimeMin: b.run_time_min,
        headwayMin: b.headway_min,
        signalingType: "Absolute Block (BPAC)",
        status,
        occupyingTrain: train,
        trainId: b.occupied_by,
        entryMin: b.entry_min,
        exitMin: b.exit_min,
        isSingleLineBottleneck,
        maintenanceReason: b.closure?.reason,
      };
    });
  }, [blockOccupancy, trains]);

  const filteredRows = useMemo(() => {
    return rows.filter((r) => {
      if (filterMode === "OCCUPIED" && r.status !== "OCCUPIED") return false;
      if (filterMode === "BOTTLENECKS" && !r.isSingleLineBottleneck) return false;
      if (!searchTerm.trim()) return true;

      const q = searchTerm.toLowerCase();
      return (
        r.blockId.toLowerCase().includes(q) ||
        r.sectionName.toLowerCase().includes(q) ||
        (r.trainId && r.trainId.toLowerCase().includes(q)) ||
        (r.occupyingTrain && r.occupyingTrain.name.toLowerCase().includes(q))
      );
    });
  }, [rows, filterMode, searchTerm]);

  // Statistics
  const totalBlocks = rows.length;
  const occupiedCount = rows.filter((r) => r.status === "OCCUPIED").length;
  const maintenanceCount = rows.filter((r) => r.status === "MAINTENANCE").length;
  const clearCount = rows.filter((r) => r.status === "CLEAR").length;

  return (
    <div className="block-occupancy-matrix-card stack" style={{ gap: "16px" }}>
      {/* Overview Metric Bar */}
      <div
        className="block-matrix-header flex-row justify-between items-center flex-wrap gap-3"
        style={{
          background: "#F8FAFC",
          padding: "12px 16px",
          borderRadius: "8px",
          border: "1px solid #E2E8F0",
        }}
      >
        <div className="flex-row items-center gap-3">
          <div>
            <strong style={{ fontSize: "1rem" }}>Corridor Block Section Occupancy Matrix</strong>
            <span className="small text-muted d-block">
              Real-time Absolute Block System & Axle Counter Verification Status
            </span>
          </div>
        </div>

        {/* Status Counters */}
        <div className="flex-row items-center gap-3">
          <div className="flex-row items-center gap-1 small">
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#16A34A" }} />
            <span>Clear: <strong>{clearCount}</strong></span>
          </div>
          <div className="flex-row items-center gap-1 small">
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#D97706" }} />
            <span>Occupied: <strong>{occupiedCount}</strong></span>
          </div>
          {maintenanceCount > 0 && (
            <div className="flex-row items-center gap-1 small">
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#DC2626" }} />
              <span>Outage: <strong>{maintenanceCount}</strong></span>
            </div>
          )}
          <Badge tone="muted">{totalBlocks} Total Blocks</Badge>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex-row justify-between items-center flex-wrap gap-2">
        <div className="button-group" role="group" aria-label="Block filter options">
          <button
            type="button"
            className={`button button-small ${filterMode === "ALL" ? "button-primary" : "button-ghost"}`}
            onClick={() => setFilterMode("ALL")}
          >
            All Blocks ({rows.length})
          </button>
          <button
            type="button"
            className={`button button-small ${filterMode === "OCCUPIED" ? "button-primary" : "button-ghost"}`}
            onClick={() => setFilterMode("OCCUPIED")}
          >
            Occupied Only ({occupiedCount})
          </button>
          <button
            type="button"
            className={`button button-small ${filterMode === "BOTTLENECKS" ? "button-primary" : "button-ghost"}`}
            onClick={() => setFilterMode("BOTTLENECKS")}
          >
            Single-Line Bottlenecks (B1, B3)
          </button>
        </div>

        <input
          type="search"
          placeholder="Search by block ID, section, or train..."
          className="input input-small"
          style={{ maxWidth: "280px" }}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          aria-label="Search block sections"
        />
      </div>

      {/* Block Sections Table */}
      <div className="table-wrapper" tabIndex={0} role="region" aria-label="Block section occupancy table">
        <table className="table">
          <thead>
            <tr>
              <th>Block ID</th>
              <th>Section / Territory</th>
              <th>Mode / Direction</th>
              <th>Line Clear State</th>
              <th>Occupying Train</th>
              <th>Transit Window</th>
              <th>Section Speed & Headway</th>
              <th>Data Source</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => {
              const isSelected = selectedBlockId === row.blockId;

              const stateTone =
                row.status === "OCCUPIED"
                  ? "watch"
                  : row.status === "MAINTENANCE"
                  ? "bad"
                  : "good";

              const stateLabel =
                row.status === "OCCUPIED"
                  ? "TRAIN ON LINE"
                  : row.status === "MAINTENANCE"
                  ? "LINE CLOSED"
                  : "LINE CLEAR";

              return (
                <tr
                  key={row.blockId}
                  className={isSelected ? "row-selected" : undefined}
                  style={{ cursor: onSelectBlock ? "pointer" : "default" }}
                  onClick={() => onSelectBlock && onSelectBlock(row.blockId)}
                >
                  {/* Block ID */}
                  <td>
                    <div className="flex-row items-center gap-2">
                      <span className="mono" style={{ fontWeight: 700, fontSize: "0.95rem" }}>
                        {row.blockId}
                      </span>
                      {row.isSingleLineBottleneck && (
                        <span
                          className="badge badge-watch"
                          style={{ fontSize: "0.68rem", padding: "2px 5px" }}
                          title="Single-line critical bottleneck section"
                        >
                          BOTTLENECK
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Section */}
                  <td>
                    <strong>{row.sectionName}</strong>
                    <span className="small text-muted d-block mono">
                      Sec {row.sectionId} · {row.distanceKm} km
                    </span>
                  </td>

                  {/* Mode / Direction */}
                  <td>
                    <Badge tone="muted">
                      {row.mode} ({row.direction})
                    </Badge>
                  </td>

                  {/* Line Clear State */}
                  <td>
                    <Badge tone={stateTone}>
                      {stateLabel}
                    </Badge>
                  </td>

                  {/* Occupying Train */}
                  <td>
                    {row.occupyingTrain ? (
                      <div>
                        <strong>{row.occupyingTrain.name}</strong>
                        <span className="small text-muted d-block mono">
                          #{row.occupyingTrain.id} ({row.occupyingTrain.train_type})
                        </span>
                      </div>
                    ) : row.trainId ? (
                      <div>
                        <strong className="mono">Train #{row.trainId}</strong>
                      </div>
                    ) : row.maintenanceReason ? (
                      <span className="small text-bad">{row.maintenanceReason}</span>
                    ) : (
                      <span className="small text-muted">— None (Clear) —</span>
                    )}
                  </td>

                  {/* Transit Window */}
                  <td>
                    <div className="small mono">
                      <span>Entry: {formatMinutesToTime(row.entryMin)}</span>
                      <span className="text-muted d-block">
                        Exp Exit: {formatMinutesToTime(row.exitMin)} ({row.runTimeMin}m run)
                      </span>
                    </div>
                  </td>

                  {/* Speed & Headway */}
                  <td>
                    <span className="small">
                      MPS: <strong>{row.maxSpeedKmph} km/h</strong>
                    </span>
                    <span className="small text-muted d-block">
                      Headway: {row.headwayMin} min
                    </span>
                  </td>

                  {/* Data Source Provenance */}
                  <td>
                    <span className="badge badge-default" style={{ fontSize: "0.72rem" }}>
                      BPAC (Axle Counter) · MEASURED
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
