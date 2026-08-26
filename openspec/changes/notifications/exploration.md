# Exploration: Notifications Module (Módulo de Notificaciones — transversal)

## Current State

SIGPI has **zero notification infrastructure**. There is no `apps/notifications`, no
`Notification` model, no email backend configuration, no SMTP settings, no Celery
notification task, and no frontend notifications page. The SPEC (§10, §12) lists
`notifications/` as a suggested app and `Notification` as an entity, but nothing
implements them.

What DOES exist is the event fabric a notifications module can plug into:

1. **Domain signals (the established hybrid pattern)** — cross-module-integration
   deliberately chose "Django signals for event notifications" and explicitly deferred
   delivery: `call_state_changed` "Future: notify linked projects (no receiver in MVP)";
   project_workflow proposal: "Notification delivery (email/in-app) — deferred to
   `notifications` module".
   - `project_state_changed` — emitted in `ProjectService._log_transition()`
     (`backend/apps/projects/services.py`), payload: `project, from_state, to_state,
     triggered_by`. Currently consumed ONLY by project_workflow (creates/resets/cancels
     `WorkflowInstance`). Every FSM transition also writes `ProjectStateLog` + emits
     `AuditEvent(PROJECT_STATE_CHANGE)`.
   - `call_state_changed` — emitted in `CallService._log_transition()`
     (`backend/apps/calls/services.py` + `signals.py`), payload: `call, from_state,
     to_state, triggered_by`. **No receiver in MVP.**
   - `workflow_completed` — emitted in `WorkflowService.complete_workflow()`
     (`backend/apps/project_workflow/signals.py`), payload: `project_id, instance_id,
     triggered_by`.
   - Progress has **NO signal** — `ProgressService._log_transition()` only writes
     `ProgressStateLog` + `AuditEvent(PROGRESS_STATE_CHANGE)`. A notifications receiver
     needs a new `progress_state_changed` signal (same pattern) or a receiver on
     `AuditEvent`.
   - Documents: `SignatureService.sign()` emits `AuditEvent(DOCUMENT_SIGNED)` directly
     via `AuditEventEmitter` — no Django signal.
   - Budgets: `BudgetService.add_execution()` enforces RN-020; over-execution without
     `authorized_by`/`authorized_at` raises `ValidationError` — no event for the
     "authorization required" case.

2. **Audit module (just built, archived 2026-08-25)** — `AuditEvent` + `AuditEventEmitter`
   are the canonical traceability store. `apps/audit/signals.py` adds generic CRUD
   capture (post_save/post_delete on Project, ProgressReport, Researcher, Budget,
   Document) gated on request audit context. Audit events carry `entity_type`,
   `entity_id`, `project_id`, `institution_id`, `details`. **Audit is a write-side
   event stream the notifications module could observe, but it is designed for
   traceability, not routing** — semantic domain signals are the better trigger source.

3. **Celery** — broker/backend on Redis (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`),
   `app.autodiscover_tasks()`, beat schedule in `backend/config/celery.py`. Only one
   task exists: `sync_keycloak_roles` (every 5 min). A `dispatch_notification` task is
   the natural extension point.

4. **Recipient resolution** — no helper exists; the pieces do:
   - `User` (`accounts/models.py`): `email` unique + required. Delivery address ready.
   - `Researcher` (`researchers/models.py`): `primary_email`, optional OneToOne `user`.
   - Roles: 7 fixed with `level` (1=Superadmin … 7=Auditor) via `InstitutionMembership`.
     Director = level ≤ 3 (`IsCenterDirector`), Institution Admin = level ≤ 2
     (`IsInstitutionAdmin`), center scoping via `membership.centers`
     (`IsCenterDirector.has_object_permission`).
   - "Notify the director" ⇒ users with an active `InstitutionMembership` at
     `role.level <= 3` for the project's institution (center-scoped via
     `membership.centers` where the SPEC implies center scope).
   - "Notify the researcher" ⇒ `ProgressReport.created_by` (user) or
     `Project.principal_investigator.researcher.user` / `primary_email`.

5. **SPEC triggers** (SPEC_sigpi.md §13–§16):
   - HU-001 / Gherkin: project sent to review → **director of center notified**.
   - HU-003: progress observed → **researcher notified**.
   - HU-005: budget line overrun → **authorization requested / restriction shown**
     (notification to admin is the natural reading; SPEC says "solicita autorización").
   - §13.5 / CA-008: document signed → parties notified (implied; SPEC records
     signer/date/hash/version but does not name notification recipients).
   - Call opened → researchers notified: **NOT in SPEC** — only the cross-module
     exploration's "future" note (notify linked projects on close/archive).

## Gaps

| Gap | Detail |
|-----|--------|
| No app/models | No `apps/notifications`; no `Notification`/`NotificationTemplate`/`NotificationLog`/`UserPreference` models (SPEC §12 lists `Notification`). |
| No channels | Zero email infrastructure (`EMAIL_BACKEND`/SMTP absent everywhere; Keycloak realm has empty `smtpServer: {}`). No in-app read API. No frontend page (`frontend/app/` has no notifications route). |
| No dispatch task | Celery has no notification task; async delivery path unbuilt. |
| Missing triggers | Progress emits no signal; document signing emits no signal; budget overrun emits no event. |
| No recipient resolver | No helper maps event → recipients by role level / center / project membership. |
| No tenant surface | New tables must follow RLS + `TENANT_REQUIRED_PREFIXES` pattern (as audit did) — not yet defined. |
| No delivery semantics | No read/unread state, no preferences, no retry/backoff, no audit link (notification→AuditEvent). |

## Approaches

1. **Standalone `apps/notifications` + signal receivers (recommended)** — new app with
   `Notification` (in-app), `NotificationTemplate`, `NotificationLog` (delivery state),
   `UserPreference` (channel opt-out). Receivers subscribe to existing domain signals
   (`project_state_changed`, `call_state_changed`, `workflow_completed`), new signals
   added where missing (`progress_state_changed` in progress, `document_signed` in
   documents), plus a budget-overrun event. Creation is synchronous (same
   transaction); delivery is a Celery task (email stub/log-only in MVP). Read-only
   ViewSet + RLS, mirroring the audit module.
   - Pros: matches the established hybrid pattern; decoupled (emitting modules stay
     untouched except new signal defs); testable; tenant-safe by design.
   - Cons: new signal defs needed in progress/documents/budgets; must handle
     transaction-atomicity of receivers (signals fire inside `transaction.atomic` in
     services).
   - Effort: High.

2. **Audit-event-driven** — receiver on `AuditEvent` (post_save) derives notifications
   from audit events.
   - Pros: single event source; no changes to emitting modules at all.
   - Cons: audit is a traceability stream, not a routing stream; every CRUD event would
     need filtering; risk of noise and double-notify (generic audit signals + semantic
     emitters both write AuditEvent); couples two concerns.
   - Effort: Medium.

3. **Explicit `NotificationService.notify()` calls in every module's service layer** —
   Pros: explicit and precise. Cons: violates the established signal convention,
   touches 5+ modules, easy to miss paths, tight coupling.
   - Effort: Medium.

## Recommendation

**Approach 1**: standalone `apps/notifications` app consuming domain signals, with
in-app notifications + a Celery-dispatched email channel (log-only stub until real SMTP
exists — matching project_workflow's "log-only stub" deferral language). Add
`progress_state_changed` and `document_signed` signals where they don't exist and a
budget overrun event in `BudgetService.add_execution`. Follow the audit module's
playbook for the read API: read-only ViewSet, `IsSameInstitution`-style scoping,
denormalized `institution_id`, RLS migration, and `/api/notifications/` in
`TENANT_REQUIRED_PREFIXES`. NotificationLog records delivery attempts so notifications
remain observable without email infrastructure. MVP scope: in-app + log-only email;
real SMTP deferred.

## Affected Areas

- `backend/apps/notifications/` (new) — models, receivers, services, Celery task,
  serializers, viewsets, filters, permissions, urls, tests, migrations.
- `backend/apps/progress/` — add `progress_state_changed` signal (emit in
  `_log_transition`).
- `backend/apps/documents/` — add `document_signed` signal (emit in
  `SignatureService.sign`).
- `backend/apps/budgets/services.py` — emit overrun/authorization-required event.
- `backend/config/settings/base.py` — register app; email settings (when channel live).
- `backend/config/celery.py` — notification dispatch task (+ optional beat sweep).
- `backend/config/urls.py`, `config/middleware/tenant.py` — `/api/notifications/`
  tenant-required prefix.
- RLS migrations for notification tables (PostgreSQL-only, mirror audit `0009`).
- Frontend (deferred) — notifications page/bell.
- `SPEC_sigpi.md` §10/§12 — `notifications/` app and `Notification` entity.

## Risks

- **Transaction atomicity**: receivers fire inside `transaction.atomic()` in services;
  notification rows and outbound delivery must not half-commit. Use post-commit
  dispatch or make the Celery task the only side effect.
- **Double notification**: generic audit CRUD signals + semantic signals can both fire
  for one transition; the module must subscribe to ONE source per trigger.
- **Noise/volume**: every FSM transition could notify; templates + UserPreference gating
  are required, not optional.
- **Tenant isolation breach**: notification tables/API must get RLS + tenant-required
  prefix; forgetting this is a cross-institution leak.
- **Recipient resolution complexity**: "director of center" is role-level + center
  membership, not a FK; resolver needs tests for multi-institution and
  center-scoped cases.
- **Circular imports**: keep signal definitions in the emitting module (established
  convention); notifications must only import signals, never be imported by them.

## Open Questions

1. **Channels for MVP**: in-app only, email only, or both? Email infra is absent; SPEC
   never names a channel.
2. **Call opened → researchers**: not in SPEC. Notify all institution researchers, only
   researchers linked to the call's projects, or defer entirely?
3. **Document signed → "parties"**: who? Signer, PI, center director, all project
   members?
4. **Budget threshold**: overrun-without-authorization is currently a 400
   (`ValidationError`). Notify institution admin on that path, per line, at a
   percentage threshold?
5. **Email delivery**: real SMTP in this change, or log-only stub (project_workflow
   precedent)?
6. **Frontend scope**: backend-only this change, or include the in-app UI page?

## Ready for Proposal

**Yes.** Scope is well-bounded by the SPEC's two explicit triggers (director on submit,
researcher on observe) plus the three deferred signals. Before the proposal, the
orchestrator should confirm with the user: (a) MVP channels (in-app vs email vs both),
(b) call-opened scope, and (c) whether real SMTP is in scope or a log-only stub.