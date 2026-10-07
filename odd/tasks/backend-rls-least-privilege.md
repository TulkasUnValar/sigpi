# Backend RLS least privilege

- **Feature**: `backend-rls-least-privilege`
- **Branch**: `fix/backend-ci-packaging` (PR #38, base `main`)
- **Created**: 2026-09-29
- **TDD**: ON — source `openspec/config.yaml` (`strict_tdd: true`, `tdd_policy.strict: true`, coverage floor 80%). Runner: `pytest -c backend/pyproject.toml` from the repo root, CI-faithful venv at `backend/.venv-wsl`.

## Objective

Make SIGPI's row-level security actually enforce tenant isolation, and leave the Backend CI job (PR #38) green.

## Problem

Five CI failures remain, all `notifications/tests/test_rls.py::TestRLSEnforcement`. They are not policy bugs; they are four stacked defects:

1. **Privilege, not policy.** CI/docker provision `POSTGRES_USER=sigpi` as a superuser with `BYPASSRLS`, and the app connects with that same role. Superusers and `BYPASSRLS` roles skip RLS unconditionally, and `FORCE ROW LEVEL SECURITY` does not change that. So RLS restricts nobody today — a least-privilege defect, not just a test defect.
2. **Unsafe policy expression.** Every `tenant_isolation` policy uses `institution_id = current_setting('sigpi.institution_id')::uuid`. With an empty GUC the cast raises `DataError: invalid input syntax for type uuid: ""` instead of denying the row. Because permissive policies have all their expressions evaluated, `superadmin_bypass` cannot rescue a query that dies there. A blanket switch to a non-superuser role therefore breaks 1040 tests (958 passed / 579 errors when measured).
3. **The middleware never applies the GUC.** `TenantRLSMiddleware` issues bare `SET LOCAL` with no surrounding transaction (`ATOMIC_REQUESTS` absent, no `transaction.atomic()`; `CONN_MAX_AGE=60`). Verified against PostgreSQL 18: `WARNING: SET LOCAL can only be used in transaction blocks`, value left unset. Masked today by defect 1 — and it would break every request the moment a non-superuser role is introduced.
4. **Silent harness.** The middleware swallows its errors into `logger.debug`, and the enforcement tests skip rather than fail when PostgreSQL or the role is unavailable, so the gap never surfaces.

## Why

The Backend CI job has been red on `main` since at least 2026-09-03. Closing it is what unlocks the three frontend PRs (#35–#37) and honest delivery for everything behind it. Defects 1–3 are also real production security defects, not test artifacts.

## Scope

**In:** the SQL text of the RLS policies; the tests that pin that text; a repo-wide regression guard; the middleware transaction shape; the non-owner application role and its provisioning; the loudness of the test harness.

**Out:** per-test tenant fixtures for the whole 1040-test suite; the frontend PR chain.

## Constraints

- Artifacts in English; neutral/professional register.
- Migrations here are rewritten in place when a committed RLS migration is wrong — precedent: commit `7e08b0b` edited `accounts/0004_rls_policies.py` in place and added `products/0002_rls_policies.py`. Nothing is deployed; CI and local dev build from scratch. Consequence: a local PostgreSQL database must be recreated (or migrations re-run on a fresh DB) to pick up the hardened policies.
- PR #38 already carries 1,586 changed lines across 55 files (`git diff --shortstat main...HEAD`), so the 400-line review budget is already exceeded before this work starts.
- A child PR stacked on `fix/backend-ci-packaging` would receive no CI at all: `ci.yml` only triggers when the PR base is `main`.

## Authorized scope

User selected **"Plan RLS (PR #38)"** on 2026-09-29, continuing the plan recorded under Engram topic `backend/rls-least-privilege-plan`.

## Tasks

| ID | Task | Route | Trigger evidence | Status |
|----|------|-------|------------------|--------|
| T1 | RED: add `backend/tests/test_rls_policy_contract.py` — a repo-wide guard: no migration reads the tenant GUC without `missing_ok`, and every guarded read is wrapped in `NULLIF(..., '')` | delegated writer | 21 target files (13 migrations + 8 test files) — writer trigger fires | done — `1eb452f` |
| T2 | GREEN: harden all 29 `tenant_isolation` reads in the 13 RLS migrations to `NULLIF(current_setting('sigpi.institution_id', true), '')::uuid` | delegated writer | same work unit | done — `1eb452f` |
| T3 | Update the 8 pinned SQL assertions (`audit/tests/test_rls.py:135` + 7 `"...institution_id = current_setting"` pins) to pin the safe form | delegated writer | same work unit | done — `1eb452f` |
| T4 | **Moved to a separate change.** Middleware redesign: set the tenant GUC inside a request-spanning transaction and before the first RLS-protected read | separate change | see "Deferred to a separate change" | moved |
| T5 | Add the non-owner `sigpi_app` role and its grants, idempotently, so a non-privileged session can be assumed | delegated writer | 2+ non-trivial files — writer trigger fires | done — `e8ecdec` |
| T6 | Assume the role with `SET ROLE sigpi_app` inside the three enforcement suites only, leaving the suite-wide connection untouched | delegated writer | same work unit | done — `e8ecdec` |
| T7 | Loud harness: on PostgreSQL, fail (never skip) when the role is missing, still privileged, or the table owner | delegated writer | same work unit | done — `e8ecdec` |
| T9 | Harden the `superadmin_bypass` predicate against an **empty** `sigpi.bypass_rls` — same defect class as T2, found during verification | delegated writer | same 13-file set | done — `f40cfaf` |
| T8 | Verify the Backend job green end to end on PR #38 and watch the run | per-action fresh worker | — | done — run `36601633763`, `success` at `e8ecdec` |

## Decisions (resolved)

Chosen on 2026-09-29: **unblock CI honestly now, move the production redesign to its own change.**

- **Test tenant-context strategy:** test-scoped. Only the three enforcement suites assume `sigpi_app` with `SET ROLE`; the rest of the suite keeps the existing connection, so no suite-wide behaviour changes. Rejected: a session-default `sigpi.bypass_rls=true`, and per-test tenant fixtures for all 1040 tests.
- **Role provenance:** created idempotently by the application layer so CI needs no service change. CI's postgres service has no `volumes:` mount, so `/docker-entrypoint-initdb.d` is not available there.
- **Still open (deferred with T4):** `ATOMIC_REQUESTS = True` versus wrapping `self.get_response(request)` in `transaction.atomic()`; and whether to switch the runtime to `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD`.

## Deferred to a separate change

The middleware redesign is **not** optional for real enforcement, and it is bigger than "create a role". Two coupled defects:

1. **`SET LOCAL` outside a transaction is a no-op.** Verified on PostgreSQL 18: `WARNING: SET LOCAL can only be used in transaction blocks`, value left unset. `DATABASES` has `CONN_MAX_AGE: 60` and no `ATOMIC_REQUESTS`.
2. **Ordering: the GUC is set after the first RLS-protected read.** `accounts_institutionmembership` is RLS-protected (`accounts/0004_rls_policies.py:33-34`), and `TenantMiddleware` queries it at `config/middleware/tenant.py:71-80` — before `TenantRLSMiddleware` (next in `MIDDLEWARE`) sets anything. Under a non-owner role that query returns `None`, so `active_membership` would always be empty and tenancy would break on every request.

The bootstrap is solvable from the session: `accounts_user` and `django_session` are **not** RLS-protected, so the tenant can be read from the session without touching a protected table, and the GUC can be set inside a request-spanning transaction before the membership query runs.

Doing this inside PR #38 would mix an auth/tenancy redesign into a 1,586-line CI-repair PR. It belongs in its own PR based on `main`, where CI actually runs on it.

## Acceptance criteria

1. `backend/tests/test_rls_policy_contract.py` passes and fails if any unsafe cast is reintroduced. **MET** — three contracts, each mutation-proven.
2. Zero occurrences of `current_setting('sigpi.institution_id')::uuid` (without `missing_ok`) anywhere under `backend/apps/*/migrations/`. **MET** — 0 found; 29 safe wrappers; `CREATE POLICY` unchanged at 58.
3. With the GUC unset **or** set to `''`, an institution-scoped query returns zero rows and raises nothing. **MET** for both the tenant GUC and the bypass GUC, on PostgreSQL 18 as a non-owner role.
4. `notifications/tests/test_rls.py::TestRLSEnforcement` passes against a real PostgreSQL connecting as a non-superuser, non-`BYPASSRLS` role. **MET** — all seven pass in the CI log, under `SET ROLE sigpi_app`.
5. The rest of the suite stays green under the chosen strategy. **MET** — `2580 passed, 27 skipped, 0 failed`, reproduced locally and in CI.
6. The Backend CI job reports success on PR #38. **MET** — run `36601633763` reported `conclusion=success` at `e8ecdec`; Backend `pass` in 2m52s, Frontend `pass` in 1m31s; PR #38 is `mergeable=MERGEABLE`, `mergeState=CLEAN`.

## Checks

- Fast: `pytest -c backend/pyproject.toml backend/tests/test_rls_policy_contract.py backend/apps/notifications/tests/test_rls.py backend/apps/audit/tests/test_rls.py` (SQLite engine; policy-text assertions run, enforcement tests skip).
- Real: the full suite against a throwaway PostgreSQL cluster (the previous session used `initdb -A trust -U sigpi`, port 5433, and matched CI exactly).
- Lint/format: `ruff check` / `ruff format` pinned at `0.16.9`.
- Type gate: `tsc`-equivalent for this work is CI's own path; `pyright` stays advisory.

## Verification evidence

- **RED (before T2):** `2 failed in 0.16s` — the guard enumerated exactly 29 offenders across the 13 migrations.
- **GREEN:** `108 passed, 35 skipped in 11.78s` across the ten RLS modules. The 35 skips are the PostgreSQL enforcement tests, expected on SQLite.
- **Lint:** `ruff check apps/` → `All checks passed!`; `ruff format --check apps/` → `337 files already formatted`. CI's real scope is `cd backend && ruff check apps/` and `ruff format --check apps/` (`.github/workflows/ci.yml:78,83`), so the 6 pre-existing formatter offenders under `backend/config/` sit outside the gate and the writer's `partial` was over-cautious. The new guard file also passes both checks.
- **Static integrity:** 0 occurrences of the unsafe cast under `backend/apps/`; 29 safe-form occurrences; total `CREATE POLICY` count unchanged at 58; `superadmin_bypass` predicates unchanged at 29; the intentional notification-template `USING (true)` policy untouched.
- **Empirical, PostgreSQL 18** (scratch schema, non-owner role `NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS`, probe dropped afterwards):

  | GUC state | old policy | new policy |
  |---|---|---|
  | never set | `ERROR: unrecognized configuration parameter "sigpi.institution_id"` | **0 rows, no error** |
  | set to `''` | `ERROR: invalid input syntax for type uuid: ""` | **0 rows, no error** |
  | matching institution | — | 1 row |

  Acceptance criterion 3 is satisfied with observed evidence.
- **Guard mutation proof.** The guard's first, line-oriented version had a real hole: a two-line unsafe cast inside `project_workflow/migrations/0002_rls_policies.py`'s `CHILD_TABLES_SQL` dict made it report `2 passed`. After rewriting the guard to match normalized patterns instead of lines, the same mutation produces `1 failed` naming `apps/project_workflow/migrations/0002_rls_policies.py:43`, the file restores to an identical sha256, and the guard passes again. Baseline→mutated→restored: `True / True / True`.
- **Independent verification** (an adversarial `general` agent with no knowledge of the author's reasoning): `verified_with_findings`, **no blocker**, and all 8 updated assertions judged kept-strong or strengthened from the weaker old substring.
- **Commit:** `1eb452f` on `fix/backend-ci-packaging` — 22 files, +158/−55. Every pre-commit hook passed.

### T5–T7 and T9 — the enforcement harness and the bypass predicate

- **Decisive measurement, reproduced by the orchestrator:** the FULL suite on a throwaway PostgreSQL 18 cluster reports **`2580 passed, 27 skipped, 0 failed`** (exit 0). Before this work it was `5 failed, 2572 passed, 27 skipped`, and all five failures were `notifications/tests/test_rls.py::TestRLSEnforcement`. The 8-test difference is accounted for: +2 from the guard added in `1eb452f`, +1 from the bypass contract, +5 cleared failures.
- **Enforcement suites on PostgreSQL:** `63 passed` (60 enforcement + 3 guard tests), versus skipping entirely before.
- **SQLite:** `51 passed, 12 skipped` — the enforcement tests still skip, which is correct on an engine with no RLS.
- **Static integrity:** 0 unsafe tenant casts, 29 safe wrappers, 0 old bypass predicates, 29 new bypass predicates, `CREATE POLICY` unchanged at 58.
- **Bypass predicate, proven on PostgreSQL 18 as a non-owner role:**

  | `sigpi.bypass_rls` | old predicate | new predicate |
  |---|---|---|
  | unset | 0 rows (fine) | 0 rows |
  | `''` | `ERROR: invalid input syntax for type boolean: ""` | **0 rows, no error** |
  | `'true'` | — | 1 row |
  | `'false'` | — | 0 rows |

- **Guard mutation proofs.** Reintroducing the unsafe tenant cast (including split across two lines inside a helper dict) fails Contract A naming the exact line; reintroducing the old bypass predicate fails the bypass contract naming `apps/accounts/migrations/0009_audit_rls.py:34`. Every mutation was restored to a byte-identical sha256.
- **Migration idempotency** (independent verification, applied twice against real PostgreSQL): the second `GRANT sigpi_app TO CURRENT_USER` is a NOTICE, not an error; the `DO` block is a true no-op; the role ends at `rolsuper=f rolbypassrls=f rolcreatedb=f rolcreaterole=f rolcanlogin=f` and owns 0 tables.
- **Self-heal proof:** a role pre-provisioned as `SUPERUSER LOGIN CREATEDB CREATEROLE BYPASSRLS` converges to `super=false bypass=false login=false createdb=false owned_tables=0` after the migration, and the full suite still reports 0 failures against that database.
- **Role-leak proof:** `current_user` was observed as `sigpi` → `sigpi_app` → `sigpi` around a passing test, an assertion-failing test, and a DB-erroring test. No leak, because `SET ROLE` is transactional in PostgreSQL and the test transaction's rollback reverts it.
- **Loud-harness proof:** the fixture was mutation-tested against all three failure paths — role missing, role made a superuser, role made the owner of an RLS table — and it FAILS with a specific message in each, never skipping.
- **Commits:** `f40cfaf` (14 files, +99/−56) and `e8ecdec` (5 files, +260/−45). Every pre-commit hook passed.

## Follow-ups (found, out of scope, recorded)

- **F4 — CI does not lint `backend/tests/`.** CI's ruff scope is `apps/` only, so the new guard file is unlinted by the gate (it is clean anyway). Extending the ruff scope is a separate change.
- **F5 — stale raw cast in archived design docs.** `openspec/archive/**` and `openspec/changes/archive/**` still contain the unsafe form (e.g. `openspec/archive/projects/design.md:383`). Not runtime, but a copy-paste source for future policies.
- **CORRECTION (2026-09-29): an earlier note here claimed INSERT is ungated because no policy declares `WITH CHECK`. That is WRONG.** Every policy is `ALL` with only `USING`, and PostgreSQL uses the `USING` expression as `WITH CHECK` for INSERT when `WITH CHECK` is absent. Verified against PostgreSQL 18 with a non-owner role: an INSERT whose `institution_id` is NULL, or with no tenant GUC set at all, raises `new row violates row-level security policy`. This is not a gap to close — it is the mechanism that makes enforcement real, and it is the reason the deferred runtime switch needs the audit and Celery paths solved first.
- **Eight pinned assertions assert the substring appears *somewhere* in a migration's combined SQL**, not that the specific table's policy contains it. Pre-existing limitation, unchanged.
- **The audit enforcement assertions are weak enough to be vacuous** (`backend/apps/audit/tests/test_rls.py:202-215` asserts `count >= 0`, and `:187-200` only asserts `count == 0`). Under default-deny (RLS on, policy missing) they still pass, so a policy-removal regression there would slip through; the notifications suite's positive assertions would catch it. Pre-existing, but now more visible because the tests finally run under real RLS.
- **The harness checks role attributes, not membership.** A `sigpi_app` that is a *member of* a `BYPASSRLS` role is not detected. Verified empirically to be inert — role attributes are not inherited, and only an explicit re-`SET ROLE` would escalate — so it is defense-in-depth, not a false-pass path.
- **The bypass contract does not bind the trailing cast.** `NULLIF(current_setting('sigpi.bypass_rls', true), '')` used with a non-boolean cast would still satisfy it.
- **`ruff` in `backend/.venv-wsl` is 0.16.0 while `pyproject.toml` pins 0.16.9.** Both verdicts agree on the current tree; the environment is stale.
- **CI does not lint `backend/tests/`** (F4, above): the guard file is unlinted by the gate.
- **Four `TestRLSEnforcement` classes are stubs and stay skipped**, so the green is real but enforcement coverage is thin: `documents`, `projects`, `calls`, and `accounts` (`backend/apps/accounts/tests/test_rls.py:26`) all skip with empty method bodies. The classes that actually assert enforcement are `notifications` and `audit`, and those now pass under `sigpi_app`. Filling the four stubs is real work that the new role mechanism finally makes possible.
- **The Codecov upload step is silently failing**: `Upload coverage report` logs `Token required - not valid tokenless upload` and only stays green because `fail_ci_if_error: false`. Coverage has not actually been uploaded. Pre-existing; the job's green does not mean coverage reached Codecov.
- **`25 skipped` of the `27 skipped` are stub enforcement tests**, which makes the skipped count easy to misread as passing coverage.
- **Blocked-on-decision blind spot.** The guard protects the 27 in-block sites plus any single- or multi-line occurrence anywhere in a migration file; it does not resolve helper-dict indirection, so a future policy built by string concatenation from a variable would need a runtime check instead.

## Progress log

- 2026-09-29 — Started. Reconnaissance mapped 13 RLS migrations / 29 unsafe expressions (a 30th grep hit lives in a test assertion), 8 pinned assertions, 2 policy names, and the two open risks. The middleware `SET LOCAL` defect was confirmed empirically against PostgreSQL 18 and persisted under Engram topic `backend/tenant-guc-set-local-broken`.
- 2026-09-29 — T1–T3 landed as one work unit: `1eb452f` (22 files, +158/−55). Guard, hardened migrations, updated pins, and the corrected notifications docstring. Verified by RED→GREEN, a repo-wide static integrity count, an empirical PostgreSQL 18 probe, a guard mutation proof, and an independent adversarial verification. The guard was rewritten once inside this work unit after the verifier proved a split-line hole.
- 2026-09-29 — Next: T4–T7 are blocked on decisions D1/D2/D3. Note that T4 is now a prerequisite rather than an optional extra: with the middleware still issuing bare `SET LOCAL`, introducing the `sigpi_app` role would make every request see zero rows (or raise, given the observed `unrecognized configuration parameter` behaviour).
- 2026-09-29 — Scope decided: unblock CI honestly now, move the production redesign to its own change. T5–T7 landed as `e8ecdec` (5 files, +260/−45): the `sigpi_app` role in a migration (chosen over an init script because CI's postgres service has no `volumes:` mount), a shared loud `postgres_app_role` fixture, and `SET ROLE` scoped to the three enforcement suites.
- 2026-09-29 — Verification found a second instance of the same defect class: `COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool` covers an unset bypass GUC but raises `invalid input syntax for type boolean: ""` when it is empty. Confirmed on PostgreSQL 18, then hardened in all 29 predicates as `f40cfaf` (14 files, +99/−56) with a third guard contract.
- 2026-09-29 — Scoped correction after independent verification: the role migration now also converges an existing `sigpi_app` onto the intended attributes (a hand-provisioned superuser role no longer silently keeps `BYPASSRLS`), and the fixture's `RESET ROLE` teardown no longer errors on an aborted transaction.
- 2026-09-29 — Orchestrator reproduced the decisive result: `2580 passed, 27 skipped, 0 failed` on PostgreSQL. A stray 39 MB PostgreSQL data directory created by a failed probe inside the repo root was identified and removed.
- 2026-09-29 — Remaining: T8 (push and watch the Backend job on PR #38). Deferred: the middleware redesign (T4) as its own change from `main`.
- 2026-09-29 — T8 done. Pushed `0bfe08e..e8ecdec`; run `36601633763` completed `success`. CI's own log reports `2580 passed, 27 skipped in 104.47s` and every `notifications/tests/test_rls.py::TestRLSEnforcement` test PASSED — including the five that were the whole point. PR #38 is `MERGEABLE` / `CLEAN`. The Backend job had been red on `main` since at least 2026-09-03.
- 2026-09-29 — Feature complete for this branch. Not done, deliberately: merging PR #38 (user decision), the four stub enforcement classes, the Codecov token, and the T4 middleware redesign.
