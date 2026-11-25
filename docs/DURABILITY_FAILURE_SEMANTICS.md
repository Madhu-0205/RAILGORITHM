# Durability & Failure Semantics Specification — RAILGORITHM v2.5

## 1. Executive Summary & Problem Definition

In distributed and high-throughput railway telemetry systems, accepting sensor and movement events requires an unambiguous transactional lifecycle. Prior to RAILGORITHM v2.5, persistence exceptions during event processing could silently fall back to degraded in-memory execution while returning an affirmative acknowledgement (`success: True`), falsely indicating to external dispatchers or feeds that an event was durably committed.

RAILGORITHM v2.5 eliminates this vulnerability by establishing strict, formal transactional durability boundaries, atomic state rollback semantics, payload tampering detection, and differentiated guarantees between **LIVE_OPERATIONAL** and **SYNTHETIC_SIMULATION** environments.

---

## 2. The Strict Ingestion & Durability Lifecycle

Every operational event processed by `OperationalEventProcessor` follows a strict linear state transition sequence:

```mermaid
flowchart TD
    A["1. Receive Event"] --> B["2. Environment Isolation Check"]
    B --> C["3. Canonical Payload Hash Computation"]
    C --> D["4. Idempotency & Collision Validation"]
    D --> E["5. Working State Mutation (Snapshot Copy)"]
    E --> F["6. Transactional Persistence & Checkpoint Advance"]
    F -->|Commit Succeeded| G["7. Atomic State Swap & Acknowledge"]
    F -->|Commit Failed (Live)| H["8. Rollback State Mutation & Raise 503"]
    F -->|Commit Failed (Simulation)| I["9. Degraded In-Memory Fallback"]
```

### Step-by-Step Execution Protocol:

1. **Receive:** The raw or normalized telemetry payload is received via REST API or internal streaming broker.
2. **Environment Isolation Check:** The event's `environment` tag (`LIVE_OPERATIONAL`, `SYNTHETIC_SIMULATION`, or `HISTORICAL_PLAYBACK`) is verified against the operational state's environment mode. Cross-environment contamination is rejected with `EnvironmentIsolationError`.
3. **Canonical Payload Hash Computation:** A deterministic SHA-256 hash of the canonicalized event attributes is computed:
   $$\text{Hash} = \text{SHA256}(\text{feed\_id} : \text{sequence\_num} : \text{event\_id} : \text{train\_id} : \text{event\_type} : \text{location\_id} : \text{timestamp} : \text{speed} : \text{delay} : \text{direction} : \text{environment})$$
4. **Idempotency & Collision Validation:**
   - **Tier 1 (In-Memory LRU Cache):** Checks if `event_id` is cached. If present, verifies payload hash. A hash mismatch raises `PayloadTamperingError`.
   - **Tier 2 (SQLite Persistent Store):** Queries `ProcessedEventRecord`. If `event_id` exists, verifies hash. If `(feed_id, sequence_num)` exists with a *different* `event_id`, raises `SequenceCollisionError`.
5. **Atomic Working State Mutation:** A deep copy of the active state is created (`working_state = copy.deepcopy(state)`). All kinematic movements, block occupancies, delay updates, and conflict detections are applied exclusively to `working_state`. The active authoritative `state` remains completely unmodified during this step.
6. **Transactional Persistence & Checkpoint Advance:** Within a single database transaction:
   - A `ProcessedEventRecord` is inserted with the event metadata, payload hash, and target state version.
   - The corresponding `FeedCheckpointRecord` is updated: `highest_seen_sequence`, `last_contiguous_sequence`, and `gap_count` are recomputed.
   - `session.commit()` is issued to SQLite (configured with Write-Ahead Logging `PRAGMA journal_mode=WAL` and `busy_timeout=30000`).
7. **Atomic State Swap & Acknowledgement:** Only upon successful database commit, the active in-memory state is atomically swapped:
   `state.clear(); state.update(working_state)`
   The Tier 1 LRU cache is populated, and an affirmative response (`success: True, durability: "DURABLE_SQLITE"`) is acknowledged.

---

## 3. Differentiated Durability Semantics: Live vs. Simulation

| Guarantee Dimension | `LIVE_OPERATIONAL` Mode | `SYNTHETIC_SIMULATION` Mode |
| :--- | :--- | :--- |
| **Commit Requirement** | **Mandatory.** Must commit to disk before acknowledgement. | Optional / Configurable. In-memory execution allowed. |
| **Commit Failure Behavior** | **Fail-Fast.** Transaction rolls back; in-memory state is NOT mutated; raises `DurabilityUnavailableError`. | **Graceful Degradation.** Reverts to `DEGRADED_IN_MEMORY`; marks durability status transparently. |
| **API Response on Disk Failure** | **HTTP 503 Service Unavailable** with `{status: "DURABILITY_UNAVAILABLE", retryable: True}`. | **HTTP 200 OK** with `{status: "DEGRADED_IN_MEMORY", warning: "Persistence failed"}`. |
| **Authoritative Status** | Marked non-authoritative if durability is degraded. | Marked simulation-only. |
| **Dashboard Indicator** | Critical red banner: `DURABILITY UNAVAILABLE`. | Amber indicator: `IN-MEMORY SIMULATION`. |

---

## 4. Integrity Violation & Fault Types

### 4.1. Payload Tampering (`PayloadTamperingError`)
If an event arrives with an `event_id` that has already been processed or committed, but the incoming payload attributes yield a different SHA-256 hash, the system immediately rejects the event with `PayloadTamperingError` (HTTP 400). This prevents replay attacks, data corruption, or conflicting telemetry from overwriting established state.

### 4.2. Sequence Collision (`SequenceCollisionError`)
If an incoming event carries a sequence number `(feed_id, sequence_num)` that was already committed by a *different* `event_id`, the system detects an anomalous sequence collision. The event is rejected with `SequenceCollisionError` (HTTP 400), preventing sequence reuse on the same feed.

### 4.3. Concurrent Duplicate Processing Races
When two concurrent threads or workers attempt to ingest the exact same event simultaneously:
1. Both threads validate and attempt to commit.
2. The database's unique constraint on `ProcessedEventRecord.event_id` permits exactly one transaction to commit.
3. The losing thread catches `IntegrityError`, rolls back its local transaction, re-queries the persistent record, verifies matching payload hash, and returns an **idempotent success acknowledgement** (`idempotent: True`).
4. State mutation occurs exactly once, preserving state version consistency.

---

## 5. Feed Checkpoint Watermarks & Gap Tracking

In `FeedCheckpointRecord`, RAILGORITHM v2.5 maintains three distinct metrics per feed:

1. **`last_processed_sequence`**: The sequence number of the most recently processed event.
2. **`last_contiguous_sequence`**: The highest sequence number up to which *all* preceding sequences $[1, \dots, K]$ have been durably acknowledged without any missing events.
3. **`gap_count`**: The count of missing sequence numbers between 1 and `highest_seen_sequence`:
   $$\text{gap\_count} = \max(0, \text{highest\_seen\_sequence} - |\text{processed\_sequences}|)$$

When out-of-order events arrive (e.g., sequence 1 arrives, then sequence 3), `last_contiguous_sequence` remains 1 and `gap_count` increments to 1. When sequence 2 subsequently arrives, the gap is filled, `last_contiguous_sequence` advances to 3, and `gap_count` returns to 0.
