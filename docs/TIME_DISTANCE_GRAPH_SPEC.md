# RAILGORITHM v2.6 — Master Time-Distance Train Graph Specification

## 1. Operational Overview & Domain Context

In Indian Railways Section Control Offices, the **Master Train Graph** (commonly referred to as the **Time-Distance Graph**, **String Chart**, or **Controller's Chart**) serves as the primary visual decision-support instrument for Section Controllers.

Section Controllers oversee train movements across multiple stations and block sections. The chart maps movements through time and space simultaneously, enabling operating personnel to:
1. Instantly detect schedule adherence and punctuality deviations.
2. Identify upcoming single-line meets and crossings (cross-overs).
3. Visualize planned overtaking maneuvers (precedence) where faster Mail/Express trains overtake slower Passenger or Freight services.
4. Detect headway compressions and line-capacity bottlenecks before conflicts manifest on physical track circuits.

---

## 2. Mathematical Coordinate System & Geometry

The graph maps a two-dimensional operational coordinate space:

$$\text{Point} = (t, d) \in [T_{\text{start}}, T_{\text{end}}] \times [0, D_{\text{corridor}}]$$

- **Horizontal Axis ($t$):** Time in Indian Standard Time (IST, UTC+05:30), 24-hour notation.
  - Scale: Linear, with major vertical grid lines every 60 minutes and minor dashed ticks every 15 minutes.
  - Viewports: Configurable 2-hour, 3-hour, 6-hour, or 24-hour operational horizons.
  - Current Time Cursor: Vertical high-contrast dashed marker at $t = t_{\text{sim}}$ displaying `$t$ IST`.

- **Vertical Axis ($d$):** Corridor chainage in physical kilometers ($0.0 \text{ km}$ to $60.0 \text{ km}$):
  - **Nandpur Junction (`NDL`):** km $0.0$ (Diamond throat, 3 platforms)
  - **Karanpur (`KRN`):** km $14.0$ (Crossing station, 2 platforms)
  - **Malgaon Junction (`MLG`):** km $32.0$ (Major junction, diamond crossing throat, 3 platforms)
  - **Suryapur (`SRP`):** km $48.0$ (Crossing station, 2 platforms)
  - **Vasanthpur (`VSN`):** km $60.0$ (Terminal station, 2 platforms)

---

## 3. Directional Trajectory Conventions

In Indian Railways operating practice, train movements follow standardized directional slopes:

### 3.1 UP Trains (Nandpur $\rightarrow$ Vasanthpur)
- **Slope:** $\frac{\Delta d}{\Delta t} > 0$ (Sloping downward on screen from km 0 at top to km 60 at bottom).
- **Physical Meaning:** Trains proceeding from origin station Nandpur toward terminal station Vasanthpur.

### 3.2 DOWN Trains (Vasanthpur $\rightarrow$ Nandpur)
- **Slope:** $\frac{\Delta d}{\Delta t} < 0$ (Sloping upward on screen from km 60 at bottom to km 0 at top).
- **Physical Meaning:** Trains returning from Vasanthpur toward Nandpur.

### 3.3 Station Halts & Dwell Time
- **Geometry:** Horizontal line segment at station chainage $d = d_{\text{station}}$.
- **Duration:** $\Delta t_{\text{dwell}} = t_{\text{dep}} - t_{\text{arr}} \ge 1\text{ min}$.
- **Operational Rule:** Meets and crossings on single-line sections must occur strictly during station dwells where loop lines are available.

---

## 4. Multi-Layer Trajectory Visual Semantics

Each train trajectory is rendered with three distinct visual layers:

1. **Scheduled Baseline Trajectory:**
   - **Style:** Faint solid grey line (`#94A3B8`, opacity $0.6$, stroke width $1.5\text{px}$).
   - **Meaning:** Published Working Timetable (WTT) baseline without delays.
2. **Actual Historical Trajectory ($t \le t_{\text{sim}}$):**
   - **Style:** High-contrast solid line color-coded by train category.
   - **Meaning:** Proven real-world movements recorded by track circuits and axle counters.
3. **Projected / Advisory Trajectory ($t > t_{\text{sim}}$):**
   - **Style:** Dashed line (`stroke-dasharray="6 3"`).
   - **Meaning:** Predictive arrival and departure milestones incorporating current delay $\Delta_{\text{proj}}$.

### Train Category Color Coding:
- **Express / Superfast:** Vibrant Blue (`#2563EB`)
- **Passenger:** Emerald Green (`#059669`)
- **Suburban MEMU:** Amber (`#D97706`)
- **Freight Goods:** Deep Purple (`#7C3AED`)

---

## 5. Single-Line Bottleneck Highlighting

The corridor includes two single-line bottleneck sections where simultaneous opposing movements are physically impossible:
- **Section S1 (NDL–KRN):** Block `B1`, km $0.0$ to $14.0$ ($14\text{ km}$, nominal run time $12\text{ min}$).
- **Section S3 (MLG–SRP):** Block `B3`, km $32.0$ to $48.0$ ($16\text{ km}$, nominal run time $14\text{ min}$).

These sections are shaded with an amber background (`#FEF3C7`, opacity $0.35$) with explicit `SINGLE LINE` annotations. Controllers can immediately verify that UP and DOWN lines intersect only at station levels, never inside the shaded single-line zones.

---

## 6. Conflict & Warning Overlays

When the Independent Constraint Validator identifies an active safety or headway conflict:
- A pulsing circular warning glyph (`#DC2626`) is projected at $(t_{\text{start}}, d_{\text{location}})$.
- Accompanied by conflict type label (e.g. `⚠️ HEADWAY_VIOLATION` or `⚠️ OPPOSING_MOVE`).
- Hovering or clicking reveals the conflicting train IDs and validation evidence.

---

## 7. Accessibility & Human Factors

In compliance with railway control room accessibility standards:
- **Direction Filters:** Instant toggling between `All Movements`, `UP Only`, and `DOWN Only`.
- **Time Viewport Scaling:** One-click duration switches ($2\text{h}$, $3\text{h}$, $6\text{h}$).
- **Hover Inspection:** Interactive floating HUD displaying train number, speed class, scheduled vs projected delay, origin/destination, and current location.
- **Accessible Table Fallback:** Direct keyboard-accessible toggle to a structured tabular view for screen readers and high-contrast numerical inspection.
