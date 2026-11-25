import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ConflictRegulationWorkspace } from "./ConflictRegulationWorkspace";
import type { Conflict } from "../types";

const mockConflicts: Conflict[] = [
  {
    id: "cnf-201",
    type: "HEADWAY_VIOLATION",
    severity: "HIGH",
    status: "OPEN",
    location: { kind: "SECTION", label: "Section S1 (NDL–KRN)" },
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

const mockDecisions = [
  {
    id: "rec-101",
    label: "Hold Freight 701 on Karanpur Loop Line",
    affected_stations: ["KRN", "MLG"],
    disagreement: true,
    created_at: "06:20 IST",
  },
];

describe("ConflictRegulationWorkspace", () => {
  it("renders active conflicts table and tabs", () => {
    render(
      <MemoryRouter>
        <ConflictRegulationWorkspace
          conflicts={mockConflicts}
          pendingDecisions={mockDecisions}
        />
      </MemoryRouter>
    );

    // Header & tabs
    expect(screen.getByText(/Crossing, Precedence & Train Regulation Workspace/i)).toBeDefined();
    expect(screen.getByText(/Active Route Conflicts \(1\)/i)).toBeDefined();
    expect(screen.getByText(/AI Regulation Alternatives \(1\)/i)).toBeDefined();

    // Table content
    expect(screen.getByText("cnf-201")).toBeDefined();
    expect(screen.getByText("HEADWAY VIOLATION")).toBeDefined();
  });

  it("switches to AI Regulation Alternatives tab and displays candidate options", () => {
    render(
      <MemoryRouter>
        <ConflictRegulationWorkspace
          conflicts={mockConflicts}
          pendingDecisions={mockDecisions}
        />
      </MemoryRouter>
    );

    const aiTab = screen.getByRole("button", { name: /AI Regulation Alternatives/i });
    fireEvent.click(aiTab);

    expect(screen.getByText("Hold Freight 701 on Karanpur Loop Line")).toBeDefined();
    expect(screen.getByText("MODEL DISAGREEMENT")).toBeDefined();
    expect(screen.getByText("OPTIMAL (Feasible Schedule)")).toBeDefined();
    expect(screen.getByText("PASS (Hard Constraints Verified)")).toBeDefined();
  });

  it("switches to Meets & Precedence tab", () => {
    render(
      <MemoryRouter>
        <ConflictRegulationWorkspace
          conflicts={mockConflicts}
          pendingDecisions={mockDecisions}
        />
      </MemoryRouter>
    );

    const meetsTab = screen.getByRole("button", { name: /Meets & Precedence/i });
    fireEvent.click(meetsTab);

    expect(screen.getByText(/Single-line crossing meets/i)).toBeDefined();
  });
});
