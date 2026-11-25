# RAILGORITHM 2.0 — Security and Scalability Review

**Document Version:** 2.0.0  
**Date:** 25 November 2026  
**Scope:** Application Security, Authentication, RBAC, Audit Integrity, Database Portability  
**System Classification:** Simulation-Only Decision Support  

---

## 1. Authentication and Secret Management

### Production Posture & Safe Boot Checks
In RAILGORITHM 2.0, the application introduces strict configuration guardrails (`backend/app/config.py` and `assert_safe_for_production()`):
- **Development Default Rejection:** If `RAILGORITHM_ENV=production` is set, the application will refuse to start if:
  1. `RAILGORITHM_JWT_SECRET` starts with `railgorithm-dev-only` or uses the development default.
  2. `RAILGORITHM_ALLOW_DEMO_CREDENTIALS` is enabled (`true`).
  3. `RAILGORITHM_SEED_DEMO` is enabled (`true`).
  4. `RAILGORITHM_DATABASE_URL` uses SQLite (`sqlite:///...`).
- **Enforcement:** Protected by unit tests `test_production_configuration_rejects_default_secret_and_demo_credentials` and `test_production_configuration_accepts_postgres_and_explicit_secret`.

### Login Rate Limiting
- To mitigate brute-force attacks against authentication endpoints, an in-process sliding-window rate limiter is implemented at `/api/v1/auth/login`.
- Default: 10 attempts per minute per IP (`RAILGORITHM_LOGIN_RATE_LIMIT=10`).
- Excess attempts return `HTTP 429 Too Many Requests`.

### HTTP Security Headers
All API responses now include defensive security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Cache-Control: no-store`

---

## 2. Role-Based Access Control and Station Scoping

### Role Hierarchy
1. **Section Master (`SECTION_MASTER`)**:
   - Broad authority across all sections and stations.
   - Authorized to create simulations, advance/pause/reset time, inject disruptions, approve recommendations, and inspect the audit trail.
2. **Station Master (`STATION_MASTER`)**:
   - Station-scoped authority (e.g. Station `MLG`).
   - Read-only access to section-wide dashboards; conflict views and recommendations are automatically scoped to their station.
   - Cannot create simulations, advance time, inject disruptions, or read the audit trail.
   - Decisions on recommendations outside their station scope are blocked with `HTTP 403 Forbidden`.

---

## 3. Cryptographic Audit Integrity

### Two-Tier Integrity Protection
RAILGORITHM 2.0 implements a tamper-evident audit log with two independent layers:
1. **Append-Only SHA-256 Hash Chain:**
   Each event hash binds the previous event's hash, timestamp, event type, actor ID, and payload digest:
   $$H_k = \text{SHA256}(H_{k-1} \,\|\, t_k \,\|\, type_k \,\|\, user_k \,\|\, payload_k)$$
   Database triggers (`audit_events_no_update`, `audit_events_no_delete`) abort any direct SQL `UPDATE` or `DELETE` operations on `audit_events`.
2. **Tail Truncation Detection (`AuditChainHead`):**
   A dedicated single-row table (`audit_chain_head`) records the latest hash ($H_{last}$) and total event count ($N$).
   - Protected by trigger `audit_chain_head_no_delete`.
   - On verification, `verify_audit_chain()` compares the computed chain length and head hash against `AuditChainHead`.
   - If an attacker truncates recent events from the table, the hash chain appears internally valid, but `AuditChainHead` mismatch detects the truncation immediately.

---

## 4. Database Portability and PostgreSQL Migration Path

### Portability Verification
- In development and testing, SQLite is used for lightweight, zero-dependency local execution.
- SQLAlchemy 2.0 ORM mappings in `backend/app/models.py` have been verified for clean compilation against the PostgreSQL dialect (`test_schema_compiles_for_postgresql_without_sqlite_only_types`).
- Standard SQL types (`String`, `Integer`, `Float`, `DateTime(timezone=True)`, `JSON`) are used throughout, avoiding SQLite-specific constructs like unstructured BLOBs.

### PostgreSQL Migration Blueprint
When deploying to a production Kubernetes or cloud environment:
1. Configure `RAILGORITHM_DATABASE_URL=postgresql+psycopg://user:password@host:5432/railgorithm`.
2. Apply database migrations via Alembic.
3. Replace SQLite triggers with PostgreSQL row-level triggers:
   ```sql
   CREATE OR REPLACE FUNCTION abort_audit_mutation() RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'Audit trail is append-only';
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER audit_no_mutation
   BEFORE UPDATE OR DELETE ON audit_events
   FOR EACH ROW EXECUTE FUNCTION abort_audit_mutation();
   ```
4. Utilize `SELECT ... FOR UPDATE` row locking during `append_audit` to ensure concurrent transaction safety.
