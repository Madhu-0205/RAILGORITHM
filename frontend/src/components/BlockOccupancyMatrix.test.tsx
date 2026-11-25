import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BlockOccupancyMatrix } from "./BlockOccupancyMatrix";
import type { BlockOccupancy, Section, Train } from "../types";

const mockSections: Section[] = [
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
];

const mockBlockOccupancy: BlockOccupancy[] = [
  {
    block_id: "B1",
    section_id: "S1",
    from_station: "NDL",
    to_station: "KRN",
    mode: "SINGLE",
    direction: "BIDIRECTIONAL",
    run_time_min: 12,
    headway_min: 4,
    occupied_by: "12625",
    entry_min: 360,
    exit_min: 372,
    closure: null,
  },
  {
    block_id: "B2U",
    section_id: "S2",
    from_station: "KRN",
    to_station: "MLG",
    mode: "DOUBLE",
    direction: "UP",
    run_time_min: 10,
    headway_min: 3,
    occupied_by: null,
    entry_min: null,
    exit_min: null,
    closure: null,
  },
  {
    block_id: "B2D",
    section_id: "S2",
    from_station: "KRN",
    to_station: "MLG",
    mode: "DOUBLE",
    direction: "DOWN",
    run_time_min: 10,
    headway_min: 3,
    occupied_by: null,
    entry_min: null,
    exit_min: null,
    closure: {
      id: "cls-1",
      block_id: "B2D",
      start_min: 360,
      end_min: 480,
      reason: "Track Maintenance",
      created_by: "admin",
      created_at: "2026-11-25T06:00:00Z",
    },
  },
];

const mockTrains: Train[] = [
  {
    id: "12625",
    name: "Nandpur Express",
    train_type: "EXPRESS",
    priority: 1,
    effective_priority: 1,
    direction: "UP",
    origin: "NDL",
    destination: "VSN",
    status: "RUNNING",
    station_id: null,
    next_station: "KRN",
    section_id: "S1",
    block_id: "B1",
    platform: null,
    delay_min: 0,
    projected_delay_min: 0,
    scheduled_departure: "06:00",
    scheduled_arrival_next: "06:12",
    hold_until: null,
    waiting_reason: null,
    total_wait_min: 0,
    route: ["NDL", "KRN", "MLG", "SRP", "VSN"],
    label: "SYNTHETIC",
  },
];

describe("BlockOccupancyMatrix", () => {
  it("renders block sections with states and stats counters", () => {
    render(
      <BlockOccupancyMatrix
        sections={mockSections}
        blockOccupancy={mockBlockOccupancy}
        trains={mockTrains}
      />
    );

    // Header & counters
    expect(screen.getByText(/Corridor Block Section Occupancy Matrix/i)).toBeDefined();
    expect(screen.getByText(/3 Total Blocks/i)).toBeDefined();

    // Table rows
    expect(screen.getByText("B1")).toBeDefined();
    expect(screen.getByText("B2U")).toBeDefined();
    expect(screen.getByText("B2D")).toBeDefined();

    // States
    expect(screen.getByText("TRAIN ON LINE")).toBeDefined();
    expect(screen.getByText("LINE CLEAR")).toBeDefined();
    expect(screen.getByText("LINE CLOSED")).toBeDefined();

    // Occupying train
    expect(screen.getByText("Nandpur Express")).toBeDefined();
  });

  it("filters by Occupied Only and Single-Line Bottlenecks", () => {
    render(
      <BlockOccupancyMatrix
        sections={mockSections}
        blockOccupancy={mockBlockOccupancy}
        trains={mockTrains}
      />
    );

    // Click Occupied Only
    const occupiedBtn = screen.getByRole("button", { name: /Occupied Only/i });
    fireEvent.click(occupiedBtn);
    expect(screen.getByText("B1")).toBeDefined();
    expect(screen.queryByText("B2U")).toBeNull();

    // Click Bottlenecks
    const bottleneckBtn = screen.getByRole("button", { name: /Single-Line Bottlenecks/i });
    fireEvent.click(bottleneckBtn);
    expect(screen.getByText("B1")).toBeDefined();
    expect(screen.queryByText("B2U")).toBeNull();
  });

  it("searches blocks by train or section name", () => {
    render(
      <BlockOccupancyMatrix
        sections={mockSections}
        blockOccupancy={mockBlockOccupancy}
        trains={mockTrains}
      />
    );

    const searchInput = screen.getByRole("searchbox", { name: /Search block sections/i });
    fireEvent.change(searchInput, { target: { value: "Nandpur" } });

    expect(screen.getByText("B1")).toBeDefined();
    expect(screen.queryByText("B2U")).toBeNull();
  });

  it("triggers onSelectBlock callback when row clicked", () => {
    const onSelect = vi.fn();
    render(
      <BlockOccupancyMatrix
        sections={mockSections}
        blockOccupancy={mockBlockOccupancy}
        trains={mockTrains}
        onSelectBlock={onSelect}
      />
    );

    const row = screen.getByText("B1");
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith("B1");
  });
});
