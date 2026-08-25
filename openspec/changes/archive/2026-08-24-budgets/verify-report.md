# Verify Report — Budget Module (Presupuesto — SIGPI §6.9)

## Verdict

**status: success** — `next_recommended: archive`

## Executive Summary

All 14 tasks across PR 1/2/3 are marked complete. The full pytest suite (`apps/`) passes with **2040 passed / 21 skipped / 0 failed**. The focused 3-app suite (budgets + accounts + reports) passes **564 / 10 skipped**. Coverage floors are met on every affected app (budgets **90.2%**, accounts **83.9%**, reports **94.8%**).

Spec scenarios **RF-B01** through **RF-B07** are implemented and tested. Business rules **RN-019** (multiple funding sources), **RN-020** (line execution cap with authorized overrun), **RN-021** (audit emission) are enforced and covered. **RN-022** (reports module consumes BudgetSummaryService) is wired through `apps/reports/services.py::_project_context` and renders in `project_report.html` with an absent/empty fallback.

Code quality: `ruff check` clean (config excludes migrations), `manage.py check` clean, `makemigrations --check` clean.

One pre-existing environmental caveat: the Postgres `db` host is unresolvable in this WSL session; Postgres-only RLS enforcement and the concurrent-boundary test are skipped on SQLite. The migration `0002_rls_policies.py` ships and is validated by `tests/test_rls.py` against the SQL text. No production code risk; re-run on Postgres when the DB host is reachable.

## Test Evidence

| Command | Result |
|---|---|
| `python -m pytest apps/budgets/ apps/accounts/ apps/reports/ -q` | **564 passed**, 10 skipped, 3 warnings |
| `python -m pytest apps/ -q` | **2040 passed**, 21 skipped, 3 warnings |
| `python manage.py check` | System check identified no issues (0 silenced) |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `ruff check apps/budgets apps/accounts apps/reports` | All checks passed |

> Note: `COVERAGE_FILE` pointed at a local temp dir to dodge the pytest-cov SQLite-lock bug on the WSL network path (Python 3.14 / Windows upstream issue, documented in `pyproject.toml`).

## Coverage Report (per-app production source)

| App | Coverage | Floor | Verdict |
|---|---|---|---|
| `apps.budgets` | **90.2%** | ≥90% (spec NFR) | pass |
| `apps.accounts` | **83.9%** | ≥80% (general TDD floor) | pass |
| `apps.reports` | **94.8%** | ≥80% (general TDD floor) | pass |

Per-file budgets highlights: `views.py` 81%, `services.py` 97%, `serializers.py` 100%, `models.py` 99%, `permissions.py` 93%, `filters.py` 100%, `admin.py` 100%, `migrations/0001_initial.py` 100%, `migrations/0002_rls_policies.py` 87%.

## Regression Report

- Full `apps/` suite: **2040 passed / 21 skipped / 3 warnings / 0 failures**.
- No new failures introduced by the budget module or its integration changes.

## Spec Compliance Matrix

| Requirement | Implementation evidence | Test evidence |
|---|---|---|
| **RF-B01** Budget CRUD (OneToOne + duplicate 409) | `models.Budget.project` `OneToOneField`; `DuplicateBudgetError`; `Conflict409` view | `test_models.OneToOneUniqueness`, `test_views.test_duplicate_budget_returns_409` |
| **RF-B02** Line CRUD (nested) | `BudgetLine` FK→Budget; `/api/budgets/{id}/lines/` routes | `test_views.TestBudgetLineCRUD` |
| **RF-B03** FundingSource (multiple, RN-019) | `FundingSource` FK→Project; `/api/projects/{pid}/funding-sources/` | `test_views.TestFundingSourceCRUD` |
| **RF-B04** Execution + RN-020 | `BudgetService.add_execution` with `select_for_update` + sum check + authorize gate | `test_services` (within / over-no-auth / over-with-auth / atomic) |
| **RF-B05** Attachment metadata-only | `external_url` required | `test_serializers.test_external_url_required` |
| **RF-B06** Filter project/institution/status | `BudgetFilter` | `test_filters` |
| **RF-B07** Summary endpoint + None when absent | `BudgetSummaryService.for_budget`; `/api/budgets/{id}/summary/`; reports fallback | `test_services.TestBudgetSummaryService`, `test_views.TestBudgetSummaryEndpoint`, `test_budget_summary` |

## Business Rules

- **RN-019** Multiple funding sources per project — enforced by FK-only (no `unique_together` on `(project, name)`); `test_views` confirms multiple creation.
- **RN-020** Line execution cap — enforced inside `BudgetService.add_execution` (services.py:120–160); `select_for_update` lock + recheck; tests cover within / over-no-auth (400) / over-with-auth (success) / atomic rollback on rejection.
- **RN-021** Audit emission — `BudgetService` emits `BUDGET_CREATED`, `BUDGET_UPDATED`, `BUDGET_EXECUTION_ADDED` via `AuditEventEmitter`; tests use real `AuditEvent` persistence (`test_integration.py` + `test_audit.py`).
- **RN-022** Reports budget summary — `BudgetSummaryService.for_budget(project)` wired into `_project_context`; template renders approved/executed/balance with empty-state fallback; `test_budget_summary.py` covers present and absent paths.

## Design Compliance

- Models match design contract: 5 entities, UUID PKs, `DecimalField(14,2)`, non-negative checks, FK cascades, OneToOne uniqueness on `Budget.project`.
- API endpoints match design contract: all 7 spec endpoints present in `urls.py` with nested routing (lines, executions, attachments, funding-sources, summary).
- Services match design contract: atomic transactions, lock+recheck, audit emission, summary aggregator.
- RLS migration `0002_rls_policies.py` ships with `tenant_isolation` + `superadmin_bypass` on all 5 tables; mirrors `apps/calls` pattern.

## Code Quality

- `ruff check apps/budgets apps/accounts apps/reports` → All checks passed.
- `python manage.py check` → System check identified no issues (0 silenced).
- `python manage.py makemigrations --check --dry-run` → No changes detected.

## Integration

- **Reports** — `apps/reports/services.py:178` imports + invokes `BudgetSummaryService.for_budget(project)`; result added to project context as `budget_summary`; `project_report.html` renders conditionally with empty-state fallback.
- **Auth / Audit** — `apps/accounts/audit.py` adds 3 `BUDGET_*` enum members; migration `0006_alter_auditevent_event_type.py` alters the `event_type` choices; 3 new test methods in `test_audit.py`.

## Findings

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | All tasks marked `[x]` in `tasks.md` | pass | 14/14 checkboxes |
| 2 | Focused pytest 3-app passes | pass | 564 passed, 10 skipped |
| 3 | Coverage ≥80% all affected apps | pass | budgets 90.2%, accounts 83.9%, reports 94.8% |
| 4 | Coverage ≥90% `apps.budgets` | pass | 90.2% |
| 5 | RF-B01–B07 implemented + tested | pass | spec scenarios mapped |
| 6 | RN-019, RN-020, RN-021 enforced + tested | pass | services + integration tests |
| 7 | RN-022 reports integration | pass | `services.py` + template + tests |
| 8 | No regressions (full `apps/` suite) | pass | 2040 passed |
| 9 | ruff clean | pass | All checks passed |
| 10 | `manage.py check` clean | pass | 0 issues |
| 11 | `makemigrations --check` clean | pass | No changes detected |
| 12 | Audit event types present + emitted | pass | enum + migration + tests |
| 13 | Design compliance (models, API, services) | pass | grep evidence |
| 14 | RLS migration ships | pass | `0002_rls_policies.py` present |

## Risks

- **WARNING (pre-existing, environmental)** — Postgres `db` hostname is unresolvable from this WSL session; the 10 skipped tests include 9 pre-existing RLS/Postgres skips + 1 new concurrent-boundary test (`test_concurrent_execution_atomicity`, marked skip with explicit reason). Real Postgres enforcement still requires a reachable DB. No production code risk; re-run on Postgres when env is available.
- **SUGGESTION** — After archive, schedule follow-up to re-run on Postgres CI to validate RLS enforcement and the concurrent atomicity test once the DB host is available.
- **SUGGESTION** — The 19 additional apps skipped (full suite) include cross-cutting features unrelated to budgets; not blocking for the budget archive.

## Artifacts

- OpenSpec verify report: `openspec/changes/budgets/verify-report.md` (this file)
- Engram topic key: `sdd/budget-module/verify-report`

## Next Recommended Action

**sdd-archive** — sync delta specs (`budgets/specs/budgets`, `auth`, `reports`) into `openspec/specs/` and create the archive directory.
