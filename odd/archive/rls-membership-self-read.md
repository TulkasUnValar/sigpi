# RLS membership self-read (login + institution switch)

- Feature: `rls-membership-self-read`
- Branch: `fix/rls-enforcement-completion` (extends PR #41, base `main`)
- TDD: ON — `openspec/config.yaml` `strict_tdd: true`; runner `cd backend; python -m pytest`
- Delivery: `single-pr` — lands as commits on the existing PR #41, which the user approved to merge once this fix is in.
- Artifact store: `openspec` files + this document; Engram mirror `odd/rls-membership-self-read/tasks`.

## Objective

Make the authenticated user able to see their OWN institution memberships under
the least-privilege `sigpi_app` role, so that local login can establish the
initial institution and institution switching works.

## Problem (verified empirically, PostgreSQL 18)

`accounts_institutionmembership` is RLS-scoped by `institution_id = GUC` only
(`apps/accounts/migrations/0004_rls_policies.py:32-62`). There is no
"own membership" policy anywhere in the repository. "Which institutions does
this authenticated user belong to?" is an inherently cross-tenant question that
a single-tenant GUC cannot answer.

Observed under `SET ROLE sigpi_app` (throwaway cluster, port 5433):

| Flow | Result |
|---|---|
| `POST /auth/login/`, fresh session | `200`, but `active_institution_id: null`, `memberships: []`, session institution `None` |
| `POST /auth/switch-institution/` A → B | `403 "You do not belong to this institution."` |
| membership rows visible, empty GUC | `0` |
| membership rows visible, GUC = A | `1` |

Consequences: after login the user has no active institution (every
tenant-required endpoint then answers `400 Active institution required`);
`/auth/me/` lists no memberships; switching institution is impossible. Before
PR #41 the runtime connected as a `BYPASSRLS` superuser, so RLS was inert and
none of this surfaced. CI cannot catch it: the `backend` job runs as the owner
and `verify_app_role_rls` only probes `accounts_auditevent`.

## Why not the alternatives

- **Momentary `bypass_rls` in the views** (the app role already has a
  `superadmin_bypass FOR ALL` policy): smallest diff, but it puts bypass inside
  the application process at exactly the place PR #41 argued against, and a
  leaked GUC would silently disable enforcement.
- **Reading memberships from an unprotected table**: there is no such table;
  inventing one to dodge RLS moves the isolation gap rather than closing it.

Chosen: a third GUC `sigpi.user_id` plus a `FOR SELECT` policy that lets a
session read rows whose `user_id` is its own. Tenant isolation is unchanged for
every other row; the only widening is "a user may read their own memberships",
which is the minimum needed and cannot expose another user's rows.

## Scope

In scope:
- `sigpi.user_id` GUC in `config/tenant_context.py` (written with the other two,
  reset by `clear`, re-applied on reconnect).
- `config/middleware/tenant.py` sets it from the authenticated session user.
- Migration `apps/accounts/0013` adding the `own_memberships` `FOR SELECT`
  policy on `accounts_institutionmembership`.
- `apps/accounts/views.py`: `local_login_view` re-establishes the context after
  `login()`; `switch_institution_view` re-scopes to the institution the session
  adopts before emitting.
- Real enforcement tests in `apps/accounts/tests/test_rls.py`.

Out of scope:
- The 25 stub `TestRLSEnforcement` classes in other apps (separate follow-up).
- `WITH CHECK` review on the remaining tables.
- Any frontend change (the response shape does not change).

## Constraints

- Artifacts and code in English, neutral register.
- No password or secret committed.
- Migrations keep running as the owner; tests keep `POSTGRES_APP_USER` unset.
- The three GUCs must always be written together, so a stale `sigpi.user_id`
  can never leak across a pooled connection.
- Native PostgreSQL is required for the enforcement tests; they skip on SQLite.

## Tasks

### T1 — RED: enforcement tests for login, switch and self-read
- [x] Add `backend/apps/accounts/tests/test_rls.py` using the `postgres_app_role`
      fixture (real RLS, no owner bypass in the assertions), with:
  - login under `sigpi_app` sets the primary institution and returns a non-empty
    `memberships` list;
  - switching A → B under `sigpi_app` returns `200` and the session adopts B;
  - a user sees only their own membership rows;
  - non-vacuity control: with an empty `sigpi.user_id` the user's own rows are
    **not** visible (proves the new policy is load-bearing).
- [x] Observe RED against PostgreSQL before implementing.
- Evidence: pytest output showing the failures.

### T2 — `sigpi.user_id` GUC
- [x] `config/tenant_context.py`: add `USER_GUC`; carry it through `_context`,
      `apply_to`, `activate`, `clear`, `tenant_context()` and
      `_reapply_on_new_connection`. `user_id` defaults to `None` so existing
      callers (Celery, middleware) keep working.

### T3 — middleware sets the user GUC
- [x] `config/middleware/tenant.py`: pass `request.user.pk` when authenticated,
      else `None`.

### T4 — migration
- [x] `apps/accounts/migrations/0013_membership_self_read.py`: add
      `own_memberships FOR SELECT USING (user_id = NULLIF(current_setting('sigpi.user_id', true), '')::uuid)`
      on `accounts_institutionmembership`; reversible. PostgreSQL-only, no-op on SQLite.

### T5 — views
- [x] `local_login_view`: after `login()`, activate with `(None, False, user.pk)`
      so the primary-membership read is allowed; then adopt the session
      institution and re-activate with `(institution_id, False, user.pk)` before
      the audit emit.
- [x] `switch_institution_view`: after adopting the new institution, re-activate
      with `(new_institution_id, False, user.pk)` before the audit emit.

### T6 — GREEN and regression
- [x] New suite green on PostgreSQL.
- [x] Full backend suite green on PostgreSQL and on SQLite.
- [x] `ruff check apps/` and `ruff format --check apps/` clean.

### T7 — work-unit commits on the branch
- [x] Commit the fix and its tests together, conventional commits, no AI attribution.

### T8 — OIDC membership sync under the app role (added after verification)
- [x] `apps/accounts/backends.py` `_sync_membership`: wrap the membership
      `get_or_create`/save and the center sync in
      `tenant_context(connection, institution.pk, False, user.pk)`, matching the
      import pattern used by the Celery tasks (`from config.tenant_context import tenant_context`).
      Today the OIDC callback runs anonymously at middleware time, so the GUCs
      are empty and the INSERT violates `tenant_isolation` → 500 on the primary
      auth path.
- [x] Enforce with a test that calls the OIDC backend's `create_user` (and the
      `update_user` path) with a `sigpi_institution_id` claim while assumed as
      `sigpi_app`, asserting the membership row is created/updated.
- Evidence: RED (membership write raises a policy violation) then GREEN.

### T9 — switch response lists the adopted institution's centers
- [x] `apps/accounts/views.py` `switch_institution_view`: the lookup
      `.prefetch_related("centers")` runs while the GUC still holds the OLD
      institution, and `institutions_researchcenter` is RLS-protected, so the
      response's `centers` is always empty. Drop the stale prefetch so the
      response reads centers after the re-scope.
- [x] Extend the switch enforcement test to assert the response carries the
      center assigned to the adopted membership.
- Evidence: RED (`centers: []`) then GREEN.

### T10 — document the non-active centers constraint
- [x] `_serialize_user` reads every membership's centers under the single
      active-institution GUC, so memberships other than the active one report
      `centers: []`. The client contract only consumes the active membership's
      centers (`frontend/store/auth.ts` `deriveActiveMembership` /
      `deriveCenters`; `deriveInstitutions` uses only id+name). Record this as a
      deliberate consequence of tenant scoping with a comment — do NOT widen
      center visibility for data no consumer reads.

## Acceptance criteria

1. Under `SET ROLE sigpi_app`, a local login with a primary membership yields
   `200`, `active_institution_id` set, and a non-empty `memberships` list.
2. Under `SET ROLE sigpi_app`, switching from the active institution to another
   institution the user belongs to yields `200`.
3. Under `SET ROLE sigpi_app`, a session carrying user X's id sees X's
   membership rows and none of user Y's.
4. With an empty `sigpi.user_id`, X's own rows are invisible (non-vacuity).
5. Existing behaviour as the owner is unchanged; no migration runs as `sigpi_app`.
6. Under `SET ROLE sigpi_app`, the OIDC backend's `create_user`/`update_user`
   with a `sigpi_institution_id` claim creates/updates the membership instead of
   raising an RLS policy violation.
7. Under `SET ROLE sigpi_app`, the switch response's `centers` contains the
   center assigned to the adopted membership.

## Route declaration

| Task | Route | Trigger evidence |
|---|---|---|
| T1 | delegated (one writer) | 4+ files to touch; tests plus implementation form one cohesive change |
| T2–T5 | delegated (same writer) | preparation-for-write + 2+ non-trivial files |
| T6 | delegated verification | high risk (auth/RLS); writer self-checks + parent spot check |
| T7 | inline | mechanical commit |

## Verification

- `cd backend && POSTGRES_HOST=/tmp POSTGRES_PORT=5433 POSTGRES_USER=sigpi POSTGRES_PASSWORD=sigpi POSTGRES_DB=sigpi PYTEST_RUNNING=true .venv-312/bin/python -m pytest apps/accounts/tests/test_rls.py -v`
- `cd backend && .venv-312/bin/python -m pytest apps/ -q` (SQLite) and the same with the PostgreSQL env above.
- `cd backend && .venv-312/bin/ruff check apps/ && .venv-312/bin/ruff format --check apps/`

## Progress

**CLOSED — merged to `main` as `90ba294`.**

- Landed on branch `fix/rls-enforcement-completion` as commit `0065f55`
  (`feat(rls): make login and institution switch work under the app role`),
  which extends PR #41.
- PR #41 merged 2026-09-30 with a merge commit (`chore(merge): integrate the
  RLS enforcement completion into main`); `origin/main` is at `90ba294`.
- CI green on the PR head and on the post-merge `main` run `36782268780`
  (Backend, Backend app-role RLS, Frontend all pass).

Evidence per task:

- **T1–T5, T8, T9** — built on branch `fix/rls-enforcement-completion` as commit `0065f55` on top of `8832c0c`; the enforcement tests ran on a throwaway
  PostgreSQL 18 cluster (port 5433) with `SET ROLE sigpi_app`, not as the owner.
  - T8 RED: `new row violates row-level security policy for table "accounts_institutionmembership"` from `_sync_membership` via both `create_user` and `update_user`; GREEN after the tenant-context wrapper.
  - T9 RED: `centers` in the switch response was `[]`; GREEN with the center id present.
  - T1 RED: login returned no active institution and an empty `memberships` list; switch returned 403.
- **T6** — PostgreSQL full suite `2616 passed, 24 skipped`; SQLite `2583 passed, 57 skipped`; `ruff check apps/ config/` clean; `ruff format --check` clean; `makemigrations --check` reports no changes.
- **T7** — one work-unit commit, tests alongside the code, conventional message, no AI attribution.
- **T10** — documented in `_serialize_user`; no behaviour change.

Two independent adversarial verification rounds ran against the fix. The first
found the OIDC blocker (T8) and the two `centers` findings (T9, T10); the second
confirmed all three closed and surfaced the `tenant_context` reentrancy defect,
which is fixed and covered by `TestNestedTenantContext` (RED verified by
temporarily reverting the context manager).

Not covered here (separate follow-ups, unchanged):
- the 25 stub `TestRLSEnforcement` classes in `budgets`, `calls`, `documents`,
  `projects` and `accounts`' siblings, plus `test_rls.py` for `products` and
  `progress`;
- the tautological `assert count >= 0` in `audit/tests/test_rls.py:216`;
- the silent superuser fallback in `settings/base.py` (`POSTGRES_APP_USER or
  POSTGRES_USER`), the dead `DATABASE_URL`, the silent Codecov upload, CI's
  ruff scope, and the Django version claims.
