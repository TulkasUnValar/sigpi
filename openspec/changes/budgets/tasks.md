# Tasks: Budget Module (Presupuesto — SIGPI §6.9)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2200–2600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | App scaffolding + models + 0001_initial + RLS 0002 | PR 1 | `cd backend; python -m pytest apps/budgets/tests/test_models.py apps/budgets/tests/test_rls.py` | `python manage.py migrate` on Postgres; `python manage.py check` | delete `apps/budgets/` + revert settings/urls; drop budget tables |
| 2 | Serializers, filters, permissions, views/urls, service (RN-020/021), admin + tests | PR 2 | `cd backend; python -m pytest apps/budgets/tests/` | DRF browseable API manual nested POST via test client | revert serializers/filters/views/urls/services/admin; keeps models |
| 3 | Audit types + reports RN-022 summary wiring + integration tests | PR 3 | `cd backend; python -m pytest apps/budgets/tests/ apps/reports/tests/test_services.py` | generate project report PDF, assert budget_summary present/absent | revert audit choices + reports service/template change |

## Phase 1: Foundation (PR 1)

- [x] 1.1 Create `backend/apps/budgets/` package (`__init__.py`, `apps.py` `BudgetsConfig`); register `apps.budgets` in `backend/config/settings/base.py` LOCAL_APPS; add `path("api/", include("apps.budgets.urls"))` to `backend/config/urls.py`
- [x] 1.2 Create `models.py`: Budget (UUID PK, project OneToOne, institution FK, name, approved_amount, status draft/approved/executed/closed, timestamps; unique project + `(institution,status)` index), BudgetLine, FundingSource, BudgetExecution (nullable authorized_by/authorized_at), BudgetAttachment (required external_url); money fields Decimal(14,2) + non-negative validator + DB check; parent cascade, auth user SET_NULL
- [x] 1.3 Generate `0001_initial.py` (5 tables, FKs, checks, indexes, one-to-one uniqueness)
- [x] 1.4 Create `0002_rls_policies.py` mirroring `apps/calls/migrations/0002_rls_policies.py`: tenant_isolation + superadmin_bypass on all 5 tables; Budget direct institution; lines/executions/attachments subquery Budget; FundingSource subquery Project; Postgres-only, SQLite no-op
- [x] 1.5 Write RED tests `tests/test_models.py` (constraints, uniqueness, non-negative) + `tests/test_rls.py` (migration exists, SQL, Postgres guard, enforcement)

## Phase 2: Core Implementation (PR 2)

- [ ] 2.1 Write RED `tests/test_serializers.py` then `serializers.py` (read-only parent/tenant fields; nested line/source/execution/attachment serializers; external_url required)
- [ ] 2.2 Write RED `tests/test_filters.py` then `filters.py` (project, institution, status; institution-scoped)
- [ ] 2.3 Write RED `tests/test_permissions.py` then `permissions.py` (level ≤3 mutate, researcher read-only, director center membership, over-execution auth)
- [ ] 2.4 Write RED `tests/test_services.py` then `services.py`: `BudgetService` atomic create/update/delete/execution, lock+recheck line, RN-020 (sum ≤ approved unless authorized), emit `BUDGET_CREATED/UPDATED/EXECUTION_ADDED` via AuditEventEmitter; `BudgetSummaryService.for_budget()` → approved/executed/balance or None
- [ ] 2.5 Write RED `tests/test_views.py` + `tests/test_urls.py` then `views.py` + `urls.py`: Budget ViewSet (GET/POST/PATCH/DELETE + summary @action), nested lines/executions/attachments, `/api/projects/{pid}/funding-sources/`; duplicate budget 409, overrun 400, cross-institution 404
- [ ] 2.6 Create `admin.py` registering all 5 models (list_display, search, filters)

## Phase 3: Integration + Reports (PR 3)

- [ ] 3.1 Add `BUDGET_CREATED`, `BUDGET_UPDATED`, `BUDGET_EXECUTION_ADDED` to `AuditEventType` in `backend/apps/accounts/audit.py`
- [ ] 3.2 In `backend/apps/reports/services.py::_project_context`, add conditional `budget_summary` via `BudgetSummaryService.for_budget(project)` (absent/empty when no Budget); extend report template/context for RN-022
- [ ] 3.3 Write integration tests: report context includes/excludes budget_summary; summary math; audit payloads; RN-020 authorized/unauthorized + atomic concurrent boundaries
- [ ] 3.4 Verify ≥90% coverage on `apps.budgets` (`--cov=apps.budgets`); `python manage.py check` + migrate on Postgres
