# RLS enforcement completion

- **Feature**: `rls-enforcement-completion`
- **Branch**: `fix/rls-enforcement-completion` (base `main` @ `3ed3383`)
- **Created**: 2026-09-29
- **TDD**: ON — source `openspec/config.yaml` (`strict_tdd: true`, floor 80%). Runner: `pytest -c backend/pyproject.toml` from the repo root, venv `backend/.venv-wsl`.

## Objective

Close everything that stands between the current state and turning RLS on for real, then switch the runtime to the least-privilege role and verify it in CI.

## Order matters

The fixes come **before** the role switch, because the switch is what turns enforcement on and each fix is what stops a real path from breaking. Switching first would break a failed login, two Celery tasks and report template isolation at once.

## Problem — what breaks once enforcement is real

Reconnaissance recorded under Engram topic `backend/rls-runtime-blast-radius` established:

1. **`reports_reporttemplate` has no RLS at all.** It has an `institution` FK (`backend/apps/reports/models.py:202`) and `db_table = "reports_reporttemplate"` (:212), but it was created in `reports/0003`, after `reports/0002` applied the app's policies, so no migration ever covered it. A multi-tenant isolation gap.
2. **Audit inserts with no institution abort.** Every `AuditEvent` write goes through `AuditEventEmitter.emit` → `AuditEvent.objects.create` (`backend/apps/accounts/audit.py:188-200`). Failed login (`accounts/views.py:119,131`), logout without a session institution (`:248`) and OIDC login (`accounts/apps.py:23-29`) all emit with `institution_id = None`. Policies are `ALL` + `USING`, and PostgreSQL uses the `USING` expression as `WITH CHECK` for INSERT when none is declared — verified empirically. So a failed login would return a 500 instead of an auth error.
3. **Two Celery tasks read protected tables with no tenant context**, and both fail silently: `notifications/tasks.py:59-108` `dispatch_notification` (reads `notifications_notification`, writes `notifications_notificationlog`) logs "not found; skipping" and never sends mail; `search/tasks.py:43-67` `index_document` (reads `projects_project`, `researchers_researcher`, `products_researchproduct`, `calls_call`, `progress_progressreport`) gets `DoesNotExist` and stops updating Meilisearch.
   `accounts/tasks.py:97-157` `sync_keycloak_roles` needs **no** tenant context: it reads only unprotected tables, and its only problem was the audit INSERT, which fix 2 solves.
4. **An activation failure currently logs and continues.** That was the right shape while the runtime was a superuser; once enforcement is real it must reject the request.

## Scope

**In:** RLS for `reports_reporttemplate`; a per-command policy split for `accounts_auditevent`; tenant contexts for the two Celery tasks that need one; rejection on activation failure; `LOGIN` for `sigpi_app` and the runtime credential switch with CI verification.

**Out:** `WITH CHECK` review on the other 45 tables; filling the four stub `TestRLSEnforcement` classes; the Codecov token; CI's ruff scope.

## Authorized scope

User selected **"Policy por comando"** for the audit boundary and **"Switch + verificación en CI"** for the runtime switch on 2026-09-29, after choosing **"Mecanismo correcto, sin encender el rol"** for the preceding change.

## Decisions

- **Audit boundary: per-command policies, not a bypass window.** `SELECT` stays tenant-scoped so a row with no institution is never visible to a tenant; `INSERT` additionally accepts `institution_id IS NULL` so system events can be appended. System events become readable only through the superadmin bypass. Rejected: having the emitter write under `bypass_rls` (it reopens in the application process exactly the window this work is closing), and forbidding institution-less events (it would lose failed-login and logout traceability).
- **Runtime switch keeps migrations on the owner.** Settings prefer `POSTGRES_APP_USER` when it is defined; `migrate` and `pytest` keep using the owning role, because pytest-django creates the test database and runs migrations, which `sigpi_app` cannot do. A dedicated CI job then migrates as the owner and runs an end-to-end smoke with the application connected as `sigpi_app`, so the real role is verified on every PR instead of only being wired for docker.
- **Keep the `tenant_isolation` name for the audit `SELECT` policy.** `backend/apps/audit/tests/test_rls.py:132` pins `CREATE POLICY tenant_isolation ON {TABLE}` against the migration module text, and renaming would make that assertion describe something dead.

## Tasks

| ID | Task | Route | Status |
|----|------|-------|--------|
| W1 | RLS for `reports_reporttemplate`: new `reports/0004` migration with the standard `tenant_isolation` + `superadmin_bypass` pair using the hardened casts, plus a `reports/tests/test_rls.py` mirroring the other apps' text-level contracts | delegated writer | done — `eb86da2` |
| W2 | Per-command policies for `accounts_auditevent`: new `accounts/0011` migration splitting `tenant_isolation` into `FOR SELECT` and adding `FOR INSERT` with the `IS NULL` allowance, keeping `superadmin_bypass` on `FOR ALL` with `WITH CHECK`, plus tests for both behaviours | delegated writer | done — `45a85da` |
| W3 | Tenant context for `dispatch_notification` and `index_document`, passed in by their enqueuers, with a non-request helper in `config/tenant_context.py` | delegated writer | done — `fed9210` |
| W4 | Activation failure rejects the request | delegated writer | done — `f7de15f` |
| W5 | `LOGIN` for `sigpi_app`, `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD` in settings, docker-compose wiring, and the dedicated CI job that verifies the app role end to end | delegated writer | done — `2401f3a` |
| W6 | Full-project verification | per-action fresh worker | done — `verified_with_findings`, see below |

## Constraints

- Migrations are additive; do not edit an existing migration.
- New policies must use the hardened casts, or the repo-wide guard in `backend/tests/test_rls_policy_contract.py` fails: `NULLIF(current_setting('sigpi.institution_id', true), '')::uuid` and `NULLIF(current_setting('sigpi.bypass_rls', true), '')::bool = true`.
- Nothing may change production behaviour for the 45 already-covered tables.
- Artifacts in English.

## Acceptance criteria for W1 + W2

1. `reports_reporttemplate` ends with RLS enabled and both policies, and the repo-wide guard still passes.
2. On PostgreSQL as `sigpi_app`: an `AuditEvent` INSERT with `institution_id = NULL` **succeeds**; an INSERT with another institution's id **fails**; a tenant session **cannot SELECT** a NULL-institution row; a tenant session **can SELECT** its own rows.
3. UPDATE and DELETE on `accounts_auditevent` are denied for the app role (append-only), and nothing in the codebase updates or deletes audit rows — if something does, report it instead of breaking it.
4. The full suite stays green on PostgreSQL (baseline `2584 passed, 27 skipped, 0 failed`).
5. `reports_reporttemplate` isolation is asserted at policy-text level, consistent with every other app.

## Verification evidence

### Per task

- **W1 + W2.** PostgreSQL: `2614 passed, 27 skipped, 0 failed` after the two migrations, up from the `2584` baseline before this program. The four audit behaviours were observed on real PostgreSQL as `sigpi_app`: a NULL-institution insert succeeds, an insert claiming another institution fails with `new row violates row-level security policy`, a tenant cannot read the NULL row, and can read its own. UPDATE and DELETE affect zero rows, so the table is append-only for the application role. A mutation removing the `IS NULL` branch fails exactly the NULL-institution test and nothing else. Nothing in the codebase updates or deletes audit rows.
- **W3 + W4.** Both Celery tasks were proven on real PostgreSQL with their non-vacuity control: with the institution the task processes its row, and without a context the same read finds nothing — so the context is what makes it work, not the data. Every enqueue site was found and updated (one in `notifications/receivers.py`, five in `search/signals.py`). The fail-closed mutation proof restored log-and-continue and watched the new test fail.
- **W5.** Reproduced end to end on PostgreSQL 18: `migrate` as owner exits 0, the owner is **refused** by `verify_app_role_rls` with a message naming `rolsuper` and `rolbypassrls`, and as `sigpi_app` the check reports **0 rows with no context, 0 with another institution, 1 with its own**. With `POSTGRES_APP_USER` unset the suite is unchanged at `2614 passed, 27 skipped, 0 failed`. CI run `36630929660` then exercised the same path over real TCP and password auth: all three jobs green, including `Backend app-role RLS (least privilege)`.

### Full-project verification (W6)

`verified_with_findings`. Structural claims all held on a from-scratch PostgreSQL 18.6 cluster:

- **47 tables with RLS enabled, 0 with RLS but no policy, 0 institution-scoped tables without RLS**; 95 policies (47 `tenant_isolation` + 47 `superadmin_bypass` + 1 `tenant_insert`).
- `2614 passed, 27 skipped` on PostgreSQL (matching CI's own summary) and `2588 passed, 53 skipped` on SQLite; `makemigrations --check` clean; `migrate` from scratch idempotent; `check --deploy --fail-level ERROR` exit 0.
- The repo-wide guard passes and was mutation-proved to fail on an unguarded read, an unwrapped guarded read, the old `COALESCE` bypass form, and a multiline unsafe cast.
- Frontend: ESLint clean, `tsc --noEmit` zero errors, Jest `136 suites / 1030 tests` passing.
- No real credential is committed; no stray data directory; the CI job's log contains the literal app-role `OK` line, so it genuinely exercised the least-privilege connection rather than merely starting.

### Findings the verification raised, and what was done

- **Fixed here (introduced by W5):** `docker-compose.yml` set `POSTGRES_APP_USER` unconditionally on the `backend` service, so *every* `manage.py` command in that container — including `migrate` — would connect as the role that has no DDL rights. The switch is now a documented per-command opt-in, and `.env.example` no longer claims compose sets it automatically. Verified: the compose YAML still parses and `POSTGRES_APP_*` no longer appears in the default service environment.
- **The headline caveat, not fixed here:** 25 `TestRLSEnforcement` tests are skipped **on PostgreSQL** with skip reasons that are false there, and every method body is `pass`. So `budgets`, `calls`, `documents`, `projects` and app-level `accounts` have **no** row-isolation assertion at all. This is pre-existing and was recorded as out of scope, but the green suite hides it. `products` and `progress` have no `test_rls.py` whatsoever.
- **Not fixed here:** `audit/tests/test_rls.py::TestRLSEnforcement::test_superadmin_bypass_sees_all_rows` asserts `count >= 0`, which cannot fail; a sibling test passes for absence of data rather than for RLS.
- **Not fixed here:** RLS is enabled but not `FORCE`d on any table. That is correct only while the runtime is the non-owner `sigpi_app`; any connection as the owner silently disables every policy.
- **Not fixed here:** the README, `SPEC_sigpi.md` and `docker-compose.yml` claim Django 5.1 while `backend/pyproject.toml` requires `django>=6.0,<6.1` and the runtime is 6.0.7.
- **Not fixed here:** CI's ruff gate covers `apps/` only, so `backend/tests/` (including the contract guard) and `backend/config/` are unlinted, and four files drift outside the gate. Pyright remains advisory at 1199 errors. `DATABASE_URL` in the Backend job is read by nothing.

## Progress log

- 2026-09-29 — Program defined after the two decisions. Confirmed by reading the code: `reports_reporttemplate` is institution-scoped and no migration mentions it; `accounts/0009_audit_rls.py` holds the current `tenant_isolation` (`ALL`/`USING`) and `superadmin_bypass`; `audit/tests/test_rls.py:132` pins the old migration's text.
- 2026-09-29 — Noted while planning: `sync_keycloak_roles` needs no tenant context, so the Celery work is two tasks rather than three.
- 2026-09-29 — W1–W5 landed as `eb86da2`, `45a85da`, `fed9210`, `f7de15f`, `2401f3a` (5 commits, 36 files, +1371/−116). PR #41 opened; CI run `36630929660` green on all three jobs, including the new app-role job over real TCP.
- 2026-09-29 — W6 full-project verification completed: `verified_with_findings`. Structure verified; fixed the compose trap this program introduced; recorded the vendored test gap and the other pre-existing findings above.
