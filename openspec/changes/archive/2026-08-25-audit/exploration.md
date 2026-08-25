# Exploration: Audit Module (Módulo de Auditoría y Trazabilidad — SIGPI §6.13)

## Current State

SIGPI already has a **partial, fragmented audit capability** built around a single
generic model plus per-domain state logs. There is **no standalone `audit` app**.

### Existing audit machinery

1. **`AuditEvent` + `AuditEventEmitter`** (`backend/apps/accounts/audit.py`, model wired
   into `accounts/models.py`):
   - Fields: `id` (UUID), `user` (nullable FK), `event_type` (CharField choices,
     db_index), `timestamp` (db_index), `ip_address`, `institution_id` (denormalized
     UUID, db_index), `details` (JSONField).
   - `AuditEventEmitter` is the canonical write path: `.emit(event_type, user, ip,
     institution_id, details)`, with `extract_ip(request)` helper (X-Forwarded-For →
     REMOTE_ADDR).
   - `AuditEventType` is an ever-growing TextChoices enum spanning auth + domain events:
     LOGIN, LOGOUT, FAILED_LOGIN, INSTITUTION_SWITCH, ROLE_CHANGE, PERMISSION_DENIED,
     PROGRESS_STATE_CHANGE, REPORT_GENERATED, REPORT_APPROVED, BUDGET_CREATED,
     BUDGET_UPDATED, BUDGET_EXECUTION_ADDED, DOCUMENT_UPLOADED, DOCUMENT_SIGNED,
     MINUTES_CREATED. **No generic CREATE/UPDATE/DELETE/STATE_CHANGE type and no
     `entity` field.**
   - Consumed today for: login/logout/failed-login/institution-switch (accounts views),
     role change (accounts Celery task), report generation (reports), budget events
     (budgets), document upload/sign/minutes (documents), project & progress & call
     FSM transitions.
   - **No read/query API exists** — AuditEvent is only ever written (via the emitter)
     and asserted in tests. There is no serializer, viewset, or URL exposing it.

2. **Per-domain `*StateLog` models** (domain audit for FSM transitions, append-only,
   read-only API):
   - `ProjectStateLog` (`projects/models.py`): project, from_state, to_state,
     triggered_by, reason, created_at. Exposed read-only via
     `ProjectStateLogViewSet` (`GET /api/projects/{pk}/state-log/`).
   - `ProgressStateLog` (`progress/models.py`): same shape for progress reports.
   - `CallStateLog` (`calls/models.py`): same shape for calls.
   - All three follow the "dual audit" pattern: write a `*StateLog` row AND mirror to
     `AuditEvent` via the emitter. They carry **no IP, no old/new values** — just
     from/to state + reason.

3. **Permissions / roles**: `IsAuditor` permission class (read-only, SAFE_METHODS),
   Auditor role seeded at level 7 (`sigpi_auditor` keycloak role), read-only across
   all modules. Auditors are expected to consume audit data.

### Tenant isolation (critical constraint)

- Multi-institution tenancy is enforced by **PostgreSQL RLS** (`accounts` migration
  `0004_rls_policies.py`) with `institution_id` column checks plus a superadmin bypass.
- `AuditEvent` has an `institution_id` field but is **NOT** in the
  `TENANT_SCOPED_TABLES` list and has **no RLS policy** applied.
- `TenantMiddleware.TENANT_REQUIRED_PREFIXES` does **not** include an `/api/audit/`
  prefix, so a new audit endpoint would not require an active tenant unless added.
- This is the single most important design constraint for the new module.

## Gaps (what §6.13 requires that is missing)

| RF | Requirement | Gap |
|----|-------------|-----|
| RF-100 | Register create/edit/logical-delete/state-change | Partial — state changes are logged; **no generic create/update/delete events** for arbitrary entities; **no logical-delete events anywhere**. |
| RF-101 | Register user, date, IP, entity, action, old/new values | **Missing** — `AuditEvent` has no `entity` (entity name + id) field and no `old_values`/`new_values`; only free-form `details` JSON. No action taxonomy. |
| RF-102 | Query audit by project | **Missing** — no way to filter events by project; `details` JSON is not queryable by project id. |
| RF-103 | Query audit by user | Partial — `AuditEvent.user` exists and is indexed; no API exposed. |
| RF-104 | Query audit by entity | **Missing** — no entity column at all. |
| RF-105 | Register digital signature events | **Done** — `DOCUMENT_SIGNED` emitted with document_id/version/sha256. |
| RF-106 | Register sensitive document downloads | **Missing** — `download` and `version_detail` actions return presigned GET URLs but emit **no** audit event. No event type for downloads, no "sensitive" flag. |

Additional gaps:
- No dedicated `apps/audit` app; no audit serializers/viewsets/URLs/filters.
- No RLS for the audit table and no `/api/audit/` tenant requirement.
- No historical/old-new value capture (requires a diffing mechanism at write time).
- No audit UI/API to satisfy the Auditor role's read-only consumption.

## Open Questions

1. **Model strategy**: extend the existing `accounts.AuditEvent` with `entity` +
   `old_values`/`new_values` columns, or build a new `audit.AuditEvent` in a standalone
   app? (Standalone keeps `accounts` focused but risks two competing audit models.)
2. **Tenant scoping**: should the audit API be RLS-scoped per institution, or should
   the Auditor (level 7) have cross-institution read access (per keycloak role comment
   "read-only access across all institutions")? SPEC §6.13 permission table says
   "Consultar auditoría: Superadmin Sí, Admin institucional Sí, Director Limitado,
   Auditor Sí" — ambiguous on cross-institution.
3. **Entity linkage**: how to associate an event with a project (RF-102)? Add a generic
   `entity_type` + `entity_id` (UUID) + optional `project_id` denormalized column, and
   rely on `institution_id` for tenancy.
4. **Capture mechanism**: model signals (post_save/post_delete on all models) vs
   explicit emitter calls in services/views. Signals give blanket coverage (RF-100
   "todo cambio relevante") but risk noise and circular imports; explicit calls are
   precise but easy to miss. A hybrid (explicit for critical paths + targeted signals)
   may be needed.
5. **Old/new value capture**: full JSON snapshots of changed fields, or only diffs?
   Performance vs completeness. Requires `m2m_changed`/`pre_save` handling.
6. **Download tracking (RF-106)**: log presigned GET issuance (approximation) or
   actual object access (requires MinIO eventing / S3 access logging — larger scope)?
   What counts as "sensitive" (doc_type classification)?
7. **Compatibility**: existing `AuditEventType` enum is append-only via migrations.
   Adding generic CREATE/UPDATE/DELETE types is backward-compatible; renaming/refactor
   of `accounts.AuditEvent` is not (2040+ tests reference it).

## Risks

- **Two audit models / drift**: extending `accounts.AuditEvent` vs creating
  `audit.AuditEvent` could split writes across two tables. Must pick one canonical
  store or a clear migration path.
- **Tenant isolation breach**: if the audit API is not RLS-scoped and not added to
  `TENANT_REQUIRED_PREFIXES`, auditors/admins could read across institutions — a
  compliance risk in a multi-institution national system.
- **Data volume**: append-only full-snapshot auditing of every entity can balloon the
  table. Needs pagination, retention, and possibly partitioning.
- **Backward compatibility**: `AuditEvent` is heavily tested and referenced across
  accounts/reports/budgets/documents/projects/progress/calls. Any schema change must be
  additive (new nullable columns) to keep existing tests and the dual-audit pattern
  intact.
- **Noise / signal**: blanket signals produce noise and hard-to-maintain code;
  hand-placed emitter calls miss events. Both extremes are failure modes for RF-100.
- **Download semantics**: presigned-GET logging is not true access logging (client
  fetches directly from MinIO); it can be bypassed and does not prove a download
  occurred.

## Recommended Approach

**Build a standalone `apps/audit` app that owns the canonical audit read model and API,
while reusing `AuditEvent` as the base model (or introducing `audit.AuditEvent` with a
compatibility shim).** Concretely:

1. **Canonical model**: create `apps/audit` with an `AuditLog`/`AuditEvent` model that
   **extends or supersedes** `accounts.AuditEvent`, adding `entity_type` (str),
   `entity_id` (UUID nullable), `action` (CREATE/UPDATE/DELETE/STATE_CHANGE/SIGN/
   DOWNLOAD/LOGIN/etc.), `old_values`/`new_values` (JSON), and a denormalized
   `project_id` (nullable, for RF-102). Reuse `AuditEventEmitter` as the write path
   (move/alias it into the audit app to keep `accounts` clean and preserve the ~50+
   existing call sites).
2. **Capture**: keep the existing explicit emitter calls (preserves current coverage)
   and **add targeted capture** for create/update/delete of the core entities
   (projects, users, researchers, budgets, documents) where RF-100/RF-101 demand it —
   likely via `post_save`/`pre_save`/`post_delete` signals in a dedicated
   `audit/signals.py`, wired via app `ready()`.
3. **Query API**: a read-only `AuditLogViewSet` with `django-filter` support for
   `project_id` (RF-102), `user` (RF-103), and `entity_type`+`entity_id` (RF-104),
   plus `action`/`date_range`/`institution` filters. Permission: `IsAuditor` +
   `IsSameInstitution` (or a dedicated cross-institution auditor policy per open
   question 2).
4. **RF-106 downloads**: emit `DOWNLOAD` events in the `download`/`version_detail`
   document views (presigned GET issuance) and classify sensitive doc types. Note the
   limitation (presigned vs true access) as a documented tradeoff.
5. **Tenant/RLS**: add the audit table to RLS `TENANT_SCOPED_TABLES` and add
   `/api/audit/` to `TENANT_REQUIRED_PREFIXES`; expose the AuditEvent types as
   generic CREATE/UPDATE/DELETE additions to keep RF-105 (DOCUMENT_SIGNED) intact.

This is the **extend existing** approach rather than a wholly new parallel system: it
unifies on one emitter + one table, adds the missing entity/old-new fields additively,
and builds the query surface the SPEC demands. Effort is **Medium-High** due to the RLS,
signal, and backward-compat surface.

## Affected Areas

- `backend/apps/accounts/audit.py` — base `AuditEvent`/`AuditEventType`/emitter;
  additive extension or move.
- `backend/apps/accounts/models.py` — imports `AuditEvent`; may need migration shim.
- `backend/apps/audit/` (new) — model, signals, serializers, viewsets, urls, filters,
  permissions, RLS migration, tests.
- `backend/apps/documents/views.py` + `services.py` — add DOWNLOAD events (RF-106).
- `backend/config/settings/base.py` — add `apps.audit` to `LOCAL_APPS`; possibly middleware.
- `backend/config/urls.py` — include `apps.audit.urls`.
- `backend/config/middleware/tenant.py` — add `/api/audit/` tenant-required prefix.
- Existing RLS migrations / `0004_rls_policies.py` — add audit table.
- `backend/apps/accounts/permissions.py` — `IsAuditor` reuse; maybe new cross-tenant policy.
- `SPEC_sigpi.md` §6.13 — source of requirements (RF-100..106).

## Ready for Proposal

**Yes.** The scope is well-defined by RF-100..106 and the existing audit machinery is
understood. Before the proposal, the orchestrator should confirm with the user: (a) the
**cross-institution access** question for the Auditor role (RLS vs cross-tenant), and
(b) whether **download tracking** may be presigned-GET logging or must be true MinIO
access logging (scope/effort difference).
