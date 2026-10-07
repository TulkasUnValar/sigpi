# Notification retention cleanup (`cleanup_old_notifications`)

- Feature: `notification-retention-cleanup`
- Branch: `fix/notification-retention-cleanup` (from `fix/runtime-connectivity`, base `main` @ `119e8ec`).
- TDD: ON — `openspec/config.yaml` `strict_tdd: true`, `red_green_refactor: true`. Runner: `pytest -c backend/pyproject.toml` from the **repo root** (`backend/.venv-312`). Default engine is in-memory SQLite; RLS-only tests require PostgreSQL and self-skip otherwise.
- Delivery: `single-pr` — one small, self-contained backend change.
- Artifact store: this document; Engram mirror `odd/notification-retention-cleanup/tasks`.

## Objective

Ship the real body of the `cleanup_old_notifications` Celery task so the
retention policy that `config/celery.py` already schedules (daily 03:00
America/Bogota) actually runs, instead of the worker logging it as an
unregistered task.

## Problem (verified)

`backend/config/celery.py:35-38` schedules `cleanup_old_notifications`, but no
task with that name exists anywhere in the codebase. The worker logs it as
unregistered every night at 03:00. The retention requirement is documented but
unimplemented:

- `openspec/specs/notifications/spec.md:150` — "Read notifications SHOULD be
  purged after 90 days and unread after 365 days by a scheduled Celery task;
  days configurable via settings. `NotificationLog` retained 12 months."

## Scope

In scope:
- Settings knobs in `backend/config/settings/base.py` for the three thresholds
  (defaults 90 / 365 / 365 days), env-overridable, per "configurable via
  settings".
- `cleanup_old_notifications` `@shared_task` in
  `backend/apps/notifications/tasks.py`.
- Tests first (strict TDD) in
  `backend/apps/notifications/tests/test_tasks.py`.
- An RLS enforcement test in
  `backend/apps/notifications/tests/test_tasks_rls.py` proving the task purges
  across tenants under the least-privilege role.
- Update the stale "ships in a later phase" comment in `config/celery.py`.

Out of scope:
- Any model or migration change.
- Soft-delete (the model has none; the spec says "purged" → hard `DELETE`).
- Touching `dispatch_notification` or the beat entry itself.
- A broader retention settings module / admin surface.

## Design decisions

1. **Age reference per row state.** A read notification is purged when
   `read_at < now - READ_DAYS`; an unread one when `created_at < now -
   UNREAD_DAYS`; a `NotificationLog` when `created_at < now - LOG_DAYS`.
   Rationale: the spec pairs the two thresholds on read state and the model
   carries `read_at` precisely for this; measuring "read" age from `created_at`
   would purge a notification read yesterday just because it is old. Read rows
   have `read_at` set; unread rows do not.
2. **Cross-tenant system task → RLS bypass.** The task is all-tenant, so it has
   no institution to establish a tenant context with. `notifications_notification`
   and `notifications_notificationlog` have RLS enabled
   (`apps/notifications/migrations/0002_rls.py`); under `sigpi_app`
   (NOSUPERUSER, NOBYPASSRLS) a DELETE with no GUC is default-deny and would
   silently affect **zero** rows. The task must activate the existing bypass
   GUC: `with tenant_context(connection, None, bypass=True):`. This is the
   first production use of `bypass=True`; the policy `superadmin_bypass` exists
   exactly for this. Under SQLite `tenant_context` is a no-op.
3. **Hard delete.** `QuerySet.delete()` (no soft-delete field exists). Cascade
   removes a notification's `NotificationLog` rows; the log purge handles logs
   whose notification is still within retention.
4. **Return a counts dict** (`{"read_deleted", "unread_deleted", "logs_deleted"}`)
   so the outcome is observable in Celery results and testable.

## Tasks

### T1 — RED: failing tests first
- [ ] In `test_tasks.py`, add `TestCleanupOldNotifications` covering: purge of
      a read notification past the window; keep of a recent read one; purge of
      an unread one past the window; keep of a recent unread one; purge of an
      old `NotificationLog`; keep of a recent one; each threshold honored when
      overridden via `settings`; the returned counts dict.
- [ ] Run the suite; confirm the new tests FAIL for the right reason (task
      missing), not for an unrelated error.

### T2 — GREEN: settings + task
- [ ] `backend/config/settings/base.py`: add
      `NOTIFICATIONS_RETENTION_READ_DAYS`, `NOTIFICATIONS_RETENTION_UNREAD_DAYS`,
      `NOTIFICATIONS_RETENTION_LOG_DAYS` (defaults 90/365/365), env-overridable
      following the existing `os.environ.get(...)` style.
- [ ] `backend/apps/notifications/tasks.py`: add
      `@shared_task(name="cleanup_old_notifications")` implementing the three
      purges inside `tenant_context(connection, None, bypass=True)`.
- [ ] `backend/config/celery.py`: replace the "ships in a later phase" comment
      with the implemented status.

### T3 — RLS enforcement test
- [ ] In `test_tasks_rls.py` (PostgreSQL-only, `postgres_app_role`): seed rows
      for two institutions, run the task, assert both tenants' expired rows are
      gone while in-window rows survive — proving the bypass, since a
      no-context DELETE would remove nothing.

### T4 — verification
- [ ] Notification task tests green on SQLite; notifications app suite green.
- [ ] Full PostgreSQL suite green (bypass path exercised under `sigpi_app`).
- [ ] `ruff check` and `ruff format --check` clean.

### T5 — work-unit commit
- [ ] One conventional commit, no AI attribution, executed from inside WSL
      (the `wsl-guard` pre-commit hook rejects Windows commits).

## Acceptance criteria

1. `cleanup_old_notifications` exists as a registered task with the beat name
   `cleanup_old_notifications`, and the existing
   `TestRetentionBeatSchedule` stays green.
2. Read rows are purged only after `READ_DAYS` since `read_at`; unread only
   after `UNREAD_DAYS` since `created_at`; logs only after `LOG_DAYS`.
3. Thresholds are configurable via settings; changing a setting changes the
   purge boundary.
4. The purge works across all tenants under the least-privilege role (RLS
   bypass), proven by the PG-only test.
5. No production model/migration change.

## Route declaration

| Task | Route | Trigger evidence |
|---|---|---|
| T1–T2 | delegated writer | 2+ non-trivial files (settings, task, tests, celery comment) |
| T3 | delegated (same writer) | RLS test lives in the same change |
| T4 | parent spot check + writer self-verify | per-action checks |
| T5 | delegated writer | mechanical commit |

## Verification

```
cd /home/tulkasubuntu/01-sigpi   # repo ROOT
backend/.venv-312/bin/python -m pytest -c backend/pyproject.toml \
  backend/apps/notifications/tests/test_tasks.py -v
```

Full PG suite (throwaway cluster on /tmp:5433) and `ruff check backend` /
`ruff format --check backend` for closure.

## Progress

**DONE — implemented, verified on SQLite and independently verified on real
PostgreSQL (RLS bypass proven non-vacuous).** Branch `fix/notification-retention-cleanup`,
commit `06afd48` (`feat(notifications): implement cleanup_old_notifications
retention task`), 6 files, +428 / −14.

- T1 RED observed: `ImportError: cannot import name 'cleanup_old_notifications'
  from 'apps.notifications.tasks'`.
- T2/T3 implemented: retention settings, `cleanup_old_notifications` task, RLS
  test, updated `config/celery.py` status comment.
- T4 (writer, SQLite): `test_tasks.py` — 24 passed; notifications app suite —
  136 passed, 10 skipped (the RLS tests self-skip on SQLite via
  `postgres_app_role`); `ruff check backend` clean; `ruff format --check` clean
  for the touched files.
- T4 (independent verifier, real PostgreSQL): notifications suite — **146
  passed, 0 skipped**, including
  `TestCleanupOldNotificationsTenantBypass::test_purges_expired_rows_of_both_tenants`
  (ran, not skipped). Adversarial mutation proof: flipping `bypass=True` →
  `bypass=False` makes that test fail with
  `{'read_deleted': 0, 'unread_deleted': 0, 'logs_deleted': 0}` — the
  least-privilege DELETE affects zero rows — then restored; `git status` clean
  and `HEAD` unchanged at `06afd48`. The bypass is load-bearing and the test is
  non-vacuous.
- T5: single work-unit commit; no AI attribution.
- Environment note: host `127.0.0.1:5432` is served by the native WSL PG 18, so
  the Docker `sigpi-db` was reached as host `db` inside the compose network (and
  cross-checked against a PG 18 cluster on 5433). No product defect either way.
- Findings: no CRITICAL/WARNING. Open notes (not defects): `delete()[0]` counts
  cascaded rows; the three deletes are not wrapped in `transaction.atomic`; log
  retention is 365 days for the spec's "12 months"; ruff 0.16.7 in the venv vs
  0.16.9 pinned.
- Delivery (push / PR base) is the user's decision; the branch currently stacks
  on the local-only `fix/runtime-connectivity`.
