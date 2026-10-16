# RLS runtime enforcement — request tenant context

- **Feature**: `rls-runtime-enforcement`
- **Branch**: `fix/rls-runtime-enforcement` (base `main` @ `b6fffbc`)
- **Created**: 2026-09-29
- **PR**: [#39](https://github.com/TulkasUnValar/sigpi/pull/39) → `main`, CI green at `ff6a09e`
- **TDD**: ON — source `openspec/config.yaml` (`strict_tdd: true`, floor 80%). Runner: `pytest -c backend/pyproject.toml` from the repo root, venv `backend/.venv-wsl`.

## Objective

Make the request-scoped tenant context **actually reach the database**, so that when the runtime finally connects as a least-privilege role, row-level security applies to the view's own queries. This change deliberately does **not** switch the runtime role.

## Problem

`TenantRLSMiddleware` sets the tenant GUC with bare `SET LOCAL` and no surrounding transaction. `SET LOCAL` outside a transaction block is a verified no-op (PostgreSQL emits `WARNING: SET LOCAL can only be used in transaction blocks`), so the GUC is never in effect. Two further facts make the current code unable to work as written:

1. **`ATOMIC_REQUESTS = True` cannot fix this.** Django runs middleware *outside* the request transaction, so the statement would still be a no-op.
2. **Ordering.** `TenantMiddleware` reads RLS-protected `accounts_institutionmembership` at `config/middleware/tenant.py:71-80`, and it runs *before* `TenantRLSMiddleware` in `MIDDLEWARE`. So even a working GUC setter placed where the class sits today would be too late.

Today none of this is observable, because the runtime connects as `POSTGRES_USER=sigpi`, a superuser with `BYPASSRLS`, and such a role skips every policy. The defect is invisible precisely because the privilege defect masks it.

The existing tests cannot catch any of it: all five `TestTenantRLSMiddleware` tests mock the connection (`@patch("config.middleware.tenant.connection")`) and assert only that the SQL *string* was issued — never that PostgreSQL accepted it, nor that a transaction existed.

## Scope

**In:** how the request tenant context is established on the connection; where in the middleware chain it happens; re-application after a mid-request reconnect; real-PostgreSQL tests that prove the view's queries see the right rows.

**Out (deliberately deferred, each already mapped):** switching the runtime to `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD` and giving `sigpi_app` `LOGIN`; tenant contexts for the three Celery tasks (`sync_keycloak_roles`, `dispatch_notification`, `index_document`); audit events with no institution (failed login, logout, OIDC login) that would abort an INSERT; the missing RLS on `reports_reporttemplate`; `WITH CHECK` policy work.

## Constraints

- **Zero production behaviour change.** The runtime stays a superuser, so the GUC remains inert in production until the role switch lands. The deliverable is a mechanism that is correct and *provably verified*, so the switch becomes small.
- Migrations are untouched.
- Artifacts in English, neutral register.
- The `postgres_app_role` fixture (`backend/conftest.py`) already gives the tests a real non-owner role; this change finally exercises it against the middleware path.

## Authorized scope

User selected **"Mecanismo correcto, sin encender el rol"** on 2026-09-29.

## Design decisions

**Connection-scoped `SET`, not a request-spanning transaction.** Chosen because a transaction wrapping the whole request would hold row locks across external I/O and change commit semantics:
- `select_for_update` in `calls/services.py:101,112,123,134,145`, `project_workflow/services.py:136,183,259,286,314,359`, `budgets/services.py:147` would keep locks until the response finished instead of until the service returned.
- MinIO (`documents/services.py:221,284`), Meilisearch (`search/views.py:50-51`), OIDC HTTP (`config/settings/base.py:183-206`) and WeasyPrint rendering (`reports/views.py:190-192`) all run inside requests.
- The ~14 existing `transaction.atomic()` blocks in `projects/services.py:120-260` would degrade to savepoints, so a service that commits on return could later be rolled back by an unrelated request failure.

The tradeoff accepted in exchange: a connection-scoped value outlives the statement, so it must be cleared and can leak if the clearing fails. Two mechanisms remove that risk:
1. **Every request writes both GUCs unconditionally** before any query, so a value left by a previous request is always overwritten. An anonymous request writes `sigpi.institution_id = ''` and `sigpi.bypass_rls = 'false'`, which the hardened `NULLIF(...)` policies turn into a clean deny.
2. **Reset in `finally`**, plus a `connection_created` receiver that re-applies the GUCs to any connection Django creates while a request context is active — covering a mid-request reconnect after a dropped connection.

`SET LOCAL` inside a transaction was rejected as the primary mechanism for the lock reasons above, not for correctness.

## Tasks

| ID | Task | Route | Trigger evidence | Status |
|----|------|-------|------------------|--------|
| T1 | RED: real-PostgreSQL middleware tests (`backend/apps/accounts/tests/test_tenant_rls_middleware.py`) proving the view's queries see the tenant's rows under `SET ROLE sigpi_app`, and that the context is cleared after the response | delegated writer | new file + 2 existing test modules — writer trigger fires | done — `ff6a09e` |
| T2 | GREEN: introduce the tenant-context module (contextvar + connection-scoped apply/clear + `connection_created` receiver) and rewrite `TenantRLSMiddleware` to use it | delegated writer | same work unit | done — `ff6a09e` |
| T3 | Reorder `MIDDLEWARE` so the tenant context is established before `TenantMiddleware`'s first RLS-protected read; update the ordering test in `test_config.py` | delegated writer | same work unit | done — `ff6a09e` |
| T4 | Replace the five connection-mocking tests in `test_middleware.py` with assertions that hold under the new design, keeping their intent | delegated writer | same work unit | done — `ff6a09e` |
| T5 | Verify on real PostgreSQL: the new tests pass and the full suite stays green | per-action fresh worker | — | done — writer + parent reproduction |

## Acceptance criteria

1. On PostgreSQL, under `SET ROLE sigpi_app`, a query executed inside the middleware chain for institution A **sees institution A's rows** and not institution B's. This is the decisive assertion: if the middleware did nothing, the connection would be under a non-owner role with no GUC, so A's own rows would be invisible too and the test would fail.
2. The tenant context is cleared after the response: a query issued afterwards sees nothing, and the GUC read back is empty.
3. The tenant context survives a mid-request reconnect — a connection created while the context is active also receives the GUCs.
4. On SQLite the middleware is a no-op and the suite is unaffected.
5. The full suite stays green on PostgreSQL (baseline `2580 passed, 27 skipped, 0 failed`).
6. No production behaviour change: the runtime credentials and `DATABASES` are untouched.

## Checks

- `pytest -c backend/pyproject.toml backend/apps/accounts/tests/test_middleware.py backend/apps/accounts/tests/test_config.py backend/apps/accounts/tests/test_tenant_rls_middleware.py` on SQLite.
- The same on a throwaway PostgreSQL cluster (the CI-faithful recipe: `initdb -A trust -U sigpi`, `pg_ctl -o "-p 5433 -k /tmp"`, `createdb`).
- The full suite on that cluster.
- `ruff check backend/apps/` / `ruff format --check backend/apps/`.

## Verification evidence

- **RED, against the code as it was:** all four new tests failed on PostgreSQL 18 under `SET ROLE sigpi_app`, each with a message naming the real cause — `The view's query did not see institution A's own membership: the tenant GUC never reached the connection, so RLS denied A's rows too.`, `The tenant context was never active inside the view.`, `active_membership is None: TenantRLSMiddleware did not establish the tenant context before TenantMiddleware's RLS-protected membership read.`, and `The tenant GUC was not re-applied to the connection opened mid-request.`
- **GREEN:** four new tests pass on PostgreSQL; the middleware and config modules report `28 passed`. On SQLite the whole set reports `28 passed, 4 skipped`, so the new tests skip on the engine that has no RLS.
- **Full suite on a throwaway PostgreSQL 18 cluster: `2584 passed, 27 skipped, 0 failed`** (baseline `2580 passed, 27 skipped, 0 failed`, +4 for the new tests). Reproduced twice: once by the writer and once by the orchestrator.
- **Mutation proof — ordering (writer).** Moving `TenantRLSMiddleware` back after `TenantMiddleware` fails two tests, one naming `active_membership is None` and one naming the declared order. The sha256 of `base.py` was identical before and after; restored cleanly.
- **Mutation proof — the mechanism (orchestrator, on a different seam).** Neutering `apply_to` so it writes nothing makes all four new tests fail; restoring the file byte-for-byte (sha256 match) makes them pass again.
- **Why these tests are not vacuous.** The decisive assertion is that the view's query *sees the tenant's own rows*. Under a non-owner role with no GUC the database denies everything, so a middleware that does nothing returns zero rows and that assertion fails — which is exactly what the RED phase and both mutation proofs demonstrate. The cleared-context test also asserts the context was active inside the view first, so it cannot pass by trivially observing nothing.
- **Driver:** `psycopg2 2.9.12`; `import psycopg` raises `ModuleNotFoundError`. `set_config(..., false)` is used so the primitive stays correct if the project later moves to psycopg3, where `SET x = %s` would stop working.
- **Lint:** `ruff check apps/` clean, `ruff format --check apps/` → `339 files already formatted`.
- **Commit:** `ff6a09e` — 6 files, +513/−104. All pre-commit hooks passed. The ruff hook also normalised two pre-existing formatting drift sites in `middleware/tenant.py` (a blank line after the module docstring and a collapsed `.select_related(...)` chain); accepted as the repo's own gate.

### Honest caveat on the reconnect test

The harness logs in as the superuser and assumes `sigpi_app` with `SET ROLE`, which is session state that a dropped connection loses. Inside the test the view therefore re-assumes the role after reconnecting, so the test asserts what the middleware actually owns — that the `connection_created` receiver re-applies the GUC to the new connection (read back directly) — rather than full role survival across a reconnect. That part only becomes real once the runtime logs in as the app role directly. This is documented in the test's own docstring and is not hidden.

### Verification depth, stated plainly

The independent-adversarial-verifier step used for the previous change was replaced here by: the writer's RED-then-GREEN against the real old implementation, the writer's ordering mutation proof, the orchestrator's own mutation on a different seam, and the orchestrator reading all three artifacts in full. That is multi-actor and mutation-backed, but it is not the same as a fresh adversarial reviewer, and the residual risk sits in the global `connection_created` receiver, which no per-request test can fully characterise.

### CI, on PR #39

- Run `36618608960` reported `conclusion=success` at `ff6a09e`; Backend `pass` in 3m4s, Frontend `pass` in 1m15s. PR #39 is `MERGEABLE` / `CLEAN` with exactly one commit.
- CI's own log: `================= 2584 passed, 27 skipped in 106.23s =================`, and all four new tests reported `PASSED` on real PostgreSQL under `SET ROLE sigpi_app`, including `test_rls_context_set_before_tenant_middleware_read`. `test_config.py::TestMiddlewareRegistration::test_rls_middleware_before_tenant_middleware` also `PASSED`. Coverage for the new file: 110 statements, 1 missed, 99%.
- **Pyright delta, checked rather than assumed:** pyright is advisory by explicit CI decision, and the new test file adds a handful of `reportAttributeAccessIssue` diagnostics from django-stubs limitations (custom manager `create_user`, dynamically-set `request.active_membership` / `request.user`, `HttpResponse(str)`). These are not a new class of problem: the suite already reports **442** diagnostics mentioning `create_user` and **62** mentioning `active_membership`. No action taken; the project-wide count moved by about +1.

## Progress log

- 2026-09-29 — Scope decided. The blast-radius map (`backend/rls-runtime-blast-radius`) established that `ATOMIC_REQUESTS` cannot fix the middleware, that INSERT is gated by the `USING`-as-`WITH CHECK` rule, that three Celery tasks would silently break under a role switch, that audit inserts with no institution abort, and that `reports_reporttemplate` has no RLS at all.
- 2026-09-29 — Also verified before writing code: `SET LOCAL` outside a transaction is a no-op and leaves the value unchanged; `set_config(name, value, false)` works under psycopg2 and accepts a bind parameter; `SET x = %s` also happens to work under psycopg2 only because it interpolates client-side, which is why `set_config` was chosen for driver portability. An initial suspicion that `SET` with a placeholder is a syntax error was my own mistake — it was an artefact of `PREPARE ... AS SET`, not of the production path.
- 2026-09-29 — T1–T5 landed as one work unit `ff6a09e` (6 files, +513/−104). All five acceptance criteria met and reproduced by the orchestrator. The change is deliberately inert in production until the role switch.
- 2026-09-29 — Remaining for the next change: give `sigpi_app` `LOGIN` and switch the runtime credentials; make the activation-failure path reject the request instead of continuing; tenant contexts for the three Celery tasks; audit events with no institution; RLS for `reports_reporttemplate`; then re-check `WITH CHECK` deliberately.
- 2026-09-29 — PR #39 opened against `main` with CI green (`36618608960`, success at `ff6a09e`). Before opening it the `branch-pr` skill was loaded and checked against this repository: SIGPI has no `PULL_REQUEST_TEMPLATE.md`, only `ci.yml` (no PR-validation workflow), zero issues, and none of PRs #35–#38 link an issue or carry a label, so the skill's issue-first and `type:*` label requirements describe the gentle-ai repo rather than this one. The repository's own convention was followed; the skill's body structure was reused.
