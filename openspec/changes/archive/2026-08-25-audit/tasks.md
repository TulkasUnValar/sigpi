# Tasks: Audit & Traceability Module (SIGPI §6.13)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1100–1200 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 (stacked to main) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Migrations 0008 + 0009 (fields, indexes, RLS) | PR 1 | `cd backend; python -m pytest apps/audit/tests/test_rls.py apps/accounts/tests/test_migrations.py` | `python manage.py migrate; python manage.py makemigrations --check --dry-run` | Revert removes fields/policies; no signal/API code shipped yet |
| 2 | App scaffold + emitter extension + signal layer (no API) | PR 2 | `cd backend; python -m pytest apps/audit/tests/test_signals.py apps/audit/tests/test_emitter.py` | Run Django shell: save/delete a Project/Researcher and inspect `AuditEvent` rows | Unregister signals + revert `audit.py`; API never exposed |
| 3 | API read path (permission, serializers, filters, ViewSet, URLs) + config wiring | PR 3 | `cd backend; python -m pytest apps/audit/tests/test_api.py` | `GET /api/audit/?project_id=…` as auditor vs researcher | Revert API files + `/api/audit/` route + tenant prefix; signal/emitter writes unaffected |
| 4 | Documents DOWNLOAD events + e2e/integration coverage | PR 4 | `cd backend; python -m pytest apps/audit/tests/test_integration.py apps/documents/tests/` | `GET /api/documents/{id}/download/` asserts event; MinIO-down path asserts no event | Revert `documents/views.py` emitter lines; audit infra intact |

## Phase 1: Foundation — Migrations

- [x] 1.1 Create `backend/apps/accounts/migrations/0008_audit_traceability.py`: `AddField` nullable `entity_type` Char(50), `entity_id` UUID, `action` Char(20), `old_values`/`new_values` JSON, `project_id` UUID; `AlterField(event_type)` with expanded choices; `AddIndex` `(entity_type, entity_id)`, `(project_id, -timestamp)`, `(action, -timestamp)`
- [x] 1.2 Create `backend/apps/accounts/migrations/0009_audit_rls.py` (PostgreSQL-only): `ENABLE ROW LEVEL SECURITY`; `tenant_isolation` policy on `institution_id`; `superadmin_bypass` policy; reverse `DROP POLICY IF EXISTS` + disable RLS
- [x] 1.3 Add `entity_type`, `entity_id`, `action`, `old_values`, `new_values`, `project_id` fields to `AuditEvent` model in `backend/apps/accounts/models.py` (or `audit.py`) with matching indexes/choices
- [x] 1.4 Update `AuditEventType` choices in `backend/apps/accounts/audit.py`: add CREATE, UPDATE, DELETE, STATE_CHANGE, DOCUMENT_DOWNLOADED

## Phase 2: Emitter & Signal Capture

- [x] 2.1 Extend `AuditEventEmitter.emit()` in `backend/apps/accounts/audit.py` with keyword-only `entity_type, entity_id, action, old_values, new_values, project_id`, forwarding to `AuditEvent.objects.create`; keep old positional/keyword signature valid (backward-compatible)
- [x] 2.2 Create `backend/apps/audit/__init__.py`, `backend/apps/audit/apps.py` (AuditConfig with `ready()` connecting receivers via `dispatch_uid`)
- [x] 2.3 Create `backend/apps/audit/context.py`: request-scoped `ContextVar` carrying user/IP/institution; reset in middleware `finally`; explicit emitter kwargs override context
- [x] 2.4 Create `backend/apps/audit/signals.py`: `pre_save` loads prior row + diff; `post_save` emits CREATE/UPDATE; `post_delete` emits DELETE; receivers ignore raw saves, missing institution, and `AuditEvent`; never call `save()` on source (no recursion)
- [x] 2.5 Wire receivers for Project, ProgressReport, Researcher, Budget, Document (design tracked list); derive `project_id` from object or its project relation; safe scalar serialization of `old_values`/`new_values`. NOTE: User NOT tracked in PR 2 — task prompt lists the five models, not User.

## Phase 3: Read-Only API

- [x] 3.1 Create `backend/apps/audit/permissions.py`: `IsAuditReader` allowing Auditor, Director, Institutional Admin; superuser bypass; deny researchers/others
- [x] 3.2 Create `backend/apps/audit/serializers.py`: `AuditLogSerializer` exposing entity/action/values/project/user/timestamp fields
- [x] 3.3 Create `backend/apps/audit/filters.py`: `AuditFilter` for `project_id, user_id, entity_type, entity_id, action, event_type, date_from, date_to, institution_id`
- [x] 3.4 Create `backend/apps/audit/views.py`: `AuditLogViewSet(ReadOnlyModelViewSet)` with `DjangoFilterBackend`, `PageNumberPagination` (`max_page_size=100`), `IsAuthenticated` + `IsAuditReader`; queryset institution-filtered unless superuser; `select_related("user")`; order `-timestamp`
- [x] 3.5 Create `backend/apps/audit/urls.py` using `SimpleRouter` at `/api/audit/`
- [x] 3.6 Register `apps.audit` in `backend/config/settings/base.py`; add `/api/audit/` to `backend/config/urls.py`; add `/api/audit/` to `TENANT_REQUIRED_PREFIXES` in `backend/config/middleware/tenant.py`

## Phase 4: Documents Download Events (RF-106)

- [x] 4.1 In `backend/apps/documents/views.py` `version_detail` and `download`: emit `DOCUMENT_DOWNLOADED` (`action=DOWNLOAD`, `entity_type="document"`, `entity_id`, `project_id`, `details={document_id, version}`) immediately after `_get_storage().presign_get(...)` returns, before building response (503 path emits nothing)

## Phase 5: Tests

> PR 1 delivered `backend/apps/accounts/tests/test_audit_migrations.py` (26 passing, 2 PostgreSQL-only skipped) covering model fields, composite indexes, event-type choices, 0008/0009 migration structure, RLS SQL, and migration reversibility.

- [x] 5.1 `backend/apps/accounts/tests/test_audit_emitter.py` (delivered in `apps/accounts/tests/` per PR 2 task): backward compatibility of legacy kwargs; new kwargs forwarded; AuditEventType choices
- [x] 5.2 `backend/apps/audit/tests/test_signals.py`: create/update/delete signals; field-diff old/new; raw-save and missing-institution skip; no-change save skip; AuditEvent excluded
- [x] 5.3 `backend/apps/audit/tests/test_api.py`: each filter (RA-3..RA-5), ordering, 100-item cap, read-only methods, role denial (RA-8 non-auditor 403), institution isolation, superuser bypass (+ `backend/apps/audit/tests/test_permissions.py`: IsAuditReader role matrix)
- [x] 5.4 `backend/apps/audit/tests/test_rls.py` (PostgreSQL): policies exist; `tenant_isolation` and `superadmin_bypass` SQL
- [x] 5.5 `backend/apps/audit/tests/test_integration.py`: project CRUD/FSM STATE_CHANGE; document download + version_detail success and storage-failure (no event); signature event; budget; legacy suite compatibility; coverage ≥80%
