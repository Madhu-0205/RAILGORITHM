import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RestrictionsAndIncidentsPanel } from "./RestrictionsAndIncidentsPanel";
import type { Closure, PlatformOutage } from "../types";

const mockClosures: Closure[] = [
  {
    id: "cls-01",
    block_id: "B1",
    start_min: 360,
    end_min: 480,
    reason: "Track tamping machine block",
    created_by: "admin",
    created_at: "06:00 IST",
  },
];

const mockOutages: PlatformOutage[] = [
  {
    id: "out-01",
    station_id: "MLG",
    platform_id: "P3",
    start_min: 360,
    end_min: 480,
    reason: "Platform apron repair",
    created_by: "admin",
    created_at: "06:00 IST",
  },
];

describe("RestrictionsAndIncidentsPanel", () => {
  it("renders engineering restrictions table with caution orders", () => {
    render(<RestrictionsAndIncidentsPanel closures={mockClosures} outages={mockOutages} />);

    // Header & tabs
    expect(screen.getByText(/Operational Restrictions & Incident Management Workspace/i)).toBeDefined();
    expect(screen.getByText(/Engineering Restrictions/i)).toBeDefined();
    expect(screen.getByText(/Active Incidents/i)).toBeDefined();

    // Restrictions
    expect(screen.getByText("cls-01")).toBeDefined();
    expect(screen.getByText("out-01")).toBeDefined();
    expect(screen.getByText("PSR-01")).toBeDefined();
    expect(screen.getByText("TSR-14")).toBeDefined();
    expect(screen.getByText("45 km/h")).toBeDefined();
  });

  it("switches to Active Incidents tab and displays incident entries", () => {
    render(<RestrictionsAndIncidentsPanel closures={mockClosures} outages={mockOutages} />);

    const incTab = screen.getByRole("button", { name: /Active Incidents/i });
    fireEvent.click(incTab);

    expect(screen.getByText("INFRASTRUCTURE FAILURE")).toBeDefined();
    expect(screen.getByText("#INC-2026-081")).toBeDefined();
    expect(screen.getByText(/Axle counter reset required following brief transient pulse drop/i)).toBeDefined();
    expect(screen.getByText("UNUSUAL DETENTION")).toBeDefined();
  });
});
