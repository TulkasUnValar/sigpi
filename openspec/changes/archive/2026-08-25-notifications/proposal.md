# Proposal: Notifications Module (transversal)

## Intent

SIGPI has zero notification infrastructure. SPEC triggers require actors to be informed on key events: HU-001 (project sent to review → center director notified), HU-003 (progress observed → researcher notified), HU-005 (budget overrun → authorization requested), §13.5 (document signed → parties notified). This change delivers a tenant-safe `notifications` module so actors get in-app notifications without coupling emitting modules to delivery.

## Scope

### In Scope
- New backend app `apps/notifications` (models, receivers, resolver, serializers, viewsets, permissions, Celery task, migrations, tests)
- 4 SPEC triggers: project→review→director; progress observed→researcher; budget line overrun→institution admin; document signed→signer + project PI
- In-app `Notification` rows + read-only tenant-scoped API (`/api/notifications/`)
- Email log-only stub (no SMTP) via Celery `dispatch_notification`; `NotificationLog` records attempts
- `UserPreference` model (channel opt-out, no UI)
- RLS + `TENANT_REQUIRED_PREFIXES` for notification tables

### Out of Scope
- Call opened/closed → researchers (deferred, not in SPEC)
- Real SMTP/email rendering (future activation)
- Frontend UI (bell/page, read/unread UX)
- Non-SPEC triggers (`workflow_completed`)

## Capabilities

### New Capabilities
- `notifications`: Notification/NotificationTemplate/NotificationLog/UserPreference models; signal receivers; recipient resolution (role-level + center scope); Celery dispatch; read-only API; RLS

### Modified Capabilities
- `progress`: emit `progress_state_changed` in `_log_transition`
- `documents`: emit `document_signed` in `SignatureService.sign`
- `budgets`: emit overrun event when `add_execution` raises `ValidationError` (RN-020)

## Approach

Standalone `apps/notifications` consuming domain signals (signal-driven, not audit-event-driven — cleaner routing, less noise; audit stays a traceability stream). Creation synchronous inside the sender's transaction; delivery async via Celery. Signals defined in emitting modules; notifications only imports them (no circular imports). Mirror the audit module playbook for read API + RLS.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/notifications/` | New | Module: models, receivers, Celery task, API |
| `backend/apps/progress/signals.py` | Modified | New `progress_state_changed` signal |
| `backend/apps/documents/signals.py` | Modified | New `document_signed` signal |
| `backend/apps/budgets/services.py` | Modified | Overrun event on ValidationError path |
| `backend/config/settings/base.py` | Modified | Register app |
| `backend/config/celery.py` | Modified | `dispatch_notification` task |
| `backend/config/urls.py`, `config/middleware/tenant.py` | Modified | Tenant-required prefix |
| Migrations (notifications + RLS) | New | PostgreSQL RLS mirroring audit |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Transaction atomicity (receivers fire inside `atomic()`) | Med | Only side effect = Notification row + task enqueue; no I/O in receiver |
| Double notification (audit CRUD + semantic signals) | Med | One source per trigger; subscribe to semantic signals only |
| Noise/volume | High | Templates + `UserPreference` gating, not optional |
| Tenant isolation breach | Low | RLS migration + tenant prefix mandatory (audit playbook) |
| Recipient resolution complexity | Med | Dedicated resolver + tests for multi-institution/center-scoped cases |

## Rollback Plan

- Remove `apps.notifications` from `INSTALLED_APPS`, unregister receivers, remove URL/tenant-prefix entries
- Reverse migrations (drop notification tables)
- Remove added signal emissions in progress/documents/budgets (additive, reversible)
- Email stub has no external side effects

## Dependencies

- Existing domain signals (`project_state_changed`) and services; Celery + Redis (already configured); audit module (optional notification→AuditEvent link)

## Success Criteria

- [ ] Notification rows created for all 4 SPEC triggers with correct recipients
- [ ] `dispatch_notification` task writes `NotificationLog` email entries (log-only)
- [ ] Read API returns only caller-institution rows; RLS enforced
- [ ] Backend tests pass; coverage ≥ 80%