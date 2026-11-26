import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSimulation } from "../simulation";
import { useAsync } from "../lib/useAsync";
import { numberOrDash } from "../lib/format";
import type { BlockOccupancy, Network, Section, Station } from "../types";
import { Badge, EmptyState, ErrorBanner, KpiCard, Panel, Spinner } from "../components/ui";
import { RailwayCorridorDiagram } from "../components/RailwayCorridorDiagram";
import { BlockOccupancyMatrix } from "../components/BlockOccupancyMatrix";

const DEFAULT_STATIONS: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

const DEFAULT_SECTIONS: Section[] = [
  {
    id: "S1",
    from_station: "NDL",
    to_station: "KRN",
    mode: "SINGLE",
    headway_min: 4,
    max_speed_kmph: 90,
    blocks: [{ id: "B1", direction: "BIDIRECTIONAL", run_time_min: 12 }],
  },
  {
    id: "S2",
    from_station: "KRN",
    to_station: "MLG",
    mode: "DOUBLE",
    headway_min: 3,
    max_speed_kmph: 110,
    blocks: [
      { id: "B2U", direction: "UP", run_time_min: 10 },
      { id: "B2D", direction: "DOWN", run_time_min: 10 },
    ],
  },
  {
    id: "S3",
    from_station: "MLG",
    to_station: "SRP",
    mode: "SINGLE",
    headway_min: 4,
    max_speed_kmph: 90,
    blocks: [{ id: "B3", direction: "BIDIRECTIONAL", run_time_min: 14 }],
  },
  {
    id: "S4",
    from_station: "SRP",
    to_station: "VSN",
    mode: "DOUBLE",
    headway_min: 3,
    max_speed_kmph: 110,
    blocks: [
      { id: "B4U", direction: "UP", run_time_min: 9 },
      { id: "B4D", direction: "DOWN", run_time_min: 9 },
    ],
  },
];

export function BlockSectionBoardPage() {
  const { selectedId, revision } = useSimulation();
  const [filterMode, setFilterMode] = useState<"ALL" | "OCCUPIED" | "SINGLE_LINE">("ALL");

  const { data, error, loading, reload } = useAsync(
    () => (selectedId ? api.dashboard(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const { data: networkData } = useAsync<{
    network: Network;
    block_occupancy: BlockOccupancy[];
  } | null>(
    () => (selectedId ? api.network(selectedId) : Promise.resolve(null)),
    [selectedId, revision],
  );

  const corridorStations = networkData?.network.stations || DEFAULT_STATIONS;
  const corridorSections = networkData?.network.sections || DEFAULT_SECTIONS;
  const blockOccupancies = networkData?.block_occupancy || data?.occupied_blocks || [];
  const corridorTrains = data?.trains || [];
  const corridorConflicts = data?.conflicts || [];

  const occupiedBlocksCount = useMemo(() => {
    return blockOccupancies.filter((b) => !!b.occupied_by).length;
  }, [blockOccupancies]);

  const singleLineBlocks = useMemo(() => {
    return corridorSections
      .filter((s) => s.mode === "SINGLE")
      .flatMap((s) => s.blocks.map((b) => b.id));
  }, [corridorSections]);

  const occupiedSingleLineBlocks = useMemo(() => {
    return blockOccupancies.filter((b) => !!b.occupied_by && singleLineBlocks.includes(b.block_id));
  }, [blockOccupancies, singleLineBlocks]);

  if (!selectedId) {
    return (
      <EmptyState
        title="No simulation selected"
        description="Select an active simulation to view the Block Section Control Board."
      />
    );
  }

  if (loading && !data) return <Spinner label="Loading Block Section Board..." />;
  if (error) return <ErrorBanner message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stack">
      {/* Workspace Header */}
      <div className="page-heading">
        <div>
          <div className="flex-row gap-2 items-center">
            <h1>Absolute Block Section Board</h1>
            <span className="badge badge-accent">LINE CLEAR & TRACK CIRCUITS</span>
          </div>
          <p className="muted">
            Indian Railways Absolute Block System status, axle counter detection, direction locks, and single-line tokens
          </p>
        </div>
        <div className="heading-badges flex-row gap-2 items-center">
          <Link to="/" className="button button-small button-ghost">
            ← Back to Overview
          </Link>
          <span className="badge badge-watch">Sim Time: {data.simulation.sim_time} IST</span>
        </div>
      </div>

      {/* Block Status KPI Strip */}
      <div className="kpi-grid">
        <KpiCard
          label="Total Block Sections"
          value={corridorSections.flatMap((s) => s.blocks).length}
          hint="6 configured block sections"
          tone="neutral"
          period="Current Instant"
          source="Infrastructure Topology"
          quality="MEASURED"
        />
        <KpiCard
          label="Occupied Blocks"
          value={occupiedBlocksCount}
          hint={`${corridorSections.flatMap((s) => s.blocks).length - occupiedBlocksCount} blocks clear`}
          tone={occupiedBlocksCount > 3 ? "watch" : "good"}
          period="Current Instant"
          source="Axle Counter & Track Relays"
          quality="MEASURED"
        />
        <KpiCard
          label="Single-Line Bottlenecks"
          value={`${occupiedSingleLineBlocks.length} / ${singleLineBlocks.length}`}
          hint="B1 (NDL-KRN) · B3 (MLG-SRP)"
          tone={occupiedSingleLineBlocks.length > 0 ? "watch" : "good"}
          period="Current Instant"
          source="Single Line Token Circuits"
          quality="MEASURED"
        />
        <KpiCard
          label="Block Closures"
          value={(data.closures || []).length}
          hint="Engineering possession blocks"
          tone={(data.closures || []).length > 0 ? "bad" : "good"}
          period="Active Caution Bulletin"
          source="Caution Order Register"
          quality="MEASURED"
        />
      </div>

      {/* Horizontal Corridor Track & Movement Schematic */}
      <Panel
        title="Horizontal Corridor Movement & Block Layout Schematic"
        subtitle="Live geographic progression across Nandpur, Karanpur, Malgaon Junction, Suryapur, and Vasanthpur"
      >
        <RailwayCorridorDiagram
          stations={corridorStations}
          sections={corridorSections}
          blockOccupancy={blockOccupancies}
          trains={corridorTrains}
          conflicts={corridorConflicts}
          selectedStationId={undefined}
          onSelectStation={() => {}}
        />
      </Panel>

      {/* Block Filter Controls */}
      <div
        className="flex-row justify-between items-center"
        style={{
          background: "#1E293B",
          color: "#F8FAFC",
          padding: "10px 16px",
          borderRadius: "8px",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <div className="flex-row items-center gap-2">
          <span style={{ fontSize: "0.80rem", fontWeight: 700, color: "#38BDF8", textTransform: "uppercase" }}>
            Filter Blocks:
          </span>
          <div className="button-group">
            <button
              type="button"
              className={`button button-small ${filterMode === "ALL" ? "button-primary" : "button-ghost"}`}
              onClick={() => setFilterMode("ALL")}
            >
              All Blocks ({corridorSections.flatMap((s) => s.blocks).length})
            </button>
            <button
              type="button"
              className={`button button-small ${filterMode === "OCCUPIED" ? "button-primary" : "button-ghost"}`}
              onClick={() => setFilterMode("OCCUPIED")}
            >
              Occupied Only ({occupiedBlocksCount})
            </button>
            <button
              type="button"
              className={`button button-small ${filterMode === "SINGLE_LINE" ? "button-primary" : "button-ghost"}`}
              onClick={() => setFilterMode("SINGLE_LINE")}
            >
              Single-Line Only ({singleLineBlocks.length})
            </button>
          </div>
        </div>

        <div className="flex-row items-center gap-3">
          <span className="badge" style={{ background: "#065F46", color: "#ECFDF5", fontSize: "0.74rem" }}>
            ● AXLE COUNTERS SYNCHRONIZED
          </span>
        </div>
      </div>

      {/* Absolute Block Section Occupancy Matrix */}
      <Panel
        title="Corridor Absolute Block Section Matrix"
        subtitle="Live verification of Block Exclusivity (HC-001) and Minimum Statutory Headway (HC-002)"
      >
        <BlockOccupancyMatrix
          sections={
            filterMode === "SINGLE_LINE"
              ? corridorSections.filter((s) => s.mode === "SINGLE")
              : corridorSections
          }
          blockOccupancy={
            filterMode === "OCCUPIED"
              ? blockOccupancies.filter((b) => !!b.occupied_by)
              : blockOccupancies
          }
          trains={corridorTrains}
        />
      </Panel>
    </div>
  );
}
