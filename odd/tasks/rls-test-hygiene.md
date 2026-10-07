# RLS test hygiene: shared helper + per-table structural asserts

- Feature: `rls-test-hygiene`
- Base `main` @ `2e2fd64`.
- TDD: ON — `openspec/config.yaml` `strict_tdd: true`; runner `pytest -c backend/pyproject.toml` from the **repo root**.
- Delivery: two PRs — **A** (shared helper + all ten files) with maintainer-approved `size:exception`, then **B** (per-table isolated structural asserts).
- Artifact store: `openspec` files + this document; Engram mirror `odd/rls-test-hygiene/tasks`.

## Objective

Two test-hygiene follow-ups on the ten RLS enforcement suites:

- **A — shared helper.** The generic RLS mechanics are copied per file. Extract
  them into one module so the GUC contract and the isolation assertions have a
  single source of truth.
- **B — isolated structural asserts.** The migration-text assertions match
  predicate substrings anywhere in the concatenated migration SQL, so a
  single-table predicate regression slips through. Assert each table's predicate
  inside its own `CREATE POLICY ... ON <table> USING (...)` block.

## Problem

The ten target files each carry a byte-identical helper block
(`TENANT_GUC`, `BYPASS_GUC`, `_get_apply_function_source`, `_set_rls`,
`_assert_only_a_visible`, `_assert_both_visible`) plus a parameterizable
`_get_migration` and a `_get_all_sql` method — ~51 lines/file × 10 ≈ 510
duplicated lines.

The structural checks call `_get_all_sql()`, which returns the concatenation of
`ENABLE_RLS_SQL` **and** `DISABLE_RLS_SQL` (the latter also contains
`tenant_isolation` inside `DROP POLICY`). Examples of non-isolating asserts:
`researchers:204-207,216`, `project_workflow:212-215,223`, `reports:270-273`,
`budgets:197-200,209-213`, `calls:197-200,207-211`. `institutions` has no
predicate assertion at all.

## Scope

In scope:
- New shared module `backend/tests/rls_helpers.py`.
- Refactor the ten files to import from it (generic helpers only; app-specific
  `_seed_*`, table lists and expectations stay local).
- Add `policy_using(sql, table, policy="tenant_isolation")` and replace the
  non-isolating structural asserts with per-table isolated ones; add the missing
  `institutions` predicate assertion.

Out of scope:
- `accounts`, `audit`, `notifications` test files — different helper names and
  signatures (`accounts` `_set_rls` is 4-arg; `notifications` uses
  `_set_rls_context`). Not part of A.
- Sharing the `TestRLSEnforcement` class bodies / base-class refactor.
- Any production code or migration change.

## Design decisions

1. **Shared module**: `backend/tests/rls_helpers.py`, imported as
   `from tests.rls_helpers import ...`. Safe because `backend/tests/__init__.py`
   exists and `backend/pyproject.toml` sets `pythonpath = ["backend"]`; the
   supported invocation is from the repo root (`pytest -c backend/pyproject.toml`).
   Default pytest importmode (`prepend`) plus `__init__.py` in every `tests/`
   dir means no basename collisions.
2. **Exports**: `TENANT_GUC`, `BYPASS_GUC`, `load_migration(app_label,
   migration_name)`, `get_all_sql(migration)`, `get_apply_function_source(...)`,
   `set_rls(connection, institution_id, bypass)`, `assert_only_a_visible(...)`,
   `assert_both_visible(...)`, and (added in B) `policy_using(sql, table,
   policy="tenant_isolation")`. `load_migration` must accept an arbitrary
   `(app_label, migration_name)` so `reports` can load both `0002_rls_policies`
   and `0004_reporttemplate_rls`, and `institutions` can load `0003_rls_policies`.
3. **Isolation regex**: `policy_using` anchors on `CREATE POLICY` (never `DROP
   POLICY`), matches the table's `USING (...)` with `re.DOTALL`, and returns the
   whitespace-normalized predicate. Do not reintroduce a line-oriented matcher
   (see `backend/tests/test_rls_policy_contract.py` history: a cast split across
   lines was missed once).

## Quality bar

- The refactor is behavior-preserving: every existing test keeps the same
  pass/skip result, and non-vacuity is unchanged.
- Each structural assert must fail if that table's predicate (and only that
  table's) is removed from the migration.
- SQLite still skips enforcement via `postgres_app_role`; migration-text tests
  stay SQLite-safe (`load_migration` runs at call time, not import time).

## Tasks

### T1 — A1: shared module + first five files
- [ ] Add `backend/tests/rls_helpers.py` with the generic helpers.
- [ ] Refactor `budgets`, `calls`, `projects`, `documents`, `products` to import
      from it; delete the local duplicates; keep app-specific seeds/expectations.

### T2 — A2: remaining five files
- [ ] Refactor `progress`, `institutions`, `researchers`, `project_workflow`,
      `reports` the same way (`reports` must keep loading both migrations).

### T3 — B: per-table isolated structural asserts
- [ ] Add `policy_using()` to `rls_helpers.py`.
- [ ] Replace the non-isolating asserts in all ten files with per-table isolated
      ones; add the missing `institutions` predicate assertion.

### T4 — full verification
- [ ] Full PostgreSQL and SQLite suites green; `ruff check` and
      `ruff format --check` clean.
- [ ] Adversarial check: tests still prove isolation; a single-table predicate
      mutation is caught by the new structural asserts.

### T5 — commits and PRs
- [ ] One work-unit commit per slice, tests only, conventional messages, no AI
      attribution; chained PRs `stacked-to-main`.

## Acceptance criteria

1. No generic RLS helper is duplicated in the ten files.
2. Every protected table has a predicate assertion scoped to that table's
   `CREATE POLICY` block.
3. All existing tests keep their pass/skip behaviour; SQLite still skips
   enforcement.
4. No production file modified.

## Verification

```
cd /home/tulkasubuntu/01-sigpi   # repo ROOT
POSTGRES_HOST=/tmp POSTGRES_PORT=5433 POSTGRES_USER=sigpi POSTGRES_PASSWORD=sigpi POSTGRES_DB=sigpi \
PYTEST_RUNNING=true backend/.venv-312/bin/python -m pytest -c backend/pyproject.toml \
  backend/apps/<app>/tests/test_rls.py -v
```

Plus the full PostgreSQL and SQLite suites, and ruff.

## Progress

**IN PROGRESS — PR A CLOSED, PR B pending.** Base `main` @ `2e2fd64`.

- **T1/T2 (PR A) — DONE, MERGED.** `backend/tests/rls_helpers.py` created; all ten
  test files refactored to import it. PR #51 merged to `main` as `119e8ec`
  (`size:exception` approved; 11 files, +532 / −1129). Full PostgreSQL `2703
  passed / 2 skipped`; SQLite `2619 passed / 86 skipped`; ruff clean; adversarial
  review: PRESERVED (helper bodies identical, no assertion changed, `reports`
  keeps both migrations).
- **T3 (PR B) — PENDING (not started).** Add `policy_using(sql, table,
  policy="tenant_isolation")` to `rls_helpers.py` and replace the non-isolating
  migration-text asserts with per-table isolated ones in all ten files; add the
  missing `institutions` predicate assertion. Must include a mutation proof
  (temporarily remove one table's predicate → the new assert fails; restore).
- **T4 — pending** (full suites + ruff + adversarial/mutation verification).
- **T5 — pending** (commit B, PR, CI, merge).

Resume tomorrow: start PR B from `main` @ `119e8ec`; the working tree is clean
except the deliberate untracked entries (`.gitignore` modification, `odd/`,
`opencode.json`, `.gentle-ai-default-agent.json`). The reconnaissance for B
(per-table predicates, the `policy_using` regex, the `CREATE POLICY` vs
`DROP POLICY` caveat) is in this document's earlier sections.
