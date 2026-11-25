# RAILGORITHM 2.1 — Security & Audit Verification Report

**Document ID:** `RAIL-DOC-21-SEC-AUDIT`  
**Version:** 2.1.0  
**Date:** 2026-11-25  
**Status:** Validated  
**Scope:** Synthetic railway simulation and decision-support only. Zero live infrastructure control.

---

## 1. Threat Model & Security Objectives

In a railway traffic management decision-support system, operational integrity and non-repudiation are paramount. Even though RAILGORITHM is strictly a simulation environment, it implements safety-grade data architecture to ensure recommendations and human decisions cannot be manipulated, duplicated, or covertly erased.

### Evaluated Threat Vectors
1. **T1: Historical Record Modification:** An attacker or malfunctioning script attempts to alter past decisions, recommendations, or audit logs to rewrite operational history.
2. **T2: Event Deletion:** An actor attempts to delete audit entries or decisions to hide improper interventions.
3. **T3: Tail Truncation:** An attacker attempts to truncate the most recent audit events from the end of the log to obscure recent actions.
4. **T4: Payload Corruption & Hash Tampering:** An attacker modifies stored JSON payloads or attempts to recalculate hashes.
5. **T5: Head Pointer Desynchronization:** An attacker modifies the persistent audit head pointer in `audit_chain_head`.
6. **T6: Concurrent Decision Race Conditions:** Multiple controllers or automated clients attempt to decide simultaneously on the same recommendation.
7. **T7: Unauthorized Role & Scope Escalation:** A Station Master attempts to approve recommendations that affect stations outside their assigned territorial jurisdiction.
8. **T8: Stale Recommendation Exploitation:** A controller approves a recommendation after the simulation clock and physical train positions have advanced.
9. **T9: Duplicate Decision Injection:** Submitting multiple contradictory decisions for a single recommendation.

---

## 2. Defensive Mechanisms & Architectural Controls

### A. Immutable Database Triggers
The SQLite database schema (`app/db.py`) enforces append-only immutability at the SQL storage layer:
- `audit_events_no_update`: `BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;`
- `audit_events_no_delete`: `BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;`
- `decisions_no_update`: `BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT, 'decisions is append-only'); END;`
- `decisions_no_delete`: `BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT, 'decisions is append-only'); END;`

### B. Cryptographic Hash Chaining
Audit events form a forward-secure cryptographic blockchain:
- Genesis event has `prev_hash = "0" * 64`.
- Every subsequent event computes:
  $$\text{hash}_k = \text{SHA256}(\text{hash}_{k-1} \,\|\, \text{event\_type}_k \,\|\, \text{actor}_k \,\|\, \text{actor\_role}_k \,\|\, \text{sim\_id}_k \,\|\, \text{rec\_id}_k \,\|\, \text{canonical\_json}(\text{payload}_k))$$
- A dedicated tracking table `audit_chain_head` maintains the latest head hash:
  $$\text{head\_hash} = \text{hash}_{\text{latest}}$$
- The function `verify_audit_chain(db)` walks the entire sequence from genesis to head, verifying each link and cross-checking the terminal link against `audit_chain_head`.

### C. Concurrency & Scope Enforcement
- **Race Condition Protection:** Unique constraint on `decisions.recommendation_id` combined with database transactions ensures atomic decision resolution.
- **Role-Based Territorial Scoping:** `_authorize_scope(user, affected_stations)` enforces that Station Masters can only decide on actions where `affected_stations \subseteq \{\text{user.station\_id}\}`. Section Masters are required for multi-station or corridor actions.
- **State Version Fencing:** Every recommendation binds to an integer `state_version`. If `simulation.state_version != recommendation.state_version`, the recommendation is flagged `STALE` and the approval is rejected with `HTTP 409 Conflict`.

---

## 3. Adversarial Penetration Test Results

All threat vectors were tested using automated adversarial test suites (`backend/tests/test_security_audit_adversarial.py`):

| Test Case | Adversarial Action Tested | Expected Security Response | Test Result |
| :--- | :--- | :--- | :--- |
| **`test_adversarial_audit_trigger_blocks_update`** | Direct raw SQL `UPDATE` on `audit_events` | SQL trigger aborts transaction (`RAISE(ABORT)`) | **PASSED** (Transaction aborted) |
| **`test_adversarial_audit_trigger_blocks_delete`** | Direct raw SQL `DELETE` on `audit_events` | SQL trigger aborts transaction (`RAISE(ABORT)`) | **PASSED** (Transaction aborted) |
| **`test_adversarial_invalid_hash_detected`** | Payload corrupted while bypassing triggers | `verify_audit_chain` flags invalid hash | **PASSED** (`valid: false`, Hash mismatch) |
| **`test_adversarial_tail_truncation_detected`** | Deleting the most recent audit event | Chain verification fails against `audit_chain_head` | **PASSED** (`valid: false`, Head mismatch) |
| **`test_adversarial_head_mismatch_detected`** | Modifying `head_hash` in `audit_chain_head` | Chain verification detects tampered head | **PASSED** (`valid: false`, Head mismatch) |
| **`test_adversarial_concurrent_decisions`** | Concurrent multi-threaded approvals | Exactly one succeeds (200), other rejected (409) | **PASSED** (`[200, 409]` verified) |
| **`test_adversarial_unauthorized_scope_decision_blocked`** | Station Master decides cross-station action | Request rejected with HTTP 403 Forbidden | **PASSED** (Access denied) |
| **`test_adversarial_stale_recommendation_rejected`** | Approval attempted after simulation advance | Request rejected with HTTP 409 Conflict | **PASSED** (Stale rejected) |

---

## 4. Limits of Database-Level Protections & Production Considerations

### What In-Database Protections Protect Against
- Application-level software bugs.
- Compromised or malicious API clients.
- Privilege escalation within the application layer.
- Unintentional operator errors (duplicate clicks, concurrent submissions).

### What In-Database Protections Do NOT Protect Against
- **Direct OS File Access:** An adversary with root/administrator access or direct read/write permissions to the SQLite database file on disk (`test.db`) can bypass SQLite triggers by opening the database with `sqlite3` without trigger execution or by directly modifying the file with a hex editor.
- **Process Memory Tampering:** A rogue local process with `ptrace` or debugger privileges can tamper with process memory before commits.

### Production Railway Deployment Recommendations
For physical production deployments (outside simulation):
1. **Write-Once-Read-Many (WORM) Storage:** Mirror audit logs immediately to append-only immutable storage appliances.
2. **External Remote Syslog:** Stream signed audit events off-host in real time to an isolated Security Information and Event Management (SIEM) system.
3. **Hardware Security Modules (HSM):** Sign audit block hashes using a dedicated cryptographic hardware module.
4. **Operating System File Hardening:** Restrict SQLite/PostgreSQL data file permissions to dedicated, non-login service accounts with strict filesystem access control lists (ACLs).
