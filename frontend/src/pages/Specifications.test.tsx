import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SpecificationsPage } from "./Specifications";
import { api } from "../api";

vi.mock("../api", () => ({
  api: {
    assumptions: vi.fn(),
    constraints: vi.fn(),
    systemVersions: vi.fn(),
  },
}));

describe("SpecificationsPage", () => {
  it("renders assumptions, constraints, and system versions", async () => {
    vi.mocked(api.assumptions).mockResolvedValue({
      version: "assumptions-2.0.0",
      label: "SYNTHETIC",
      disclaimer: "Configured synthetic assumption — not verified Indian Railways rules.",
      assumptions: [
        {
          id: "NET-001",
          category: "network",
          title: "Synthetic linear section",
          value: "5 stations, 4 sections",
          unit: "topology",
          source: "Configured synthetic assumption",
          configurable_via: null,
          affects: ["routing", "block occupancy"],
        },
      ],
    });

    vi.mocked(api.constraints).mockResolvedValue({
      version: "constraints-2.0.0",
      label: "SYNTHETIC",
      disclaimer: "Independent constraint specification.",
      counts: { hard: 13, soft: 4 },
      constraints: [
        {
          id: "HC-001",
          name: "Block Exclusivity",
          kind: "HARD",
          scope: "BLOCK",
          statement: "At most one train may occupy a block at any time.",
          enforced_by: ["Simulation engine", "Independent validator", "CP-SAT cumulative"],
          assumption_ids: ["NET-001"],
          failure_effect: "Imminent collision hazard.",
        },
      ],
    });

    vi.mocked(api.systemVersions).mockResolvedValue({
      simulation_model: "simulation-2.0.0",
      assumptions: "assumptions-2.0.0",
      constraints: "constraints-2.0.0",
      optimizer: "cpsat-2.0.0",
      validator: "validator-2.0.0",
      label: "SYNTHETIC",
    });

    render(<SpecificationsPage />);

    expect(await screen.findByText("Assumptions & constraints")).toBeInTheDocument();
    expect(screen.getAllByText("assumptions-2.0.0").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("constraints-2.0.0").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("NET-001")).toBeInTheDocument();
    expect(screen.getByText("HC-001")).toBeInTheDocument();
    expect(screen.getByText("Block Exclusivity")).toBeInTheDocument();
  });
});
