# RAILGORITHM Dashboard Design System Specification

## 1. Design Philosophy

RAILGORITHM v2.5 modernizes railway operational dashboards by marrying **traditional Indian Railways operational familiarity** with a **modern enterprise control-center interface**.

The interface is engineered to eliminate visual noise:
- **Not a generic SaaS analytics template**: No vanity marketing metrics, generic line graphs without domain semantics, or excessive whitespace.
- **Not a cryptocurrency trading platform**: No pulsating tickers, high-frequency price graphs, or dark-mode neon glows.
- **Not a futuristic sci-fi AI interface**: No pseudo-holographic HUD elements, glowing rings, or fabricated confidence dials.
- **A genuine Railway Traffic Management & Decision-Support System**: Clean high-contrast typography, high information density, unambiguous signal/status colors, accessible tabular records, and physical track schematic representations familiar to Station Masters and Section Controllers.

---

## 2. 10-Second Operational Rule

Within 10 seconds of opening the dashboard, a railway operating employee must immediately know:
1. **What is happening?** (Active trains moving, on-time percentage, throughput).
2. **Where is it happening?** (Station platforms, single-line bottleneck blocks, junction diamond crossings).
3. **Which trains or sections are affected?** (Specific train numbers, scheduled vs actual arrival times, block IDs).
4. **Why is there a delay or conflict?** (Platform dwell extension, line-clear headway violation, maintenance outage).
5. **What requires immediate attention?** (Critical route conflicts, diamond crossing throat saturation).
6. **What actions or recommendations are available?** (Advisory CP-SAT / PPO hold/divert options with validation status).

---

## 3. Color Tokens & Semantic Palette

The color system strictly separates **navigation structure**, **operational workspace**, and **safety/status indications**. Status is **never communicated by color alone**; it is always accompanied by an explicit text badge and iconic indicator.

### A. Navigation & Workspace

| Token | Hex / CSS Value | Operational Usage |
| :--- | :--- | :--- |
| `--nav-bg` | `#101B2B` | Primary Sidebar background (Deep Railway Navy) |
| `--nav-bg-secondary` | `#17263B` | Active nav items, hovered states, user chip background |
| `--nav-text` | `#F8FAFC` | Primary sidebar typography |
| `--nav-text-muted` | `#94A3B8` | Subordinate labels and scope indicators in navigation |
| `--nav-active` | `#2563EB` | Active navigation indicator bar (3px solid) |
| `--bg` | `#F1F5F9` | Primary workspace canvas (Clean Slate Grey) |
| `--panel` | `#FFFFFF` | Card, container, and table background (Pure White) |
| `--panel-strong` | `#F8FAFC` | Table headers, muted panels, and secondary card footers |
| `--border` | `#E2E8F0` | Structural card borders and header separators |
| `--border-soft` | `#CBD5E1` | Subtle divider lines and table row separators |
| `--text` | `#0F172A` | Primary workspace typography (High Contrast Slate) |
| `--text-muted` | `#64748B` | Secondary notes, timestamps, units, and captions |

### B. Railway Operational Status Tokens

| Operational State | Primary Accent | Soft Background | Border Token | Text Token | Icon | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Normal / Available** | `#16A34A` | `#DCFCE7` | `#86EFAC` | `#15803D` | ✓ | Clear block section, available platform berth, on-time train |
| **Warning / Attention** | `#D97706` | `#FEF3C7` | `#FDE68A` | `#B45309` | ⚠ | Minor delay (5–15m), block occupied, high throat load |
| **Critical / Conflict** | `#DC2626` | `#FEE2E2` | `#FECACA` | `#B91C1C` | ✕ | Track closure, route headway conflict, saturated junction |
| **Information / AI** | `#2563EB` | `#DBEAFE` | `#BFDBFE` | `#1D4ED8` | ℹ | Advisory recommendation, pending human decision |
| **No Data / Neutral** | `#64748B` | `#F1F5F9` | `#CBD5E1` | `#475569` | ● | Empty observation window, unobserved historical metric |

---

## 4. Typography & Numerical Hierarchy

- **Font Family**: System native modern sans-serif (`Inter`, `Segoe UI`, `-apple-system`, `sans-serif`).
- **Monospace Font**: Fixed-width tabular digits (`SFMono-Regular`, `JetBrains Mono`, `monospace`) for train IDs, clock times, kilometrage, and coordinates.
- **Tabular Numerals**: All KPI metrics and timetable times use `font-variant-numeric: tabular-nums` to prevent horizontal jitter during live ticker refreshes.
- **Type Scale**:
  - `h1`: 1.65rem (26px), weight 700 — Dashboard and Page Headings.
  - `h2`: 1.10rem (18px), weight 650 — Section and Panel Headers.
  - `h3`: 0.98rem (16px), weight 600 — Card Titles and Modal Headers.
  - `body`: 0.88rem (14px), weight 400 — General descriptions and table cells.
  - `caption/small`: 0.76rem (12px), weight 500 — Field labels, hints, and timestamps.
  - `kpi-value`: 1.55rem (25px), weight 700 — Metric numbers.

---

## 5. Component Standards

### A. Operational KPI Cards (`KpiCard`)
Every KPI card is an authoritative unit of operational status and must provide:
1. **Label**: Plain-language railway operational name.
2. **Value & Unit**: Formatted number or string, rendering `"—"` if `null`.
3. **Quality Badge**: Data classification pill:
   - `MEASURED`: Directly recorded from physical block detection or station log.
   - `CALCULATED`: Authoritatively computed by backend formula.
   - `PREDICTED`: Projected schedule arrival or departure.
   - `HEURISTIC`: Simulation estimate (e.g. Delay Propagation Index).
   - `NO_DATA`: Window unobserved.
4. **Tone Indicator**: Semantic border bar and icon (✓, ⚠, ✕, ℹ, ●).
5. **Contextual Metadata**: Reporting period, data source, and descriptive tooltip.

### B. Responsive Data Tables (`table-wrapper`)
In conformance with modern web accessibility guidelines:
- Wrapped in `<div tabIndex={0} role="region" aria-label="...">`.
- Sticky column headers (`thead th`) with solid `#F8FAFC` background to maintain context during vertical scrolling.
- Horizontal scroll container with clear overflow bounds.
- Zebra row hover (`#F8FAFC`) with high-contrast text.

### C. Native SVG Corridor Diagrams (`RailwayCorridorDiagram`)
- Implemented as zero-dependency native SVG with full accessibility tags: `<svg role="img" aria-label="...">`, `<title>`, and `<desc>`.
- Double-track vs single-track graphical differentiation.
- Real-time train position markers showing Train Number and direction arrow (`▶` for UP, `◀` for DN).
- Diamond junction throat graphical representation for Malgaon Junction (`MLG`).
- Dynamic conflict warning indicators positioned over affected track segments.

---

## 6. Accessibility & Responsiveness

- **WCAG 2.1 AA Compliance**: All text elements meet or exceed 4.5:1 contrast ratios against light and dark backgrounds.
- **Focus Rings**: Interactive elements provide explicit 2px focus outlines (`outline: 2px solid var(--accent-border)`).
- **Keyboard Navigation**: Tables and horizontal scroll regions are keyboard-scrollable (`tabIndex={0}`).
- **Responsive Layout**:
  - Desktop (>1080px): 240px persistent deep-navy sidebar + full multi-column dashboard grid.
  - Tablet / Laptop (768px–1080px): Single-column stacked layout with full horizontal table scroll regions.
  - Mobile (<768px): Compact header and collapsed filter controls.
