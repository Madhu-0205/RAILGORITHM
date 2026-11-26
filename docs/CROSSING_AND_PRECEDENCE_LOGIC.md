# Crossing and Precedence Analysis Logic (v2.8)

**Document ID:** SPEC-V28-CPA  
**Status:** Approved  
**Version:** 2.8.0  
**Scope:** Smarter Candidate Action Generation & Railway Operations Heuristics  

---

## 1. Domain Challenge: Crossing and Precedence

In single-line and mixed-traffic railway operations, crossing (meet-pass) and precedence (overtake) decisions represent the Section Controller's most critical responsibilities.

In prior versions (v2.7 and earlier), candidate action generation relied on static values:
- Uniform holds of 5, 10, or 15 minutes regardless of physical block length.
- Blind priority overrides without checking station loop line availability.
- No overtaking logic for following trains on double-line or loop-equipped sections.

RAILGORITHM v2.8 implements **Intelligent Crossing & Precedence Analysis** (`backend/app/domain/candidates.py`).

---

## 2. Dynamic Meet-Pass Hold Calculation

When opposing trains $T_1$ and $T_2$ approach a bidirectional single-line block, static holding intervals either create unnecessary detention or fail to provide adequate clearance.

v2.8 computes the dynamic clearance duration:

$$\text{ClearanceNeeded} = \max\left(3, T_{\text{exit}}^{\text{opposing}}(B) - T_{\text{arrival}}^{\text{held}}(S) + H\right)$$

Where:
- $T_{\text{exit}}^{\text{opposing}}(B)$ is the projected minute when the opposing train exits the single-line block $B$.
- $T_{\text{arrival}}^{\text{held}}(S)$ is the arrival minute of the held train at the crossing station $S$.
- $H$ is the sectional headway buffer (configured at 5 min).

$$\text{HoldMin} = \min\left(\text{MaxHold}_{T_2}, \text{ClearanceNeeded}\right)$$

This guarantees that the held train departs the crossing station immediately after the opposing train clears the block, minimizing idle detention on loop lines.

---

## 3. Station Loop Line Capacity & Simultaneous Reception Evaluation

Holding a train at a station requires verifying track infrastructure:
- **Stations with $> 1$ Platform/Loop Line:** Can accommodate simultaneous reception or hold a lower-priority train while a higher-priority service crosses or overtakes on the main line.
- **Single-Platform Stations:** Holding a train blocks all traffic in both directions. Candidate rationales explicitly flag whether loop capacity exists.

### Priority Ordering Invariant
Indian Railways train classification hierarchy:
1. **Priority 1 (Super-Fast / Premier):** Rajdhani, Shatabdi, Vande Bharat, Tejas.
2. **Priority 2 (Mail / Express):** Superfast Express, Mail, Long-distance Express.
3. **Priority 3 (Passenger / Sub-Urban):** Fast Passenger, MEMU, DEMU, Local.
4. **Priority 4 / 5 (Freight):** Container, Coal/Mineral rakes, Departmental ballast trains.

When conflict occurs between $T_{\text{high}}$ (Priority 1) and $T_{\text{low}}$ (Priority 4), the candidate generator strictly favors holding $T_{\text{low}}$ at the preceding station with loop capacity.

---

## 4. Overtaking on Double-Line and Loop Sections

When a higher-priority service follows a slower train in the same direction:
1. The candidate generator identifies the next upcoming station along the route with multiple platforms (`platforms > 1`).
2. It generates a specialized loop overtake candidate:
   `Hold {slow_train} at {station} for 8 min (Loop overtake)`
3. Rationale explicitly cites loop berthing to allow overtaking without causing headway compression on the open section.
