# Notifications Specification (SIGPI HU-001, HU-003, HU-005, §13.5)

## Purpose

Transversal tenant-safe notifications module (`apps.notifications`). Actors receive in-app notifications when SPEC triggers fire; email is a log-only Celery stub (no SMTP). Emitting modules stay decoupled from delivery: they emit domain signals; notifications consumes them via receivers. Mirrors the audit module playbook (RLS + read-only API).

## Functional Requirements

### Requirement: RN-1 — Project Submitted Notifies Center Director (HU-001)

When a project transitions to `enviado`, the system MUST create a `Notification` for the center director of the project's center.

The notifications module SHALL subscribe to the existing `project_state_changed` signal and react only to `to_state="enviado"`. Recipient resolution MUST select the active center director of the project's center within the project's institution.

#### Scenario: Director receives notification on submit
- GIVEN a Project P in `borrador` in Center C and a User D who is Director of C
- WHEN the PI submits P (transition `borrador` → `enviado`)
- THEN a `Notification` is created with recipient=D, event_type=`PROJECT_SUBMITTED`, linked to P

#### Scenario: No director resolves — no notification
- GIVEN Center C has no active director
- WHEN a project in C is submitted
- THEN no notification is created and the resolver logs a warning

#### Scenario: Non-submit transitions ignored
- GIVEN a Project P transitions `enviado` → `en_revision`
- WHEN `project_state_changed` fires with `to_state` ≠ `enviado`
- THEN no Notification is created

### Requirement: RN-2 — Observed Advance Notifies Researcher (HU-003)

When an advance transitions to `observado`, the system MUST create a `Notification` for the advance's author (`created_by`).

The notifications module SHALL subscribe to `progress_state_changed` and react only to `to_state="observado"`.

#### Scenario: Researcher notified on observe
- GIVEN a ProgressReport R in `en_revision` authored by Researcher I
- WHEN the director observes R (`en_revision` → `observado`)
- THEN a `Notification` is created with recipient=I, event_type=`PROGRESS_OBSERVED`, linked to R

#### Scenario: Approval does not notify
- GIVEN a ProgressReport R in `en_revision`
- WHEN the director approves R (`to_state="aprobado"`)
- THEN no Notification is created

### Requirement: RN-3 — Signed Document Notifies Signer and PI (§13.5)

When a document version is signed, the system MUST create `Notification` rows for the signer and the project's responsible investigator (PI).

The notifications module SHALL subscribe to `document_signed`. The PI is resolved via the document's `project` FK; if the document has no linked project, ONLY the signer is notified.

#### Scenario: Signer and PI notified
- GIVEN an unsigned Document D linked to Project P with PI Researcher I
- WHEN User S signs D via `SignatureService.sign`
- THEN two `Notification` rows are created with event_type=`DOCUMENT_SIGNED`: recipient=S and recipient=I

#### Scenario: Document without project
- GIVEN a Document D with no linked project
- WHEN a user signs D
- THEN exactly one `Notification` is created for the signer

#### Scenario: Re-sign does not re-notify
- GIVEN a version already signed
- WHEN a second sign attempt fails with 409
- THEN no new `Notification` is created

### Requirement: RN-4 — Budget Overrun Attempt Notifies Institution Admin (HU-005)

When an execution would exceed the line's approved amount without authorization (RN-020), the system MUST create a `Notification` for an institutional administrator of the project's institution.

The notifications module SHALL subscribe to `budget_overrun_attempted`, emitted when `add_execution` rejects the overrun.

#### Scenario: Admin notified on overrun attempt
- GIVEN a BudgetLine with approved_amount=1000 and executions summing 900 in Institution I with Admin A
- WHEN a user attempts an execution of 200 without authorization
- THEN a `Notification` is created with recipient=A, event_type=`BUDGET_OVERRUN_ATTEMPTED`, linked to the BudgetLine

#### Scenario: Authorized overrun does not notify
- GIVEN a director records an over-limit execution with `authorized_by` set
- WHEN the execution is created
- THEN no Notification is created

## Event Types Catalog

| Event Type | Emitting Module | Signal & Filter | Recipient | SPEC Source |
|---|---|---|---|---|
| `PROJECT_SUBMITTED` | projects | `project_state_changed`, `to_state=enviado` | Center director of project's center | HU-001 |
| `PROGRESS_OBSERVED` | progress | `progress_state_changed`, `to_state=observado` | Advance author (`created_by`) | HU-003 |
| `DOCUMENT_SIGNED` | documents | `document_signed` | Signer + Project PI | §13.5 |
| `BUDGET_OVERRUN_ATTEMPTED` | budgets | `budget_overrun_attempted` | Institution admin | HU-005 |

- One source per trigger: notifications SHALL subscribe ONLY to the semantic signals listed; no audit-CRUD receivers.
- Out of scope: `workflow_completed`, call opened/closed, real SMTP, frontend UI.

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **Notification** | `id` (UUID PK), `institution` (FK, denormalized RLS), `recipient` (FK→User), `event_type` (CharField), `template` (FK→NotificationTemplate), `title`, `body`, `context` (JSON), `entity_type` + `entity_id` (nullable), `is_read` (Bool, default False), `read_at` (nullable), `created_at` | No GenericForeignKey; composite index `(recipient, is_read, -created_at)`; tenant-scoped |
| **NotificationTemplate** | `id`, `code` (unique), `title_template`, `body_template`, `is_active` (default True) | Seeded for the 4 event types; inactive template suppresses creation |
| **NotificationLog** | `id`, `notification` (FK, nullable), `channel` (TextChoices: email), `recipient_email`, `status` (pending/sent/failed), `attempt_count`, `last_error` (nullable), `created_at`, `updated_at` | Written by Celery task only |
| **UserPreference** | `id`, `user` (FK unique), `channel` (TextChoices: email), `enabled` (Bool, default True), `created_at`, `updated_at` | Per-channel opt-out; no UI in this change |

## API Contract

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/notifications/` | GET | Session | List own notifications; filters `is_read`, `event_type`; paginated (100/page) |
| `/api/notifications/unread_count/` | GET | Session | `{"count": N}` of own unread notifications |
| `/api/notifications/{id}/` | GET | Session | Detail — own notification only |
| `/api/notifications/{id}/read/` | POST | Session | Mark read; idempotent |
| `/api/notifications/read_all/` | POST | Session | Mark all own notifications read |
| `/api/notifications/preferences/` | GET, PATCH | Session | Read/update own `UserPreference` (email opt-out) |

Write endpoints are limited to read-state mutations; `Notification` rows are created ONLY by receivers (no create/update/delete API).

## Channel Semantics

| Channel | Delivery | Mechanism |
|---|---|---|
| In-app | Sync | `Notification` row created inside the sender's transaction (single DB insert; no I/O in receiver) |
| Email | Async | `dispatch_notification` Celery task enqueued via `transaction.on_commit`; writes `NotificationLog` (status, attempt_count, last_error). NO SMTP — log-only stub |

- Email MUST be skipped when the recipient's `UserPreference` disables email.
- Receivers MUST NOT perform I/O (no SMTP, no HTTP) inside the transaction.
- Delivery failure MUST NOT roll back the triggering transaction.

## Permissions Matrix

| Actor | Read own | Read others' | Mark read | Preferences |
|---|---|---|---|---|
| Any authenticated user | ✓ | — | ✓ (own) | ✓ (own) |
| Admin / Director | ✓ (own) | — | ✓ (own) | ✓ (own) |
| Superuser | ✓ (own, RLS bypass) | — (recipient filter always enforced) | ✓ (own) | ✓ (own) |

- Every read MUST enforce `recipient == request.user` AND institution RLS; cross-user access returns 404 (RLS hides the row).

## Acceptance Criteria

- [ ] All RN-1..RN-4 scenarios pass under pytest (receiver, resolver, API tests).
- [ ] Exactly one `Notification` row per recipient per triggering event (no duplicates on resubmit cycles).
- [ ] `dispatch_notification` writes a `NotificationLog` row per enabled email recipient with `status=sent` (stub).
- [ ] `GET /api/notifications/` returns only `recipient == request.user` rows; RLS verified in `test_rls.py`.
- [ ] Mark-read endpoints are idempotent; preferences PATCH persists.
- [ ] Coverage on `apps.notifications` ≥ 80% (config floor).

## Non-Functional Requirements

- **Volume**: Receiver work MUST stay <50 ms per event (single INSERT, no I/O). Per event, 1–2 notification rows max (RN-3).
- **Retention**: Read notifications SHOULD be purged after 90 days and unread after 365 days by a scheduled Celery task; days configurable via settings. `NotificationLog` retained 12 months.
- **Retry**: `dispatch_notification` MUST retry up to 3 times with exponential backoff (countdown 60×2^n); failed attempts persist `last_error` and increment `attempt_count`.
- **Tenancy**: Notification tables MUST carry `tenant_isolation` + `superadmin_bypass` RLS policies; `TENANT_REQUIRED_PREFIXES` MUST include `notifications`.
- **Testing**: Strict TDD; coverage ≥80%.