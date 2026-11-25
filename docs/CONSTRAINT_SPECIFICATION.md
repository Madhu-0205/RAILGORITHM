# RAILGORITHM 2.0 — Constraint Specification

**Document Version:** 2.0.0  
**Specification Key:** `constraints-2.0.0`  
**Classification:** Formal Railway Traffic Management Constraints  
**System Scope:** Simulation-Only Decision Support  

---

## 1. Principles of Independent Constraint Validation

In RAILGORITHM 2.0, the **Constraint Validator is architecturally and computationally decoupled** from both the CP-SAT Optimizer and the PyTorch PPO Policy. 

- Neither CP-SAT nor PPO can declare an invalid candidate executable.
- Every candidate action (heuristics, baseline, or CP-SAT schedule) is subjected to forward trajectory simulation in a cloned state.
- Hard constraints must be satisfied unconditionally; violation results in immediate rejection of the candidate (`eligible = False`).
- Soft constraints represent operational trade-offs and quality metrics minimized by the objective function.

```
+--------------------------------------------------------------------+
|                        Candidate Generator                         |
|  (Heuristic Holds / Platform Reassignments / CP-SAT Full Schedule) |
+---------------------------------+----------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
|               Independent Hard-Constraint Validator                |
|      (Topology, Block Exclusivity, Headway, Closures, Holds)       |
+---------------------------------+----------------------------------+
                                  |
                   +--------------+--------------+
                   |                             |
             [Passes All HC]              [Fails Any HC]
                   |                             |
                   v                             v
+------------------------------------+  +----------------------------+
|        Eligible Candidates         |  |   Ineligible Candidates    |
|   (Ranked by PPO / Delay Metric)   |  |   (Recorded with Violations|
+------------------------------------+  |    Refused Execution Gate) |
                                        +----------------------------+
```

---

## 2. Hard Constraints (HC-001 to HC-013)

Hard constraints define absolute physical and safety boundaries. Violation of any hard constraint constitutes a fatal failure mode.

### HC-001: Block Exclusivity (Spatial Disjointness)
- **Scope:** Block level
- **Mathematical Statement:** For any block $b$ and distinct trains $i \neq j$:
  $$[entry_{i,b}, exit_{i,b}) \cap [entry_{j,b}, exit_{j,b}) = \emptyset$$
- **Enforced By:** Simulation Engine, Conflict Detector, CP-SAT `AddNoOverlap`, Independent Validator.
- **Operational Hazard:** Collision hazard.

### HC-002: Minimum Longitudinal Headway
- **Scope:** Block / Section level
- **Mathematical Statement:** For consecutive trains $i$ followed by $j$ in the same direction on block $b$:
  $$entry_{j,b} \ge exit_{i,b} + headway(b)$$
- **Enforced By:** Conflict Detector (`HEADWAY`), CP-SAT interval precedence, Validator.
- **Operational Hazard:** Rear-end collision risk, signalling trip.

### HC-003: Single-Line Directional Exclusivity (No Opposing Movement)
- **Scope:** Single-line section ($S_1, S_3$)
- **Mathematical Statement:** If train $i$ runs UP and train $j$ runs DOWN on single-line section $S$:
  $$entry_{j,S} \ge exit_{i,S} + headway(S) \quad \lor \quad entry_{i,S} \ge exit_{j,S} + headway(S)$$
- **Enforced By:** Conflict Detector (`SINGLE_LINE_CROSSING`), CP-SAT `AddNoOverlap`, Validator.
- **Operational Hazard:** Head-on collision hazard.

### HC-004: Maximum Station Hold Policy
- **Scope:** Train / Station level
- **Mathematical Statement:** For train $i$ with category priority class $c(i)$:
  $$hold\_duration_i \le max\_hold(c(i))$$
- **Enforced By:** Candidate Generator, Independent Validator.
- **Operational Hazard:** Crew expiry, passenger stranding, systemic gridlock.

### HC-005: Station Platform Track Capacity
- **Scope:** Station level
- **Mathematical Statement:** At any station $s$ and time $t$:
  $$\sum_{i} \mathbf{1}_{\{at\_station(i, s, t)\}} \le |platforms(s)| - outages(s, t)$$
- **Enforced By:** Conflict Detector (`PLATFORM_CAPACITY`), CP-SAT platform assignment, Validator.
- **Operational Hazard:** Station throat lockup, platform overrun.

### HC-006: Junction Throat Concurrent Movements
- **Scope:** Junction stations (`NDL`, `MLG`)
- **Mathematical Statement:** For throat area at junction $s$, concurrent crossing movements cannot exceed throat capacity $K_{throat}$:
  $$\sum_{i} \mathbf{1}_{\{transiting\_throat(i, s, t)\}} \le K_{throat}(s)$$
- **Enforced By:** Conflict Detector (`JUNCTION_CONFLICT`), CP-SAT `AddCumulative`, Validator.
- **Operational Hazard:** Interlocking conflict, derailment risk at diamond crossings.

### HC-007: Block Closure and Possession Exclusion
- **Scope:** Block level
- **Mathematical Statement:** For any block closure on block $b$ over window $[t_{start}, t_{end}]$:
  $$\forall i: \quad [entry_{i,b}, exit_{i,b}) \cap [t_{start}, t_{end}) = \emptyset$$
- **Enforced By:** Conflict Detector (`BLOCK_CLOSURE`), CP-SAT fixed unavailability, Validator.
- **Operational Hazard:** Collisions with maintenance equipment or open track works.

### HC-008: Running Train Non-Preemption
- **Scope:** Train state level
- **Mathematical Statement:** Holds can only be assigned to a train if $state(i) \in \{AT\_STATION, NOT\_STARTED\}$. If $state(i) == IN\_SECTION$, $hold(i) = 0$.
- **Enforced By:** Candidate Generator, Validator.
- **Operational Hazard:** Unplanned braking in intermediate sections.

### HC-009: Topological Route Admissibility
- **Scope:** Network level
- **Mathematical Statement:** A train may only traverse blocks and stations that form an admissible contiguous path in the directed physical network graph.
- **Enforced By:** Simulation Router, Validator.
- **Operational Hazard:** Wrong-route setting.

### HC-010: Speed Restriction Compliance
- **Scope:** Block / Section level
- **Mathematical Statement:** Train speed cannot exceed the lower of the train's maximum speed and the active section speed restriction:
  $$v_{i,b} \le \min(v_{max}(i), v_{limit}(b))$$
- **Enforced By:** Kinematic Projection, Validator.
- **Operational Hazard:** Track stress, derailment on curves.

### HC-011: Monotonic State Progression
- **Scope:** Simulation temporal state
- **Mathematical Statement:** For simulation time $t$, state version $V$, and any approved action applied at version $V$:
  $$V_{apply} = V_{recommendation} \quad \text{and} \quad t_{apply} \ge t_{recommendation}$$
- **Enforced By:** Human Decision Service (`test_stale_recommendation_cannot_be_approved`).
- **Operational Hazard:** Applying decisions based on obsolete network snapshots.

### HC-012: Explicit Human Authorization Gate
- **Scope:** Control workflow
- **Mathematical Statement:** No recommendation may mutate the simulation state without:
  $$confirm\_apply == True \quad \land \quad len(rationale) \ge 5 \quad \land \quad role \in AUTHORIZED\_ROLES$$
- **Enforced By:** FastAPI Decision Router, Decision Service.
- **Operational Hazard:** Autonomous AI actuation without human oversight.

### HC-013: Append-Only Cryptographic Audit Invariance
- **Scope:** Security & Audit
- **Mathematical Statement:** For event $k \ge 1$:
  $$H_k = \text{SHA256}(H_{k-1} \,\|\, event\_data_k) \quad \text{and} \quad H_{head} == H_{last} \quad \text{and} \quad N_{head} == k$$
- **Enforced By:** Database triggers (`audit_events_no_update`, `audit_events_no_delete`, `audit_chain_head_no_delete`), `verify_audit_chain`.
- **Operational Hazard:** Undetected log tampering, historical falsification.

---

## 3. Soft Constraints (SC-001 to SC-004)

Soft constraints define service quality objectives. They are optimized by CP-SAT and evaluated during candidate ranking.

### SC-001: Weighted Delay Minimization
- **Objective:** $\min \sum_{i} priority(i) \times \max(0, arrival_i - timetable_i)$
- **Weighting:** EXPRESS (weight 5), PASSENGER (weight 3), MEMU (weight 2), FREIGHT (weight 1).

### SC-002: Maximum Individual Delay (Minimax Fairness)
- **Objective:** $\min \max_{i} (arrival_i - timetable_i)$
- **Purpose:** Prevents severe starvation of low-priority traffic.

### SC-003: Residual Conflict and Cascading Delay Penalty
- **Objective:** $\min \sum_{c \in residual\_conflicts} severity\_weight(c)$
- **Severity Weights:** CRITICAL (ineligible), HIGH (50), MEDIUM (20), LOW (5).

### SC-004: Platform Reassignment and Timetable Stability
- **Objective:** Minimize unnecessary platform track changes and schedule churn relative to booked timetable.

---

## 4. Constraint Enforcement Matrix

| ID | Constraint Name | Kind | Scope | Detector | Optimizer | Validator | Runtime API Gate |
|---|---|---|---|---|---|---|---|
| `HC-001` | Block Exclusivity | HARD | BLOCK | Yes | Yes | Yes | Yes |
| `HC-002` | Minimum Headway | HARD | BLOCK | Yes | Yes | Yes | Yes |
| `HC-003` | Single-Line Meet | HARD | SECTION | Yes | Yes | Yes | Yes |
| `HC-004` | Max Hold Policy | HARD | TRAIN | No | Bounds | Yes | Yes |
| `HC-005` | Platform Capacity| HARD | STATION | Yes | Yes | Yes | Yes |
| `HC-006` | Junction Throat | HARD | JUNCTION| Yes | Cumulative| Yes | Yes |
| `HC-007` | Block Closure | HARD | BLOCK | Yes | Fixed | Yes | Yes |
| `HC-008` | Non-Preemption | HARD | TRAIN | No | Variables | Yes | Yes |
| `HC-009` | Topological Path | HARD | NETWORK | No | Graph | Yes | Yes |
| `HC-010` | Speed Restriction| HARD | BLOCK | Yes | Variables | Yes | Yes |
| `HC-011` | Non-Staleness | HARD | STATE | No | No | No | Yes (HTTP 409) |
| `HC-012` | Human Gate | HARD | WORKFLOW| No | No | No | Yes (HTTP 422) |
| `HC-013` | Audit Hash Chain | HARD | AUDIT | No | No | No | DB Triggers |
| `SC-001` | Weighted Delay | SOFT | SYSTEM | No | Obj Term | Scored | Reported |
| `SC-002` | Max Delay | SOFT | SYSTEM | No | Obj Term | Scored | Reported |
| `SC-003` | Delay Risk | SOFT | SYSTEM | Yes | Obj Term | Scored | Reported |
| `SC-004` | Platform Stability| SOFT | STATION | No | Obj Term | Scored | Reported |
