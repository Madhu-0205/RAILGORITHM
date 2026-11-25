# RAILGORITHM 2.3 — Railway Data Validation Specification

## 1. Scope & Regulatory Framework

This specification defines the formal validation invariants, infrastructure constraints, rolling stock rules, and physical safety limits enforced on all incoming telemetry events ingested into **RAILGORITHM 2.3**.

The validation rules are modeled after standard operating practices of Indian Railways (IR), including:
- **IR-G&SR**: Indian Railways General and Subsidiary Rules (Rule 3.38, 4.08, 4.09).
- **IR-OM**: Operating Manual for Railway Traffic (Block Working & Headway).
- **Hard Constraints (HC-001 to HC-006)**: Mathematical non-negotiable invariants defined in the RAILGORITHM Constraint Specification.

---

## 2. Infrastructure & Rolling Stock Metadata

Validation parameters are dynamically resolved based on the active railway network topology and rolling stock classification.

### 2.1. Train Maximum Permissible Speed (MPS) Tiers

Every train active in the system is classified into a category governed by a distinct MPS cap:

| Train Category | Identifier / Pattern | Permitted MPS | Regulatory Reference | Description |
| :--- | :--- | :--- | :--- | :--- |
| **FREIGHT** | `BOXN-*`, `BCN-*`, `FREIGHT-*` | **75.0 km/h** | `IR-G&SR-4.08-FRT` | Heavy axle load mineral/container freight stock. |
| **MEMU / SUBURBAN** | `MEMU-*`, `64*` | **90.0 km/h** | `IR-G&SR-4.08-SUB` | Mainline electric multiple units with frequent acceleration cycles. |
| **PASSENGER / ORD** | `5*`, `PASS-*` | **100.0 km/h** | `IR-G&SR-4.08-ORD` | Conventional ICF passenger rakes. |
| **EXPRESS / SUPERFAST** | `12*`, `22*`, `EXP-*` | **130.0 km/h** | `IR-G&SR-4.08-EXP` | LHB rakes operating on Group A/B trunk routes. |

*Note: If an incoming telemetry event reports a speed exceeding the train's category MPS by more than $5.0\text{ km/h}$ (tolerance margin for instrument error), the event is rejected with `TRAIN_SPEED_LIMIT_EXCEEDED`.*

### 2.2. Section Permissible Speeds & Temporary Speed Restrictions (TSR)

Sectional speed limits are determined by track geometry, cant deficiency, and signaling layout:
- **Section 1 (Kalyan West - Malgaon)**: Maximum sectional speed = **100.0 km/h**.
- **Section 2 (Malgaon - Kasara East)**: Maximum sectional speed = **110.0 km/h**.
- **TSR Overrides**: When engineering or maintenance work is active, a TSR can be imposed dynamically on any specific block or junction turnout (e.g., $30\text{ km/h}$ on turnout `T-MLG-01`). TSRs take absolute precedence over sectional and train MPS.

$$\text{Effective Speed Cap} = \min\left(\text{MPS}_{\text{train}}, \text{Limit}_{\text{section}}, \text{Limit}_{\text{TSR}}\right)$$

If an event reports a speed exceeding the effective speed cap, it is rejected with `TSR_SPEED_LIMIT_EXCEEDED` or `SECTION_SPEED_LIMIT_EXCEEDED`.

---

## 3. Directional Movement & Block Signalling

### 3.1. Directional Locking on Double-Line Sections

In double-line sections, track circuits are electrically interlocked for unidirectional traffic:
- **UP Line Blocks** (suffixed with `U`, e.g., `B2U`): Exclusively dedicated to trains moving in the `UP` direction ($+x$ axis, Kalyan $\to$ Kasara).
- **DOWN Line Blocks** (suffixed with `D`, e.g., `B2D`): Exclusively dedicated to trains moving in the `DOWN` direction ($-x$ axis, Kasara $\to$ Kalyan).

**Invariant**: Under `IR-G&SR-3.38`, no train may occupy a unidirectional block against the established direction of traffic:

$$\text{Direction}(\text{Train}) == \text{PermittedDirection}(\text{Block})$$

Any reported movement violating this invariant is rejected with `WRONG_DIRECTION_ENTRY`.

### 3.2. Block Occupancy Continuity & Unmatched Exits

A block exit event is physically impossible unless the train is currently recorded as occupying that block:
- **Condition**: On `BLOCK_EXIT` at location $L$, verify that $\text{Occupant}(L) == \text{TrainID}$.
- **Rejection**: If the train was not recorded in block $L$, reject with `UNMATCHED_BLOCK_EXIT` under `IR-G&SR-BLOCK-CONT`.

### 3.3. Mutual Exclusion & Absolute Block System

Under the Absolute Block System (`HC-001`):
$$\forall b \in \text{Blocks}, \quad \sum_{t \in \text{Trains}} \mathbb{I}(\text{Occupies}(t, b, \tau)) \le 1$$
If telemetry reports a train entering a block that is currently occupied by another active train, the event is flagged as a critical safety violation: `BLOCK_MUTUAL_EXCLUSION_VIOLATION`.

---

## 4. Minimum Headway & Junction Throat Management

### 4.1. Absolute Headway Separation (`HC-002`)

To ensure braking distance and signal aspect clearance under automatic and absolute block signaling:
$$\Delta t_{\text{headway}} = t_{\text{entry}}(t_2, b) - t_{\text{entry}}(t_1, b) \ge 180\text{ seconds}$$
If a following train enters block $b$ less than $180\text{ s}$ after the leading train entered or cleared, the entry is rejected with `HEADWAY_VIOLATION`.

### 4.2. Junction Diamond Throat Capacity (`HC-006`)

At complex interlocking junctions (such as Malgaon Junction `MLG`), multiple diamond crossings and slips constrain simultaneous movements through the station throat:
- **Throat Block Cluster**: $T_{\text{MLG}} = \{ \text{B3}, \text{B4}, \text{B5}, \text{B2U}, \text{B2D} \}$.
- **Physical Capacity Limit**: Maximum concurrent movements $C_{\text{throat}} \le 2$.

$$\sum_{b \in T_{\text{MLG}}} \mathbb{I}(\text{Occupied}(b)) \le 2$$

Any telemetry reporting a 3rd concurrent train entering the throat cluster is rejected with `JUNCTION_THROAT_OVERFLOW`.

---

## 5. Temporal Consistency & Clock Drift

Telemetry events must adhere to strict temporal boundaries:
- **Future Timestamps**: Rejects timestamps where $t_{\text{event}} > t_{\text{server}} + 60\text{ s}$ (`TIMESTAMP_IN_FUTURE`).
- **Stale Timestamps**: Rejects historical events older than the sliding operational window: $t_{\text{event}} < t_{\text{server}} - 300\text{ s}$ (`TIMESTAMP_TOO_OLD`).
- **Spatial Teleportation**: Computes the implied velocity between consecutive reported positions $(x_1, t_1)$ and $(x_2, t_2)$:
  $$v_{\text{implied}} = \frac{|x_2 - x_1|}{t_2 - t_1}$$
  If $v_{\text{implied}} > 200.0\text{ km/h}$, the event is flagged as `SPATIAL_TELEPORTATION`.

---

## 6. Comprehensive Validation Reason Code Matrix

The following matrix documents all 21 standardized reason codes enforced by `RailwayIngestionValidator`:

| Reason Code | Category | Invariant Checked | Regulatory Rule | Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| `VALID_EVENT` | Success | All physical, topological & temporal checks pass | `IR-G&SR-VALID` | Normalized & applied to state. |
| `DUPLICATE_SEQUENCE_NUM` | Idempotency | Sequence number already processed for feed | `FEED-IDEMPOTENCY` | Discarded without mutation. |
| `DUPLICATE_PAYLOAD_HASH` | Idempotency | SHA-256 payload hash already recorded | `FEED-DEDUP` | Discarded without mutation. |
| `TIMESTAMP_IN_FUTURE` | Temporal | Event timestamp $> \text{now} + 60\text{ s}$ | `TIME-SYNC-01` | Rejected to contradiction buffer. |
| `TIMESTAMP_TOO_OLD` | Temporal | Event timestamp $< \text{now} - 300\text{ s}$ | `TIME-SYNC-02` | Rejected to contradiction buffer. |
| `TRAIN_SPEED_LIMIT_EXCEEDED` | Kinematic | Speed $>$ Train Category MPS (e.g. Freight $> 75$) | `IR-G&SR-4.08` | Rejected to contradiction buffer. |
| `SECTION_SPEED_LIMIT_EXCEEDED` | Kinematic | Speed $>$ Sectional MPS (e.g. Sec 1 $> 100$) | `IR-G&SR-4.09` | Rejected to contradiction buffer. |
| `TSR_SPEED_LIMIT_EXCEEDED` | Kinematic | Speed $>$ Active Temporary Speed Restriction | `IR-G&SR-4.09-TSR` | Rejected to contradiction buffer. |
| `WRONG_DIRECTION_ENTRY` | Interlocking | Train direction opposed to unidirectional block | `IR-G&SR-3.38` | Rejected; safety alert raised. |
| `UNMATCHED_BLOCK_EXIT` | State Tracking | Train exiting block it was never recorded in | `IR-G&SR-BLOCK-CONT` | Rejected to contradiction buffer. |
| `HEADWAY_VIOLATION` | Separation | Time delta between consecutive trains $< 180\text{ s}$ | `HC-002` | Rejected; conflict alert raised. |
| `JUNCTION_THROAT_OVERFLOW` | Interlocking | Simultaneous throat occupancy $> 2$ trains | `HC-006` | Rejected; interlocking lock held. |
| `PLATFORM_ALREADY_OCCUPIED` | Capacity | Platform already occupied by another train | `HC-003` | Rejected; hold signal enforced. |
| `BLOCK_MUTUAL_EXCLUSION_VIOLATION` | Safety | Two trains occupying identical block track circuit | `HC-001` | Critical safety alert raised. |
| `SPATIAL_TELEPORTATION` | Kinematic | Implied velocity between points $> 200\text{ km/h}$ | `PHYS-KIN-01` | Rejected to contradiction buffer. |
| `UNKNOWN_TRAIN_ID` | Schema | Train identifier not found in active timetable | `TIMETABLE-01` | Rejected with schema error. |
| `UNKNOWN_LOCATION_ID` | Schema | Location identifier not found in network topology | `TOPOLOGY-01` | Rejected with schema error. |
| `CIRCUIT_BREAKER_TRIPPED` | Fault Tolerance | Feed error rate exceeded failure threshold | `FEED-CB-01` | Feed isolated; reconnection pending. |
| `ENVIRONMENT_MISMATCH` | Isolation | Telemetry environment tag $\ne$ system mode | `ENV-ISO-01` | Rejected; cross-env blocked. |
| `UNAUTHORIZED_FEED_SOURCE` | Security | Feed ID not authorized in feed registry | `SEC-AUTH-01` | HTTP 401/403 returned. |
| `CORRUPTED_PAYLOAD_SCHEMA` | Schema | JSON schema deserialization or field validation fail | `SCHEMA-VAL-01` | HTTP 422 returned. |
