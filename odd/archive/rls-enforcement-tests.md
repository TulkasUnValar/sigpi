# RLS enforcement tests for the remaining apps

- Feature: `rls-enforcement-tests`
- Branch: new branch off `main` (`90ba294`); base `main` is green and PR #41 is merged.
- TDD: ON — `openspec/config.yaml` `strict_tdd: true`; runner `cd backend; python -m pytest`
- Delivery: chained PRs, `stacked-to-main` (re-sliced after the 400-line review budget was exceeded; 5 slices).
- Artifact store: `openspec` files + this document; Engram mirror `odd/rls-enforcement-tests/tasks`.

## Objective

Replace the skipped, empty `TestRLSEnforcement` stubs with real row-isolation
tests, so every app that claims RLS enforcement actually asserts it against
rows — and close the two apps that have an RLS migration but no test file.

## Problem

Four apps ship a `TestRLSEnforcement` class that is entirely
`@pytest.mark.skip` with `pass` bodies and a skip reason that reads as a
capability note ("Requires PostgreSQL with RLS support"), which hides the fact
that the app has no isolation assertion at all:

| App | File | Stubbed tests |
|---|---|---|
| `budgets` | `tests/test_rls.py:240` | 6 (budget, line, execution, attachment, funding_source, bypass) |
| `calls` | `tests/test_rls.py:247` | 5 (call, document, CallProject, state log, bypass) |
| `projects` | `tests/test_rls.py:250` | 6 (project, member, document, observation, state log, bypass) |
| `documents` | `tests/test_rls.py:288` | per the file's own stub list |

`products` and `progress` have an RLS migration (`products/0002_rls_policies.py`,
`progress/0002_rls_policies.py`) but **no** `tests/test_rls.py` at all.

`audit/tests/test_rls.py` has two weak tests: `test_user_a_cannot_read_institution_y_events`
counts an empty table (0 rows regardless), and `test_superadmin_bypass_sees_all_rows`
asserts nothing meaningful — its body ends on a comment, with no assertion that
bypass actually reveals more.

The mechanism to do this properly already exists: the `postgres_app_role`
fixture (`backend/conftest.py`) assumes `SET ROLE sigpi_app`, and
`accounts/tests/test_rls.py` and `notifications/tests/test_tasks_rls.py` are the
proven templates.

## Scope

In scope:
- Convert the four skipped `TestRLSEnforcement` stubs into real enforcement tests.
- Add `products/tests/test_rls.py` and `progress/tests/test_rls.py` (structural
  checks plus real enforcement).
- Strengthen the two weak `audit/tests/test_rls.py` tests.
- Report (do not implement) whether `institutions`, `researchers`,
  `project_workflow` and `reports` have real enforcement or only migration-text
  checks.

Out of scope:
- Any production code or migration change. If a policy looks wrong, report it;
  do not change it here.
- The 21 other smaller recorded items.

## Quality bar (this is the point of the change)

Every enforcement test must be non-vacuous:

1. **Seed real rows** for two institutions, A and B, in the app's protected
   tables (seeding protected rows as `sigpi_app` needs a bypass context, exactly
   like `apps/notifications/tests/test_tasks_rls.py` does).
2. **With the GUC set to A**: A's rows are visible (`count >= 1`, or the specific
   seeded pk is present) **and** B's are not (`count == 0`). Asserting only the
   zero is vacuous — it would pass on an empty table.
3. **The superadmin bypass test must prove it reveals MORE**: set bypass and
   assert the count covers both institutions (`>= 2` across A and B), not
   `count >= 0`.
4. Never write `assert count >= 0`, `assert True`, or an assertion whose truth
   does not depend on RLS.
5. Skip on SQLite through the `postgres_app_role` fixture, never by silently
   passing.

## Tasks

### T1 — `budgets`: fill the 6 stubbed tests
- [ ] Replace the skipped class with real tests using `postgres_app_role`,
      covering `budgets_budget`, `budgets_budgetline`, `budgets_budgetexecution`,
      `budgets_budgetattachment`, `budgets_fundingsource` and the bypass case.
      Confirm the table list against `budgets/migrations/0002_rls_policies.py`.

### T2 — `calls`: fill the 5 stubbed tests
- [ ] Same treatment for the call, document, CallProject and state-log tables,
      plus bypass. Confirm against `calls/migrations/0002_rls_policies.py`.

### T3 — `projects`: fill the 6 stubbed tests
- [ ] Same treatment for project, member, document, observation and state-log
      tables, plus bypass. Confirm against `projects/migrations/0002_rls_policies.py`.

### T4 — `documents`: fill the stubbed tests
- [ ] Same treatment for the tables in `documents/migrations/0002_rls_policies.py`.

### T5 — `audit`: strengthen the two weak tests
- [ ] `test_user_a_cannot_read_institution_y_events` must seed a row for
      institution Y and prove it is invisible to X (not merely that an empty
      table counts 0).
- [ ] `test_superadmin_bypass_sees_all_rows` must assert that bypass reveals at
      least one row that the tenant context hides.

### T6 — `products`: add `tests/test_rls.py`
- [ ] Structural checks over `products/migrations/0002_rls_policies.py` plus real
      enforcement for its protected tables and the bypass case.

### T7 — `progress`: add `tests/test_rls.py`
- [ ] Same, for `progress/migrations/0002_rls_policies.py`.

### T8 — full verification
- [ ] The new/updated suites green on PostgreSQL.
- [ ] Full backend suite green on PostgreSQL and on SQLite.
- [ ] `ruff check apps/` and `ruff format --check apps/` clean.

### T9 — commit
- [ ] One work-unit commit per app group, tests only, conventional messages, no AI attribution.

### T10 — report the enforcement gap (no implementation)
- [ ] For `institutions`, `researchers`, `project_workflow` and `reports`, state
      whether each has real enforcement tests or only migration-text checks, with
      file:line evidence.

## Acceptance criteria

1. No `@pytest.mark.skip` class with `pass` bodies remains in `budgets`, `calls`,
   `projects`, `documents`.
2. `products` and `progress` each have a `tests/test_rls.py` with at least one
   cross-institution test and one bypass test.
3. No new assertion is vacuous: each negative assertion is paired with a
   positive assertion over a seeded row, and each bypass assertion requires more
   rows than the tenant context reveals.
4. Everything runs on PostgreSQL via `postgres_app_role`; SQLite skips rather
   than passing silently.
5. Existing behaviour unchanged; no production file modified.

## Verification

- `cd backend && POSTGRES_HOST=/tmp POSTGRES_PORT=5433 POSTGRES_USER=sigpi POSTGRES_PASSWORD=sigpi POSTGRES_DB=sigpi PYTEST_RUNNING=true .venv-312/bin/python -m pytest apps/<app>/tests/test_rls.py -v`
- Full PostgreSQL and SQLite suites, plus ruff.

## Progress

**CLOSED — shipped as a 5-PR `stacked-to-main` chain; all merged to `main`.**
Work moved from `test/rls-enforcement-coverage` (off `main` @ `90ba294`) to five
stacked branches because the total (~1,240 authored lines) exceeded the 400-line
review budget:

| PR | Slice | Authored lines | Merge commit |
|----|-------|----------------|--------------|
| #42 | `budgets` + `calls` | 285 | `6750dcc` |
| #43 | `projects` + `documents` | 303 | `6e35e74` |
| #44 | `audit` | 79 | `bb30d69` |
| #45 | `products` | 342 | `e55ee53` |
| #46 | `progress` | 362 | `41aa430` |

Every PR: CI green (Backend Python 3.12, Backend app-role RLS, Frontend). Final
post-merge `main` run `37340824706` is green.

Status per task:

- **T1 `budgets` — DONE.** 6 real tests (PR #42).
- **T2 `calls` — DONE.** 5 real tests (PR #42).
- **T3 `projects` — DONE.** 6 real tests (PR #43).
- **T4 `documents` — DONE.** 5 real tests (PR #43).
- **T5 `audit` — DONE.** Two weak tests strengthened (PR #44).
- **T6 `products` — DONE, VERIFIED.** New `products/tests/test_rls.py`, 16 tests,
  adversarially confirmed non-vacuous (PR #45).
- **T7 `progress` — DONE, VERIFIED.** New `progress/tests/test_rls.py`, 17 tests,
  adversarially confirmed non-vacuous (PR #46).
- **T8 — DONE.** Full PostgreSQL `2676 passed / 2 skipped / 0 failed`; full SQLite
  `2612 passed / 66 skipped / 0 failed`; `ruff check apps/` and
  `ruff format --check apps/` clean.
- **T9 — DONE.** Five work-unit commits, five PRs, all merged to `main`.
- **T10 — DELIVERED.** `institutions`, `researchers`, `project_workflow` and
  `reports` have **no** runtime RLS-enforcement tests — only migration-text
  assertions (`sigpi.institution_id` appears only inside SQL-string asserts).
  None uses `postgres_app_role` / `SET ROLE sigpi_app`.

Evidence:

- **Non-vacuity (adversarial, read-only):** all 7 files NON_VACUOUS; the negative
  assertions fail when the policies are dropped. Non-blocking nits: two `audit`
  positive controls (`test_insert_with_null_institution_succeeds`,
  `test_tenant_can_select_own_institution_rows`) are controls, not isolation
  proofs; the six files set the GUC session-scoped (`set_config(..., false)`) vs
  the transaction-local template, a latent order-coupling (no false pass today).
- **Budget:** every slice stayed under 400 authored lines (additions + deletions).

Follow-ups (not part of this change): real RLS-enforcement tests for the four T10
apps; the `set_config(..., true)` GUC hygiene; the `.gitignore` / `opencode.json` /
`odd/` untracked decisions.
