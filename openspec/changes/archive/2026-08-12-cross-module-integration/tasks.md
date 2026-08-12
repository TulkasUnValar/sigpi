# Tasks: Cross-Module Integration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300 (4 new files, 8 modified, ~6 test files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

## Phase 1: Regression Mitigation (Pre-Flight)

- [x] 1.1 Update `ProjectFactory` default or add status overrides in `backend/apps/products/tests/conftest.py` (`ProductFactory`) and `backend/apps/progress/tests/conftest.py` (`ProgressReportFactory`) so linked projects use `status="aprobado"` / `status="en_ejecucion"` respectively — prevents guard breakage in existing tests.
- [x] 1.2 Run `cd backend; python -m pytest apps/products apps/progress` — confirm all existing tests pass with updated factory defaults before guards land.

## Phase 2: Signal Infrastructure (IP-1, IP-5)

- [x] 2.1 **RED** — Create `backend/apps/calls/tests/test_signals.py`: test `call_state_changed.send` is called with `call`, `from_state`, `to_state`, `triggered_by` on each FSM transition; test no signal on failed transition (FR-001).
- [x] 2.2 **GREEN** — Create `backend/apps/calls/signals.py` with `call_state_changed = django.dispatch.Signal()`. Modify `backend/apps/calls/apps.py` `ready()` to import signals. Add `call_state_changed.send()` inside `_log_transition()` in `backend/apps/calls/services.py` (3 lines, inside `transaction.atomic()`).
- [x] 2.3 **RED** — Create `backend/apps/project_workflow/tests/test_workflow_completed_signal.py`: test `workflow_completed.send` is called with `project_id`, `instance_id`, `triggered_by` when `complete_workflow()` runs; test no auto-transition (FR-005).
- [x] 2.4 **GREEN** — Define `workflow_completed = django.dispatch.Signal()` in `backend/apps/project_workflow/signals.py`. Add `workflow_completed.send()` in `complete_workflow()` in `backend/apps/project_workflow/services.py` (2 lines).

## Phase 3: Service Guards (IP-2, IP-3, IP-4)

- [x] 3.1 **RED** — Create `backend/apps/progress/tests/test_project_state_guard.py`: test `ProgressService.create()` raises `ValidationError` for projects in `borrador`, `enviado`, `en_revision`, `observado`; succeeds for `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, `cerrado` (FR-002, BR-001).
- [x] 3.2 **GREEN** — In `backend/apps/progress/services.py`: define `PROGRESS_ALLOWED_PROJECT_STATES = frozenset({"en_ejecucion", "suspendido", "finalizado", "en_cierre", "cerrado"})`, add `_validate_project_state_for_progress()` guard, call it in `ProgressService.create()`. Replace old `_validate_project_not_terminal`.
- [x] 3.3 **RED** — Create `backend/apps/products/tests/test_project_state_guard.py`: test `perform_create` raises `PermissionDenied` for projects in `borrador`, `enviado`, `en_revision`, `observado`; succeeds for `aprobado`, `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre` (FR-003, BR-002).
- [x] 3.4 **GREEN** — In `backend/apps/products/views.py` `perform_create()`: add `PRODUCT_ALLOWED_PROJECT_STATES` frozenset and project-state guard (6 lines, raises `PermissionDenied`).
- [x] 3.5 **RED** — Create `backend/apps/reports/tests/test_entity_validation.py`: test `ReportRenderer.validate_entity()` returns 404 for unresolvable UUID, 403 for cross-institution, passes for valid entity (FR-004, BR-003).
- [x] 3.6 **GREEN** — Add `validate_entity()` method to `ReportRenderer` in `backend/apps/reports/services.py` with standardized `{"detail": "..."}` errors. Update `backend/apps/reports/views.py` to delegate entity validation to it.

## Phase 4: Integration Test + Verification

- [x] 4.1 Create `backend/tests/integration/test_cross_module_flow.py` (`@pytest.mark.integration`): end-to-end flow — Call open → Project linked → Approved → Execution → Progress created → Product registered → Report generated.
- [x] 4.2 Run full suite: `cd backend; python -m pytest` — confirm 0 regressions, all new tests green, coverage ≥ 80%.
