export type Role = "SECTION_MASTER" | "STATION_MASTER";

export interface User {
  id: string;
  username: string;
  role: Role;
  display_name: string;
  station_id: string | null;
  section_id: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface SimulationSummary {
  id: string;
  name: string;
  scenario_key: string;
  status: string;
  sim_time_min: number;
  state_version: number;
  seed: number;
  label: string;
  created_at: string;
  created_by: string;
}

export interface Scenario {
  key: string;
  name: string;
  description: string;
  start_time_min: number;
  seed: number;
  train_count: number;
  closure_count: number;
  platform_outage_count: number;
  label: string;
}

export interface Train {
  id: string;
  name: string;
  train_type: string;
  priority: number;
  effective_priority: number;
  direction: string;
  origin: string;
  destination: string;
  status: string;
  station_id: string | null;
  next_station: string | null;
  section_id: string | null;
  block_id: string | null;
  platform: string | null;
  delay_min: number;
  projected_delay_min: number;
  scheduled_departure: string | null;
  scheduled_arrival_next: string | null;
  hold_until: string | null;
  waiting_reason: string | null;
  total_wait_min: number;
  route: string[];
  label: string;
}

export interface Metrics {
  sim_time_min: number;
  sim_time: string;
  trains_total: number;
  trains_active: number;
  trains_completed: number;
  trains_delayed: number;
  total_delay_min: number;
  average_delay_min: number;
  average_completed_delay_min: number;
  max_delay_min: number;
  on_time_arrivals: number;
  on_time_performance_pct: number;
  throughput_trains_per_hour: number;
  section_utilization_pct: number;
  platform_utilization_pct: number;
  waiting_min_total: number;
  label: string;
}

export interface Conflict {
  id: string;
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: string;
  location: {
    kind: string;
    station_id?: string;
    section_id?: string;
    block_id?: string;
    label: string;
  };
  trains: string[];
  train_names: string[];
  start_min: number;
  start: string;
  end_min: number;
  end: string;
  description: string;
  evidence: Record<string, unknown>;
}

export interface BlockOccupancy {
  block_id: string;
  section_id: string;
  from_station: string;
  to_station: string;
  mode: string;
  direction: string;
  run_time_min: number;
  headway_min: number;
  occupied_by: string | null;
  entry_min: number | null;
  exit_min: number | null;
  closure: Closure | null;
}

export interface Platform {
  station_id: string;
  platform_id: string;
  occupied_by: string | null;
  outage: PlatformOutage | null;
  status: string;
}

export interface Closure {
  id: string;
  block_id: string;
  start_min: number;
  end_min: number;
  reason: string;
  created_by: string;
  created_at: string;
}

export interface PlatformOutage {
  id: string;
  station_id: string;
  platform_id: string;
  start_min: number;
  end_min: number;
  reason: string;
  created_by: string;
  created_at: string;
}

export interface Station {
  id: string;
  name: string;
  code: string;
  platforms: string[];
  x: number;
  is_junction: boolean;
}

export interface Section {
  id: string;
  from_station: string;
  to_station: string;
  mode: string;
  headway_min: number;
  max_speed_kmph: number;
  blocks: {
    id: string;
    direction: string;
    run_time_min: number;
  }[];
}

export interface Network {
  id: string;
  name: string;
  timezone: string;
  label: string;
  stations: Station[];
  sections: Section[];
}

export interface SimulationView {
  id: string;
  scenario_key: string;
  name: string;
  seed: number;
  status: string;
  label: string;
  scenario_date: string;
  timezone: string;
  sim_time: string;
  sim_time_min: number;
  state_version: number;
  network: Network;
  trains: Train[];
  conflicts: Conflict[];
  block_occupancy: BlockOccupancy[];
  platforms: Platform[];
  closures: Closure[];
  platform_outages: PlatformOutage[];
  metrics: Metrics;
  events: { id: number; event_type: string; message: string; at_min: number }[];
  data_label: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  simulation: {
    id: string;
    name: string;
    scenario_key: string;
    status: string;
    sim_time: string;
    sim_time_min: number;
    state_version: number;
    seed: number;
    label: string;
    scenario_date: string;
    timezone: string;
  };
  metrics: Metrics;
  trains: Train[];
  active_trains: Train[];
  delayed_trains: Train[];
  conflicts: Conflict[];
  conflict_count: number;
  occupied_blocks: BlockOccupancy[];
  available_platforms: Platform[];
  closures: Closure[];
  platform_outages: PlatformOutage[];
  active_closures: Closure[];
  upcoming_closures: Closure[];
  active_outages: PlatformOutage[];
  pending_recommendations: RecommendationSummary[];
  pending_recommendation_count: number;
  model_status: {
    ppo: {
      trained: boolean;
      status: string;
      model_version: string;
      reason?: string;
      evaluation?: Record<string, unknown>;
    };
    cpsat: { version: string; status: string };
  };
  data_label: string;
  role_scope: { role: Role; station_id: string | null; section_id: string | null };
}

export interface RecommendationSummary {
  id: string;
  status: string;
  evidence_status: string;
  disagreement: boolean;
  created_at: string;
  headline: string | null;
  recommended_label: string | null;
  recommended_candidate_id: string | null;
  affected_stations: string[];
  is_stale: boolean;
  state_version: number;
  sim_time: string;
}

export interface CandidateOutcome {
  measurement: string;
  simulation_minutes: number;
  total_delay_min: number | null;
  average_delay_min: number | null;
  max_delay_min: number | null;
  weighted_delay: number | null;
  on_time_performance_pct: number | null;
  throughput_trains_per_hour: number | null;
  conflicts_before: number;
  conflicts_after: number;
  conflict_reduction: number;
  residual_conflicts: {
    id: string;
    type: string;
    severity: string;
    description: string;
  }[];
  residual_critical: number;
}

export interface Alternative {
  candidate_id: string;
  label: string;
  description: string;
  action: Record<string, unknown> & { type: string };
  source: string;
  eligible: boolean;
  selected: boolean;
  rejection_reason: string | null;
  validation_status: string;
  action_validation_status: string;
  expected_outcome: CandidateOutcome;
  weighted_delay: number | null;
  score: number | null;
}

export interface RecommendedCandidate {
  candidate_id: string;
  label: string;
  description: string;
  action: Record<string, unknown> & { type: string };
  source: string;
  expected_outcome: CandidateOutcome;
  validation_status: string;
  action_validation_status: string;
  validation_summary: {
    checks_total: number;
    checks_passed: number;
    checks_warned: number;
    checks_failed: number;
    validator_version: string | null;
  };
  weighted_delay: number | null;
  score: number | null;
}

export interface Explanation {
  headline: string;
  questions: Record<string, string>;
  limitations: string[];
}

export interface RecommendationDetail {
  recommendation_id: string;
  simulation_id: string;
  status: string;
  evidence_status: string;
  disagreement: boolean;
  created_at: string;
  created_by: string;
  model_version: string;
  optimizer_version: string;
  is_stale: boolean;
  current_state_version: number;
  simulation_status: string;
  affected_stations: string[];
  simulation_time: string;
  state_version: number;
  label: string;
  conflicts: Conflict[];
  recommended: RecommendedCandidate | null;
  alternatives: Alternative[];
  optimizer: {
    status: string;
    message: string;
    objective_value: number | null;
    solve_time_s: number;
    schedule_validation_status?: string;
    validator_version?: string;
    [key: string]: unknown;
  };
  ppo: {
    available: boolean;
    trained?: boolean;
    reason: string;
    ranking: { candidate_id: string; score: number; policy_probability: number }[];
    top_candidate_id?: string;
    value_estimate?: number;
    model_version: string;
    model_metrics?: Record<string, unknown>;
    disclaimer?: string;
  };
  baseline_ranking: { candidate_id: string; label: string }[];
  comparison: {
    measurement_note?: string;
    no_intervention?: CandidateOutcome;
    baseline_heuristic_choice?: CandidateOutcome;
    cpsat_only?: CandidateOutcome;
    hybrid_recommended?: CandidateOutcome;
    [key: string]: unknown;
  };
  explanation: Explanation;
  quantitative_evidence: Record<string, unknown>;
  limitations: string[];
  disagreement_detail: {
    ppo_top_candidate_id: string | null;
    cpsat_candidate_id: string | null;
    recommended_candidate_id: string | null;
    ppo_disagreement: boolean;
    cpsat_disagreement: boolean;
    ppo_vs_cpsat_disagreement: boolean;
    selection_rule: string;
  };
  parent_recommendation_id: string | null;
  decision: Decision | null;
}

export interface Decision {
  id: string;
  recommendation_id: string;
  action: string;
  rationale: string;
  modifications: Record<string, unknown> | null;
  decided_by: string;
  decided_role: string;
  decided_at: string;
  applied: boolean;
  simulation_result: Record<string, unknown> | null;
  validation_status: string | null;
  model_version: string;
  optimizer_version: string;
  execution_mode: string;
}

export interface Analytics {
  simulation_id: string;
  scenario_key: string;
  scenario_name: string;
  simulation_time: string;
  sim_time_min: number;
  state_version: number;
  label: string;
  data_disclaimer: string;
  kpis: Record<string, number>;
  recommendation_stats: Record<string, number | null>;
  section_utilization: {
    section_id: string;
    label: string;
    mode: string;
    utilization_pct: number;
  }[];
  platform_utilization: {
    station_id: string;
    label: string;
    utilization_pct: number;
  }[];
  train_delays: {
    train_id: string;
    name: string;
    status: string;
    delay_min: number;
    projected_delay_min: number;
    priority: number;
    train_type: string;
  }[];
  conflicts: Conflict[];
  latest_recommendation_comparison: Record<string, unknown> | null;
  comparison_note: string;
}

export interface WhatIfResult {
  status: string;
  action?: Record<string, unknown>;
  minutes?: number;
  validation?: Record<string, unknown>;
  message?: string;
  baseline_metrics?: Metrics;
  hypothetical_metrics?: Metrics;
  deltas?: {
    total_delay_min: number;
    average_delay_min: number;
    on_time_performance_pct: number;
    conflicts: number;
  };
  baseline_conflicts?: Conflict[];
  hypothetical_conflicts?: Conflict[];
  applied_to_live_simulation: boolean;
  note?: string;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  actor: string;
  actor_role: string;
  simulation_id: string | null;
  recommendation_id: string | null;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
  created_at: string;
}

export interface ModelRecord {
  name: string;
  version: string;
  trained: boolean;
  status: string;
  config: Record<string, unknown>;
  metrics: Record<string, unknown>;
  artifact_path: string | null;
  created_at: string;
}
