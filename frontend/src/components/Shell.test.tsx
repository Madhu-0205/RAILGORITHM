import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Shell } from "./Shell";

const authState: {
  user: {
    id: string;
    username: string;
    role: string;
    display_name: string;
    station_id: string | null;
    section_id: string | null;
  };
  initialising: boolean;
  login: () => void;
  logout: () => void;
} = {
  user: {
    id: "u1",
    username: "section.master",
    role: "SECTION_MASTER",
    display_name: "Section Controller",
    station_id: null,
    section_id: "NDL-KRN-MLG-SRP-VSN",
  },
  initialising: false,
  login: vi.fn(),
  logout: vi.fn(),
};

vi.mock("../auth", () => ({
  useAuth: () => authState,
}));

vi.mock("../simulation", () => ({
  useSimulation: () => ({
    simulations: [
      {
        id: "sim-1",
        name: "Single line meet",
        scenario_key: "single_line_meet",
        status: "RUNNING",
        sim_time_min: 390,
        state_version: 3,
        seed: 20260301,
        label: "SYNTHETIC",
        created_at: "2026-03-01T00:00:00",
        created_by: "section.master",
      },
    ],
    selected: {
      id: "sim-1",
      name: "Single line meet",
      scenario_key: "single_line_meet",
      status: "RUNNING",
      sim_time_min: 390,
      state_version: 3,
      seed: 20260301,
      label: "SYNTHETIC",
      created_at: "2026-03-01T00:00:00",
      created_by: "section.master",
    },
    selectedId: "sim-1",
    scenarios: [],
    loading: false,
    error: null,
    revision: 0,
    select: vi.fn(),
    refresh: vi.fn(),
    create: vi.fn(),
  }),
}));

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("Shell", () => {
  it("shows the synthetic-data banner and simulation context", () => {
    renderShell();
    expect(screen.getByRole("note")).toHaveTextContent(/SYNTHETIC DATA/i);
    expect(screen.getByText("06:30")).toBeInTheDocument();
    expect(screen.getByText(/version 3/)).toBeInTheDocument();
  });

  it("shows every navigation item for a Section Master", () => {
    renderShell();
    for (const label of [
      "Dashboard",
      "Train Movements",
      "Railway Network",
      "Conflict Detection",
      "AI Recommendations",
      "Disruption Management",
      "What-if Simulation",
      "Analytics",
      "Audit Trail",
    ]) {
      expect(screen.getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });

  it("renders the nested route content", () => {
    renderShell();
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });

  it("hides section-only screens from a Station Master", () => {
    const original = authState.user;
    authState.user = {
      id: "u2",
      username: "station.master",
      role: "STATION_MASTER",
      display_name: "Station Controller",
      station_id: "MLG",
      section_id: null,
    };
    try {
      renderShell();
      expect(screen.queryByText("Disruption Management")).not.toBeInTheDocument();
      expect(screen.queryByText("Audit Trail")).not.toBeInTheDocument();
      expect(screen.getByText("Train Movements")).toBeInTheDocument();
      expect(screen.queryByText("New simulation")).not.toBeInTheDocument();
      expect(screen.getByText(/Scope: station MLG/)).toBeInTheDocument();
    } finally {
      authState.user = original;
    }
  });
});
