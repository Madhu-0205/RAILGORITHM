# RAILGORITHM v2.7 — Multi-Station Railway Operations Specification

**Document Version:** 2.7.0  
**Effective Date:** 25 November 2026  
**Status:** Engineering Specification & Operational Guidelines  
**Authority:** Corridor Traffic Management & Control Office  
**Scope:** Multi-Station Operational Coordination, Section Regulation & Inter-Station Block Working  

---

## 1. Corridor Operational Geography & Infrastructure Topology

The reference RAILGORITHM territory models a critical $60.0\text{ km}$ mixed-traffic mainline corridor in Indian Railways operating territory, spanning five configured stations and four connecting sections:

```
[ NDL ] ====== (S1: Single Line, 15 km) ====== [ KRN ] ====== (S2: Double Line, 15 km) ====== [ MLG ]
Nandpur                                        Karanpur                                        Malgaon Jn
Chainage: 0.0 km                               Chainage: 15.0 km                               Chainage: 30.0 km
Platforms: P1, P2                              Platforms: P1, P2                               Platforms: P1, P2, P3
                                                                                               (Diamond Crossing Throat)
                                                                                                      ||
                                                                                                      ||
[ VSN ] ====== (S4: Double Line, 15 km) ====== [ SRP ] ====== (S3: Single Line, 15 km) ========//
Vasanthpur                                     Suryapur
Chainage: 60.0 km                              Chainage: 45.0 km
Platforms: P1, P2                              Platforms: P1, P2
```

### 1.1 Detailed Section Characteristics

| Section ID | Boundary Stations | Track Mode | Block Sections | Length | Max Speed | Headway | Operating Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S1** | Nandpur (`NDL`) – Karanpur (`KRN`) | **Single Line** | `B1` (Bidirectional) | $15.0\text{ km}$ | $90\text{ km/h}$ | $4\text{ min}$ | Tokenless Absolute Block. Opposing movements strictly prohibited. Train meets must occur at NDL or KRN loop lines. |
| **S2** | Karanpur (`KRN`) – Malgaon Jn (`MLG`) | **Double Line** | `B2U` (UP), `B2D` (DOWN) | $15.0\text{ km}$ | $110\text{ km/h}$ | $3\text{ min}$ | Unidirectional double line. Simultaneous parallel UP and DOWN runs permitted under GR 8.01. |
| **S3** | Malgaon Jn (`MLG`) – Suryapur (`SRP`) | **Single Line** | `B3` (Bidirectional) | $15.0\text{ km}$ | $90\text{ km/h}$ | $4\text{ min}$ | Bottleneck section adjacent to Malgaon diamond crossing. Precedence regulation critical to avoid throat gridlock. |
| **S4** | Suryapur (`SRP`) – Vasanthpur (`VSN`) | **Double Line** | `B4U` (UP), `B4D` (DOWN) | $15.0\text{ km}$ | $110\text{ km/h}$ | $3\text{ min}$ | Unidirectional double line terminating at Vasanthpur yard terminal. |

---

## 2. Multi-Station Status Aggregation & Control Strip Architecture

The **Station Control Strip (`StationControlStrip.tsx`)** provides real-time telemetry aggregation across all stations simultaneously:

### 2.1 Metric Aggregation Rules
For each station $s \in S$:
1. **Berthed Trains ($N_{\text{berthed}}$):** Count of trains with `station_id == s.id`.
2. **Approaching Trains ($N_{\text{approaching}}$):** Count of trains with `next_station == s.id` and `station_id != s.id`.
3. **Departed Trains ($N_{\text{departed}}$):** Count of trains whose planned route includes $s$, but whose current position is past $s$ or status is `COMPLETED`.
4. **Delayed Trains ($N_{\text{delayed}}$):** Count of trains currently at or approaching $s$ with $\text{projected\_delay\_min} > 0$.
5. **Platform Availability ($P_{\text{avail}}$):** Computed dynamically as:
   $$P_{\text{avail}} = \max(0, P_{\text{total}} - P_{\text{occupied}} - P_{\text{outage}})$$
   where $P_{\text{occupied}}$ is the count of berths occupied by trains, and $P_{\text{outage}}$ is active platform engineering closures.

### 2.2 Visual Status Tone Classification
- **Normal (`good` / Emerald):** Zero critical/high conflicts, no platform outages, and delayed trains $\le 1$.
- **Active Caution (`watch` / Amber):** Non-critical route delay, platform maintenance block, or active caution order (TSR/PSR) within station yard.
- **Critical Alert (`bad` / Crimson):** Unresolved headway/opposing move conflict, platform capacity saturation ($P_{\text{avail}} = 0$), or interlocking signal outage.

---

## 3. Inline Station Yard Inspection Semantics

Controllers frequently require detailed yard layouts without navigating away from corridor-level string charts and block occupancy boards:

1. **Triggering Inspection:** Clicking any station card in the Control Strip or pressing `Enter`/`Space` when focused selects the station and expands the **Station Master Yard Inspection Console** directly below the strip.
2. **Interlocking Mirroring (`StationWorkingDiagram.tsx`):**
   - Renders exact Electronic Interlocking (EI) track layout for the selected station.
   - Highlights main running lines (UP Main, DOWN Main), passenger loop platforms, and goods sidings.
   - Displays real-time track circuit status: Green (Clear and signalled), Amber (Route set), Red (Occupied by train), Magenta (Caution order/TSR).
3. **Berthing Slot Telemetry (`StationPlatformBerths.tsx`):**
   - Displays each platform line with occupancy state (`AVAILABLE`, `OCCUPIED`, `OUTAGE`), berthed train ID, and scheduled departure countdown.
4. **Local Timetable Board (`StationTrainBoard.tsx`):**
   - Displays incoming and outgoing train movements specific to the inspected station, including scheduled vs projected timings and platform allocations.
5. **Context Retention:** The Section Controller can toggle between stations in 1 click or dismiss the inspection (`Close Station Inspection ✕`) to return to the streamlined corridor view without re-querying or resetting filters.

---

## 4. Diamond Scissors Crossing Throat Management (Malgaon Junction)

Malgaon Junction (`MLG`) is the operational pivot of the corridor, where single-line section S3 meets double-line section S2 through a high-density diamond scissors crossing throat:

1. **Physical Capacity Limit:** The diamond scissors throat allows a maximum of **2 simultaneous non-conflicting parallel movements** (e.g., UP Main through run + DOWN Loop reception).
2. **Throat Saturation Modeling:**
   $$\text{Throat Load \%} = \left(\frac{\text{Active Transits} + \text{Queued Diamond Demands}}{\text{Throat Capacity (2)}}\right) \times 100\%$$
3. **Regulation Protocol:**
   - When Throat Load $\ge 80\%$, the system flags **SATURATED** status.
   - The CP-SAT solver prioritizes higher-priority passenger trains (Rajdhani/Shatabdi/Superfast, Priority 1) over stopping passengers (Priority 2) and freights (Priority 3).
   - Freights approaching Malgaon are automatically proposed for regulation at Karanpur (`KRN`) Down Loop or Suryapur (`SRP`) Up Loop to prevent junction gridlock.

---

## 5. Inter-Departmental Coordination Diary & Shift Handover Console

Section Controllers coordinate train operations with five primary departmental control desks:

1. **Station Masters (SM):** Train arrival/departure advice, platform readiness, shunting authorisations, line clear verification.
2. **Traction Power Controller (TPC):** 25 kV AC OHE traction supply status, section feeder tripping, power blocks.
3. **Signal & Telecom Controller (S&T):** Track circuit failures, point motor detection errors, axle counter transient drops, EI data logger health.
4. **Permanent Way Controller (P-Way):** Track renewal blocks, deep screening, temporary speed restriction (TSR) notices, rail fracture cautions.
5. **Loco Foreman / Power Controller:** Locomotive availability, crew balancing, banking engine requirements on gradients.

### 5.1 Formal Shift Handover Continuity Protocol
To eliminate communication gaps between incoming and outgoing Section Controllers, the console enforces a structured four-point handover briefing:
1. **Corridor Status Briefing:** Active trains in section, delayed trains, and throughput achieved during the preceding shift.
2. **Engineering Caution Review:** Review of all active Temporary Speed Restrictions (TSR), Permanent Speed Restrictions (PSR), and planned night maintenance blocks.
3. **Pending Infrastructure Incidents:** Status of ongoing S&T signal rectifications or track inspection work.
4. **Cryptographic Handover Signature:** Outgoing Section Controller signs the electronic handover log with their callsign (`SC-402`), shift identity, and timestamp. The signature is recorded in the immutable audit trail before the next controller assumes desk control.
