# RAILGORITHM v2.9 — CROSSING & PRECEDENCE INTELLIGENCE

## 1. Context & Operational Challenge

Single-line sections and convergence junctions represent the most severe capacity bottlenecks on the Indian Railways network. On a single-line block section (e.g. S1: Nandpur `NDL` to Karanpur `KRN`), opposing train movements cannot occupy the section concurrently under the Absolute Block System (HC-003).

When two opposing trains approach a single-line section, the Section Controller must make a critical operational decision:
1. Which train should proceed first into the single-line section?
2. Where should the meet-pass take place?
3. What is the optimal sequence permutations across train priority tiers?

In previous iterations, the recommendation engine generated only a single heuristic meet-pass suggestion without evaluating the inverse sequence or alternative crossing stations. **RAILGORITHM v2.9** implements full **Sequence Permutation & Spatial Alternative Analysis**.

---

## 2. Sequence Permutation Generation

When a single-line crossing conflict is detected, the candidate generation engine (`backend/app/domain/candidates.py`) evaluates multiple distinct sequence permutations:

### 2.1 Option 1A: Primary Sequence ($A \prec B$)
- **Operational Strategy**: Higher-priority train $A$ (e.g. Rajdhani or Superfast Express) is granted line clear to traverse the single-line section without stopping.
- **Regulation Action**: Lower-priority train $B$ (e.g. Freight or Mail/Express) is held on the loop siding at the boundary station for the required clearing interval.
- **Tag**: `{train_A}_BEFORE_{train_B}`
- **Calculated Hold**:
  $$\text{Hold} = \min\left( \text{MaxHold}_B, \; \Delta t_{\text{conflict}} + t_{\text{headway}} \right)$$

### 2.2 Option 1B: Inverse Sequence ($B \prec A$)
- **Operational Strategy**: The lower-priority train $B$ is permitted to traverse the single-line section first, while the higher-priority train $A$ is held at the opposite station.
- **Operational Justification**:
  - Train $A$ is already delayed beyond its recovery threshold, and holding it briefly allows train $B$ to clear an otherwise deadlocked block without causing cumulative delay.
  - Train $B$ is close to clearing the block, whereas train $A$ is still running through an approach section.
- **Tag**: `{train_B}_BEFORE_{train_A}`

### 2.3 Option 1C: Spatial Relocation to Junction Station (e.g., `MLG`)
- **Operational Strategy**: Instead of forcing the meet at a small single-platform crossing station with limited passing loops, advance the meet point to a multi-platform junction station (Malgaon Junction `MLG`, km 50).
- **Benefits**:
  - `MLG` features multiple platform reception lines and goods loop sidings.
  - Allows concurrent passenger boarding while waiting for opposing traffic to clear, avoiding passenger detention on unscheduled sidings.

---

## 3. Loop Line Overtaking on Double-Line Sections

For same-direction traffic on double-line sections (e.g. Section 2: Karanpur `KRN` to Malgaon `MLG`), high-speed express services frequently overtake slower freight or stopping passenger trains.

### 3.1 Precedence & Overtake Rules
1. **Loop Line Availability**: Overtaking can only be recommended at stations configured with at least two running platforms or loop sidings.
2. **Headway Assurance**: The held service must remain on the loop line until the overtaking service has cleared the advance block and restored the automatic/absolute block headway ($h \ge 5\text{ min}$).
3. **Crew Hours of Employment Regulation (HER)**: The engine verifies that holding a freight service does not cause loco pilots or train managers to breach maximum continuous duty hours without crew-changing facilities.

---

## 4. Constraint Feasibility & Independent Validator Gate

Every generated crossing and precedence alternative must pass the independent constraint validator (`validator.py`):

```
Candidate Generated
    ↓
Check HC-001 (Block Exclusivity)
    ↓
Check HC-003 (Single-Line Crossing Exclusivity)
    ↓
Check HC-005 (Platform & Loop Capacity)
    ↓
Cloned Simulation Measurement (Outcome Delay & OTP)
    ↓
Eligible Candidate Pool
```

- If an action routes a train into an occupied single-line block, validator flags **`INVALID` (HC-003 Violation)**.
- If an action attempts a loop overtake at a single-platform halt, validator flags **`INVALID` (HC-005 Platform Outage)**.
- Only candidates with valid outcomes enter the ranked recommendation pool.

---

## 5. Explicit Handling of `NO_FEASIBLE_ALTERNATIVE`

When infrastructure closures, severe delay ripple, or full station outages render every conceivable regulation action infeasible:
1. **Zero Fabrication**: The system strictly refuses to manufacture a synthetic or unverified recommendation.
2. **Status Reporting**: Returns `evidence_status = "NO_FEASIBLE_SOLUTION"`.
3. **Diagnostic Report**: Details the binding constraints (e.g., all 4 block sections closed, all loop sidings occupied).
4. **Advisory Posture**: Alerts the Section Controller that human manual regulation, emergency pilot working, or train cancellation is required under General & Subsidiary Rules (G&SR).
