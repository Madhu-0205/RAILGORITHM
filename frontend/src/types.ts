export type Role = "SECTION_MASTER" | "SECTION_CONTROLLER" | "STATION_MASTER" | "ADMIN";

export interface User {
  id: string;
  username: string;
  role: Role;
  display_name: string;
  station_id: string | null;
  section_id: string | null;
  zone?: string | null;
  division?: string | null;
  control_area?: string | null;
  assigned_stations?: string[];
  assigned_sections?: string[];
  active?: boolean;
  last_login_at?: string | null;
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
  disruption_count?: number;
  service_pattern?: string;
  tags?: string[];
  train_categories?: string[];
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
  related_types?: string[];
  constraint_id?: string | null;
  constraint_spec_version?: string;
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

export interface EvidenceItem {
  id: string;
  category: string;
  source: string;
  fact: string;
  evidence_class: 'OBSERVED' | 'CALCULATED' | 'PREDICTED' | 'HEURISTIC' | 'UNKNOWN' | 'STALE' | 'NO_DATA';
  confidence_or_status?: string;
  timestamp?: string;
}

export interface StructuredEvidence {
  A_situation?: {
    title: string;
    content: string;
    evidence_class: string;
    operational_posture: string;
    active_trains_count: number;
    corridor_state: string;
  };
  B_detection?: {
    title: string;
    primary_conflict_type: string;
    location_summary: string;
    time_to_conflict_min: number;
    evidence_class: string;
  };
  C_evidence?: {
    title: string;
    items: EvidenceItem[];
  };
  D_constraints?: {
    title: string;
    hard_constraints_checked: Array<{ id: string; description: string; status: string }>;
    soft_constraints_evaluated: Array<{ id: string; description: string; penalty_weight: number }>;
  };
  E_recommended_action?: {
    title: string;
    action_type: string;
    target_train_id: string;
    location: string;
    parameters: Record<string, unknown>;
    operational_rationale: string;
  };
  F_expected_outcome?: {
    title: string;
    metrics: Record<string, unknown>;
    conflict_reduction: number;
    throughput_impact: string;
  };
  G_alternative_actions?: {
    title: string;
    feasible_alternatives_count: number;
    alternatives_summary: Array<{ label: string; outcome_delay_min: number; status: string }>;
  };
  H_no_action_consequence?: {
    title: string;
    content: string;
    evidence_class: string;
    baseline_metrics?: Record<string, unknown>;
  };
  I_trade_offs?: {
    title: string;
    gained: string[];
    sacrificed: string[];
  };
  J_uncertainty?: {
    title: string;
    content: string;
    confidence_available: boolean;
    uncertainty_range_min?: number;
    data_quality_caveat?: string;
  };
  K_validity?: {
    title: string;
    state_version: number;
    valid_until_sim_time: string;
    revalidation_triggers: string[];
  };
}

export interface ComparisonMatrixItem {
  attribute: string;
  recommended: string | number;
  best_alternative: string | number;
  no_action_baseline: string | number;
  operational_significance: string;
}

export interface DevelopingDelay {
  train_id: string;
  train_name: string;
  train_type: string;
  category: 'OBSERVED_DELAY' | 'DEVELOPING_DELAY' | 'PREDICTED_DETENTION' | 'RECOVERY_OPPORTUNITY';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  current_delay_min: number;
  projected_delay_range: {
    min_delay_min: number;
    expected_delay_min: number;
    max_delay_min: number;
  };
  primary_driver: string;
  bottleneck_location: string;
  actionability: 'ACTIONABLE_NOW' | 'MONITOR_CLOSELY' | 'INFORMATION_ONLY';
}

export interface DelayPropagationGraph {
  nodes: Array<{
    id: string;
    label: string;
    train_id: string;
    train_type: string;
    current_delay_min: number;
    projected_delay_min: number;
    cascade_depth: number;
  }>;
  edges: Array<{
    source_train_id: string;
    target_train_id: string;
    dependency_type: 'HEADWAY_FOLLOWING' | 'CROSSING_MEET_PASS' | 'PLATFORM_BOTTLENECK';
    location: string;
    delay_transferred_min: number;
  }>;
  cascade_chains: Array<{
    initiating_train_id: string;
    chain_length: number;
    total_accumulated_delay_min: number;
    impacted_trains: string[];
  }>;
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
  urgency_category?: string;
  overall_quality_state?: string;
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
  affected_resources?: {
    trains: string[];
    blocks: string[];
    sections: string[];
    stations: string[];
  };
  predicted_impacts?: Record<string, unknown>;
  validation_report?: Record<string, unknown>;
  solver_status?: string | null;
  ppo_evidence?: {
    available: boolean;
    model_version: string | null;
    policy_probability: number | null;
    top_candidate_id: string | null;
    note: string;
  };
  trade_offs?: TradeOffs;
  uncertainty?: Uncertainty;
  provenance?: Provenance;
  value_labels?: {
    calculated: string[];
    predicted: string[];
    assumed: string[];
  };
}

export interface TradeOffRow {
  candidate_id: string;
  label: string;
  source: string;
  weighted_delay: number | null;
  residual_conflicts: number;
  total_delay_min: number | null;
  selected: boolean;
}

export interface TradeOffs {
  available: boolean;
  reason?: string;
  selection_rule?: string;
  selected?: TradeOffRow | null;
  eligible_alternatives?: TradeOffRow[];
  note?: string;
}

export interface Uncertainty {
  confidence_percentage: number | null;
  note?: string;
  sources_of_uncertainty?: string[];
  measurement_label?: string;
}

export interface Provenance {
  state_version?: number;
  simulation_time?: string;
  candidate_id?: string | null;
  candidate_source?: string | null;
  conflicts_considered?: string[];
  constraint_ids?: string[];
  solver?: Record<string, unknown>;
  ppo?: Record<string, unknown>;
  alternatives_considered?: {
    candidate_id: string;
    eligible: boolean;
    score: number | null;
    source: string;
    rejection_reason: string | null;
  }[];
  versions?: Record<string, string>;
}

export interface DecisionSupport {
  human_in_control: boolean;
  recommendation_is_not_a_decision: boolean;
  requires_confirmation: boolean;
  authorized_roles?: string[];
  recorded_separately?: boolean;
  allowed_decisions?: string[];
  note?: string;
}

export interface Explanation {
  headline: string;
  questions: Record<string, string>;
  limitations: string[];
  structured_reasoning?: Record<string, unknown>;
}

export interface PredictiveRegulation {
  decision_urgency?: {
    urgency_category: string;
    time_to_act_min: number | null;
    decision_window_label: string;
    critical_location: string | null;
    earliest_conflict_time: string | null;
    action_required: boolean;
  };
  multi_horizon_projections?: Array<{
    horizon_min: number;
    horizon_label: string;
    target_time: string;
    total_conflicts: number;
    actionable_conflicts: number;
    critical_conflicts: number;
    projected_total_delay_min: number;
    conflict_types: string[];
  }>;
  train_delay_trends?: Record<string, {
    trend: string;
    rate_min_per_hour: number;
    primary_cause: string;
    cause_description: string;
    current_delay_min: number;
    projected_final_delay_min: number;
  }>;
  knock_on_propagation?: {
    delayed_train_id: string;
    affected_train_count: number;
    total_knock_on_delay_min: number;
    affected_trains: Array<{
      train_id: string;
      name: string;
      priority: number;
      train_type: string;
      knock_on_delay_min: number;
      bottleneck_location: string | null;
    }>;
    bottleneck_locations: string[];
  };
  comparative_timeline?: {
    available: boolean;
    focus_train_id?: string;
    focus_train_name?: string;
    stations?: Array<{
      station_id: string;
      scheduled_arrival: string;
      no_action_arrival: string;
      recommended_arrival: string;
      alternative_arrival?: string;
      delay_savings_min: number;
    }>;
    net_delay_savings_min?: number;
  };
  developing_delays?: DevelopingDelay[];
  propagation_graph?: DelayPropagationGraph;
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
  predictive_regulation?: PredictiveRegulation;
  structured_evidence?: StructuredEvidence;
  comparison_matrix?: ComparisonMatrixItem[];
  data_quality?: {
    overall_quality_state: string;
    is_eligible_for_recommendations: boolean;
    stale_input_warning: boolean;
    items?: Record<string, { quality_state: string; detail: string; critical: boolean }>;
    issues?: string[];
  };
  confidence_disclosure?: {
    confidence_label: string;
    is_calibrated: boolean;
    display_percentage: number | null;
    explanation: string;
    safety_note?: string;
  };
  provenance?: Provenance;
  trade_offs?: TradeOffs;
  uncertainty?: Uncertainty;
  decision_support?: DecisionSupport;
  assumption_spec_version?: string;
  constraint_spec_version?: string;
  objective_profile?: string;
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
  feedback_category?: string | null;
  structured_rationale_tag?: string | null;
  predicted_outcome?: Record<string, unknown> | null;
  actual_outcome?: Record<string, unknown> | null;
  prediction_error?: Record<string, unknown> | null;
  data_quality?: Record<string, unknown> | null;
  three_way_comparison?: Record<string, unknown> | null;
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

export interface FeedHealthMetrics {
  feed_id: string;
  feed_name: string;
  status: "HEALTHY" | "DEGRADED" | "STALE" | "OFFLINE" | "DURABILITY_UNAVAILABLE" | "REPLAY_UNCERTAIN";
  connected: boolean;
  last_heartbeat_at: string | null;
  freshness_seconds: number;
  is_stale: boolean;
  events_received_total: number;
  events_valid_total: number;
  duplicates_detected_total: number;
  sequence_gaps_total: number;
  contradictions_detected_total: number;
  mean_ingestion_latency_ms: number;
  error_rate_pct: number;
  reconnection_attempts: number;
  circuit_breaker_open: boolean;
  mode: string;
  stale_threshold_seconds: number;
  degraded_threshold_seconds: number;
}

export interface StationMasterKpis {
  station_id: string;
  station_name: string;
  simulation_time: string;
  sim_time_min: number;
  time_period: string;
  data_freshness: {
    status: string;
    freshness_seconds: number;
    is_stale: boolean;
    last_heartbeat_at: string | null;
  };
  kpis: {
    trains_monitored: number;
    on_time_trains: number;
    delayed_trains: number;
    schedule_adherence_pct: number | null;
    adherence_status?: "NORMAL" | "NO_DATA";
    adherence_explanation?: string;
    punctuality_threshold_min?: number;
    average_arrival_delay_min: number | null;
    average_departure_delay_min: number | null;
    platform_availability_pct: number;
    platforms_total: number;
    platforms_available: number;
    platforms_occupied: number;
    platforms_outage: number;
    pending_recommendations_count: number;
    operational_alerts_count: number;
  };
  platform_slots: {
    platform_id: string;
    status: "OCCUPIED" | "AVAILABLE" | "OUTAGE";
    train_id: string | null;
    description: string;
  }[];
  monitored_trains: {
    id: string;
    name: string;
    train_type: string;
    priority: number;
    status: string;
    is_at_station: boolean;
    platform: string | null;
    projected_delay_min: number;
    is_on_time: boolean;
    destination: string;
    scheduled_arrival: string | null;
    scheduled_departure: string | null;
  }[];
  operational_alerts: Conflict[];
  pending_recommendations: {
    id: string;
    label: string;
    created_at: string | null;
    state_version: number;
  }[];
  kpi_definitions: Record<string, string>;
}

export interface SectionControllerKpis {
  simulation_time: string;
  sim_time_min: number;
  time_period: string;
  data_freshness: {
    status: string;
    freshness_seconds: number;
    is_stale: boolean;
    last_heartbeat_at: string | null;
    error_rate_pct: number;
  };
  kpis: {
    trains_active: number;
    trains_completed: number;
    trains_scheduled: number;
    trains_delayed: number;
    average_section_delay_min: number;
    total_section_delay_min: number;
    block_occupancy_pct: number;
    blocks_occupied: number;
    blocks_total: number;
    junction_throat_load_pct: number;
    junction_queue_length: number;
    junction_congestion_level: "LOW" | "MODERATE" | "HIGH" | "SATURATED";
    throughput_trains_per_hour: number;
    on_time_performance_pct: number;
    delay_propagation_index: number;
    secondary_delay_min: number;
    knock_on_risk_level: "LOW" | "MODERATE" | "HIGH" | "SEVERE";
    conflicts_total: number;
    conflicts_critical: number;
    conflicts_major: number;
    conflicts_minor: number;
    pending_decisions_count: number;
    recovery_clearance_rate_pct: number | null;
  };
  junction_status: {
    junction_id: string;
    junction_name: string;
    throat_capacity: number;
    active_transits: number;
    transiting_trains: string[];
    congestion_level: string;
  };
  occupied_bottlenecks: { block_id: string; train_id: string }[];
  severity_breakdown: Record<string, number>;
  active_conflicts: Conflict[];
  pending_decisions: {
    id: string;
    label: string;
    affected_stations: string[];
    disagreement: boolean;
    created_at: string | null;
  }[];
  kpi_definitions: Record<string, string>;
}

// ==========================================
// ROLE-SEPARATED WORKSPACES TYPES
// ==========================================

export interface StationMasterOverview {
  station_id: string;
  station_name: string;
  station_code: string;
  is_junction: boolean;
  operational_status: "NORMAL" | "CONGESTED" | "REGULATED" | "DEGRADED";
  simulation_time: string;
  sim_time_min: number;
  summary_counts: {
    total_scheduled_today: number;
    monitored_window_trains: number;
    arriving_next_30m: number;
    departing_next_30m: number;
    through_next_30m: number;
    currently_at_station: number;
    delayed_trains_count: number;
    on_time_trains_count: number;
  };
  adherence: {
    schedule_adherence_pct: number | null;
    adherence_status: "NORMAL" | "DEGRADED" | "NO_DATA";
    explanation: string;
    punctuality_threshold_min: number;
    average_delay_min: number | null;
  };
  platform_summary: {
    total_platforms: number;
    available: number;
    occupied: number;
    outage: number;
    occupancy_pct: number;
  };
  data_quality: {
    overall_status: string;
    feed_status: string;
    confidence_score: number;
    freshness_seconds: number;
    is_stale: boolean;
  };
}

export interface StationTrack {
  track_id: string;
  track_name: string;
  category: "PLATFORM" | "LOOP_LINE" | "SIDING" | "SHUNTING_NECK";
  line_type: string;
  state: "CLEAR" | "OCCUPIED" | "RESERVED" | "RESTRICTED" | "BLOCKED" | "STALE" | "UNKNOWN";
  length_m: number;
  electrified: boolean;
  max_speed_kmph: number;
  occupied_by: {
    train_id: string;
    name: string;
    type: string;
    priority: number;
    direction: string;
    origin: string;
    destination: string;
    delay_min: number;
  } | null;
  route_locked: boolean;
  locked_for_train: string | null;
  restrictions?: string | null;
}

export interface StationMasterLayout {
  station_id: string;
  station_name: string;
  station_code: string;
  is_junction: boolean;
  junction_throat_capacity: number;
  throat_status: string;
  tracks: StationTrack[];
  berthing_capacity_total_m: number;
  speed_restrictions: {
    location: string;
    speed_limit_kmph: number;
    reason: string;
  }[];
}

export interface MovementBoardEntry {
  train_id: string;
  train_name: string;
  train_type: string;
  priority: number;
  direction: string;
  origin: string;
  destination: string;
  scheduled_arrival: string | null;
  estimated_arrival: string | null;
  scheduled_departure: string | null;
  estimated_departure: string | null;
  assigned_platform: string | null;
  status: "ON_TIME" | "DELAYED" | "EARLY";
  delay_min: number;
  speed_kmph: number;
  line_clear_status: string;
  dwell_min: number;
  traction: string;
}

export interface StationMasterMovementBoard {
  station_id: string;
  simulation_time: string;
  sim_time_min: number;
  window_ahead_min: number;
  arriving: MovementBoardEntry[];
  departing: MovementBoardEntry[];
  through: MovementBoardEntry[];
  history: MovementBoardEntry[];
}

export interface AdjacentStationInfo {
  station_id: string;
  station_name: string;
  code: string;
  relative_position: string;
  distance_km: number;
  section_id: string;
  section_mode: "SINGLE" | "DOUBLE";
  headway_min: number;
  blocks: {
    block_id: string;
    direction: string;
    signaling_type: string;
    state: "CLEAR" | "OCCUPIED" | "CLOSED";
    train: {
      train_id: string;
      train_name: string;
      direction: string;
      speed_kmph: number;
    } | null;
  }[];
  line_clear_status: string;
  last_movement_event: {
    message: string;
    time: string;
  };
  telemetry_freshness_seconds: number;
}

export interface StationMasterAdjacentStations {
  station_id: string;
  station_name: string;
  simulation_time: string;
  sim_time_min: number;
  upstream_station: AdjacentStationInfo | null;
  downstream_station: AdjacentStationInfo | null;
  junction_branches: {
    branch_id: string;
    name: string;
    mode: string;
    length_km: number;
    status: string;
    signaling: string;
  }[];
}

export interface StationMasterAlerts {
  station_id: string;
  station_name: string;
  simulation_time: string;
  sim_time_min: number;
  active_conflicts: Conflict[];
  pending_recommendations: {
    id: string;
    label: string;
    action: string;
    confidence: number;
    explanation: string;
    evidence_status: string;
    safety_checks: { rule: string; name: string; status: string }[];
    created_at: string | null;
  }[];
}

export interface MonitoredStationSummary {
  station_id: string;
  station_name: string;
  code: string;
  km_marker: number;
  is_junction: boolean;
  total_platforms: number;
  occupied_platforms: number;
  available_platforms: number;
  throat_status: string;
}

export interface SectionControllerOverview {
  section_name: string;
  operating_boundaries: string;
  control_area: string;
  simulation_time: string;
  sim_time_min: number;
  kpis: {
    monitored_stations_count: number;
    trains_active: number;
    trains_delayed: number;
    trains_total: number;
    average_delay_min: number;
    total_delay_min: number;
    punctuality_pct: number;
    blocks_total: number;
    blocks_occupied: number;
    block_occupancy_pct: number;
    critical_bottlenecks_count: number;
    bottlenecks_occupied_count: number;
    active_conflicts_count: number;
    delay_propagation_index: number;
  };
  monitored_stations: MonitoredStationSummary[];
  data_quality: {
    status: string;
    feed_status: string;
    confidence_score: number;
    freshness_seconds: number;
    is_stale: boolean;
  };
}

export interface SectionControllerTopology {
  corridor_length_km: number;
  stations: {
    station_id: string;
    name: string;
    code: string;
    km: number;
    is_junction: boolean;
    platforms_count: number;
  }[];
  sections: {
    section_id: string;
    from_station: string;
    to_station: string;
    mode: string;
    distance_km: number;
    max_speed_kmph: number;
    headway_min: number;
    traction_type: string;
    blocks: {
      block_id: string;
      direction: string;
      signaling_type: string;
      run_time_min: number;
      is_occupied: boolean;
      occupant_train: string | null;
      km_start: number;
      km_end: number;
    }[];
  }[];
  speed_restrictions: {
    section_id: string;
    km_location: number;
    speed_limit_kmph: number;
    reason: string;
  }[];
  signaling_territory: string;
}

export interface TrainLedgerEntry {
  train_id: string;
  train_name: string;
  train_type: string;
  priority: number;
  direction: string;
  origin: string;
  destination: string;
  status: string;
  current_location: string;
  current_km: number | null;
  speed_kmph: number;
  delay_min: number;
  projected_delay_min: number;
  precedence_class: string;
  crew_duty_hours: number;
  eta_section_exit: string;
}

export interface SectionControllerTrainLedger {
  simulation_time: string;
  sim_time_min: number;
  total_trains: number;
  trains: TrainLedgerEntry[];
}

export interface BlockBoardEntry {
  block_id: string;
  section_id: string;
  from_station: string;
  to_station: string;
  mode: string;
  direction: string;
  signaling_type: string;
  signal_aspect: "GREEN" | "YELLOW" | "DOUBLE_YELLOW" | "RED";
  state: "CLEAR" | "OCCUPIED" | "BLOCKED" | "MAINTENANCE";
  occupant_train: {
    train_id: string;
    train_name: string;
    direction: string;
    speed_kmph: number;
    delay_min: number;
  } | null;
  headway_min: number;
  axle_counter_status: string;
  telemetry_freshness_seconds: number;
}

export interface SectionControllerBlockBoard {
  simulation_time: string;
  sim_time_min: number;
  total_blocks: number;
  occupied_blocks: number;
  blocks: BlockBoardEntry[];
}

export interface JunctionCrossingScenario {
  id: string;
  junction_id: string;
  junction_name: string;
  conflict_type: string;
  train_a: {
    train_id: string;
    name: string;
    type: string;
    priority: number;
    direction: string;
    current_delay_min: number;
  };
  train_b: {
    train_id: string;
    name: string;
    type: string;
    priority: number;
    direction: string;
    current_delay_min: number;
  };
  recommended_resolution: {
    action: string;
    loop_station?: string;
    loop_track?: string;
    crossing_station?: string;
    holding_train?: string;
    holding_track?: string;
    through_train?: string;
    explanation: string;
    delay_impact_train_a_min: number;
    delay_impact_train_b_min: number;
    net_corridor_saving_min: number;
    safety_constraints_verified: { rule: string; name: string; status: string }[];
  };
  alternative_option: {
    action: string;
    explanation: string;
    delay_impact_train_a_min: number;
    delay_impact_train_b_min: number;
    net_corridor_penalty_min: number;
  };
}

export interface SectionControllerJunctionWorkspace {
  simulation_time: string;
  sim_time_min: number;
  monitored_junctions: string[];
  active_scenarios: JunctionCrossingScenario[];
  conflicts_count: number;
}

export interface SectionControllerAlerts {
  simulation_time: string;
  sim_time_min: number;
  conflicts: Conflict[];
  recommendations: {
    id: string;
    label: string;
    action: string;
    affected_trains: string[];
    affected_stations: string[];
    confidence: number;
    explanation: string;
    evidence_status: string;
    disagreement: boolean;
    created_at: string | null;
  }[];
}
