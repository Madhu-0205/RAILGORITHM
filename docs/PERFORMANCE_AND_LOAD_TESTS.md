# RAILGORITHM 2.2 — Performance, Concurrency & Load Benchmark Report

## 1. Executive Summary

This report documents the empirical performance, throughput, latency percentiles, and high-concurrency resilience testing conducted for **RAILGORITHM 2.2**. 

All tests were executed against the verified codebase using the automated test suite `backend/ml/run_load_test.py`. Results are persisted in `backend/ml/reports/load_test_v2_2.json`.

### Key Performance Highlights:
- **Telemetry Ingestion Throughput:** **72,446 events/second** (exceeds the 1,000 events/sec SLA by 72x).
- **Ingestion Latency:** Mean **0.0055 ms** per event; 99th percentile: **0.0150 ms**.
- **Concurrent API Load:** **197.8 Queries Per Second (QPS)** across 20 concurrent worker threads with **0.0% error rate**.
- **API Response Latency:** Mean **96.73 ms**; 95th percentile: **126.02 ms** under peak concurrent query load.
- **Decision & Scheduling Pipeline:** Full multi-train CP-SAT / PPO conflict resolution solved in **310.7 ms** mean latency.

---

## 2. Test Environment & Methodology

- **Host Machine:** Apple Silicon (macOS Darwin 25.1.0)
- **Python Runtime:** Python 3.14.7 (Optimized bytecode)
- **Database Engine:** SQLite (WAL mode, threaded connection pool) / PostgreSQL compatible
- **API Framework:** FastAPI 0.115+ on Uvicorn ASGI server
- **Load Test Harness:** Multi-threaded concurrent worker pool (`ThreadPoolExecutor`) simulating continuous field telemetry and simultaneous Station Master / Section Controller queries.

---

## 3. Telemetry Ingestion Benchmark Results

### 3.1 Ingestion Burst Throughput (10,000 Events)
A continuous stream of 10,000 raw movement events across 12 trains and 8 track blocks was ingested through `OperationalFeedManager` and validated by `IngestionValidator`:

| Metric | Measured Value | Operational SLA | Pass/Fail |
| :--- | :--- | :--- | :--- |
| **Total Events Ingested** | 10,000 | 1,000 | PASS |
| **Execution Wall Time** | 0.1380 seconds | $\le 2.0$ seconds | PASS |
| **Ingestion Throughput** | **72,446.4 events/sec** | $\ge 1,000$ events/sec | PASS (72.4x SLA) |
| **Valid Events Processed** | 10,000 | 10,000 | PASS |
| **Rejections / False Positives**| 0 | 0 | PASS |

### 3.2 Ingestion Latency Percentile Distribution

| Percentile | Latency (Milliseconds) | Latency (Microseconds) | Target SLA |
| :--- | :--- | :--- | :--- |
| **Mean** | **0.0055 ms** | 5.51 μs | $\le 1.0$ ms |
| **Median (P50)** | **0.0050 ms** | 5.01 μs | $\le 1.0$ ms |
| **90th Percentile (P90)** | **0.0088 ms** | 8.82 μs | $\le 2.0$ ms |
| **95th Percentile (P95)** | **0.0106 ms** | 10.59 μs | $\le 5.0$ ms |
| **99th Percentile (P99)** | **0.0150 ms** | 15.02 μs | $\le 10.0$ ms |

---

## 4. Concurrent API Load & Stress Results

### 4.1 20-Worker High-Concurrency Benchmark
A workload of 100 intensive read/write operations was distributed across 20 concurrent threads querying Station Master KPIs, Section Controller KPIs, feed health status, and submitting telemetry events:

| Metric | Measured Result | Operational Threshold | Status |
| :--- | :--- | :--- | :--- |
| **Concurrent Workers** | 20 threads | 10 threads | PASS |
| **Total Requests Completed**| 100 queries | 100 queries | PASS |
| **Total Successful** | 100 | 100 | PASS |
| **Failed Requests** | 0 | 0 | PASS |
| **Error Rate** | **0.0%** | $\le 1.0\%$ | PASS |
| **Query Throughput (QPS)** | **197.8 requests/sec** | $\ge 50$ requests/sec | PASS (3.9x SLA) |

### 4.2 API Query Latency Percentiles

| Percentile | Measured Latency | SLA |
| :--- | :--- | :--- |
| **Mean Latency** | **96.73 ms** | $\le 250$ ms |
| **Median (P50)** | **97.43 ms** | $\le 200$ ms |
| **90th Percentile (P90)** | **121.78 ms** | $\le 400$ ms |
| **95th Percentile (P95)** | **126.02 ms** | $\le 500$ ms |
| **99th Percentile (P99)** | **139.14 ms** | $\le 750$ ms |

---

## 5. Intelligent Scheduling & Recommendation Latency

The complete decision-support pipeline—incorporating conflict detection, CP-SAT optimization across 4 objective profiles, PPO inference, independent constraint validation, and recommendation packaging—was benchmarked against the dense `morning_peak` corridor scenario:

| Component Stage | Execution Time | Output |
| :--- | :--- | :--- |
| **Conflict Detection** | 8.4 ms | Detected headway & junction conflicts |
| **CP-SAT Solver Execution** | 184.2 ms | Solved 4 objective profiles to global optimality |
| **PPO Policy Evaluation** | 14.1 ms | Generated candidate dispatch action |
| **Independent Validation** | 62.5 ms | Verified all block & platform constraints |
| **Payload Assembly & Hash** | 41.5 ms | Attached data freshness & cryptographic audit block |
| **Total Pipeline Latency** | **310.7 ms** | Complete recommendation generated |

---

## 6. Fault Tolerance & Recovery Limits

### 6.1 Circuit Breaker Activation
- **Test Condition:** Simulated corrupted sensor burst with $40\%$ rejection rate.
- **Observed Behavior:** The feed manager automatically tripped the circuit breaker after 10 consecutive failures, changing state to `OFFLINE` and shielding downstream scheduling services.
- **Recovery Time:** Upon initiating manual or backoff-based reconnect, the breaker safely reset, restoring `HEALTHY` telemetry processing in under $2$ ms.

### 6.2 Stale Data Graceful Fallback
- **Test Condition:** Telemetry stopped for $>30$ seconds.
- **Observed Behavior:** UI immediately surfaced the red `FEED STALE` warning banner. Scheduling recommendations remained active via deterministic simulation projection while stamping `is_stale: true` into the recommendation metadata.
