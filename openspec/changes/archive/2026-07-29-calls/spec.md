# Calls Module Specification (SIGPI §6.8)

## Purpose

Manage funding calls (convocatorias) — internal and external — with a 6-state FSM lifecycle, metadata-only document records, and constrained project association. Calls are institution-scoped and guarded by `director_centro` for lifecycle transitions.

## Requirements

### Requirement: Call CRUD (RF-067)

The system MUST allow creating, reading, updating, and deleting Call records. Initial status MUST be `borrador`. Internal calls MUST reject `external_entity`; external calls MUST require it. All four dates (`submission_start`, `submission_end`, `evaluation_start`, `evaluation_end`) are nullable; when present, ordering MUST be validated.

#### Scenario: Create internal call

- GIVEN an authenticated director_centro of Institution I
- WHEN POST `/api/calls/` with `type=internal`, `title`, `description`, all dates null
- THEN a Call is created with `status="borrador"`, `institution=I`, `external_entity=""`

#### Scenario: Create external call without entity

- GIVEN an authenticated director_centro
- WHEN POST `/api/calls/` with `type=external` and no `external_entity`
- THEN 400 `{"external_entity":["External entity is required for external calls."]}`

#### Scenario: Internal call with entity rejected

- GIVEN an authenticated director_centro
- WHEN POST `/api/calls/` with `type=internal` and `external_entity="CONAHCYT"`
- THEN 400 `{"external_entity":["Internal calls must not have an external entity."]}`

#### Scenario: Date ordering validation

- GIVEN a create payload where `submission_end` < `submission_start`
- WHEN POST `/api/calls/`
- THEN 400 `{"submission_end":["Submission end must be on or after submission start."]}`

#### Scenario: Update call in borrador

- GIVEN a Call in `borrador`
- WHEN PATCH `/api/calls/{id}/` with updated `title`
- THEN the Call is updated

#### Scenario: Delete call in borrador

- GIVEN a Call in `borrador` with no linked projects
- WHEN DELETE `/api/calls/{id}/`
- THEN 204 and the Call is removed

#### Scenario: Delete call in non-borrador rejected

- GIVEN a Call in `abierta`
- WHEN DELETE `/api/calls/{id}/`
- THEN 403 `{"detail":"Only calls in borrador can be deleted."}`

### Requirement: FSM Lifecycle (RF-068)

The system MUST manage 6 states via `django-fsm`: `borrador → abierta → cerrada → en_evaluacion → resultados_publicados → archivada`. All transitions MUST be guarded by `director_centro` role. `CallService` MUST use `select_for_update` to prevent race conditions. Each transition MUST emit an `AuditEvent`.

#### Scenario: Open call

- GIVEN a Call in `borrador`
- WHEN director_centro POSTs `/api/calls/{id}/open_call/`
- THEN status becomes `abierta` and AuditEvent is emitted

#### Scenario: Close call

- GIVEN a Call in `abierta`
- WHEN director_centro POSTs `/api/calls/{id}/close_call/`
- THEN status becomes `cerrada`

#### Scenario: Start evaluation

- GIVEN a Call in `cerrada`
- WHEN director_centro POSTs `/api/calls/{id}/start_evaluation/`
- THEN status becomes `en_evaluacion`

#### Scenario: Publish results

- GIVEN a Call in `en_evaluacion`
- WHEN director_centro POSTs `/api/calls/{id}/publish_results/`
- THEN status becomes `resultados_publicados`

#### Scenario: Archive from resultados_publicados

- GIVEN a Call in `resultados_publicados`
- WHEN director_centro POSTs `/api/calls/{id}/archive/`
- THEN status becomes `archivada` (terminal)

#### Scenario: Archive directly from cerrada

- GIVEN a Call in `cerrada`
- WHEN director_centro POSTs `/api/calls/{id}/archive/`
- THEN status becomes `archivada` (terminal)

#### Scenario: Invalid transition rejected

- GIVEN a Call in `borrador`
- WHEN POST `/api/calls/{id}/publish_results/`
- THEN 409 `{"detail":"Transition not allowed from current state."}`

#### Scenario: Non-director transition rejected

- GIVEN a Call in `borrador` and a user without `director_centro` role
- WHEN POST `/api/calls/{id}/open_call/`
- THEN 403 `{"detail":"Only center directors can perform this action."}`

### Requirement: Document Metadata (RF-069)

The system MUST store `CallDocument` records with `name`, `doc_type`, and `external_url`. No file upload in MVP. Documents MUST be nested under their parent Call.

#### Scenario: Create document

- GIVEN a Call in any non-terminal state
- WHEN POST `/api/calls/{id}/documents/` with `name`, `doc_type`, `external_url`
- THEN CallDocument is created

#### Scenario: List documents

- GIVEN a Call with 3 documents
- WHEN GET `/api/calls/{id}/documents/`
- THEN response contains 3 document objects

#### Scenario: Update document

- GIVEN an existing CallDocument
- WHEN PATCH `/api/calls/{id}/documents/{did}/` with updated `name`
- THEN the document is updated

#### Scenario: Delete document

- GIVEN an existing CallDocument
- WHEN DELETE `/api/calls/{id}/documents/{did}/`
- THEN 204

### Requirement: Project Association (RF-070)

The system MUST link Projects to Calls via `CallProject`. `UniqueConstraint(project)` enforces one call per project. Projects MAY only be linked when the Call is in `abierta` state.

#### Scenario: Link project to open call

- GIVEN a Call in `abierta` and a Project not linked to any call
- WHEN POST `/api/calls/{id}/projects/` with `project`
- THEN CallProject is created

#### Scenario: Link project to non-open call rejected

- GIVEN a Call in `borrador`
- WHEN POST `/api/calls/{id}/projects/` with `project`
- THEN 403 `{"detail":"Projects can only be linked to open calls."}`

#### Scenario: Duplicate project association rejected

- GIVEN a Project already linked to Call A
- WHEN POST `/api/calls/{id}/projects/` with that project for Call B
- THEN 409 `{"detail":"Project is already associated with a call."}`

#### Scenario: Unlink project

- GIVEN a CallProject record
- WHEN DELETE `/api/calls/{id}/projects/{pid}/`
- THEN 204 and the association is removed

### Requirement: Filtering (RF-071)

The system MUST support filtering Calls by `state`, `type`, `external_entity`, date ranges, and `institution`. Ordering and search MUST be enabled.

#### Scenario: Filter by state

- GIVEN 3 Calls with states `borrador`, `abierta`, `cerrada`
- WHEN GET `/api/calls/?state=abierta`
- THEN only the `abierta` call is returned

#### Scenario: Filter by type

- GIVEN 2 internal and 1 external call
- WHEN GET `/api/calls/?type=external`
- THEN only the external call is returned

#### Scenario: Filter by date range

- GIVEN calls with various `submission_start` dates
- WHEN GET `/api/calls/?submission_start_after=2026-01-01&submission_start_before=2026-06-30`
- THEN only calls within the range are returned

### Requirement: RLS Tenant Isolation (RF-072)

The system MUST enforce Row-Level Security on `calls_call` via `institution_id`. Users MUST only see their institution's calls. Superadmin bypass MUST be honored.

#### Scenario: Institution-scoped list

- GIVEN User A from Institution X and User B from Institution Y
- WHEN User A GETs `/api/calls/`
- THEN only Institution X calls are returned

#### Scenario: Cross-institution detail access denied

- GIVEN a Call belonging to Institution Y
- WHEN User A (Institution X) GETs `/api/calls/{y_call_id}/`
- THEN 404 (object not visible)

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **Call** | `id` (UUID PK), `institution` (FK→Institution), `institution_id` (UUID, denorm for RLS), `title`, `description`, `call_type` (internal/external), `external_entity` (CharField, blank), `submission_start` (Date, null), `submission_end` (Date, null), `evaluation_start` (Date, null), `evaluation_end` (Date, null), `status` (FSMField), `created_at`, `updated_at` | CHECK: `type=internal → external_entity=''`; CHECK: `type=external → external_entity≠''`; CHECK: date ordering when present |
| **CallDocument** | `id` (UUID PK), `call` (FK→Call), `name`, `doc_type` (TextChoices), `external_url`, `created_at` | — |
| **CallProject** | `id` (UUID PK), `call` (FK→Call), `project` (FK→Project), `linked_at` | UniqueConstraint(`project`) |

### Enumerations

- `CallType`: `internal`, `external`
- `CallDocumentType`: `convocatoria`, `anexo`, `reglamento`, `resultado`, `otro`
- `CallStatus` (FSM): `borrador`, `abierta`, `cerrada`, `en_evaluacion`, `resultados_publicados`, `archivada`

### FSM Specification

| Source | Target | Trigger | Guard | Side Effects |
|---|---|---|---|---|
| `borrador` | `abierta` | `open_call()` | `director_centro` | Log; emit `AuditEvent` |
| `abierta` | `cerrada` | `close_call()` | `director_centro` | Log; emit `AuditEvent` |
| `cerrada` | `en_evaluacion` | `start_evaluation()` | `director_centro` | Log; emit `AuditEvent` |
| `en_evaluacion` | `resultados_publicados` | `publish_results()` | `director_centro` | Log; emit `AuditEvent` |
| `cerrada` | `archivada` | `archive()` | `director_centro` | Terminal; log; emit `AuditEvent` |
| `resultados_publicados` | `archivada` | `archive()` | `director_centro` | Terminal; log; emit `AuditEvent` |

Terminal state: `archivada`. No outbound transitions.

## API Contract

| Endpoint | Method | Auth | Request Body | Response |
|---|---|---|---|---|
| `/api/calls/` | GET, POST | Session | `title`, `description`, `call_type`, `external_entity?`, `submission_start?`, `submission_end?`, `evaluation_start?`, `evaluation_end?` | List / Call |
| `/api/calls/{id}/` | GET, PATCH, DELETE | Session | partial fields | Call / 204 |
| `/api/calls/{id}/open_call/` | POST | Session | — | Call |
| `/api/calls/{id}/close_call/` | POST | Session | — | Call |
| `/api/calls/{id}/start_evaluation/` | POST | Session | — | Call |
| `/api/calls/{id}/publish_results/` | POST | Session | — | Call |
| `/api/calls/{id}/archive/` | POST | Session | — | Call |
| `/api/calls/{id}/documents/` | GET, POST | Session | `name`, `doc_type`, `external_url` | List / CallDocument |
| `/api/calls/{id}/documents/{did}/` | PATCH, DELETE | Session | partial | CallDocument / 204 |
| `/api/calls/{id}/projects/` | GET, POST | Session | `project` | List / CallProject |
| `/api/calls/{id}/projects/{pid}/` | DELETE | Session | — | 204 |

## Security & Permissions

| Action | Superadmin | Admin | Director Centro | Researcher | Other |
|---|---|---|---|---|---|
| Create call | ✓ | ✓ | ✓ | — | — |
| Update call (borrador) | ✓ | ✓ | ✓ | — | — |
| Delete call (borrador, no projects) | ✓ | ✓ | ✓ | — | — |
| FSM transitions | ✓ | ✓ | ✓ | — | — |
| Manage documents | ✓ | ✓ | ✓ | — | — |
| Link/unlink projects | ✓ | ✓ | ✓ | — | — |
| List/retrieve (institution-scoped) | ✓ (all) | ✓ (all) | ✓ (own) | ✓ (own) | — |

RLS: `calls_call` table MUST have `tenant_isolation` and `superadmin_bypass` policies (mirrors existing pattern in `0004_rls_policies.py`).

## Error Handling

| Error | Status | Response |
|---|---|---|
| External call missing entity | 400 | `{"external_entity":["External entity is required for external calls."]}` |
| Internal call with entity | 400 | `{"external_entity":["Internal calls must not have an external entity."]}` |
| Date ordering violation | 400 | `{"submission_end":["Submission end must be on or after submission start."]}` |
| Invalid FSM transition | 409 | `{"detail":"Transition not allowed from current state."}` |
| Non-director transition | 403 | `{"detail":"Only center directors can perform this action."}` |
| Delete non-borrador call | 403 | `{"detail":"Only calls in borrador can be deleted."}` |
| Link project to non-open call | 403 | `{"detail":"Projects can only be linked to open calls."}` |
| Duplicate project association | 409 | `{"detail":"Project is already associated with a call."}` |
| RLS institution violation | 404 | Object not visible (404, not 403, to avoid enumeration) |

## Non-Functional Requirements

- Test coverage MUST be ≥80% (pytest, pytest-django, pytest-cov). Strict TDD Red-Green-Refactor.
- API list response SHOULD be <200ms; detail <100ms.
- `CallService` FSM methods MUST use `select_for_update` to prevent race conditions.
- All FSM transitions MUST emit `AuditEvent` (mirrors projects pattern).
- `CallDocument` is metadata-only — no file upload in MVP.
- `CallProject` enforces one call per project at DB level via `UniqueConstraint`.
