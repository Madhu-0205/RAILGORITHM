import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StationWorkingDiagram } from "./StationWorkingDiagram";
import type { Platform, PlatformOutage, Station, Train } from "../types";

const mockStation: Station = {
  id: "MLG",
  name: "Malgaon Junction",
  code: "MLG",
  platforms: ["P1", "P2", "P3"],
  x: 50,
  is_junction: true,
};

const mockPlatforms: Platform[] = [
  { station_id: "MLG", platform_id: "P1", occupied_by: "12625", outage: null, status: "OCCUPIED" },
  { station_id: "MLG", platform_id: "P2", occupied_by: null, outage: null, status: "AVAILABLE" },
  {
    station_id: "MLG",
    platform_id: "P3",
    occupied_by: null,
    outage: {
      id: "out-1",
      station_id: "MLG",
      platform_id: "P3",
      start_min: 360,
      end_min: 480,
      reason: "Track maintenance",
      created_by: "admin",
      created_at: "2026-11-25T06:00:00Z",
    },
    status: "OUTAGE",
  },
];

const mockOutages: PlatformOutage[] = [
  {
    id: "out-1",
    station_id: "MLG",
    platform_id: "P3",
    start_min: 360,
    end_min: 480,
    reason: "Track maintenance",
    created_by: "admin",
    created_at: "2026-11-25T06:00:00Z",
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
    status: "BERTHED",
    station_id: "MLG",
    next_station: "SRP",
    section_id: null,
    block_id: null,
    platform: "P1",
    delay_min: 0,
    projected_delay_min: 0,
    scheduled_departure: "06:30",
    scheduled_arrival_next: "06:45",
    hold_until: null,
    waiting_reason: null,
    total_wait_min: 0,
    route: ["NDL", "KRN", "MLG", "SRP", "VSN"],
    label: "SYNTHETIC",
  },
];

describe("StationWorkingDiagram", () => {
  it("renders station yard schematic with platforms and diamond throat", () => {
    render(
      <StationWorkingDiagram
        station={mockStation}
        platforms={mockPlatforms}
        outages={mockOutages}
        trains={mockTrains}
      />
    );

    // Header and station code
    expect(screen.getByText("MLG")).toBeDefined();
    expect(screen.getByText(/Malgaon Junction Station Yard Layout/i)).toBeDefined();

    // Platforms and lines
    expect(screen.getAllByText(/Platform 1 \(Up Loop\)/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Up Main Line \(Through Line\)/i)).toBeDefined();
    expect(screen.getByText(/Platform 2 \(Down Main \/ Platform Line\)/i)).toBeDefined();
    expect(screen.getByText(/Platform 3 \(Down Loop\)/i)).toBeDefined();

    // Diamond throat indicator for junction station
    expect(screen.getByText(/Diamond Crossing Throat \(Cap 2\)/i)).toBeDefined();
  });

  it("handles track selection and shows inspection details", () => {
    const onSelect = vi.fn();
    render(
      <StationWorkingDiagram
        station={mockStation}
        platforms={mockPlatforms}
        outages={mockOutages}
        trains={mockTrains}
        onSelectTrack={onSelect}
      />
    );

    // Initial inspection panel shows Platform 1
    expect(screen.getByText(/Track Inspection: Platform 1 \(Up Loop\)/i)).toBeDefined();
    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.getByText(/Train No: 12625/i)).toBeDefined();

    // Click Platform 2 line
    const p2Track = screen.getByText(/Platform 2 \(Down Main \/ Platform Line\)/i);
    fireEvent.click(p2Track);
    expect(onSelect).toHaveBeenCalledWith("MLG-P2");
    expect(screen.getByText(/Track Inspection: Platform 2 \(Down Main \/ Platform Line\)/i)).toBeDefined();
  });
});
