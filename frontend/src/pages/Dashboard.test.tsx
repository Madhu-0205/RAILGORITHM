import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { DashboardPage } from "./Dashboard";
import type { Dashboard, SectionControllerKpis, StationMasterKpis } from "../types";

const mockSimulation = {
  id: "sim-100",
  name: "Morning Corridor Peak",
  scenario_key: "morning_peak",
  status: "RUNNING" as const,
  sim_time_min: 420,
  sim_time: "07:00",
  state_version: 4,
  seed: 20260301,
  label: "SYNTHETIC" as const,
  created_at: "2026-03-01T07:00:00",
  created_by: "section.master",
};

const mockDashboardData: Dashboard = {
  simulation: {
    ...mockSimulation,
    scenario_date: "2026-03-01",
    timezone: "Asia/Kolkata",
  },
  metrics: {
    sim_time_min: 420,
    sim_time: "07:00",
    trains_total: 6,
    trains_active: 4,
    trains_completed: 2,
    trains_delayed: 1,
    total_delay_min: 26.0,
    average_delay_min: 6.5,
    average_completed_delay_min: 5.0,
    max_delay_min: 15.0,
    on_time_arrivals: 5,
    on_time_performance_pct: 83.3,
    throughput_trains_per_hour: 4.0,
    section_utilization_pct: 45.0,
    platform_utilization_pct: 50.0,
    waiting_min_total: 12.0,
    label: "SYNTHETIC",
  },
  conflicts: [],
  conflict_count: 0,
  trains: [],
  active_trains: [],
  delayed_trains: [],
  occupied_blocks: [],
  available_platforms: [],
  closures: [],
  platform_outages: [],
  active_closures: [],
  upcoming_closures: [],
  active_outages: [],
  pending_recommendations: [],
  pending_recommendation_count: 0,
  model_status: {
    ppo: { trained: true, status: "READY", model_version: "v2.2" },
    cpsat: { version: "9.9", status: "READY" },
  },
  data_label: "SYNTHETIC",
  role_scope: { role: "SECTION_MASTER", station_id: null, section_id: "NDL-KRN-MLG-SRP-VSN" },
};

const mockSectionKpis: SectionControllerKpis = {
  simulation_time: "07:00",
  sim_time_min: 420,
  time_period: "06:00 - 07:00 IST (Rolling 60m)",
  data_freshness: {
    status: "HEALTHY",
    freshness_seconds: 4.2,
    is_stale: false,
    last_heartbeat_at: "2026-03-01T07:00:00Z",
    error_rate_pct: 0.0,
  },
  kpis: {
    trains_active: 4,
    trains_completed: 2,
    trains_scheduled: 3,
    trains_delayed: 1,
    average_section_delay_min: 5.8,
    total_section_delay_min: 23.2,
    block_occupancy_pct: 37.5,
    blocks_occupied: 3,
    blocks_total: 8,
    junction_throat_load_pct: 66.7,
    junction_queue_length: 1,
    junction_congestion_level: "MODERATE",
    throughput_trains_per_hour: 4.0,
    on_time_performance_pct: 75.0,
    delay_propagation_index: 0.35,
    secondary_delay_min: 8.0,
    knock_on_risk_level: "LOW",
    conflicts_total: 1,
    conflicts_critical: 1,
    conflicts_major: 0,
    conflicts_minor: 0,
    pending_decisions_count: 2,
    recovery_clearance_rate_pct: 75.0,
  },
  junction_status: {
    junction_id: "MLG",
    junction_name: "Malgaon Junction",
    throat_capacity: 2,
    active_transits: 1,
    transiting_trains: ["EXP-101"],
    congestion_level: "MODERATE",
  },
  occupied_bottlenecks: [
    {
      block_id: "B1",
      train_id: "EXP-101",
    },
  ],
  severity_breakdown: {
    CRITICAL: 1,
    MAJOR: 0,
    MINOR: 0,
  },
  active_conflicts: [
    {
      id: "cnf-1",
      type: "HEADWAY",
      severity: "HIGH",
      status: "OPEN",
      location: { kind: "BLOCK", label: "NDL-KRN Block 1" },
      trains: ["T101", "T102"],
      train_names: ["Express", "Freight"],
      start_min: 430,
      start: "07:10",
      end_min: 442,
      end: "07:22",
      description: "Insufficient headway between Express and Freight",
      evidence: {},
    },
  ],
  pending_decisions: [
    {
      id: "rec-1",
      label: "Hold Freight 501 at Karanpur",
      affected_stations: ["KRN", "MLG"],
      disagreement: true,
      created_at: "2026-03-01T07:00:00Z",
    },
  ],
  kpi_definitions: {
    "Delay Propagation Index (DPI)": "Secondary Delay Minutes / Initial Schedule Delay Minutes",
  },
};

const mockStationKpis: StationMasterKpis = {
  station_id: "MLG",
  station_name: "Malgaon Junction",
  simulation_time: "07:00",
  sim_time_min: 420,
  time_period: "06:00 - 07:00 IST (Rolling 60m)",
  data_freshness: {
    status: "HEALTHY",
    freshness_seconds: 4.2,
    is_stale: false,
    last_heartbeat_at: "2026-03-01T07:00:00Z",
  },
  kpis: {
    trains_monitored: 3,
    on_time_trains: 2,
    delayed_trains: 1,
    schedule_adherence_pct: 66.7,
    average_arrival_delay_min: 4.2,
    average_departure_delay_min: 3.5,
    platform_availability_pct: 50.0,
    platforms_total: 4,
    platforms_available: 2,
    platforms_occupied: 2,
    platforms_outage: 0,
    pending_recommendations_count: 1,
    operational_alerts_count: 1,
  },
  platform_slots: [
    { platform_id: "PF-1", status: "OCCUPIED", train_id: "T101", description: "Occupied by Express" },
    { platform_id: "PF-2", status: "OCCUPIED", train_id: "T102", description: "Occupied by Freight" },
    { platform_id: "PF-3", status: "AVAILABLE", train_id: null, description: "Clear and Signalled" },
    { platform_id: "PF-4", status: "AVAILABLE", train_id: null, description: "Clear and Signalled" },
  ],
  monitored_trains: [
    {
      id: "T101",
      name: "Superfast Express",
      train_type: "EXPRESS",
      priority: 1,
      status: "RUNNING",
      is_at_station: true,
      platform: "PF-1",
      scheduled_arrival: "06:55",
      scheduled_departure: "07:05",
      projected_delay_min: 5,
      is_on_time: false,
      destination: "VSN",
    },
  ],
  operational_alerts: [
    {
      id: "alt-1",
      type: "PLATFORM_OCCUPANCY",
      severity: "MEDIUM",
      status: "OPEN",
      location: { kind: "PLATFORM", label: "PF-1" },
      trains: ["T101"],
      train_names: ["Express"],
      start_min: 420,
      start: "07:00",
      end_min: 445,
      end: "07:25",
      description: "Platform 1 dwell extension",
      evidence: {},
    },
  ],
  pending_recommendations: [
    {
      id: "rec-st-1",
      label: "Platform Diversion for T101 to PF-3",
      created_at: "2026-03-01T07:00:00Z",
      state_version: 4,
    },
  ],
  kpi_definitions: {
    "Schedule Adherence": "Percentage of monitored trains within 5 minutes of scheduled timetable",
  },
};

vi.mock("../auth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      username: "section.controller",
      role: "SECTION_MASTER",
      display_name: "Section Controller",
      station_id: null,
      section_id: "NDL-KRN-MLG-SRP-VSN",
    },
  }),
}));

vi.mock("../simulation", () => ({
  useSimulation: () => ({
    selectedId: "sim-100",
    revision: 1,
  }),
}));

describe("DashboardPage Role Intelligence", () => {
  beforeEach(() => {
    vi.spyOn(api, "dashboard").mockResolvedValue(mockDashboardData);
    vi.spyOn(api, "sectionKpis").mockResolvedValue(mockSectionKpis);
    vi.spyOn(api, "stationKpis").mockResolvedValue(mockStationKpis);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Section Controller Corridor Dashboard by default for SECTION_MASTER", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
      expect(screen.getByText("CORRIDOR DISPATCH VIEW")).toBeInTheDocument();
    });

    expect(screen.getByText("Active Corridor Trains")).toBeInTheDocument();
    expect(screen.getByText("Junction Throat Load (MLG)")).toBeInTheDocument();
    expect(screen.getByText("Delay Propagation (DPI)")).toBeInTheDocument();
  });

  it("allows switching to Station Master view and renders station platform berths", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
    });

    const stationBtn = screen.getByRole("button", { name: "Station View" });
    fireEvent.click(stationBtn);

    await waitFor(() => {
      expect(screen.getByText(/Station Master Dashboard — Malgaon Junction/i)).toBeInTheDocument();
      expect(screen.getByText("STATION MASTER VIEW")).toBeInTheDocument();
    });

    expect(screen.getByText(/Live Platform Berthing Status — Malgaon Junction/i)).toBeInTheDocument();
    expect(screen.getByText("Schedule Adherence")).toBeInTheDocument();
    expect(screen.getByText("66.7")).toBeInTheDocument();
    expect(screen.getByText("Platform Diversion for T101 to PF-3")).toBeInTheDocument();
  });

  it("toggles KPI definition reference table when clicked", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
    });

    const docBtn = screen.getByRole("button", { name: /View KPI Definitions/i });
    fireEvent.click(docBtn);

    expect(screen.getByText("KPI Traceability & Mathematical Definitions")).toBeInTheDocument();
    expect(screen.getByText(/Secondary Delay Minutes \/ Initial Schedule Delay Minutes/i)).toBeInTheDocument();
  });

  it("renders corridor traffic schematic in Section Controller view", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("img", { name: /corridor diagram showing track blocks/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Corridor Traffic & Movement Schematic")).toBeInTheDocument();
    expect(screen.getByText("Corridor Active Trains Ledger")).toBeInTheDocument();
  });

  it("filters monitored train movements and renders charts in Station Master view", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
    });

    const stationBtn = screen.getByRole("button", { name: "Station View" });
    fireEvent.click(stationBtn);

    await waitFor(() => {
      expect(screen.getByText(/Station Master Dashboard/i)).toBeInTheDocument();
    });

    // Charts should be present
    expect(screen.getByText("Station Traffic Movements")).toBeInTheDocument();
    expect(screen.getByText("Station Delay Distribution")).toBeInTheDocument();

    // Table filter interaction
    const searchInput = screen.getByPlaceholderText(/Train number, name or destination/i);
    fireEvent.change(searchInput, { target: { value: "Superfast" } });
    expect(screen.getByText("Superfast Express")).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "NonExistent" } });
    expect(screen.getByText("No matching train movements")).toBeInTheDocument();
  });

  it("renders Section Controller Control Office header with territory selector and operational clocks", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("CONTROL DESK: SC-402")).toBeInTheDocument();
    });

    expect(screen.getByText(/Territory:/i)).toBeInTheDocument();
    expect(screen.getByText(/IST Clock:/i)).toBeInTheDocument();
    expect(screen.getByText(/07:00:00 IST/i)).toBeInTheDocument();
    expect(screen.getByText(/Sim Time:/i)).toBeInTheDocument();
    expect(screen.getByText(/T\+420m/i)).toBeInTheDocument();
    expect(screen.getByText(/● HEALTHY TELEMETRY/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /select control territory/i })).toBeInTheDocument();
  });

  it("renders Multi-Station Territory Control Strip and toggles inline station yard inspection", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Multi-Station Territory Control Strip")).toBeInTheDocument();
    });

    // Check station codes rendered in strip
    expect(screen.getAllByText("NDL").length).toBeGreaterThan(0);
    expect(screen.getAllByText("KRN").length).toBeGreaterThan(0);
    expect(screen.getAllByText("MLG").length).toBeGreaterThan(0);

    // Click Karanpur card to inspect yard
    const krnBtn = screen.getByRole("button", { name: /Inspect Karanpur/i });
    fireEvent.click(krnBtn);

    await waitFor(() => {
      expect(screen.getByText(/Station Master Yard Inspection — Karanpur \(KRN\)/i)).toBeInTheDocument();
    });

    // Close inspection
    const closeBtn = screen.getByRole("button", { name: /Close Station Inspection ✕/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByText(/Station Master Yard Inspection — Karanpur \(KRN\)/i)).not.toBeInTheDocument();
  });

  it("switches between control office workspaces via navigation tabs", async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Section Controller Corridor Dashboard")).toBeInTheDocument();
    });

    // Tab to Train Movement Ledger
    const ledgerTab = screen.getByRole("button", { name: "Train Movement Ledger" });
    fireEvent.click(ledgerTab);
    expect(screen.getByText(/Section Train Movement & Regulation Ledger/i)).toBeInTheDocument();

    // Tab to Conflict Regulation
    const regTab = screen.getByRole("button", { name: "Conflict & AI Regulation" });
    fireEvent.click(regTab);
    expect(screen.getByText(/Crossing, Precedence & Train Regulation Workspace/i)).toBeInTheDocument();

    // Tab to Restrictions & Incidents
    const restrTab = screen.getByRole("button", { name: "TSR / PSR & Incidents" });
    fireEvent.click(restrTab);
    expect(screen.getByText(/Operational Restrictions & Incident Management Workspace/i)).toBeInTheDocument();

    // Tab to Coordination & Shift Handover
    const handoverTab = screen.getByRole("button", { name: "Coordination & Shift Handover" });
    fireEvent.click(handoverTab);
    expect(screen.getByText(/Control Office Coordination & Shift Handover Workspace/i)).toBeInTheDocument();
  });
});
