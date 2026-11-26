import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { OperationalAttentionPanel } from "./OperationalAttentionPanel";
import type { Conflict } from "../types";

const mockConflicts: Conflict[] = [
  {
    id: "cnf-101",
    type: "HEADWAY_VIOLATION",
    severity: "CRITICAL",
    status: "OPEN",
    location: { kind: "SECTION", label: "Section S1 (NDL–KRN)" },
    trains: ["12625", "51831"],
    train_names: ["Nandpur Express", "Karanpur Passenger"],
    start_min: 370,
    start: "06:10",
    end_min: 385,
    end: "06:25",
    description: "Trailing train spacing < 4 min statutory block headway",
    evidence: {},
  },
  {
    id: "cnf-102",
    type: "PLATFORM_OCCUPANCY",
    severity: "HIGH",
    status: "OPEN",
    location: { kind: "PLATFORM", label: "Malgaon PF-1" },
    trains: ["12625"],
    train_names: ["Nandpur Express"],
    start_min: 390,
    start: "06:30",
    end_min: 405,
    end: "06:45",
    description: "Platform berth dwell exceeding turn-around threshold",
    evidence: {},
  },
];

describe("OperationalAttentionPanel", () => {
  it("renders prioritized operational alerts sorted by severity", () => {
    render(<OperationalAttentionPanel conflicts={mockConflicts} />);

    // Header & counters
    expect(screen.getByText(/Operational Attention & Triage Queue/i)).toBeDefined();
    expect(screen.getByText(/2 Unacknowledged/i)).toBeDefined();
    expect(screen.getByText(/● 1 Critical/i)).toBeDefined();
    expect(screen.getByText(/▲ 1 High/i)).toBeDefined();

    // Alert details
    expect(screen.getByText("HEADWAY VIOLATION")).toBeDefined();
    expect(screen.getByText("PLATFORM OCCUPANCY")).toBeDefined();
    expect(screen.getByText(/Trailing train spacing < 4 min statutory block headway/i)).toBeDefined();
  });

  it("filters alerts by severity", () => {
    render(<OperationalAttentionPanel conflicts={mockConflicts} />);

    // Filter Critical
    const critBtn = screen.getByRole("button", { name: /Critical \(1\)/i });
    fireEvent.click(critBtn);

    expect(screen.getByText("HEADWAY VIOLATION")).toBeDefined();
    expect(screen.queryByText("PLATFORM OCCUPANCY")).toBeNull();
  });

  it("acknowledges an alert when the operator clicks Acknowledge", () => {
    render(<OperationalAttentionPanel conflicts={mockConflicts} />);

    const ackBtn = screen.getByRole("button", { name: /Acknowledge alert cnf-101/i });
    fireEvent.click(ackBtn);

    expect(screen.getByText(/✓ Acknowledged/i)).toBeDefined();
  });
});
