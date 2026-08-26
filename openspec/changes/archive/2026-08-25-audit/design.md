# Design: Audit & Traceability Module

## Technical Approach

Add a standalone `apps.audit` read/API and signal package while retaining `accounts.AuditEvent` as the single write table and `AuditEventEmitter` as its canonical writer. The change is additive: existing callers keep working, signals add CRUD coverage, and services retain semantic events. A request context supplies actor/IP to signals.

## Architecture Decisions

| Decision | Choice | Tradeoff / rationale |
|---|---|---|
| Persistence | Extend `accounts_auditevent`; no second model | Prevents write drift and preserves legacy tests/callers. Nullable columns protect old rows. |
| Capture | Generic signals plus explicit semantic emitter | Signals cover ordinary CRUD; emitter preserves domain context and avoids blanket noise. `AuditEvent` itself is excluded from receivers. |
| Read authorization | New `IsAuditReader` (Auditor, Director, Institutional Admin; superuser bypass) plus queryset institution scope | Existing `IsAuditor` intentionally permits higher roles, including researchers; a dedicated permission prevents researcher audit reads while preserving existing behavior. |
| RLS | PostgreSQL policies on `accounts_auditevent` | Application filtering is usable on SQLite tests; PostgreSQL remains defense in depth. |

## Data Flow and Signals

`TenantMiddleware` → request audit context (user, IP, institution) → model save/delete → `apps.audit.signals` → `AuditEventEmitter.emit()` → `accounts_auditevent` → read-only ViewSet.

`pre_save` loads the prior row for tracked models and stores a changed-field diff on the instance; `post_save` emits CREATE or UPDATE, and `post_delete` emits DELETE. `Project` FSM services continue emitting STATE_CHANGE after transition (with old/new status). Receivers are connected from `apps.audit.apps.AuditConfig.ready()`, use `dispatch_uid`, and ignore raw saves, missing institution, and `AuditEvent`. A `ContextVar` is reset in middleware `finally`; explicit emitter kwargs override context. No receiver calls `save()` on the source model, preventing recursion. Bulk operations are not signal-captured and remain explicit-emitter responsibility.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/audit/{apps,context,signals,permissions,filters,serializers,views,urls}.py` | Create | App wiring, request context, targeted receivers, API contracts. |
| `backend/apps/accounts/audit.py` | Modify | Add fields/choices and optional emitter kwargs; preserve old signature behavior. |
| `backend/apps/accounts/migrations/0008_audit_traceability.py` | Create | Six `AddField` operations, `AlterField(event_type)`, and three `AddIndex` operations. |
| `backend/apps/accounts/migrations/0009_audit_rls.py` | Create | PostgreSQL RLS policies and reverse SQL. |
| `backend/config/settings/base.py`, `config/urls.py`, `config/middleware/tenant.py` | Modify | Register app, `/api/audit/`, and tenant-required prefix/context. |
| `backend/apps/documents/views.py` | Modify | Emit DOWNLOAD only after each presigned GET succeeds. |
| `backend/apps/audit/tests/` | Create | Signal, API, RLS, and end-to-end coverage. |

Migration `0008` uses `AddField` for nullable `entity_type` (`CharField(50)`), `entity_id` (`UUIDField`), `action` (`CharField(20)`), `old_values`/`new_values` (`JSONField`), and `project_id` (`UUIDField`), then `AlterField(event_type)` for the expanded choices and `AddIndex` for `(entity_type, entity_id)`, `(project_id, -timestamp)`, and `(action, -timestamp)`. `0009` runs, on PostgreSQL only:

```sql
ALTER TABLE accounts_auditevent ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON accounts_auditevent USING
 (institution_id = current_setting('sigpi.institution_id')::uuid);
CREATE POLICY superadmin_bypass ON accounts_auditevent USING
 (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
```

Reverse drops both policies and disables RLS; use `DROP POLICY IF EXISTS` for idempotence.

## Interfaces / Contracts

`emit(event_type, user=None, ip_address=None, institution_id=None, details=None, *, entity_type=None, entity_id=None, action=None, old_values=None, new_values=None, project_id=None)` forwards all fields to `AuditEvent.objects.create`; old positional/keyword calls remain valid. `AuditLogViewSet(ReadOnlyModelViewSet)` uses `DjangoFilterBackend`, `PageNumberPagination` capped by `max_page_size=100`, `IsAuthenticated`, `IsAuditReader`; queryset is institution-filtered unless superuser. `AuditFilter` supports `project_id,user_id,entity_type,entity_id,action,event_type,date_from,date_to,institution_id`; route via `SimpleRouter` at `/api/audit/`.

Capture mapping: Project→post-save CREATE/UPDATE, post-delete DELETE, FSM emitter STATE_CHANGE; User→signals CREATE/UPDATE plus existing ROLE_CHANGE; Researcher→signals CREATE/UPDATE/DELETE; Budget→existing BUDGET_* emitter; Document→existing UPLOADED/SIGNED plus views `DOCUMENT_DOWNLOADED`/DOWNLOAD; Advance/Report→existing state/approval emitters. Signals derive `project_id` from the object or its project relation and use safe scalar serialization.

In `DocumentViewSet.version_detail` and `download`, place the emitter immediately after `_get_storage().presign_get(...)` returns and before constructing/returning the response. Include `entity_type="document"`, `entity_id`, `project_id`, `details={document_id, version}`, and request actor/institution. Exceptions return 503 before this line, so no download event is written.

## Testing Strategy

Unit RED tests cover diffs, actor context, create/update/delete/state signals, recursion exclusion, and emitter backward compatibility. API tests cover every filter, ordering, 100-item cap, read-only methods, role denial, institution isolation, and superuser bypass. Integration tests execute project CRUD/FSM, document download/version detail success and storage failure, signature, budget, and legacy suite compatibility; PostgreSQL tests assert RLS SQL/policies. Maintain ≥80% coverage.

## Performance Considerations

Queries filter by tenant, then indexed project/entity/action/time columns; the ViewSet uses `select_related("user")` and page size 100. Field diffs avoid snapshot growth. Assuming 10–20 auditable writes per active user/day, expect roughly 1–5k rows/day per institution; monitor growth and defer retention.

## Threat Matrix

All rows are N/A: this change has ordinary Django URL routing but no documentation execution, shell/subprocess, Git repository/commit/push, or PR command boundary. Therefore no threat-matrix RED tests apply.

## Migration / Rollout

Apply additive migrations before deploying signal/API code; nullable columns and unchanged legacy kwargs keep the 2040+ suite compatible. Run existing tests, then enable the new app/routes. No historical backfill or data migration is required. Rollback removes fields/policies and unregisters routes/signals.

## Open Questions

- [ ] Confirm production estimate and retention policy outside this change.
