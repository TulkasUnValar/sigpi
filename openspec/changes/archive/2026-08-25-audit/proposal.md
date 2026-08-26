# Proposal: Audit & Traceability Module (SIGPI §6.13)

## Intent

SIGPI has no queryable, tenant-safe audit surface. `AuditEvent` is write-only, lacks entity/old-new fields, has no RLS policy, and sensitive downloads are untracked. This change satisfies RF-100..106 by extending the existing model additively and exposing a read-only audit API.

## Scope

### In Scope
- Additive `AuditEvent` columns: `entity_type`, `entity_id`, `action`, `old_values`, `new_values`, `project_id`; generic `CREATE`/`UPDATE`/`DELETE`/`STATE_CHANGE` event types
- New `apps/audit`: signals, serializers, read-only `AuditLogViewSet` (django-filter: project/user/entity/action/date), urls, RLS, tests
- Hybrid capture: explicit emitter (existing ~50 call sites) + targeted `pre_save`/`post_save`/`post_delete` signals on core models
- RLS policy on audit table; `/api/audit/` tenant-required
- RF-106: `DOWNLOAD` events on document `download`/`version_detail` (presigned-GET issuance)

### Out of Scope
- True MinIO/S3 object access logging; cross-institution Auditor reads; parallel audit model or historical data migration; emitter relocation (alias/re-export only); audit UI, retention policy, audit immutability, Meilisearch indexing

## Capabilities

### New Capabilities
- `audit`: extended `AuditEvent`, generic event types, hybrid capture, read-only query API, RLS/tenant enforcement — RF-100..106

### Modified Capabilities
- `documents`: Audit Requirements delta — `download`/`version_detail` MUST emit `DOCUMENT_DOWNLOADED` (RF-106). `auth` FR-007 unchanged; emitter remains canonical write path

## Approach

Standalone `apps/audit` reuses `accounts.AuditEvent` additively (nullable columns, no renames). `AuditEventEmitter` gains optional kwargs (`entity_type`, `entity_id`, `action`, `old_values`, `new_values`, `project_id`) — backward compatible. Targeted signals capture CRUD on projects, users, researchers, budgets, documents. Read-only `AuditLogViewSet` enforces `IsAuditor`/`IsSameInstitution` + RLS; superadmin bypass covers cross-institution reads.

## Key Decisions

| Decision | Rationale |
|---|---|
| Extend existing `AuditEvent` | One table, no write drift; 2040+ tests stay green (additive nullable columns only) |
| Auditor scoped by institution | Matches FR-006 and all modules; superadmin bypass already covers cross-institution |
| Presigned-GET logging (RF-106) | Backend proves URL issuance; MinIO access logging is deferred infra scope |
| Hybrid capture | Emitter preserves coverage; targeted signals close RF-100/101 gaps without blanket noise |
| Changed-fields diff for old/new | Controls volume vs full snapshots; sufficient for traceability (assumption) |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/audit/` | New | model migration, signals, API, RLS, tests |
| `backend/apps/accounts/audit.py` | Modified | additive columns, new types, extended `emit()` |
| `backend/apps/documents/views.py`, `services.py` | Modified | `DOWNLOAD` events (RF-106) |
| `backend/config/settings/base.py`, `urls.py` | Modified | app registration + routes |
| `backend/config/middleware/tenant.py` | Modified | `/api/audit/` tenant-required prefix |
| `accounts/0004_rls_policies.py` | Modified | audit table RLS policy |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Tenant breach (RLS/prefix missed) | Med | Add both; tests assert cross-institution 403/empty |
| Breaking 2040+ `AuditEvent` tests | Low | Additive-only schema; optional kwargs; no renames |
| Append-only data volume | Med | Pagination, composite indexes, field diffs; retention deferred |
| Signal noise / missed events | Med | Targeted signals + explicit critical-path calls |
| Presigned-GET bypassable | High | Documented tradeoff; logs issuance (who/when/doc) |

## Rollback Plan

Reverse the additive migration (drop nullable columns), unregister `apps.audit` from `INSTALLED_APPS`/urls/tenant prefix, drop audit RLS policy, revert documents views. No data rewrite; existing rows unaffected.

## Dependencies

`accounts` RLS migration pattern, `IsAuditor`/`IsSameInstitution`, documents download endpoints, django-filter.

## Success Criteria

- [ ] RF-100..106 scenarios pass; backend coverage ≥80%
- [ ] `/api/audit/` tenant-required; cross-institution reads return 403/empty
- [ ] Query by project, user, entity returns expected events
- [ ] Existing suite (2040+ tests) passes unchanged
- [ ] `DOWNLOAD` event emitted on presigned GET issuance

## Open Questions

- Old/new capture: changed-fields diff assumed — confirm before specs phase
- "Sensitive" document classification for RF-106 — decide in specs phase
- Keycloak role comment implies cross-institution Auditor; decision NO per orchestrator — override requires user confirmation
