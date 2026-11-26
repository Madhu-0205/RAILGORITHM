# RAILGORITHM v2.8.1 — Master Control Graph UI Repair & Filter Specification

## 1. Executive Summary & Problem Diagnosis

In RAILGORITHM v2.8, the Master Control Graph (Time-Distance String Chart) suffered from severe visual usability defects that rendered its controls unreadable and ineffective:

1. **Dark-on-Dark Contrast Failure:**
   The chart controls container had a dark navy background (`#0F172A`). Button elements used `.button-ghost`, which inherited default text color `var(--text)` (`#0F172A`). Dark navy text on a dark navy background made button labels invisible and indistinguishable from empty space.
2. **Missing Granular Movement Filters:**
   Traffic controllers could not isolate UP movements (`NDL → VSN`, upward-sloping trajectories) from DOWN movements (`VSN → NDL`, downward-sloping trajectories).
3. **Missing Category Filtering:**
   Controllers could not isolate Superfast/Express services from Freight or Local MEMU trains to diagnose precedence bottlenecks.
4. **Missing Station Corridors & Visual Highlighting:**
   Controllers had no quick visual mechanism to highlight a specific station across the 100-kilometer corridor.
5. **No One-Click Reset Mechanism:**
   Once filters were altered, there was no obvious way to return to the nominal corridor state.
6. **No Toggleable Operational Layers:**
   Caution bands (TSR/PSR), single-line bottleneck segments, station dwell horizontal bars, and meeting points were either cluttering the view or unconfigurable.

---

## 2. Architectural Redesign & Visual Hierarchy

In release v2.8.1, the graph toolbar was completely redesigned with a dedicated CSS component architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  GRAPH CONTROLS TOOLBAR (Dark Navy #0F172A, Border #1E293B)                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  Movements: [ All Movements ] [ UP (NDL → VSN) ] [ DOWN (VSN → NDL) ]                 │
│  Category:  [ All Categories ▾ ]                                                       │
│  Station:   [ All Stations (Full Corridor) ▾ ]                                         │
│  Search:    [ Filter Train ID / Name...      ]  [ ↺ Reset Filters ]                   │
│  Time View: [ 1h ] [ 3h ] [ 6h ] [ 12h ]  [ ◀ -30m ] [ Center Now ⏱ ] [ +30m ▶ ]       │
│  Options:   [ ⚙ Overlays & Layers ▾ ]  [ ▤ Accessible Table View ]                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 CSS Styling System (`.graph-toolbar`, `.graph-btn`, `.graph-select`, `.graph-input`)

In `frontend/src/styles.css`, explicit high-contrast classes were introduced:

```css
.graph-toolbar {
  background: #0F172A;
  border: 1px solid #1E293B;
  border-radius: 8px;
  padding: 10px 14px;
  color: #F8FAFC;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.graph-btn {
  background: #1E293B;
  border: 1px solid #334155;
  color: #F8FAFC !important;
  font-weight: 500;
  font-size: 0.78rem;
  padding: 5px 11px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
}

.graph-btn:hover {
  background: #334155;
  border-color: #64748B;
  color: #FFFFFF !important;
}

.graph-btn.active {
  background: #2563EB !important;
  border-color: #3B82F6 !important;
  color: #FFFFFF !important;
  box-shadow: 0 0 8px rgba(37, 99, 235, 0.4);
}

.graph-btn-reset {
  background: #334155;
  border-color: #475569;
  color: #F59E0B !important;
}
```

---

## 3. Operational Feature Matrix

| Feature | Control Mechanism | Visual Presentation | Operational Value |
|---|---|---|---|
| **Directional Filtering** | Segmented button group (`All`, `UP`, `DOWN`) | Active button highlights blue `#2563EB` with glow. Opposite direction paths dimmed to 10% opacity (`stroke-opacity="0.10"`). | Controllers can instantly isolate opposing moves on single-line sections. |
| **Train Category** | Dropdown select (`All`, `Express`, `Passenger`, `Freight`, `MEMU`) | Non-matching train trajectory lines dimmed to 10% opacity. | Allows diagnosing freight path delays versus high-priority passenger services. |
| **Station Highlight** | Dropdown select (`NDL`, `KRN`, `MLG`, `SRP`, `VSN`) | Selected station horizontal line glows amber (`stroke="#F59E0B"`, `strokeWidth="2.5"`). | Pinpoints station milepost and dwell interactions across the corridor. |
| **Train Search** | Real-time text input | Matches train ID or name; non-matching lines dimmed to 10%. | Direct path inspection for a specific delayed or priority train. |
| **One-Click Reset** | Button `↺ Reset Filters` | Resets direction, category, station, search, and time duration to corridor defaults. | Immediately restores full operational picture in one click. |
| **Time Window Duration** | Segmented buttons (`1h`, `3h`, `6h`, `12h`) | Adjusts time axis scaling dynamically; default is 3 hours. | Supports both micro-conflict resolution and macro shift planning. |
| **Time Panning** | Buttons (`◀ -30m`, `Center Now ⏱`, `+30m ▶`) | Shifts time window back, centers on simulated clock, or looks ahead. | Allows retrospective incident analysis and predictive lookahead. |
| **Operational Overlays Panel** | Collapsible dropdown with checkboxes | Renders TSR/PSR yellow caution bands, meet-pass crossing glyphs (`⇄`), dwell bars, conflicts. | Separates signal/track constraints from pure train paths. |
| **Accessible Table View** | Toggle button | Renders semantic HTML table of all train milestones, arrivals, and departures. | WCAG 2.1 AA accessible fallback for non-graphical inspection. |

---

## 4. Verification Evidence

- **Unit & Component Testing:** `src/components/TimeDistanceGraph.test.tsx` (8 passed).
- **Screenshot Verification:**
  - `docs/screenshots/v2_8_1-mcg-default-1440px.png`: Displays high-contrast toolbar on dark navy background.
  - `docs/screenshots/v2_8_1-mcg-overlays-1440px.png`: Displays expanded operational overlays panel.
  - `docs/screenshots/v2_8_1-mcg-up-1440px.png`: Displays isolated UP train trajectories.
  - `docs/screenshots/v2_8_1-mcg-station-filter-1440px.png`: Displays highlighted Malgaon Junction station line.
  - `docs/screenshots/v2_8_1-mcg-1920px.png`: Displays responsive widescreen rendering at 1920x1080.
