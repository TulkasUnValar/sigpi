# Progress Reporting Module Specification (SIGPI §6.5)

## Overview

Enables periodic progress reporting for research projects. Investigators register advances documenting activities, difficulties, and cumulative completion percentage. Center directors review, approve, observe, or reject advances. The system maintains full revision history and calculates official project progress via a 6-state FSM (borrador → enviado → en_revision → observado → aprobado → rechazado).

Standalone bounded context: `apps.progress`. Depends on `projects` (Project FK, IsCenterDirectorForProject permission), `accounts` (User, RLS, AuditEvent).

## Functional Requirements

| Code | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| RF-041 | Investigator registers advances for their projects | Must | Any ProjectMember with permissions can create ProgressReport linked to their Project; `created_by` tracks author |
| RF-042 | Advance includes period, description, percentage, activities, difficulties, next steps | Must | ProgressReport stores `period_start`, `period_end`, `description`, `cumulative_percentage`, `activities`, `difficulties`, `next_steps` |
| RF-043 | Advance allows attachment of supporting documents | Should | ProgressDocument stores metadata (name, doc_type, external_url); file upload deferred to post-MVP |
| RF-044 | Advance can be submitted to center director | Must | `submit()` transitions borrador → enviado; requires valid period and percentage |
| RF-045 | Center director can approve advances | Must | `approve()` transitions en_revision → aprobado; updates `Project.cumulative_progress` |
| RF-046 | Center director can observe advances | Must | `observe(text)` transitions en_revision → observado; creates append-only ProgressReview |
| RF-047 | Center director can reject advances | Must | `reject()` transitions en_revision → rechazado; NOT terminal — can return to borrador |
| RF-048 | System preserves complete revision history | Must | ProgressStateLog (append-only) records every FSM transition; ProgressReview records director observations |
| RF-049 | System calculates cumulative project progress | Must | On approval, `Project.cumulative_progress` = latest approved ProgressReport's `cumulative_percentage` |

## Business Rules

| Code | Rule |
|---|---|
| RN-P01 | `cumulative_percentage` MUST be between 0.00 and 100.00 inclusive. |
| RN-P02 | `period_end` MUST be ≥ `period_start`. |
| RN-P03 | Only a Center Director of the project's center MAY approve, observe, or reject an advance (RN-010 reuse). |
| RN-P04 | Every FSM transition MUST be recorded in ProgressStateLog AND mirrored to AuditEvent. |
| RN-P05 | ProgressReview and ProgressStateLog MUST be append-only; no update or delete endpoints. |
| RN-P06 | `rechazado` is NOT terminal; `return_to_draft()` transitions rechazado → borrador. |
| RN-P07 | `aprobado` IS terminal for the advance lifecycle; no outbound transitions. |
| RN-P08 | On approval, `Project.cumulative_progress` is recalculated from the latest approved advance (not summed). |
| RN-P09 | A Project MUST exist and be in a non-terminal state for advances to be created. |
| RN-P10 | Institution-scoped queryset via RLS; all progress tables are tenant-scoped. |

## Data Model

All entities inherit institution-scoping via denormalized `institution_id` for RLS.

| Entity | Key Fields | Constraints |
|---|---|---|
| **ProgressReport** | `id` (UUID PK), `institution` (FK→Institution), `project` (FK→Project), `created_by` (FK→User), `period_start` (Date), `period_end` (Date), `description` (Text), `cumulative_percentage` (Decimal 5,2), `activities` (Text), `difficulties` (Text, blank), `next_steps` (Text, blank), `status` (FSMField), `created_at`, `updated_at` | `period_end >= period_start`; `0 <= cumulative_percentage <= 100`; DB table `progress_progressreport` |
| **ProgressReview** | `id` (UUID PK), `progress_report` (FK→ProgressReport), `reviewed_by` (FK→User, SET_NULL), `review_text` (Text), `review_type` (TextChoices: observation/rejection), `created_at` | Append-only; no update/delete endpoints |
| **ProgressDocument** | `id` (UUID PK), `progress_report` (FK→ProgressReport), `name` (CharField), `doc_type` (TextChoices), `external_url` (URLField, blank), `uploaded_at` (DateTime) | Metadata-only; file upload deferred |
| **ProgressStateLog** | `id` (UUID PK), `progress_report` (FK→ProgressReport), `from_state` (CharField), `to_state` (CharField), `triggered_by` (FK→User, SET_NULL), `reason` (Text, blank), `created_at` | Append-only |

### Enumerations

- `ProgressStatus` (FSM): `borrador`, `enviado`, `en_revision`, `observado`, `aprobado`, `rechazado`
- `ProgressDocumentType`: `evidence`, `annex`, `report`, `other`
- `ProgressReviewType`: `observation`, `rejection`

## FSM Specification

| Source | Target | Trigger | Guard | Side Effects |
|---|---|---|---|---|
| `borrador` | `enviado` | `submit()` | period valid; percentage valid | Log; emit AuditEvent |
| `enviado` | `en_revision` | `accept_review()` | IsCenterDirectorForProject | Log; emit AuditEvent |
| `en_revision` | `aprobado` | `approve()` | IsCenterDirectorForProject | Update `Project.cumulative_progress`; log; emit AuditEvent |
| `en_revision` | `observado` | `observe(review_text)` | IsCenterDirectorForProject | Create ProgressReview; log; emit AuditEvent |
| `en_revision` | `rechazado` | `reject(review_text)` | IsCenterDirectorForProject | Create ProgressReview; log; emit AuditEvent |
| `en_revision` | `borrador` | `return_to_draft()` | IsCenterDirectorForProject | Log; emit AuditEvent |
| `observado` | `enviado` | `resubmit()` | created_by or Admin | Log; emit AuditEvent |
| `observado` | `borrador` | `return_to_draft()` | IsCenterDirectorForProject | Log; emit AuditEvent |
| `rechazado` | `borrador` | `return_to_draft()` | created_by or Admin | Log; emit AuditEvent |

Terminal state: `aprobado`. No outbound transitions.
Non-terminal reject: `rechazado` allows `return_to_draft()` → `borrador`.

## API Contract

| Endpoint | Method | Auth | Request Body | Response |
|---|---|---|---|---|
| `/progress/` | GET, POST | Session | `project`, `period_start`, `period_end`, `description`, `cumulative_percentage`, `activities`, `difficulties?`, `next_steps?` | List / ProgressReport |
| `/progress/{id}/` | GET, PATCH, DELETE | Session | partial fields | ProgressReport / 204 |
| `/progress/{id}/submit/` | POST | Session | — | ProgressReport |
| `/progress/{id}/accept_review/` | POST | Session | — | ProgressReport |
| `/progress/{id}/approve/` | POST | Session | — | ProgressReport |
| `/progress/{id}/observe/` | POST | Session | `review_text` | ProgressReport |
| `/progress/{id}/reject/` | POST | Session | `review_text` | ProgressReport |
| `/progress/{id}/return_to_draft/` | POST | Session | — | ProgressReport |
| `/progress/{id}/resubmit/` | POST | Session | — | ProgressReport |
| `/progress/{id}/documents/` | GET, POST | Session | `name`, `doc_type`, `external_url` | List / Document |
| `/progress/{id}/documents/{did}/` | PATCH, DELETE | Session | partial | Document / 204 |
| `/progress/{id}/reviews/` | GET | Session | — | List ProgressReview |
| `/progress/{id}/state_history/` | GET | Session | — | List ProgressStateLog |
| `/projects/{id}/progress/` | GET | Session | — | List ProgressReport (read-only nested shortcut) |

## Security & Permissions

| Action | Superadmin | Admin | Center Director | PI | Co-Investigator | Other |
|---|---|---|---|---|---|---|
| Create advance | ✓ | ✓ | — | ✓ | ✓ (if member) | — |
| Update advance (borrador) | ✓ | ✓ | — | ✓ (creator) | ✓ (creator) | — |
| Delete advance (borrador) | ✓ | ✓ | — | ✓ (creator) | — | — |
| Submit / Resubmit | ✓ | ✓ | — | ✓ (creator) | ✓ (creator) | — |
| Accept for review | ✓ | ✓ | ✓ (RN-P03) | — | — | — |
| Approve / Observe / Reject | ✓ | ✓ | ✓ (RN-P03) | — | — | — |
| Return to draft | ✓ | ✓ | ✓ (RN-P03) | ✓ (if rechazado) | — | — |
| Manage documents | ✓ | ✓ | — | ✓ (creator) | ✓ (creator) | — |
| View reviews / state history | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (institution) |

Permission classes:
- `IsProgressCreatorOrProjectMember` — user is `created_by` OR is a ProjectMember of the associated project.
- `IsCenterDirectorForProject` — reused from `projects/permissions.py`; checks user's membership includes the project's center with Director role.

## Error Handling

| Error | Status | Response |
|---|---|---|
| Invalid percentage (< 0 or > 100) | 400 | `{"detail":"Cumulative percentage must be between 0 and 100."}` |
| period_end < period_start | 400 | `{"detail":"Period end must be on or after period start."}` |
| Invalid FSM transition | 400 | `{"detail":"Transition not allowed from current state."}` |
| Not center director | 403 | `{"detail":"Only the center director can perform this action."}` |
| Project in terminal state | 403 | `{"detail":"Cannot create advances for a closed project."}` |
| Advance not in borrador for edit | 403 | `{"detail":"Advance can only be edited in draft state."}` |
| RLS institution violation | 403 | `{"detail":"Institution access denied."}` |

## Acceptance Criteria (Gherkin)

### RF-041: Register advances

```gherkin
Scenario: Investigator creates a progress report
  GIVEN a Researcher is a ProjectMember of Project P in borrador
  WHEN they POST /progress/ with project=P, period_start, period_end, description, cumulative_percentage=25, activities
  THEN a ProgressReport is created with status="borrador" and created_by=request.user

Scenario: Non-member cannot create advance
  GIVEN a Researcher is NOT a ProjectMember of Project P
  WHEN they POST /progress/ with project=P
  THEN 403 "You must be a project member to create advances."
```

### RF-042: Advance content fields

```gherkin
Scenario: All required fields validated
  GIVEN a valid create payload missing "activities"
  WHEN POST /progress/
  THEN 400 with field-level error on activities

Scenario: Percentage boundary validation
  GIVEN a create payload with cumulative_percentage=105
  WHEN POST /progress/
  THEN 400 "Cumulative percentage must be between 0 and 100."
```

### RF-043: Document attachments (metadata-only)

```gherkin
Scenario: Attach document metadata to draft advance
  GIVEN a ProgressReport in borrador
  WHEN POST /progress/{id}/documents/ with name="Evidence Q1", doc_type="evidence", external_url="https://..."
  THEN ProgressDocument is created and linked to the report

Scenario: File upload not available
  GIVEN any ProgressReport
  WHEN viewing the document creation form
  THEN only metadata fields are shown; no file upload widget (deferred to post-MVP)
```

### RF-044: Submit advance

```gherkin
Scenario: Submit draft advance
  GIVEN a ProgressReport in borrador with valid period and percentage
  WHEN POST /progress/{id}/submit/
  THEN status becomes "enviado" and ProgressStateLog row is created

Scenario: Cannot submit with invalid data
  GIVEN a ProgressReport in borrador with period_end < period_start
  WHEN POST /progress/{id}/submit/
  THEN 400 "Period end must be on or after period start."
```

### RF-045: Approve advance

```gherkin
Scenario: Director approves advance
  GIVEN a ProgressReport in en_revision for Project P in Center C
  AND the requesting user is Director of Center C
  WHEN POST /progress/{id}/approve/
  THEN status becomes "aprobado"
  AND Project.cumulative_progress is updated to the report's cumulative_percentage
  AND ProgressStateLog records the transition

Scenario: Non-director cannot approve
  GIVEN a ProgressReport in en_revision
  AND the requesting user is NOT Director of the project's center
  WHEN POST /progress/{id}/approve/
  THEN 403 "Only the center director can perform this action."
```

### RF-046: Observe advance

```gherkin
Scenario: Director observes advance with feedback
  GIVEN a ProgressReport in en_revision
  AND the requesting user is Director of the project's center
  WHEN POST /progress/{id}/observe/ with review_text="Need more detail on methodology"
  THEN status becomes "observado"
  AND a ProgressReview is created with review_type="observation"
  AND ProgressStateLog records the transition
```

### RF-047: Reject advance

```gherkin
Scenario: Director rejects advance
  GIVEN a ProgressReport in en_revision
  AND the requesting user is Director of the project's center
  WHEN POST /progress/{id}/reject/ with review_text="Data is inconsistent"
  THEN status becomes "rechazado"
  AND a ProgressReview is created with review_type="rejection"

Scenario: Rejected advance returns to draft
  GIVEN a ProgressReport in rechazado
  WHEN POST /progress/{id}/return_to_draft/
  THEN status becomes "borrador" and investigator can edit and resubmit
```

### RF-048: Revision history

```gherkin
Scenario: Full state history queryable
  GIVEN a ProgressReport that went through borrador → enviado → en_revision → observado → enviado → en_revision → aprobado
  WHEN GET /progress/{id}/state_history/
  THEN 6 ProgressStateLog entries are returned in chronological order

Scenario: Reviews are append-only
  GIVEN a ProgressReview exists
  WHEN attempting PATCH or DELETE on /progress/{id}/reviews/{rid}/
  THEN 405 Method Not Allowed
```

### RF-049: Cumulative progress calculation

```gherkin
Scenario: Project progress updated on approval
  GIVEN Project P with cumulative_progress=0
  AND ProgressReport R1 with cumulative_percentage=30 is approved
  THEN Project P.cumulative_progress becomes 30.00

Scenario: Revised advance recalculates correctly
  GIVEN Project P with cumulative_progress=30 from a previous approval
  AND ProgressReport R2 with cumulative_percentage=50 is approved
  THEN Project P.cumulative_progress becomes 50.00 (not 80.00)

Scenario: Observing does not change project progress
  GIVEN Project P with cumulative_progress=30
  AND ProgressReport R3 is observed (not approved)
  THEN Project P.cumulative_progress remains 30.00
```

## Edge Cases

| Case | Expected Behavior |
|---|---|
| Multiple advances in borrador for same project | Allowed; each is independent |
| Submit advance when project is in terminal state (cerrado) | 403 — cannot create advances for closed projects |
| Approve advance after project center changes | IsCenterDirectorForProject checks current center assignment |
| Concurrent approval attempts | FSM transition is atomic; second attempt gets 400 "Transition not allowed" |
| cumulative_percentage = 0 on approval | Valid; Project.cumulative_progress set to 0.00 |
| cumulative_percentage = 100 on approval | Valid; project considered complete at 100% |
| Delete advance in enviado state | 403 — only borrador advances can be deleted |
| Resubmit observed advance by non-creator member | 403 — only created_by or Admin can resubmit |
| Empty activities field on submit | 400 — activities is required |
| Director observes then tries to approve same advance | 400 — advance is in observado, must be resubmitted first |

## Delta: Projects Module (Modified Capability)

### ADDED Requirements

#### Requirement: Cumulative Progress Tracking

The Project model SHALL include a denormalized `cumulative_progress` field (DecimalField, max_digits=5, decimal_places=2, default=0.00) that reflects the latest approved advance's cumulative percentage.

The ProjectService SHALL expose a `has_pending_progress_reports(project)` static method returning `True` if any ProgressReport for the project has status in (`enviado`, `en_revision`, `observado`).

##### Scenario: Cumulative progress field on Project

- GIVEN a Project exists
- WHEN GET `/projects/{id}/`
- THEN response includes `cumulative_progress` field (default 0.00)

##### Scenario: Pending reports helper for future reports module

- GIVEN a Project with one ProgressReport in `enviado` state
- WHEN `ProjectService.has_pending_progress_reports(project)` is called
- THEN returns `True`

##### Scenario: No pending reports

- GIVEN a Project with all ProgressReports in `aprobado` or `rechazado` state
- WHEN `ProjectService.has_pending_progress_reports(project)` is called
- THEN returns `False`

## Deferred Requirements

| Code | Requirement | Reason |
|---|---|---|
| RF-043 (file upload) | Actual file upload via MinIO/S3 | Infrastructure not ready; MVP uses metadata-only `external_url` |
| RF-096 | Meilisearch indexing of advances | Dependency not available; deferred to Search Integration change |
| — | Final reports module (§6.6) | Separate bounded context |
| — | PDF generation (RF-053) | Belongs to reports module |
| — | Configurable reporting periods | MVP uses flexible period_start/period_end dates |

## Non-Functional Requirements

- Test coverage MUST be ≥90% (pytest, pytest-django, pytest-cov, factory_boy).
- TDD Red–Green–Refactor is mandatory for all progress entities.
- API list response SHOULD be <200ms; detail <100ms.
- All FSM transitions MUST use `@transition` decorators with `protected=False` for admin repair.
- ProgressReview and ProgressStateLog ViewSets MUST be `ReadOnlyModelViewSet` with no write endpoints.
- Institution-scoped queryset filtering MUST be applied via `request.active_membership.institution`.
