/**
 * Formal KPI Registry for RAILGORITHM v2.6.
 *
 * Provides authoritative definitions, mathematical formulas, data provenance,
 * reporting windows, epistemic quality classifications, and missing-data semantics
 * for all operational KPIs in Station Master and Section Controller dashboards.
 */

export type KpiClassification =
  | "MEASURED"
  | "CALCULATED"
  | "PREDICTED"
  | "HEURISTIC"
  | "NO_DATA"
  | "STALE";

export interface KpiDefinition {
  id: string;
  name: string;
  role: "STATION_MASTER" | "SECTION_CONTROLLER" | "BOTH";
  formula: string;
  formulaLatex?: string;
  unit: string;
  reportingWindow: string;
  dataSource: string;
  classification: KpiClassification;
  missingDataSemantics: string;
  description: string;
  benchmarkTarget?: string;
}

export const KPI_REGISTRY: Record<string, KpiDefinition> = {
  // -------------------------------------------------------------------------
  // Station Master KPIs
  // -------------------------------------------------------------------------
  trains_monitored: {
    id: "trains_monitored",
    name: "Trains Monitored",
    role: "STATION_MASTER",
    formula: "Count of all trains scheduled to traverse or stop at station in window",
    formulaLatex: "\\sum \\mathbb{I}(\\text{train scheduled in window})",
    unit: "trains",
    reportingWindow: "Rolling 60m / Horizon",
    dataSource: "Station Working Timetable & Movement Ledger",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 if no trains are scheduled in active horizon.",
    description: "Total trains currently monitored within the station's operational boundary.",
  },
  schedule_adherence_pct: {
    id: "schedule_adherence_pct",
    name: "Schedule Adherence (5-min)",
    role: "STATION_MASTER",
    formula: "(Count of trains with delay <= 5 min / Total monitored trains) * 100",
    formulaLatex: "\\frac{|\\{t \\in T : \\text{delay}_t \\le 5\\}|}{|T|} \\times 100\\%",
    unit: "%",
    reportingWindow: "Rolling 60m",
    dataSource: "Railway Board 5-Min Punctuality Criterion",
    classification: "CALCULATED",
    missingDataSemantics: "Returns null (dash '—') when total monitored trains is 0.",
    description: "Percentage of trains arriving or departing within the 5-minute Railway Board punctuality tolerance.",
    benchmarkTarget: ">= 90%",
  },
  platform_availability_pct: {
    id: "platform_availability_pct",
    name: "Platform Availability",
    role: "STATION_MASTER",
    formula: "(Available platforms / Total configured platforms) * 100",
    formulaLatex: "\\frac{P_{\\text{available}}}{P_{\\text{total}}} \\times 100\\%",
    unit: "%",
    reportingWindow: "Current Instant",
    dataSource: "Station Interlocking & Berthing State",
    classification: "MEASURED",
    missingDataSemantics: "Exact measured fraction from interlocking sensors.",
    description: "Proportion of station passenger platforms currently unoccupied and free of maintenance outages.",
    benchmarkTarget: ">= 50%",
  },
  average_arrival_delay_min: {
    id: "average_arrival_delay_min",
    name: "Average Arrival Delay",
    role: "STATION_MASTER",
    formula: "Mean positive delay across all approaching trains: (1/|A|) * sum(max(0, delay_t))",
    formulaLatex: "\\frac{1}{|A|} \\sum_{t \\in A} \\max(0, \\text{delay}_t)",
    unit: "min",
    reportingWindow: "Rolling 60m",
    dataSource: "Section Block Tracking & Radar",
    classification: "CALCULATED",
    missingDataSemantics: "Returns null (dash '—') when no trains are approaching (|A| = 0).",
    description: "Mean delay for all inbound trains approaching station boundaries.",
    benchmarkTarget: "<= 5 min",
  },
  average_departure_delay_min: {
    id: "average_departure_delay_min",
    name: "Average Departure Delay",
    role: "STATION_MASTER",
    formula: "Mean positive delay across stationed departures: (1/|D|) * sum(max(0, delay_t))",
    formulaLatex: "\\frac{1}{|D|} \\sum_{t \\in D} \\max(0, \\text{delay}_t)",
    unit: "min",
    reportingWindow: "Rolling 60m",
    dataSource: "Platform Berthing Ledger",
    classification: "CALCULATED",
    missingDataSemantics: "Returns null (dash '—') when no trains are berthed awaiting departure.",
    description: "Mean delay for trains currently berthed at platforms awaiting line clear or departure signal.",
    benchmarkTarget: "<= 5 min",
  },
  on_time_trains: {
    id: "on_time_trains",
    name: "On-Time Trains",
    role: "STATION_MASTER",
    formula: "Count of monitored trains with delay <= 5 min",
    formulaLatex: "|\\{t \\in T : \\text{delay}_t \\le 5\\}|",
    unit: "trains",
    reportingWindow: "Rolling 60m",
    dataSource: "Timetable Adherence Ledger",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 if no trains are on time.",
    description: "Number of trains complying with the on-time arrival schedule.",
  },
  station_alerts_and_recs: {
    id: "station_alerts_and_recs",
    name: "Alerts & Recommendations",
    role: "STATION_MASTER",
    formula: "Active local conflicts + pending station advisory recommendations",
    formulaLatex: "|C_{\\text{local}}| + |R_{\\text{pending}}|",
    unit: "items",
    reportingWindow: "Active Planning Horizon",
    dataSource: "Independent Validator & Advisory Engine",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 when station is fully clear of alerts.",
    description: "Total pending decisions and active alerts requiring Station Master attention.",
  },
  pending_decisions: {
    id: "pending_decisions",
    name: "Pending Decisions",
    role: "STATION_MASTER",
    formula: "Count of advisory recommendations awaiting local SM approval",
    formulaLatex: "|R_{\\text{pending}}|",
    unit: "items",
    reportingWindow: "Decision Queue",
    dataSource: "Advisory Queue Ledger",
    classification: "CALCULATED",
    missingDataSemantics: "Returns 0 when queue is empty.",
    description: "Advisory platform or hold recommendations awaiting human authorization.",
  },

  // -------------------------------------------------------------------------
  // Section Controller KPIs
  // -------------------------------------------------------------------------
  trains_active: {
    id: "trains_active",
    name: "Active Corridor Trains",
    role: "SECTION_CONTROLLER",
    formula: "Count of trains currently in transit or berthed on corridor tracks",
    formulaLatex: "|T_{\\text{active}}|",
    unit: "trains",
    reportingWindow: "Current Instant",
    dataSource: "Block Section Transits & Track Circuits",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 if corridor is clear of trains.",
    description: "Total active train movements currently occupying section blocks or stations.",
  },
  average_section_delay_min: {
    id: "average_section_delay_min",
    name: "Average Section Delay",
    role: "SECTION_CONTROLLER",
    formula: "Mean projected delay across all active corridor trains: (1/|T|) * sum(delay_t)",
    formulaLatex: "\\frac{1}{|T|} \\sum_{t \\in T} \\text{delay}_t",
    unit: "min",
    reportingWindow: "Corridor Operational Horizon",
    dataSource: "Section Train Movement OS Book",
    classification: "CALCULATED",
    missingDataSemantics: "Returns 0.0 min when all trains on time; returns null if no trains.",
    description: "Average delay across all trains currently on the corridor.",
    benchmarkTarget: "<= 10 min",
  },
  block_occupancy_pct: {
    id: "block_occupancy_pct",
    name: "Block Section Occupancy",
    role: "SECTION_CONTROLLER",
    formula: "(Occupied blocks / Total configured corridor blocks) * 100",
    formulaLatex: "\\frac{B_{\\text{occupied}}}{B_{\\text{total}}} \\times 100\\%",
    unit: "%",
    reportingWindow: "Current Instant",
    dataSource: "Axle Counters & Track Circuits",
    classification: "MEASURED",
    missingDataSemantics: "Exact measured fraction from block instruments.",
    description: "Percentage of corridor block sections occupied by moving or held trains.",
    benchmarkTarget: "<= 70%",
  },
  junction_throat_load_pct: {
    id: "junction_throat_load_pct",
    name: "Junction Throat Load (MLG)",
    role: "SECTION_CONTROLLER",
    formula: "(Simultaneous active throat movements / Throat capacity = 2) * 100",
    formulaLatex: "\\frac{M_{\\text{throat}}}{2} \\times 100\\%",
    unit: "%",
    reportingWindow: "Simulated Horizon",
    dataSource: "Diamond Crossing Interlocking Model",
    classification: "CALCULATED",
    missingDataSemantics: "Returns 0% when no trains are transiting junction throat.",
    description: "Utilization of the Malgaon diamond crossing throat (capacity of 2 parallel moves).",
    benchmarkTarget: "<= 80%",
  },
  throughput_trains_per_hour: {
    id: "throughput_trains_per_hour",
    name: "Corridor Throughput",
    role: "SECTION_CONTROLLER",
    formula: "Completed train transits across section / elapsed simulation hours",
    formulaLatex: "\\frac{T_{\\text{completed}}}{\\Delta t_{\\text{hours}}}",
    unit: "tph",
    reportingWindow: "Rolling 60m",
    dataSource: "Movement Realization Log",
    classification: "CALCULATED",
    missingDataSemantics: "Returns 0.0 tph if no train transits completed.",
    description: "Rate of completed train movements passing through corridor boundaries.",
  },
  delay_propagation_index: {
    id: "delay_propagation_index",
    name: "Delay Propagation Index (DPI)",
    role: "SECTION_CONTROLLER",
    formula: "Secondary knock-on delay minutes / Primary initial delay minutes",
    formulaLatex: "\\text{DPI} = \\frac{\\sum \\Delta_{\\text{secondary}}}{\\sum \\Delta_{\\text{primary}}}",
    unit: "x",
    reportingWindow: "Knock-On Window",
    dataSource: "Secondary Delay Model (Advisory Simulation Heuristic)",
    classification: "HEURISTIC",
    missingDataSemantics: "Returns 0.0x if no secondary delays. Explicitly tagged as HEURISTIC.",
    description: "Simulation heuristic measuring the amplification of secondary knock-on delays.",
    benchmarkTarget: "<= 1.0x",
  },
  trains_delayed: {
    id: "trains_delayed",
    name: "Delayed Corridor Trains",
    role: "SECTION_CONTROLLER",
    formula: "Count of active trains with projected delay > 0 min",
    formulaLatex: "|\\{t \\in T_{\\text{active}} : \\text{delay}_t > 0\\}|",
    unit: "trains",
    reportingWindow: "Rolling 60m",
    dataSource: "Section Train Movement OS Book",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 if all active trains are on time.",
    description: "Number of active trains operating behind their published schedule.",
  },
  conflicts_total: {
    id: "conflicts_total",
    name: "Active Route Conflicts",
    role: "SECTION_CONTROLLER",
    formula: "Count of unresolved headway, single-line crossing, or platform conflicts",
    formulaLatex: "|C_{\\text{active}}|",
    unit: "conflicts",
    reportingWindow: "Active Horizon",
    dataSource: "Independent Constraint Validator",
    classification: "MEASURED",
    missingDataSemantics: "Returns 0 when corridor has zero safety or headway conflicts.",
    description: "Detected physical, headway, or directional movement violations requiring resolution.",
  },
  recovery_clearance_rate_pct: {
    id: "recovery_clearance_rate_pct",
    name: "Recovery Clearance Rate",
    role: "SECTION_CONTROLLER",
    formula: "(Resolved historical conflicts / Total recorded conflicts) * 100",
    formulaLatex: "\\frac{C_{\\text{resolved}}}{C_{\\text{total}}} \\times 100\\%",
    unit: "%",
    reportingWindow: "Cumulative Session",
    dataSource: "Append-Only Audit Trail",
    classification: "CALCULATED",
    missingDataSemantics: "Returns null (dash '—') when total recorded conflicts is 0.",
    description: "Historical resolution rate of conflicts detected during the operational session.",
    benchmarkTarget: ">= 80%",
  },
};

/**
 * Helper to retrieve KPI definition by ID.
 */
export function getKpiDefinition(id: string): KpiDefinition | undefined {
  return KPI_REGISTRY[id];
}

/**
 * Helper to get all KPI definitions for a given role.
 */
export function getKpisForRole(role: "STATION_MASTER" | "SECTION_CONTROLLER"): KpiDefinition[] {
  return Object.values(KPI_REGISTRY).filter(
    (kpi) => kpi.role === role || kpi.role === "BOTH"
  );
}
