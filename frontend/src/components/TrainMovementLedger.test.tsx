import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TrainMovementLedger } from "./TrainMovementLedger";
import type { Train } from "../types";

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
    status: "AT_STATION",
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
    delay_min: 12,
    projected_delay_min: 12,
    scheduled_departure: "06:15",
    scheduled_arrival_next: "06:35",
    hold_until: null,
    waiting_reason: "Single line token clearance",
    total_wait_min: 5,
    route: ["VSN", "SRP", "MLG", "KRN", "NDL"],
    label: "SYNTHETIC",
  },
];

describe("TrainMovementLedger", () => {
  it("renders train movements with status and location", () => {
    render(<TrainMovementLedger trains={mockTrains} />);

    // Header & counters
    expect(screen.getByText(/Section Train Movement & Regulation Ledger/i)).toBeDefined();
    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.getByText("Karanpur Passenger")).toBeDefined();

    // Locations
    expect(screen.getByText("At Station MLG (PF P1)")).toBeDefined();
    expect(screen.getByText("In Block B3 (S3)")).toBeDefined();

    // Delays
    expect(screen.getByText("Right Time")).toBeDefined();
    expect(screen.getByText("+12 min")).toBeDefined();
  });

  it("filters trains by status (Running, Delayed)", () => {
    render(<TrainMovementLedger trains={mockTrains} />);

    // Click Delayed
    const delayedBtn = screen.getByRole("button", { name: /Delayed \(1\)/i });
    fireEvent.click(delayedBtn);

    expect(screen.getByText("Karanpur Passenger")).toBeDefined();
    expect(screen.queryByText("Nandpur Express")).toBeNull();
  });

  it("expands milestone progress when train row clicked", () => {
    render(<TrainMovementLedger trains={mockTrains} />);

    const row = screen.getByText("Nandpur Express");
    fireEvent.click(row);

    expect(screen.getByText(/Movement Progress & Station Milestones for #12625/i)).toBeDefined();
    expect(screen.getAllByText("MLG").length).toBeGreaterThan(0);
  });
});
