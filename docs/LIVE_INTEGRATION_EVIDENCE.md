# LIVE INTEGRATION READINESS & SAFETY EVIDENCE — RAILGORITHM v2.4

## 1. Safety Principles & System Boundaries

RAILGORITHM v2.4 is designed with a strict non-negotiable safety invariant:

```
[External Signaling Feeds / Telemetry Providers]
                       │ (Read-Only Ingestion via Adapters)
                       ▼
          [RAILGORITHM Ingestion API]
                       │ (Validation, Normalization, Isolation)
                       ▼
          [Advisory Traffic Decision Engine]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[Station Master UI]         [Section Controller UI]
       │                               │
       └───────────────┬───────────────┘
                       │ (Human Review & Approval)
                       ▼
         [Synthetic Simulation Sandbox]
                       │
             ⛔ NO WRITEBACK ⛔
                       │
     [Field Interlocking & Track Hardware]
```

> [!CAUTION]
> **Zero Autonomous Infrastructure Control:**
> RAILGORITHM v2.4 contains **no field writeback channels**, no relay outputs, and no network connections to field electronic interlocking (EI), point machines, or vital signal aspect cascades. The application is strictly read-only regarding external telemetry. All recommendations remain purely advisory decision support for human traffic controllers.

---

## 2. Ingestion Adapters & Data Provider Contracts

RAILGORITHM v2.4 provides modular ingestion adapters designed to interface with standardized railway data feeds without hardcoding proprietary schemas:

### 2.1 Supported Telemetry Feed Types

| Feed Identifier | Source Protocol | Telemetry Payload | Verification Status |
| :--- | :--- | :--- | :--- |
| **`FEED-SIGNAL-01`** | JSON over HTTP/REST | Signal aspect changes, block entries, track occupancy. | Fully Verified with automated test suites. |
| **`FEED-SIGNAL-02`** | JSON over HTTP/REST | Secondary section telemetry and crossing sensors. | Fully Verified with multi-feed replay test suite. |
| **`FEED-MOCK-FAIL`** | Fault Injection Adapter | Simulates corrupted sequences, clock drift, and duplicate packets. | Verified in circuit breaker and exception tests. |

### 2.2 Feed Health & Circuit Breaker Architecture

Every feed is continuously monitored for reliability and freshness:
1. **Heartbeat & Watermark Tracking:** Tracks `last_heartbeat_at`, `freshness_seconds`, and `is_stale`. Feeds with no heartbeat for > 60 seconds are visually flagged as `STALE`.
2. **Circuit Breaker:** If a feed produces > 20% validation contradictions within a rolling window, the circuit breaker trips to `OPEN` state, isolating the corrupted feed and alerting controllers.
3. **Sequence Gap Detection:** Tracks `last_processed_sequence`. If incoming sequence skips numbers (e.g. 101 to 105), gaps are flagged for retransmission.

---

## 3. Strict Simulation vs Live Operational Isolation

To prevent synthetic what-if scenarios from contaminating operational views, RAILGORITHM enforces a 3-tier boundary:

| Isolation Boundary | Enforcement Mechanism | Failure Action |
| :--- | :--- | :--- |
| **1. Data Payload Tagging** | Every event must specify `environment: "LIVE_OPERATIONAL" \| "HISTORICAL_PLAYBACK" \| "SYNTHETIC_SIMULATION"`. | Mismatched payloads rejected with `ENVIRONMENT_MISMATCH` contradiction. |
| **2. Event Processor Boundary** | `OperationalEventProcessor` compares event environment against target state environment. | Raises `EnvironmentIsolationError` immediately on cross-environment contamination. |
| **3. Database Partitioning** | Simulation records carry explicit `label: "SYNTHETIC"`, and API outputs include mandatory disclaimers. | Prevents simulated metrics from being presented as real-world railway measurements. |

---

## 4. Operational Ingestion Endpoints

| Endpoint | HTTP Method | Role Authorization | Purpose |
| :--- | :--- | :--- | :--- |
| `/api/v1/ingestion/events` | `POST` | `SECTION_MASTER`, `STATION_MASTER` | Ingest single validated operational telemetry event. |
| `/api/v1/ingestion/events/batch` | `POST` | `SECTION_MASTER`, `STATION_MASTER` | High-throughput batch ingestion (up to 500 events). |
| `/api/v1/ingestion/events` | `GET` | Authenticated | Query recent normalized operational movement events. |
| `/api/v1/ingestion/status` | `GET` | Authenticated | Query feed health, latency, error rate, and circuit breaker status. |
| `/api/v1/ingestion/circuit-breakers/reset` | `POST` | `SECTION_MASTER` | Reset a tripped circuit breaker after feed remediation. |
