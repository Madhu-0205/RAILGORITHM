import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { RecommendationDetailPage } from "./RecommendationDetail";
import type { RecommendationDetail } from "../types";

const mockDetail: RecommendationDetail = {
  recommendation_id: "rec-v28-test",
  simulation_id: "sim-100",
  status: "PENDING",
  evidence_status: "VALIDATED",
  disagreement: false,
  created_at: "2026-03-01T07:15:00",
  created_by: "system",
  model_version: "ppo-v2.8",
  optimizer_version: "cpsat-v2.8",
  is_stale: false,
  current_state_version: 3,
  simulation_status: "RUNNING",
  affected_stations: ["NDL", "VSN"],
  simulation_time: "07:15",
  state_version: 3,
  label: "SYNTHETIC",
  conflicts: [],
  recommended: {
    candidate_id: "CAND-01",
    label: "Hold 12625 at NDL for 10 min",
    description: "Hold 12625 at NDL for 10 minutes to resolve single line crossing.",
    action: { type: "HOLD", train_id: "12625", station_id: "NDL", hold_min: 10 },
    source: "HEURISTIC",
    weighted_delay: 20,
    expected_outcome: {
      measurement: "SIMULATED_ESTIMATE",
      simulation_minutes: 30,
      total_delay_min: 15,
      average_delay_min: 5,
      max_delay_min: 10,
      weighted_delay: 20,
      conflicts_before: 2,
      conflicts_after: 0,
      conflict_reduction: 2,
      residual_conflicts: [],
      residual_critical: 0,
      on_time_performance_pct: 90,
      throughput_trains_per_hour: 4,
    },
    validation_status: "VALIDATED",
    action_validation_status: "VALIDATED",
    validation_summary: {
      checks_total: 7,
      checks_passed: 7,
      checks_warned: 0,
      checks_failed: 0,
      validator_version: "validator-2.0.0",
    },
    score: 15.0,
  },
  alternatives: [],
  optimizer: {
    status: "OPTIMAL",
    message: "Optimal schedule found",
    objective_value: 120,
    solve_time_s: 0.02,
  },
  ppo: {
    available: true,
    trained: true,
    reason: "PPO candidate ranker operational",
    ranking: [],
    model_version: "ppo-v2.8",
  },
  baseline_ranking: [],
  comparison: {},
  explanation: {
    headline: "Hold 12625 at NDL for 10 min to clear single line block",
    questions: {
      "1_what_is_happening": "Single-line meet projected between 12625 and 22692.",
      "4_why_is_this_recommended": "Lowest measured weighted delay outcome.",
    },
    limitations: ["Synthetic simulation testbed only."],
    structured_reasoning: {
      "1_operational_situation": "Express 12625 approaching single-line section NDL-VSN.",
      "2_primary_problem": "Single line crossing conflict CF-01 at block BLK-3.",
      "3_recommended_action": "Hold 12625 at NDL for 10 min.",
      "4_operational_reasoning": "Higher priority Rajdhani clears block first.",
      "5_railway_constraints_considered": [
        { constraint_id: "HC-001", name: "Block Exclusivity", status: "VERIFIED" },
        { constraint_id: "HC-003", name: "Single-Line Crossing", status: "VERIFIED" },
      ],
      "6_alternative_options_evaluated": [
        { label: "Do nothing", status: "REJECTED", reason_not_chosen: "Leaves critical conflict" },
      ],
      "7_expected_consequences": "Resolves crossing conflict with 10 min regulation hold.",
      "8_consequences_of_no_action": "Gridlock on single line section.",
      "9_verified_evidence": ["State v3", "CP-SAT status OPTIMAL", "7/7 checks passed"],
      "10_residual_uncertainty": "Advisory recommendation; human controller decides.",
    },
  },
  quantitative_evidence: {},
  limitations: ["Synthetic simulation testbed only."],
  disagreement_detail: {
    ppo_top_candidate_id: "CAND-01",
    cpsat_candidate_id: "CAND-01",
    recommended_candidate_id: "CAND-01",
    ppo_disagreement: false,
    cpsat_disagreement: false,
    ppo_vs_cpsat_disagreement: false,
    selection_rule: "Lowest measured delay plus conflict penalty.",
  },
  parent_recommendation_id: null,
  decision: null,
  predictive_regulation: {
    decision_urgency: {
      urgency_category: "NEAR_TERM",
      time_to_act_min: 8,
      decision_window_label: "Near-term regulation window (8 min remaining)",
      critical_location: "NDL-VSN",
      earliest_conflict_time: "07:23",
      action_required: true,
    },
    multi_horizon_projections: [
      {
        horizon_min: 30,
        horizon_label: "TACTICAL",
        target_time: "07:45",
        total_conflicts: 1,
        actionable_conflicts: 1,
        critical_conflicts: 0,
        projected_total_delay_min: 15,
        conflict_types: ["SINGLE_LINE_CROSSING"],
      },
      {
        horizon_min: 60,
        horizon_label: "OPERATIONAL",
        target_time: "08:15",
        total_conflicts: 2,
        actionable_conflicts: 2,
        critical_conflicts: 0,
        projected_total_delay_min: 25,
        conflict_types: ["SINGLE_LINE_CROSSING", "HEADWAY"],
      },
      {
        horizon_min: 90,
        horizon_label: "STRATEGIC",
        target_time: "08:45",
        total_conflicts: 2,
        actionable_conflicts: 2,
        critical_conflicts: 0,
        projected_total_delay_min: 35,
        conflict_types: ["SINGLE_LINE_CROSSING", "HEADWAY"],
      },
    ],
    knock_on_propagation: {
      delayed_train_id: "12625",
      affected_train_count: 2,
      total_knock_on_delay_min: 18,
      affected_trains: [
        {
          train_id: "51831",
          name: "Passenger 51831",
          priority: 3,
          train_type: "PASSENGER",
          knock_on_delay_min: 12,
          bottleneck_location: "VSN",
        },
      ],
      bottleneck_locations: ["VSN", "BLK-3"],
    },
    comparative_timeline: {
      available: true,
      focus_train_id: "12625",
      focus_train_name: "Grand Trunk Express",
      net_delay_savings_min: 8,
      stations: [
        {
          station_id: "NDL",
          scheduled_arrival: "07:15",
          no_action_arrival: "07:15",
          recommended_arrival: "07:15",
          alternative_arrival: "07:15",
          delay_savings_min: 0,
        },
        {
          station_id: "VSN",
          scheduled_arrival: "07:35",
          no_action_arrival: "07:50",
          recommended_arrival: "07:42",
          alternative_arrival: "07:48",
          delay_savings_min: 8,
        },
      ],
    },
  },
  data_quality: {
    overall_quality_state: "SIMULATION",
    is_eligible_for_recommendations: true,
    stale_input_warning: false,
    items: {},
    issues: [],
  },
  confidence_disclosure: {
    confidence_label: "Confidence: Not calibrated",
    is_calibrated: false,
    display_percentage: null,
    explanation: "Categorical evaluation only.",
  },
};

vi.mock("../api", () => ({
  api: {
    recommendation: vi.fn(),
    decide: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}));

vi.mock("../auth", () => ({
  useAuth: () => ({
    user: { username: "section.controller", role: "SECTION_MASTER", station_id: null },
  }),
}));

vi.mock("../simulation", () => ({
  useSimulation: () => ({
    selectedId: "sim-100",
    refresh: vi.fn(),
    revision: 1,
  }),
}));

describe("RecommendationDetailPage v2.8 enhancements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.recommendation as any).mockResolvedValue(mockDetail);
  });

  it("renders urgency badge and uncalibrated confidence disclosure", async () => {
    render(
      <MemoryRouter initialEntries={["/recommendations/rec-v28-test"]}>
        <Routes>
          <Route path="/recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Recommendation review")).toBeInTheDocument();
    });

    expect(screen.getByText("NEAR-TERM (5-15m)")).toBeInTheDocument();
    expect(screen.getByText("DATA: SIMULATION")).toBeInTheDocument();
    expect(screen.getByText("Confidence: Not calibrated")).toBeInTheDocument();
  });

  it("renders predictive regulation console with multi-horizon projections", async () => {
    render(
      <MemoryRouter initialEntries={["/recommendations/rec-v28-test"]}>
        <Routes>
          <Route path="/recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Predictive Train Regulation & Forward Impact")).toBeInTheDocument();
    });

    expect(screen.getByText(/Near-term regulation window/)).toBeInTheDocument();
    expect(screen.getByText(/Downstream Knock-on Propagation/)).toBeInTheDocument();
    expect(screen.getByText(/18 min/)).toBeInTheDocument();
    expect(screen.getByText(/Longitudinal Station Trajectory/)).toBeInTheDocument();
  });

  it("renders 10-point explainable recommendation reasoning", async () => {
    render(
      <MemoryRouter initialEntries={["/recommendations/rec-v28-test"]}>
        <Routes>
          <Route path="/recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Explainable Recommendation Reasoning (10-Point Operational Assessment)")).toBeInTheDocument();
    });

    expect(screen.getByText("1. Operational Situation:")).toBeInTheDocument();
    expect(screen.getByText("2. Primary Problem:")).toBeInTheDocument();
    expect(screen.getByText("3. Recommended Action:")).toBeInTheDocument();
    expect(screen.getByText("4. Operational Reasoning:")).toBeInTheDocument();
    expect(screen.getByText("5. Railway Constraints Evaluated:")).toBeInTheDocument();
    expect(screen.getByText("6. Alternatives Evaluated:")).toBeInTheDocument();
    expect(screen.getByText("7. Expected Consequences:")).toBeInTheDocument();
    expect(screen.getByText("8. Consequences of No Action:")).toBeInTheDocument();
    expect(screen.getByText("9. Verified Evidence:")).toBeInTheDocument();
    expect(screen.getByText("10. Residual Uncertainty:")).toBeInTheDocument();
  });

  it("renders feedback category and operational rationale tag selectors in decision panel", async () => {
    render(
      <MemoryRouter initialEntries={["/recommendations/rec-v28-test"]}>
        <Routes>
          <Route path="/recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Feedback category")).toBeInTheDocument();
      expect(screen.getByLabelText("Operational rationale tag")).toBeInTheDocument();
    });
  });
});
