# Verification Report: cross-module-integration

## Summary

| Field | Value |
|-------|-------|
| Change | cross-module-integration |
| Mode | Standard verify (full artifacts: proposal + spec + design + tasks) |
| Verdict | **PASS WITH WARNINGS** |
| Date | 2026-08-12 |

## Completeness

| Artifact | Present | Status |
|----------|---------|--------|
| spec.md | Yes | 5 FRs, 3 BRs, 10 scenarios |
| design.md | Yes | 5 architecture decisions, file changes, interfaces |
| tasks.md | Yes | 14/14 tasks checked |
| apply-progress.md | Yes | Strict TDD documented |

## Task Completion

| Phase | Tasks | Complete |
|-------|-------|----------|
| Phase 1: Regression Mitigation | 2 | 2/2 |
| Phase 2: Signal Infrastructure | 4 | 4/4 |
| Phase 3: Service Guards | 6 | 6/6 |
| Phase 4: Integration + Verify | 2 | 2/2 |
| **Total** | **14** | **14/14** |

## Test Execution Evidence

### New Tests (35 tests)

| Test File | Tests | Result |
|-----------|-------|--------|
| `apps/calls/tests/test_signals.py` | 6 | PASSED |
| `apps/progress/tests/test_project_state_guard.py` | 9 | PASSED |
| `apps/products/tests/test_project_state_guard.py` | 9 | PASSED |
| `apps/reports/tests/test_entity_validation.py` | 7 | PASSED |
| `apps/project_workflow/tests/test_workflow_completed_signal.py` | 3 | PASSED |
| `tests/integration/test_cross_module_flow.py` | 1 | PASSED |

### Regression Suite (full affected modules)

| Module Group | Tests | Passed | Failed | Skipped |
|--------------|-------|--------|--------|---------|
| calls + project_workflow + integration | 358 | 358 | 0 | 5 |
| progress + products + reports | 533 | 533 | 0 | 0 |
| **Total** | **891** | **891** | **0** | **5** |

### Command Evidence

```
$ cd backend && PYTEST_RUNNING=true python -m pytest apps/calls/tests/test_signals.py \
    apps/progress/tests/test_project_state_guard.py \
    apps/products/tests/test_project_state_guard.py \
    apps/reports/tests/test_entity_validation.py \
    apps/project_workflow/tests/test_workflow_completed_signal.py \
    tests/integration/test_cross_module_flow.py -v
35 passed, 1 warning in 21.26s

$ python -m pytest apps/calls apps/project_workflow tests/integration -q
358 passed, 5 skipped, 1 warning in 86.78s

$ python -m pytest apps/progress apps/products apps/reports -q
533 passed, 1 warning in 175.43s
```

## Spec Compliance Matrix

### FR-001: Call Lifecycle Signal (IP-1)

| Scenario | Implementation | Test | Status |
|----------|---------------|------|--------|
| Signal emitted on transition | `call_state_changed.send()` in `_log_transition()` inside `transaction.atomic()` | `test_signal_emitted_on_open_call`, `test_signal_emitted_on_close_call`, `test_signal_emitted_on_start_evaluation`, `test_signal_emitted_on_publish_results`, `test_signal_emitted_on_archive` | PASS |
| No signal on failed transition | Signal only emitted after successful FSM transition | `test_no_signal_on_failed_transition` | PASS |

**Evidence**: `apps/calls/signals.py:14`, `apps/calls/services.py:169-175`, all FSM methods wrap `_log_transition` in `transaction.atomic()`.

### FR-002: Progress Creation Guard (IP-2)

| Scenario | Implementation | Test | Status |
|----------|---------------|------|--------|
| Progress created for executing project | `PROGRESS_ALLOWED_PROJECT_STATES` includes `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, `cerrado` | `test_create_allows_execution_and_later[en_ejecucion]`, `[suspendido]`, `[finalizado]`, `[en_cierre]`, `[cerrado]` | PASS |
| Progress rejected for pre-approval project | `_validate_project_state_for_progress()` raises `ValidationError` with correct message | `test_create_rejects_pre_execution_project[borrador]`, `[enviado]`, `[en_revision]`, `[observado]` | PASS |

**Evidence**: `apps/progress/services.py:27-37`, guard called in `ProgressService.create()` at line 68. Error message matches spec exactly.

### FR-003: Products Creation Guard (IP-3)

| Scenario | Implementation | Test | Status |
|----------|---------------|------|--------|
| Product created for approved project | `PRODUCT_ALLOWED_PROJECT_STATES` includes `aprobado`, `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, `cerrado` | `test_create_allows_approved_and_active[aprobado]`, `[en_ejecucion]`, `[suspendido]`, `[finalizado]`, `[en_cierre]` | PASS |
| Product rejected for pre-approval project | Guard in `perform_create()` raises `PermissionDenied` with correct message | `test_create_rejects_pre_approval_project[borrador]`, `[enviado]`, `[en_revision]`, `[observado]` | PASS |

**Evidence**: `apps/products/views.py:38-40, 89-90`. Guard in `perform_create()` per design decision. Error message matches spec.

### FR-004: Report Entity Integrity (IP-4)

| Scenario | Implementation | Test | Status |
|----------|---------------|------|--------|
| Valid entity resolution | `ReportRenderer.validate_entity()` resolves project/researcher/center | `test_valid_project_entity`, `test_valid_researcher_entity`, `test_valid_center_entity` | PASS |
| Unresolvable entity | Raises `Http404("Entity not found.")` | `test_unresolvable_project_raises_404` | PASS |
| Cross-institution entity | Raises `PermissionDenied("Entity does not belong to your institution.")` | `test_cross_institution_project_raises_403`, `test_cross_institution_researcher_raises_403` | PASS |

**Evidence**: `apps/reports/services.py:41-107`. Views delegate to `validate_entity()` at `apps/reports/views.py:136-138, 185-187`. Error format uses `{"detail": "..."}` via DRF exception handling.

### FR-005: Workflow Completion Signal (IP-5)

| Scenario | Implementation | Test | Status |
|----------|---------------|------|--------|
| Signal emitted on workflow completion | `workflow_completed.send()` in `complete_workflow()` with lazy import | `test_signal_emitted_on_complete_workflow`, `test_signal_emitted_when_advance_step_completes_workflow` | PASS |
| No auto-transition in MVP | No receiver changes project status | `test_no_auto_transition_in_mvp` | PASS |

**Evidence**: `apps/project_workflow/signals.py:29`, `apps/project_workflow/services.py:193-201`. Lazy import avoids circular dependency.

## Design Coherence

| Decision | Design | Implementation | Status |
|----------|--------|---------------|--------|
| IP-3 guard location | `perform_create()` (no new service file) | Guard in `ResearchProductViewSet.perform_create()` | MATCH |
| IP-4 validation strategy | Refactor into `ReportRenderer.validate_entity()` | Method exists with standardized errors | MATCH |
| IP-2 guard pattern | Replace `_validate_project_not_terminal` | Old guard replaced with state-set check | MATCH |
| Signal emission timing | Inside `transaction.atomic()` | All call signals emitted inside atomic block | MATCH |
| IP-5 MVP scope | Signal only, no auto-transition | No receiver modifies project status | MATCH |

### Documented Deviations

1. **IP-5 lazy import**: Lazy import of `workflow_completed` inside `complete_workflow()` to avoid circular dependency. Documented in code comment at `apps/project_workflow/services.py:193`.
2. **IP-2 `cerrado` included**: Design interface section omitted `cerrado`, but spec FR-002 and tasks 3.2 explicitly include it. Implementation follows spec (authoritative).

## Quality Checks

| Check | Result | Details |
|-------|--------|---------|
| ruff | WARNING | 9 fixable issues (unused imports, import sort order) |
| mypy | NOT RUN | Infrastructure constraint (no Docker/PostgreSQL for full env) |
| Coverage | NOT MEASURED | SQLite lock issue on WSL path; apply-progress reports 98% |

## Issues

### WARNING

1. **Ruff lint issues** (9 fixable):
   - `apps/products/views.py`: I001 import sort
   - `apps/progress/services.py`: I001 import sort
   - `apps/project_workflow/tests/test_workflow_completed_signal.py`: I001, F401 (unused `pytest`, `WorkflowActionType`)
   - `tests/integration/test_cross_module_flow.py`: F401 (unused `Client`, `WorkflowService`, `Project`), I001

   **Impact**: Code quality only. No functional impact. Fixable with `ruff check --fix`.

### SUGGESTION

1. **pytest-env plugin**: The `pyproject.toml` configures `env = ["PYTEST_RUNNING=true"]` but `pytest-env` is not installed. Tests require manual `export PYTEST_RUNNING=true` or the conftest.py module-level set. Consider installing `pytest-env` for reliability.

## Risks

- **LOW**: Ruff warnings are cosmetic and easily fixed.
- **NONE**: All 891 regression tests pass. No functional regressions.
- **NONE**: All 35 new tests pass with correct assertions matching spec scenarios.

## Verdict

**PASS WITH WARNINGS**

All 5 functional requirements are implemented correctly per spec. All 14 tasks are complete. All 891 tests pass (35 new + 856 existing). Design decisions are followed. Two minor deviations are documented and justified (spec overrides design where they conflict).

The only issues are 9 ruff lint warnings (unused imports, import sort order) which are cosmetic and do not affect functionality.

## Next Recommended

1. Fix ruff warnings: `cd backend && ruff check --fix apps/ tests/`
2. Proceed to `sdd-archive` phase to sync delta specs into baseline.
