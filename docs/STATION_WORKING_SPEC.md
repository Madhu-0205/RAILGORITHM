# RAILGORITHM v2.6 — Station Working & Interlocking Diagram Specification

## 1. Domain Purpose & Operational Scope

In Indian Railways station operations, the Station Master (SM) manages train reception, platform berthing, shunting, and train dispatch within the station yard limits.

The **Station Working Diagram** in RAILGORITHM v2.6 mirrors modern Indian Railways **Electronic Interlocking (EI) Video Display Units (VDU)** and **Panel Interlocking (PI)** displays. It provides the Station Master with a real-time, topological representation of the station yard, including:
1. Reception and departure lines (passenger platform lines).
2. Main running lines (Through lines for non-stopping trains).
3. Loop lines and goods sidings.
4. Diamond crossings, crossovers, and turnouts (switches).
5. Fixed signals (Home, Starter, and Advanced Starter).
6. Track circuit and axle counter occupation status.

---

## 2. Station Yard Topologies & Line Configurations

The synthetic corridor models five distinct station configurations:

| Station Code | Station Name | Physical Role | Platform Berths | Main Lines | Loop Lines / Sidings | Special Features |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`NDL`** | Nandpur Junction | Junction & Origin | P1, P2, P3 | Up Main, Down Main | Up Loop, Goods Siding | Diamond Crossing Throat (Cap 2) |
| **`KRN`** | Karanpur | Crossing Station | P1, P2 | Up Main, Down Main | Common Loop | Single-to-Double Line Transition |
| **`MLG`** | Malgaon Junction | Central Hub | P1, P2, P3 | Up Main, Down Main | Down Loop, Goods Siding | Diamond Scissors Crossing (Cap 2) |
| **`SRP`** | Suryapur | Crossing Station | P1, P2 | Up Main, Down Main | Common Loop | Double-to-Single Line Transition |
| **`VSN`** | Vasanthpur | Terminal Station | P1, P2 | Reception Line 1, 2 | Shunting Neck, Stabling | Double Line Terminal Layout |

---

## 3. Visual Interlocking States & Color Conventions

In accordance with Indian Railways signal engineering guidelines and control room ergonomics:

| Operational State | Visual Color | Hex Code | SVG Line Style | Operating Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Clear / Available** | Emerald Green | `#22C55E` / `#16A34A` | Solid ($4\text{px}$) | Track circuit unoccupied; line clear for reception or through run. |
| **Berthed / Occupied** | Vibrant Blue / Red | `#3B82F6` / `#EF4444` | Solid ($5\text{px}$) with Train Box | Track circuit shunted or axle counter tripped by train movement. Displays Train ID. |
| **Maintenance Outage** | Bright Red / White | `#EF4444` | Dashed ($4\text{px}$, `8 4`) | Engineering block, catenary power outage, or track maintenance active. |
| **Route Set / Locked** | Amber / Yellow | `#F59E0B` | Solid highlighted | Points locked and signal cleared for approaching train. |

---

## 4. Signal Indications

The diagram visualizes fixed signals at key yard boundaries:
- **Home Signals:** Located at the outer yard limit ($180\text{m}$ to $400\text{m}$ ahead of first facing points) governing train entry from the block section.
- **Starter Signals:** Located at the departure end of each platform berth governing departure onto the main line or block section.
- **Signal Aspect Colors:**
  - **Green (Proceed):** Line clear ahead, points correctly locked, route unobstructed.
  - **Yellow (Caution):** Route set into loop line or next signal at Stop.
  - **Red (Stop):** Section ahead occupied, platform occupied, or route not set.

---

## 5. Diamond Crossing Throat Architecture (`MLG`)

Malgaon Junction (`MLG`) features a diamond scissors crossing throat connecting Section S2 (Double Line) with Section S3 (Single Line):
- **Maximum Throat Capacity:** $2$ simultaneous non-conflicting movements.
- **Conflicting Routes:** Simultaneous movements across opposing diagonal paths are prevented by hard interlocking logic (`incompatible_route_pairs`).
- **Visual Representation:** Highlighted dashed amber boundary box (`#F59E0B`) in the center of the yard schematic indicating diamond transit limits.

---

## 6. Interactive Track Inspection Panel

Clicking any track line or platform Island activates the **Track Inspection Panel**, displaying:
1. **Track Line ID & Name:** e.g. `Platform 1 (Up Loop)`, Usable Length ($650\text{m}$).
2. **Current Occupying Train:** Train Number, Name, Type, and Direction.
3. **Timetable & Dwell Milestones:** Scheduled Departure, Expected Departure, and Elapsed Dwell Time.
4. **Data Provenance:** High-Integrity Dual Axle Counters (HASSDAC) & Audio Frequency Track Circuits (AFTC) — explicitly classified as `MEASURED`.
5. **Electrical Catenary Status:** $25\text{kV AC}$ Overhead Electrification (OHE) live/isolated.
