# Predictive Train Regulation Specification (v2.8)

**Document ID:** SPEC-V28-PTR  
**Status:** Approved  
**Version:** 2.8.0  
**Domain:** Railway Traffic Management & Forward Trajectory Projection  

---

## 1. Operational Overview & Problem Definition

In traditional section control, train regulation is predominantly reactive: controllers hold or reassign trains when resource conflicts or physical headway violations are already imminent. This latency leads to cascading delays, buffer depletion at loop lines, and panic regulation decisions.

RAILGORITHM v2.8 introduces the **Predictive Train Regulation Engine** (`backend/app/domain/projection.py`), providing:
1. Multi-horizon projection across 30, 60, and 90-minute operational windows.
2. Dynamic delay development classification (`INCREASING`, `DECREASING`, `STABLE`) with root cause identification.
3. Downstream knock-on delay propagation modeling identifying all secondary affected trains.
4. Longitudinal station-by-station trajectory comparisons contrasting "No Action (Baseline)", "Recommended Action", and "Alternative Action".
5. Decision urgency categorization and unavoidable conflict horizons.

---

## 2. Multi-Horizon Projection Architecture

Forward trajectory projection projects traffic states without mutating active simulation clocks across three operational horizons:

```
[Now] ------------------> [Now + 30 min] ------------------> [Now + 60 min] ------------------> [Now + 90 min]
          TACTICAL                     OPERATIONAL                    STRATEGIC
   Immediate block clearance      Junction throat coordination   Sectional throughput & meeting
   and headway separation         and station platform berths    points optimization
```

### Horizon Semantics
- **30-Minute Tactical Horizon:** Focuses on active section blocks, immediate station halts, and headway compressions. Identified conflicts require urgent action.
- **60-Minute Operational Horizon:** Evaluates approaching station platforms, junction convergences, and crossing meets between opposing traffic on single-line sections.
- **90-Minute Strategic Horizon:** Projects downstream arrivals at corridor terminals, overtakes on double-line sections, and maintenance block interface boundaries.

Each horizon output includes:
- `target_time`: Wall clock projection timestamp (HH:MM).
- `total_conflicts`: Total projected resource overlaps.
- `actionable_conflicts`: Operational conflicts excluding background delay alerts.
- `critical_conflicts`: Non-negotiable safety or physical block violations.
- `projected_total_delay_min`: Cumulative projected delay across all active trains.
- `conflict_types`: Categorical taxonomy of upcoming bottlenecks.

---

## 3. Delay Development Detection & Root Cause Analysis

Every train's trajectory is continuously analyzed using `classify_delay_trend(train, state)`:

### Trend Categories
$$\text{Trend} = \begin{cases} 
\text{INCREASING} & \text{if } \text{ProjDelay}_{90} > \text{Delay}_{\text{current}} + 2 \\
\text{DECREASING} & \text{if } \text{ProjDelay}_{90} < \text{Delay}_{\text{current}} - 2 \\
\text{STABLE} & \text{otherwise}
\end{cases}$$

$$\text{Rate of Progression (min/hr)} = \frac{\text{ProjDelay}_{90} - \text{Delay}_{\text{current}}}{1.5}$$

### Primary Operational Causes
- `TERMINAL_DWELL`: Ready departure time exceeds working timetable scheduled departure at passenger or freight terminals.
- `REGULATION_HOLD`: Train is subject to an active controller regulation hold (`hold_until_min > now`).
- `PLATFORM_UNAVAILABILITY`: Platform capacity saturation or maintenance outage at berthing station.
- `BLOCK_CLOSURE`: Active engineering block or speed-restricted closure along forward path.
- `SPEED_RESTRICTION`: Temporary speed restriction active on forward block.
- `HEADWAY_COMPRESSION`: Caution aspect progression following slower preceding train in absolute block section.
- `CASCADING_DELAY`: Delay propagated from preceding junction or sectional conflict.
- `ON_TIME`: Operating within normal punctuality tolerances.

---

## 4. Downstream Knock-On Propagation Model

When a train suffers an unmitigated delay, its occupancy window expands. The knock-on propagation engine (`compute_knock_on_propagation`) computes the secondary impact:

$$\text{Overlap}_{B} = \max\left(0, W_{\text{delayed}}^{\text{exit}}(B) - W_{\text{other}}^{\text{entry}}(B)\right)$$

Where $W(B)$ represents the projected occupancy interval $[\text{entry}, \text{exit}]$ on block or platform $B$.

### Propagation Output Structure
- `delayed_train_id`: Identifier of the primary source train.
- `affected_train_count`: Number of downstream trains whose schedules will be delayed.
- `total_knock_on_delay_min`: Cumulative minutes of delay transferred to other trains.
- `affected_trains`: Detailed roster containing train ID, priority, knock-on minutes, and bottleneck resource.
- `bottleneck_locations`: Physical blocks and stations where congestion will concentrate.

---

## 5. Comparative Station-by-Station Trajectory Timeline

To enable informed controller evaluation, `compute_comparative_timeline` generates a synchronized station-by-station trajectory table:

| Station ID | Scheduled Arrival | No Action (Baseline) | Recommended Action | Alternative Action | Delay Savings |
|:-----------|:------------------|:---------------------|:-------------------|:-------------------|:--------------|
| NDL        | 07:15             | 07:15                | 07:15              | 07:15              | 0 min         |
| BLK-1      | 07:22             | 07:26 (+4)           | 07:22 (+0)         | 07:24 (+2)         | +4 min        |
| VSN        | 07:35             | 07:50 (+15)          | 07:42 (+7)         | 07:48 (+13)        | +8 min        |

### Net Delay Savings
$$\Delta_{\text{savings}} = \text{FinalDelay}_{\text{baseline}} - \text{FinalDelay}_{\text{recommended}}$$

---

## 6. Decision Urgency & Action Window

The Section Controller's decision urgency is classified based on the earliest actionable conflict time:

$$\text{TimeToAct} = \max(0, T_{\text{conflict}}^{\text{earliest}} - T_{\text{now}})$$

- **IMMEDIATE ($\text{TimeToAct} < 5\text{ min}$):** Conflict is imminent. Delayed action guarantees train stoppage at home signal or section gridlock.
- **NEAR_TERM ($5 \le \text{TimeToAct} \le 15\text{ min}$):** Active regulation window. Controller can implement advance loop line holds or speed adjustments.
- **PLANNED ($\text{TimeToAct} > 15\text{ min}$):** Optimal strategic regulation window. Precedence ordering can be altered with zero emergency braking.
