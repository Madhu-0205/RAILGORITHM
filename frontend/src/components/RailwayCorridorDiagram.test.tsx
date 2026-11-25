import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RailwayCorridorDiagram } from "./RailwayCorridorDiagram";
import { StationPlatformBerths } from "./StationPlatformBerths";
import { HourlyMovementsChart } from "./HourlyMovementsChart";
import { DelayDistributionChart } from "./DelayDistributionChart";
import type { BlockOccupancy, Conflict, Station, Section, Train } from "../types";

const mockStations: Station[] = [
  { id: "NDL", name: "Nandpur", code: "NDL", platforms: ["1", "2"], x: 0, is_junction: false },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["1", "2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["1", "2", "3", "4"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["1", "2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["1", "2"], x: 100, is_junction: false },
];

const mockSections: Section[] = [
  {
    id: "NDL-KRN",
    from_station: "NDL",
    to_station: "KRN",
    mode: "DOUBLE",
    headway_min: 5,
    max_speed_kmph: 110,
    blocks: [{ id: "B1", direction: "UP", run_time_min: 8 }],
  },
  {
    id: "KRN-MLG",
    from_station: "KRN",
    to_station: "MLG",
    mode: "SINGLE",
    headway_min: 8,
    max_speed_kmph: 90,
    blocks: [{ id: "B2", direction: "BIDIRECTIONAL", run_time_min: 12 }],
  },
  {
    id: "MLG-SRP",
    from_station: "MLG",
    to_station: "SRP",
    mode: "SINGLE",
    headway_min: 8,
    max_speed_kmph: 90,
    blocks: [{ id: "B4", direction: "BIDIRECTIONAL", run_time_min: 12 }],
  },
  {
    id: "SRP-VSN",
    from_station: "SRP",
    to_station: "VSN",
    mode: "DOUBLE",
    headway_min: 5,
    max_speed_kmph: 110,
    blocks: [{ id: "B5", direction: "UP", run_time_min: 9 }],
  },
];

const mockBlockOccupancy: BlockOccupancy[] = [
  {
    block_id: "B1",
    section_id: "NDL-KRN",
    from_station: "NDL",
    to_station: "KRN",
    mode: "DOUBLE",
    direction: "UP",
    run_time_min: 8,
    headway_min: 5,
    occupied_by: "EXP-101",
    entry_min: 420,
    exit_min: 428,
    closure: null,
  },
  {
    block_id: "B2",
    section_id: "KRN-MLG",
    from_station: "KRN",
    to_station: "MLG",
    mode: "SINGLE",
    direction: "BIDIRECTIONAL",
    run_time_min: 12,
    headway_min: 8,
    occupied_by: null,
    entry_min: null,
    exit_min: null,
    closure: null,
  },
];

const mockTrains: Train[] = [
  {
    id: "EXP-101",
    name: "Rajdhani Express",
    train_type: "EXPRESS",
    priority: 1,
    effective_priority: 1,
    direction: "UP",
    origin: "NDL",
    destination: "VSN",
    status: "RUNNING",
    station_id: null,
    next_station: "KRN",
    section_id: "NDL-KRN",
    block_id: "B1",
    platform: null,
    delay_min: 0,
    projected_delay_min: 0,
    scheduled_departure: "07:00",
    scheduled_arrival_next: "07:08",
    hold_until: null,
    waiting_reason: null,
    total_wait_min: 0,
    route: ["NDL", "KRN", "MLG", "SRP", "VSN"],
    label: "EXP-101 (Rajdhani Express)",
  },
];

const mockConflicts: Conflict[] = [
  {
    id: "cnf-1",
    type: "HEADWAY",
    severity: "HIGH",
    status: "OPEN",
    location: { kind: "BLOCK", block_id: "B1", section_id: "NDL-KRN", label: "Block B1" },
    trains: ["EXP-101"],
    train_names: ["Rajdhani Express"],
    start_min: 425,
    start: "07:05",
    end_min: 435,
    end: "07:15",
    description: "Close headway in block B1",
    evidence: {},
  },
];

describe("RailwayCorridorDiagram", () => {
  it("renders all stations and sections in the corridor SVG", () => {
    render(
      <RailwayCorridorDiagram
        stations={mockStations}
        sections={mockSections}
        blockOccupancy={mockBlockOccupancy}
        trains={mockTrains}
        conflicts={mockConflicts}
      />,
    );

    expect(screen.getByRole("img", { name: /corridor diagram/i })).toBeInTheDocument();
    expect(screen.getByText("Nandpur")).toBeInTheDocument();
    expect(screen.getByText("Malgaon Junction")).toBeInTheDocument();
    expect(screen.getByText("Vasanthpur")).toBeInTheDocument();
    expect(screen.getByText(/EXP-101/)).toBeInTheDocument();
  });
});

describe("StationPlatformBerths", () => {
  it("renders platform slots with statuses and trains", () => {
    const slots = [
      { platform_id: "1", status: "OCCUPIED" as const, train_id: "EXP-101", description: "At PF 1" },
      { platform_id: "2", status: "AVAILABLE" as const, train_id: null, description: "Clear & Available" },
      { platform_id: "3", status: "OUTAGE" as const, train_id: null, description: "Track Circuit Maintenance" },
    ];
    render(<StationPlatformBerths stationName="Malgaon Junction" slots={slots} />);

    expect(screen.getByText("Platform 1")).toBeInTheDocument();
    expect(screen.getByText("OCCUPIED")).toBeInTheDocument();
    expect(screen.getByText(/EXP-101/)).toBeInTheDocument();
    expect(screen.getByText("Platform 2")).toBeInTheDocument();
    expect(screen.getByText("AVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("Platform 3")).toBeInTheDocument();
    expect(screen.getByText("OUTAGE")).toBeInTheDocument();
  });
});

describe("HourlyMovementsChart", () => {
  it("renders movement buckets with title and accessibility attributes", () => {
    const data = [
      { hour: "06:00", arrivals: 2, departures: 3 },
      { hour: "07:00", arrivals: 4, departures: 2 },
    ];
    render(<HourlyMovementsChart data={data} title="Hourly Train Movements" />);

    expect(screen.getByRole("img", { name: /Hourly Train Movements/i })).toBeInTheDocument();
    expect(screen.getByText("06:00")).toBeInTheDocument();
    expect(screen.getByText("07:00")).toBeInTheDocument();
  });
});

describe("DelayDistributionChart", () => {
  it("renders delay tiers with counts and percentages", () => {
    const tiers = [
      { tier: "On Time (≤5m)", count: 5, pct: 62.5, tone: "good" as const },
      { tier: "5-15 min", count: 2, pct: 25.0, tone: "watch" as const },
      { tier: ">15 min", count: 1, pct: 12.5, tone: "bad" as const },
    ];
    render(<DelayDistributionChart tiers={tiers} title="Train Delay Distribution" />);

    expect(screen.getByRole("img", { name: /Train Delay Distribution/i })).toBeInTheDocument();
    expect(screen.getByText(/On Time \(≤5m\)/)).toBeInTheDocument();
    expect(screen.getByText("62.5%")).toBeInTheDocument();
  });
});
