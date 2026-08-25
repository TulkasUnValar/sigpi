# Tasks: Notifications Module (SIGPI HU-001, HU-003, HU-005, §13.5)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1200–1400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 (stacked to main) |
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
| 1 | Scaffold + 4 models + migration + RLS + seed | PR 1 | `cd backend; python -m pytest apps/notifications/tests/test_models.py apps/notifications/tests/test_rls.py` | `python manage.py migrate; python manage.py makemigrations --check --dry-run` | Reverse 0002/0001 + drop `apps.notifications` from INSTALLED_APPS; no signals/API shipped |
| 2 | Signals + emissions + resolver + receivers | PR 2 | `cd backend; python -m pytest apps/notifications/tests/test_signals.py apps/notifications/tests/test_receivers.py` | Django shell: submit/observe/sign/overrun; assert `Notification` rows | Revert signal emissions + unregister receivers; tables intact |
| 3 | Celery dispatch task + retention beat | PR 3 | `cd backend; python -m pytest apps/notifications/tests/test_tasks.py` | `CELERY_TASK_ALWAYS_EAGER=1 python manage.py shell` → run task, inspect `NotificationLog` | Remove task + beat entry; receiver on_commit unaffected |
| 4 | API: serializers, filters, permissions, ViewSets, URLs, config | PR 4 | `cd backend; python -m pytest apps/notifications/tests/test_api.py apps/notifications/tests/test_permissions.py` | `GET /api/notifications/` as two users; assert cross-user 404 | Revert API files + route + tenant prefix; writes unaffected |
| 5 | Integration suite + coverage gate | PR 5 | `cd backend; python -m pytest apps/notifications/ --cov=apps.notifications --cov-fail-under=80` | Full `python -m pytest` + coverage report | Tests only — revert without production impact |

## Phase 1: Foundation — Scaffold, Data Model, Migration

- [x] 1.1 RED `apps/notifications/tests/test_models.py`: fields, indexes, unique `(recipient,event_type,entity_type,entity_id)`, no GenericForeignKey
- [x] 1.2 RED `apps/notifications/tests/test_rls.py` (PostgreSQL-skip): `tenant_isolation` + `superadmin_bypass` on all four tables
- [x] 1.3 Create `apps/notifications/{__init__,apps,admin,models}.py` per design contracts (denormalized `institution`, `(recipient,is_read,-created_at)` index)
- [x] 1.4 Register `apps.notifications` in `LOCAL_APPS` (`backend/config/settings/base.py`)
- [x] 1.5 Create `migrations/0001_initial.py`: four tables + indexes + unique constraint; data migration seeds 4 templates
- [x] 1.6 Create `migrations/0002_rls.py` (PostgreSQL-only): ENABLE RLS, tenant_isolation, superadmin_bypass; reverse drops policies

## Phase 2: Signal & Receiver Layer

- [ ] 2.1 RED `apps/notifications/tests/test_signals.py` + `test_receivers.py`: filters, recipient cases, dedup, inactive-template skip, no-I/O, missing-recipient warning
- [ ] 2.2 Create `apps/{progress,documents,budgets}/signals.py` with `progress_state_changed`, `document_signed`, `budget_overrun_attempted`
- [ ] 2.3 Emit: progress `_log_transition`; `SignatureService.sign` post-atomic-write; unauthorized overrun branch of `BudgetService.add_execution`
- [ ] 2.4 Create `apps/notifications/resolver.py`: center director, advance author, signer+PI (no-project → signer only), institution admin (Admin 2/Director 3)
- [ ] 2.5 Create `apps/notifications/receivers.py`; wire in `apps.py ready()` with `dispatch_uid`; `get_or_create` + `transaction.on_commit(dispatch_notification.delay)`

## Phase 3: Celery Dispatch

- [ ] 3.1 RED `apps/notifications/tests/test_tasks.py`: preference skip, log status=sent, retry 3× (countdown 60×2^n), `last_error`/`attempt_count`
- [ ] 3.2 Create `apps/notifications/tasks.py`: `dispatch_notification(notification_id)` — log-only, no SMTP
- [ ] 3.3 Add retention beat schedule (read 90d, unread 365d, logs 12m) to `backend/config/celery.py`

## Phase 4: API Layer

- [ ] 4.1 RED `apps/notifications/tests/test_api.py` + `test_permissions.py`: list/detail/unread_count/read/read_all/preferences, filters, pagination 100, idempotency, cross-user 404
- [ ] 4.2 Create `apps/notifications/serializers.py`: `NotificationSerializer`, `UserPreferenceSerializer`
- [ ] 4.3 Create `apps/notifications/filters.py` (`is_read`, `event_type`) + `permissions.py` (`IsNotificationOwner|IsAdmin`)
- [ ] 4.4 Create `apps/notifications/views.py`: `NotificationViewSet` (list/detail/read/read_all/unread_count/preferences) + `UserPreferenceViewSet`; `recipient=request.user` incl. superuser
- [ ] 4.5 Create `apps/notifications/urls.py`; wire `/api/notifications/` in `config/urls.py`; add prefix to `TENANT_REQUIRED_PREFIXES` (`config/middleware/tenant.py`)

## Phase 5: Integration & Coverage

- [ ] 5.1 `apps/notifications/tests/test_integration.py`: real service boundaries — submit, observe, sign, overrun; rollback/on_commit; no duplicates on resubmit
- [ ] 5.2 Run full backend suite; enforce ≥80% coverage on `apps.notifications`