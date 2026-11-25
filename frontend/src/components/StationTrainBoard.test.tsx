import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StationTrainBoard } from "./StationTrainBoard";
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
    delay_min: 8,
    projected_delay_min: 8,
    scheduled_departure: "06:15",
    scheduled_arrival_next: "06:35",
    hold_until: null,
    waiting_reason: "Awaiting single line token",
    total_wait_min: 5,
    route: ["VSN", "SRP", "MLG", "KRN", "NDL"],
    label: "SYNTHETIC",
  },
];

describe("StationTrainBoard", () => {
  it("renders station train board with arrival/departure information", () => {
    render(
      <StationTrainBoard
        stationId="MLG"
        stationName="Malgaon Junction"
        trains={mockTrains}
      />
    );

    // Header
    expect(screen.getByText(/Malgaon Junction Operational Train Board/i)).toBeDefined();

    // Berthed train
    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.getByText("PF P1")).toBeDefined();
    expect(screen.getByText("BERTHED")).toBeDefined();
    expect(screen.getByText("Right Time")).toBeDefined();

    // Approaching train
    expect(screen.getByText("Karanpur Passenger")).toBeDefined();
    expect(screen.getByText("APPROACHING")).toBeDefined();
    expect(screen.getByText("+8 min")).toBeDefined();
  });

  it("filters trains by status tabs", () => {
    render(
      <StationTrainBoard
        stationId="MLG"
        stationName="Malgaon Junction"
        trains={mockTrains}
      />
    );

    // Click "At Platform"
    const atPlatformTab = screen.getByRole("button", { name: /At Platform/i });
    fireEvent.click(atPlatformTab);

    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.queryByText("Karanpur Passenger")).toBeNull();

    // Click "Approaching"
    const approachingTab = screen.getByRole("button", { name: /Approaching/i });
    fireEvent.click(approachingTab);

    expect(screen.getByText("Karanpur Passenger")).toBeDefined();
    expect(screen.queryByText("Nandpur Express")).toBeNull();
  });

  it("filters trains by direction", () => {
    render(
      <StationTrainBoard
        stationId="MLG"
        stationName="Malgaon Junction"
        trains={mockTrains}
      />
    );

    const dirSelect = screen.getByRole("combobox", { name: /Filter by train direction/i });
    fireEvent.change(dirSelect, { target: { value: "UP" } });

    expect(screen.getByText("Nandpur Express")).toBeDefined();
    expect(screen.queryByText("Karanpur Passenger")).toBeNull();
  });

  it("searches trains by name", () => {
    render(
      <StationTrainBoard
        stationId="MLG"
        stationName="Malgaon Junction"
        trains={mockTrains}
      />
    );

    const searchInput = screen.getByRole("searchbox", { name: /Search trains by number or name/i });
    fireEvent.change(searchInput, { target: { value: "Karanpur" } });

    expect(screen.getByText("Karanpur Passenger")).toBeDefined();
    expect(screen.queryByText("Nandpur Express")).toBeNull();
  });

  it("calls onSelectTrain when a row is clicked", () => {
    const onSelect = vi.fn();
    render(
      <StationTrainBoard
        stationId="MLG"
        stationName="Malgaon Junction"
        trains={mockTrains}
        onSelectTrain={onSelect}
      />
    );

    const row = screen.getByText("Nandpur Express");
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith("12625");
  });
});
