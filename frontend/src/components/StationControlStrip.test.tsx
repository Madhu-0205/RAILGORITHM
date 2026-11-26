import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StationControlStrip } from "./StationControlStrip";
import type { Closure, Conflict, Platform, PlatformOutage, Station, Train } from "../types";

const mockStations: Station[] = [
  { id: "NDL", name: "Nandpur Junction", code: "NDL", platforms: ["P1", "P2", "P3"], x: 0, is_junction: true },
  { id: "KRN", name: "Karanpur", code: "KRN", platforms: ["P1", "P2"], x: 25, is_junction: false },
  { id: "MLG", name: "Malgaon Junction", code: "MLG", platforms: ["P1", "P2", "P3"], x: 50, is_junction: true },
  { id: "SRP", name: "Suryapur", code: "SRP", platforms: ["P1", "P2"], x: 75, is_junction: false },
  { id: "VSN", name: "Vasanthpur", code: "VSN", platforms: ["P1", "P2"], x: 100, is_junction: false },
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
  {
    id: "51831",
    name: "Karanpur Passenger",
    train_type: "PASSENGER",
    priority: 3,
    effective_priority: 3,
    direction: "DOWN",
    origin: "VSN",
    destination: "NDL",
    status: "RUNNING",
    station_id: null,
    next_station: "MLG",
    section_id: "S3",
    block_id: "B3",
    platform: null,
    delay_min: 10,
    projected_delay_min: 10,
    scheduled_departure: "06:15",
    scheduled_arrival_next: "06:35",
    hold_until: null,
    waiting_reason: "Single line token wait",
    total_wait_min: 5,
    route: ["VSN", "SRP", "MLG", "KRN", "NDL"],
    label: "SYNTHETIC",
  },
];

const mockPlatforms: Platform[] = [
  { station_id: "MLG", platform_id: "P1", occupied_by: "12625", outage: null, status: "OCCUPIED" },
  { station_id: "MLG", platform_id: "P2", occupied_by: null, outage: null, status: "AVAILABLE" },
  { station_id: "MLG", platform_id: "P3", occupied_by: null, outage: null, status: "AVAILABLE" },
];

const mockOutages: PlatformOutage[] = [];
const mockConflicts: Conflict[] = [];
const mockClosures: Closure[] = [];

describe("StationControlStrip", () => {
  it("renders all configured stations dynamically", () => {
    render(
      <StationControlStrip
        stations={mockStations}
        trains={mockTrains}
        platforms={mockPlatforms}
        outages={mockOutages}
        conflicts={mockConflicts}
        closures={mockClosures}
      />
    );

    // Title & count
    expect(screen.getByText(/Multi-Station Territory Operational Strip/i)).toBeDefined();
    expect(screen.getByText(/5 Configured Stations/i)).toBeDefined();

    // Stations
    expect(screen.getByText("NDL")).toBeDefined();
    expect(screen.getByText("KRN")).toBeDefined();
    expect(screen.getByText("MLG")).toBeDefined();
    expect(screen.getByText("SRP")).toBeDefined();
    expect(screen.getByText("VSN")).toBeDefined();

    // Junction badges
    expect(screen.getAllByText("JUNCTION").length).toBe(2); // NDL & MLG
  });

  it("accurately calculates approaching and berthed trains per station", () => {
    render(
      <StationControlStrip
        stations={mockStations}
        trains={mockTrains}
        platforms={mockPlatforms}
        outages={mockOutages}
        conflicts={mockConflicts}
        closures={mockClosures}
      />
    );

    // MLG should have 1 berthed (12625) and 1 approaching (51831)
    const mlgCard = screen.getByRole("button", { name: /Inspect Malgaon Junction \(MLG\) station working/i });
    expect(mlgCard).toBeDefined();
    expect(mlgCard.textContent).toContain("Approaching: 1");
    expect(mlgCard.textContent).toContain("Berthed: 1");
    expect(mlgCard.textContent).toContain("Berthed: #12625");
  });

  it("calls onSelectStation when a station card is clicked", () => {
    const onSelect = vi.fn();
    render(
      <StationControlStrip
        stations={mockStations}
        trains={mockTrains}
        platforms={mockPlatforms}
        outages={mockOutages}
        conflicts={mockConflicts}
        closures={mockClosures}
        onSelectStation={onSelect}
      />
    );

    const krnCard = screen.getByRole("button", { name: /Inspect Karanpur \(KRN\) station working/i });
    fireEvent.click(krnCard);
    expect(onSelect).toHaveBeenCalledWith("KRN");
  });
});
