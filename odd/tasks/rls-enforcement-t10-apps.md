# RLS enforcement tests for the four T10 apps

- Feature: `rls-enforcement-t10-apps`
- Base `main` @ `41aa430`.
- TDD: ON — `openspec/config.yaml` `strict_tdd: true`; runner `pytest -c backend/pyproject.toml` from the **repo root**.
- Delivery: chained PRs, `stacked-to-main` (4 slices, one per app); each PR under the 400-line review budget.
- Artifact store: `openspec` files + this document; Engram mirror `odd/rls-enforcement-t10-apps/tasks`.

## Objective

Add real, non-vacuous cross-institution RLS enforcement tests for the four apps
the prior T10 report found uncovered: `institutions`, `researchers`,
`project_workflow` and `reports`. Keep each app's existing migration-text
structural checks.

## Problem

These four apps ship RLS migrations but no runtime enforcement test:

- `institutions/tests/test_rls.py` (251 lines) — migration-text only. Two defects:
  `test_has_reverse_code` dereferences the migration module with no
  `assert migration is not None` guard; `test_institution_not_in_tenant_tables_list`
  asserts only inside `if hasattr(mod, "TENANT_SCOPED_TABLES")`, so it passes
  vacuously if the attribute disappears.
- `researchers/tests/test_rls.py` (241 lines) — migration-text only; same missing
  None guard.
- `project_workflow/tests/test_rls.py` (344 lines) — migration-text plus a
  SQLite-only `TestApplicationLevelTenantScoping` class; no `postgres_app_role`.
- `reports/tests/test_rls.py` (210 lines) — covers only `0004`
  (`reports_reporttemplate`); `reports_report` and `reports_reportapproval` have
  neither structural nor enforcement coverage.

## Scope

In scope:
- Enforcement tests (tenant isolation + bypass) per protected table for the four apps.
- Fix the two `institutions` defects and the `researchers` None guard.
- Add structural coverage for `reports_report` and `reports_reportapproval`.

Out of scope:
- Any production code or migration change. If a policy looks wrong, report it; do
  not change it here.
- Refactoring the six already-merged test files to share helpers.

## Quality bar (the point of the change)

Every enforcement test must be non-vacuous:

1. **Seed real rows** for two institutions, A and B, in the app's protected
   tables (seed as `sigpi_app` under a bypass context:
   `set_config('sigpi.bypass_rls','true',false)`), then switch to `bypass=false`
   and set `sigpi.institution_id` to A.
2. **With the GUC set to A**: A's rows are visible (`count >= 1`, or the seeded pk
   present) **and** B's are not (`count == 0`). Asserting only the zero is vacuous.
3. **The bypass test must prove it reveals MORE**: assert the count covers both
   institutions (`== 2`), not `count >= 0`.
4. Never write `assert count >= 0`, `assert True`, or an assertion whose truth
   does not depend on RLS.
5. Skip on SQLite through the `postgres_app_role` fixture, never by silently passing.

Imitate exactly the proven template in `backend/apps/budgets/tests/test_rls.py`
(`_set_rls`, `_seed_*`, `_assert_only_a_visible` requiring A visible AND B denied,
`_assert_both_visible` requiring `== 2`).

## Protected tables and predicates

| App | Protected tables | Tenant predicate |
|---|---|---|
| `institutions` | `institutions_sede`, `institutions_facultad`, `institutions_researchcenter`, `institutions_researchgroup`, `institutions_researchline` | direct `institution_id` (`0003_rls_policies.py:48`) |
| `researchers` | `researchers_researcher` (direct); `researchers_researcheraffiliation`, `researchers_externalprofile`, `researchers_researcherattachment` (subquery via researcher) | `0002_rls_policies.py:54`, `:78` |
| `project_workflow` | `project_workflow_workflowtemplate`, `project_workflow_workflowinstance` (direct); `project_workflow_workflowstep` (via template), `project_workflow_workflowaction` (via instance) | `0002_rls_policies.py:67`, `:91` |
| `reports` | `reports_report` (direct), `reports_reportapproval` (via report), `reports_reporttemplate` (direct) | `0002_rls_policies.py:46`, `:70`; `0004_reporttemplate_rls.py:36` |

`institutions_institution` has no `institution_id` and is intentionally outside
the policy set (`0003:27-28`).

## Tasks

### T1 — `institutions`
- [ ] Fix `test_has_reverse_code` (None guard) and
      `test_institution_not_in_tenant_tables_list` (assert the attribute exists).
- [ ] Add enforcement for `Sede`, `Facultad`, `ResearchCenter`, `ResearchGroup`,
      `ResearchLine` + bypass, using the existing factories.
- [ ] Keep the structural `test_each_table_has_enable_rls`.

### T2 — `researchers`
- [ ] Add the missing None guard.
- [ ] Add enforcement for `Researcher`, `ResearcherAffiliation`, `ExternalProfile`,
      `ResearcherAttachment` + bypass. `ResearcherAffiliation.save()` calls
      `full_clean()`, so the affiliation must reference a same-institution center
      (the factory already couples them; use `is_primary=False`).

### T3 — `project_workflow`
- [ ] Add enforcement for `WorkflowTemplate`, `WorkflowInstance`, `WorkflowStep`,
      `WorkflowAction` + bypass.
- [ ] Keep the structural checks and the SQLite scoping class.

### T4 — `reports`
- [ ] Add structural + enforcement coverage for `Report` and `ReportApproval`
      (the `0002` tables), plus enforcement for `ReportTemplate` (already
      structurally covered by `0004`).
- [ ] `Report.created_by` needs a `User`; `accounts_user` is not RLS-protected.

### T5 — full verification
- [ ] New/updated suites green on PostgreSQL.
- [ ] Full backend suite green on PostgreSQL and on SQLite.
- [ ] `ruff check backend/apps` and `ruff format --check backend/apps` clean.

### T6 — commits and PRs
- [ ] One work-unit commit per app, tests only, conventional messages, no AI attribution.
- [ ] Chained PRs, `stacked-to-main`, one per app.

## Acceptance criteria

1. Each of the four apps has at least one non-vacuous cross-institution test and
   one bypass test per protected table.
2. No vacuous assertion remains (`hasattr`-guarded, `count >= 0`, unguarded
   `migration.operations`, etc.).
3. Everything runs on PostgreSQL via `postgres_app_role`; SQLite skips rather
   than passing silently.
4. Existing behaviour unchanged; no production file modified.

## Verification

```
cd /home/tulkasubuntu/01-sigpi   # repo ROOT
POSTGRES_HOST=/tmp POSTGRES_PORT=5433 POSTGRES_USER=sigpi POSTGRES_PASSWORD=sigpi POSTGRES_DB=sigpi \
PYTEST_RUNNING=true backend/.venv-312/bin/python -m pytest -c backend/pyproject.toml \
  backend/apps/<app>/tests/test_rls.py -v
```

Plus the full PostgreSQL and SQLite suites, and ruff.

## Progress

**CLOSED — shipped as a 4-PR `stacked-to-main` chain; all merged to `main`**
(`main` @ `2e2fd64`). Post-merge CI run `37363241858` green (Backend Python 3.12,
Backend app-role RLS, Frontend).

| PR | Slice | Authored lines | Merge commit |
|----|-------|----------------|--------------|
| #47 | `institutions` (+2 defect fixes) | 161 | `a61e54e` |
| #48 | `researchers` (+None guard) | 139 | `6d4d647` |
| #49 | `project_workflow` | 129 | `a304a24` |
| #50 | `reports` | 222 | `2e2fd64` |

- **T1..T4 — DONE.** Every protected table in each app has a non-vacuous
  cross-institution test plus a bypass test; the four previously reported defects
  are fixed; `reports` gained structural + enforcement coverage for its `0002`
  tables.
- **T5 — DONE.** Adversarial non-vacuity review: all four files NON_VACUOUS. Full
  PostgreSQL `2703 passed / 2 skipped / 0 failed`; full SQLite
  `2619 passed / 86 skipped / 0 failed`; `ruff check` + `format --check` clean.
- **T6 — DONE.** Four work-unit commits, four PRs, all merged.

Authored lines: 161 + 139 + 129 + 222 = ~651 total, each slice under the 400-line
budget.

Residual (not vacuity): several migration-text structural assertions
(`researchers:204-207,216`; `project_workflow:212-215,223`; `reports:267-273`)
test the concatenated module SQL, so a single-table predicate regression would not
be caught by them — enforcement is carried by the new `TestRLSEnforcement`
classes. Left as-is (pre-existing pattern, out of scope).
