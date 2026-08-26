# Design: Notifications Module

## Technical Approach

Add a standalone `apps.notifications` Django app that consumes semantic domain signals, resolves recipients, and writes in-app rows synchronously in the sender transaction. Receivers perform only ORM work; email delivery is scheduled with `transaction.on_commit` and handled by Celery. This preserves domain-module independence and avoids using audit events as a routing bus.

## Architecture Decisions

| Decision | Choice | Alternatives considered / rationale |
|---|---|---|
| Event boundary | Signals remain in emitting modules; notifications imports them in `apps.notifications.apps.ready()` with `dispatch_uid`. | Audit-event receivers add noise and couple presentation to traceability; direct imports create circular dependencies. |
| Delivery | In-app insert now; email task after commit, log-only. | SMTP in a receiver could roll back business work and violates the <50 ms/no-I/O boundary. |
| Recipient lookup | `resolver.py` queries active `InstitutionMembership` and center membership, returning distinct users. | Role checks in each receiver duplicate tenancy rules. Existing role levels are authoritative: Admin 2, Director 3. |
| Idempotency | Unique `(recipient, event_type, entity_type, entity_id)` plus `get_or_create`; entity identifiers are stored explicitly, never a `GenericForeignKey`. | Application-only deduplication races under retries. |

## Data Flow

`ProjectService / ProgressService / SignatureService / BudgetService` → semantic signal → `receivers.py` → resolver/template render → `Notification` insert → `on_commit(dispatch_notification.delay)` → `NotificationLog`.

Signals: add `progress_state_changed` in `apps/progress/signals.py`, `document_signed` in `apps/documents/signals.py`, and `budget_overrun_attempted` in `apps/budgets/signals.py`; emit from progress `_log_transition`, successful `SignatureService.sign` after its atomic write, and the unauthorized overrun branch of `BudgetService.add_execution`, respectively. Keep existing `project_state_changed` in `apps.project_workflow.signals.py`; notifications filters `to_state="enviado"`.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/notifications/{apps,models,signals,receivers,resolver,serializers,views,permissions,filters,tasks,urls}.py` | Create | App wiring, persistence, signal handlers, recipient rules, API, and Celery task. |
| `backend/apps/notifications/migrations/` | Create | Four tables, seed four templates, indexes, PostgreSQL RLS. |
| `backend/apps/{progress,documents,budgets}/signals.py` | Create | New semantic signals; services emit them at the specified success/failure boundaries. |
| `backend/config/settings/base.py`, `config/urls.py`, `config/middleware/tenant.py` | Modify | Register app, `/api/notifications/`, and tenant-required prefix. |
| `backend/config/celery.py` | Modify | Add notification retention schedule; autodiscovery finds the dispatch task. |
| `backend/apps/notifications/tests/` | Create | Unit, API, RLS, and integration coverage. |

## Interfaces / Contracts

`Notification`: UUID `id`; FK `institution` (denormalized, indexed), FK `recipient` (`User`, indexed), `event_type` (max 50, indexed), FK `template`, `title`, `body`, JSON `context`, nullable `entity_type` (50) and `entity_id` UUID, `is_read` default false, nullable `read_at`, `created_at`. Index `(recipient,is_read,-created_at)` and unique event tuple above.

`NotificationTemplate`: UUID `id`, unique `code`, `title_template`, `body_template`, `is_active` default true. `NotificationLog`: UUID `id`, nullable notification FK, email `channel`, recipient email, `status` (`pending|sent|failed`), `attempt_count`, nullable `last_error`, timestamps. `UserPreference`: UUID `id`, unique user FK, email channel, enabled default true, timestamps.

RLS enables `tenant_isolation` and `superadmin_bypass` on all four tables. `Notification` is keyed directly by its denormalized `institution_id`; `NotificationLog` inherits scope through its notification, `UserPreference` is scoped through the caller's active membership (preferences are user-global), and `NotificationTemplate` has an explicit global policy because templates are catalog data. Add `notifications` to `TENANT_REQUIRED_PREFIXES`. Querysets additionally enforce `recipient=request.user`, including for superusers.

Receivers filter event state, resolve active recipients, skip inactive templates, use `get_or_create`, and register one `on_commit` task per created row. Missing recipients log a warning and do not fail the sender transaction. `dispatch_notification(notification_id)` checks email preference, creates/updates a log-only email record, marks enabled deliveries `sent`, and retries failures up to three times with exponential backoff (60×2^n); it never sends SMTP.

`NotificationViewSet` exposes GET list/detail, `unread_count`, `read`, `read_all`, and `preferences` GET/PATCH. Pagination is 100/page; filters are `is_read` and `event_type`. `IsAuthenticated` plus own-recipient queryset makes cross-user access 404; writes only mutate read state or the caller’s preference.

## Testing Strategy

Unit tests cover each signal payload/filter, resolver role/center/institution cases, inactive templates, deduplication, no-I/O receivers, and task retry/preference behavior. API tests cover pagination, filters, unread count, idempotent read operations, preference PATCH, and cross-user denial. Integration tests exercise real project/progress/document/budget service boundaries and transaction rollback/on-commit behavior. PostgreSQL tests verify both RLS policies; SQLite tests follow the repository’s migration no-op convention. Maintain ≥80% app coverage.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable documentation | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

## Migration / Rollout

Add the new app and tables, seed templates, and make only additive signal emissions. Deploy migrations before enabling receivers; rollback removes routes/receivers and reverses notification migrations. Configure retention (read 90 days, unread 365 days, logs 12 months) without SMTP activation.

## Open Questions

- None blocking implementation.
