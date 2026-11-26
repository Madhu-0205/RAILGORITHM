import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TimeDistanceGraph } from "./TimeDistanceGraph";
import type { Conflict, Section, Station, Train } from "../types";

const mockStations: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["P1", "P2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
];

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
  {
    id: "12626",
    name: "Nandpur Express Down",
    train_type: "EXPRESS",
    priority: 1,
    effective_priority: 1,
    direction: "DOWN",
    origin: "VSN",
    destination: "NDL",
    status: "RUNNING",
    station_id: null,
    next_station: "SRP",
    section_id: "S4",
    block_id: "B4D",
    platform: null,
    delay_min: 6,
    projected_delay_min: 6,
    scheduled_departure: "06:04",
    scheduled_arrival_next: "06:13",
    hold_until: null,
    waiting_reason: null,
    total_wait_min: 0,
    route: ["VSN", "SRP", "MLG", "KRN", "NDL"],
    label: "SYNTHETIC",
  },
];

const mockConflicts: Conflict[] = [
  {
    id: "c-1",
    type: "HEADWAY_VIOLATION",
    severity: "HIGH",
    status: "ACTIVE",
    location: {
      kind: "SECTION",
      section_id: "S1",
      station_id: "NDL",
      label: "Section S1 (NDL–KRN)",
    },
    trains: ["12625"],
    train_names: ["Nandpur Express"],
    start_min: 370,
    start: "06:10",
    end_min: 385,
    end: "06:25",
    description: "Headway violation in block B1",
    evidence: {},
  },
];

describe("TimeDistanceGraph", () => {
  it("renders SVG master graph with station chainages and time axis", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
        simTimeMin={384}
        simTimeString="06:24"
      />
    );

    // SVG title / label
    expect(screen.getByRole("img", { name: /Time-Distance Train Graph/i })).toBeDefined();

    // Stations
    expect(screen.getAllByText(/NDL/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/MLG/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/VSN/i).length).toBeGreaterThan(0);

    // Single line annotations
    expect(screen.getByText(/SINGLE LINE: S1 \(NDL–KRN\)/i)).toBeDefined();

    // Simulation time cursor
    expect(screen.getByText(/06:24 IST/i)).toBeDefined();
  });

  it("filters trajectories by direction (UP and DOWN)", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
        simTimeMin={384}
        simTimeString="06:24"
      />
    );

    const upButton = screen.getByRole("button", { name: /UP \(NDL → VSN\)/i });
    fireEvent.click(upButton);
    expect(upButton.className).toContain("button-primary");

    const downButton = screen.getByRole("button", { name: /DOWN \(VSN → NDL\)/i });
    fireEvent.click(downButton);
    expect(downButton.className).toContain("button-primary");
  });

  it("toggles accessible data table view", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
      />
    );

    const toggleButton = screen.getByRole("button", { name: /View Accessible Table/i });
    fireEvent.click(toggleButton);

    // Table view displayed
    expect(screen.getByRole("region", { name: /Time-Distance train trajectories data table/i })).toBeDefined();
    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.getByText("Nandpur Express Down")).toBeDefined();

    // Toggle back to graph
    fireEvent.click(screen.getByRole("button", { name: /View Graph Chart/i }));
    expect(screen.getByRole("img", { name: /Time-Distance Train Graph/i })).toBeDefined();
  });

  it("calls onSelectTrain when trajectory clicked", () => {
    const onSelect = vi.fn();
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
        onSelectTrain={onSelect}
      />
    );

    const trainLabel = screen.getByText(/12625/i);
    fireEvent.click(trainLabel);
    expect(onSelect).toHaveBeenCalledWith("12625");
  });

  it("supports category filtering and time panning controls", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
      />
    );

    // Filter by Category
    const catSelect = screen.getByRole("combobox", { name: /Filter by train category/i });
    fireEvent.change(catSelect, { target: { value: "EXPRESS" } });
    expect(catSelect).toHaveValue("EXPRESS");

    // Pan buttons
    const panBackBtn = screen.getByRole("button", { name: /◀ -30m/i });
    fireEvent.click(panBackBtn);

    const centerBtn = screen.getByRole("button", { name: /Center Now ⏱/i });
    fireEvent.click(centerBtn);
  });

  it("supports station filtering and train search input", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
      />
    );

    // Station filter
    const stationSelect = screen.getByRole("combobox", { name: /Filter by station/i });
    fireEvent.change(stationSelect, { target: { value: "MLG" } });
    expect(stationSelect).toHaveValue("MLG");

    // Train search
    const searchInput = screen.getByRole("textbox", { name: /Search specific train/i });
    fireEvent.change(searchInput, { target: { value: "12625" } });
    expect(searchInput).toHaveValue("12625");
  });

  it("supports time window duration and filter reset", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
      />
    );

    // Click 6h duration
    const btn6h = screen.getByRole("button", { name: "6h" });
    fireEvent.click(btn6h);
    expect(btn6h.className).toContain("button-primary");

    // Click reset
    const resetBtn = screen.getByRole("button", { name: /↺ Reset/i });
    fireEvent.click(resetBtn);

    // Default window duration (3h) restored
    const btn3h = screen.getByRole("button", { name: "3h" });
    expect(btn3h.className).toContain("button-primary");
  });

  it("toggles operational overlays panel and display flags", () => {
    render(
      <TimeDistanceGraph
        stations={mockStations}
        sections={mockSections}
        trains={mockTrains}
        conflicts={mockConflicts}
      />
    );

    // Toggle overlays panel
    const overlayToggle = screen.getByRole("button", { name: /Overlays/i });
    fireEvent.click(overlayToggle);

    // Checkboxes are displayed
    expect(screen.getByText(/Speed Restrictions \(TSR\/PSR\)/i)).toBeDefined();
    expect(screen.getByText(/Crossing Points/i)).toBeDefined();
    expect(screen.getByText(/Station Dwell/i)).toBeDefined();
  });
});
