# Audit & Traceability Specification (SIGPI §6.13)

## Purpose

Provide a queryable, tenant-safe audit surface satisfying RF-100..106: record create/update/delete/state-change, capture actor/entity/old-new values, and expose read-only queries by project, user, and entity.

## Data Model (additive to `accounts.AuditEvent`)

| Field | Type | Notes |
|---|---|---|
| `entity_type` | Char(50) nullable, indexed | e.g. project, user, document |
| `entity_id` | UUID nullable, indexed | Target id (no GenericFK) |
| `action` | Char(20) nullable, indexed | CREATE/UPDATE/DELETE/STATE_CHANGE/DOWNLOAD |
| `old_values` | JSON nullable | Changed-fields diff |
| `new_values` | JSON nullable | Changed-fields diff |
| `project_id` | UUID nullable, indexed | Denormalized for RF-102 |

New composite indexes: `(entity_type, entity_id)`, `(project_id, -timestamp)`, `(action, -timestamp)`. `event_type` gains `CREATE`, `UPDATE`, `DELETE`, `STATE_CHANGE`, `DOWNLOAD` plus `DOCUMENT_DOWNLOADED`.

**RLS**: `accounts_auditevent` MUST get `tenant_isolation` (row `institution_id` = `sigpi.institution_id`) + `superadmin_bypass` policies, following the `0004_rls_policies` pattern.

## Requirements

### Requirement: RA-1 — Generic CRUD capture (RF-100)
The system MUST record creation, edit, logical-delete, and state-change of core entities via hybrid capture (explicit emitter + targeted signals).
#### Scenario: Researcher creates project
- GIVEN an investigator creates a project
- WHEN the project is saved
- THEN an AuditEvent is emitted with `event_type=CREATE`, `entity_type=project`, `entity_id`, `project_id`, `user`, `institution_id`
#### Scenario: Director approves advance (state change)
- GIVEN a director approves an advance
- WHEN the FSM transitions state
- THEN an AuditEvent with `action=STATE_CHANGE` and `new_values` recording the new state is emitted
#### Scenario: Logical delete
- GIVEN an entity is soft-deleted
- WHEN deletion occurs
- THEN an AuditEvent with `action=DELETE` is emitted

### Requirement: RA-2 — Actor & value capture (RF-101)
The system MUST record user, timestamp, IP, entity, action, and old/new values for each event.
#### Scenario: Update captures diff
- GIVEN a researcher updates a project
- WHEN the change is saved
- THEN `old_values`/`new_values` hold only changed fields, and `user`, `timestamp`, `ip_address`, `action` are non-null

### Requirement: RA-3 — Query by project (RF-102)
The system MUST allow filtering audit events by project.
#### Scenario: Auditor queries by project
- GIVEN an auditor in the institution
- WHEN GET `/api/audit/?project_id=<uuid>`
- THEN only events with that `project_id` are returned

### Requirement: RA-4 — Query by user (RF-103)
The system MUST allow filtering audit events by user.
#### Scenario: Filter by user
- GIVEN events from multiple users
- WHEN GET `/api/audit/?user_id=<uuid>`
- THEN only that user's events are returned

### Requirement: RA-5 — Query by entity (RF-104)
The system MUST allow filtering audit events by entity.
#### Scenario: Filter by entity
- GIVEN events for multiple entities
- WHEN GET `/api/audit/?entity_type=project&entity_id=<uuid>`
- THEN only matching entity events are returned

### Requirement: RA-6 — Signature events (RF-105)
The system MUST record digital-signature events; `DOCUMENT_SIGNED` MUST include `document_id`, `version`, and `sha256`.
#### Scenario: Document signed
- GIVEN a document version is signed
- WHEN signing completes
- THEN an AuditEvent `DOCUMENT_SIGNED` with `sha256` is emitted

### Requirement: RA-7 — Sensitive document downloads (RF-106)
The system MUST emit a `DOWNLOAD` event when a presigned GET is issued for a sensitive document `download` or `version_detail`.
#### Scenario: Sensitive download
- GIVEN a user requests `GET /api/documents/{id}/download/`
- WHEN the presigned GET is issued
- THEN an AuditEvent `DOCUMENT_DOWNLOADED` with `document_id` and `version` is emitted

### Requirement: RA-8 — Read-only audit API
`AuditLogViewSet` MUST be read-only; reads SHALL require `IsAuditor`+`IsSameInstitution` or superuser bypass.
#### Scenario: Non-auditor denied
- GIVEN a researcher (not auditor) in the institution
- WHEN GET `/api/audit/`
- THEN the system returns 403
#### Scenario: Cross-institution denied
- GIVEN an auditor of institution A
- WHEN reading institution B events
- THEN the system returns empty/403 (tenant-scoped)

## API Contract

| Endpoint | Method | Auth | Query params |
|---|---|---|---|
| `/api/audit/` | GET | Session; IsAuditor+IsSameInstitution or superuser | `project_id`, `user_id`, `entity_type`, `entity_id`, `action`, `event_type`, `date_from`, `date_to`, `institution_id` |
| `/api/audit/{id}/` | GET | same | — |

Read-only; ordered `-timestamp`; page size capped at 100.

## Event Types Catalog
- `event_type` (AuditEventType): existing LOGIN, LOGOUT, FAILED_LOGIN, INSTITUTION_SWITCH, ROLE_CHANGE, PERMISSION_DENIED, PROGRESS_STATE_CHANGE, REPORT_GENERATED, REPORT_APPROVED, BUDGET_CREATED, BUDGET_UPDATED, BUDGET_EXECUTION_ADDED, DOCUMENT_UPLOADED, DOCUMENT_SIGNED, MINUTES_CREATED **+ new** CREATE, UPDATE, DELETE, STATE_CHANGE, DOCUMENT_DOWNLOADED.
- `action` values: CREATE, UPDATE, DELETE, STATE_CHANGE, DOWNLOAD.

## Capture Matrix

| Model | Event | Mechanism |
|---|---|---|
| Project | CREATE/UPDATE/DELETE/STATE_CHANGE | signals + FSM emitter |
| User | CREATE/UPDATE/ROLE_CHANGE | signals/emitter |
| Researcher | CREATE/UPDATE/DELETE | signals |
| Budget | CREATE/UPDATE/EXECUTION | emitter (existing) |
| Document | UPLOADED/SIGNED/DOWNLOADED | emitter in views/services |
| Advance/Report | STATE_CHANGE/APPROVED | emitter (existing) |

## Permissions Matrix

| Actor | Read audit |
|---|---|
| Auditor | Yes — own institution (IsSameInstitution) |
| Admin institucional | Yes — own institution |
| Director | Limited — own institution |
| Superuser | Yes — all institutions (bypass) |
| Researcher / others | No (403) |

## Non-Functional Requirements
- Read queries MUST return <500 ms on indexed filters; pagination capped at 100/page.
- `old_values`/`new_values` MUST be field diffs (not full snapshots) to bound append-only volume.
- Retention policy is deferred (out of scope); data is append-only.
- Backend coverage MUST be ≥80% across RA-1..RA-8.
