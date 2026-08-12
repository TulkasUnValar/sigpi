# Archive Report: Cross-Module Integration (SIGPI)

**Change**: `cross-module-integration`
**Archived on**: 2026-08-12
**Archive target**: `openspec/changes/archive/2026-08-12-cross-module-integration/`
**Persistence mode**: openspec (per `openspec/config.yaml` → `persistence: openspec`)

---

## Executive Summary

The SDD cycle for the `cross-module-integration` change is complete. All six phases — explore, propose, spec, design, tasks, apply — were executed under strict TDD (Red-Green-Refactor) within a single-PR delivery. The change wired SIGPI's 9 MVP modules for end-to-end flow using the hybrid pattern (Django signals for event notifications + service-level guards for hard validation constraints): 5 integration points (IP-1…IP-5), 0 schema changes, 0 migrations. Verification returned **PASS WITH WARNINGS** (no CRITICAL issues); the 9 cosmetic ruff lint warnings flagged in Round 1 were remediated before archive — 0 issues remain. The SDD cycle is closed.

## SDD Cycle Traceability

| Phase | Artifact | Location | Key Result |
|-------|----------|----------|------------|
| Explore | `exploration.md` | archived | Confirmed FK infrastructure already in place; 5 integration gaps identified; recommended Hybrid approach (signals + service guards); ~6-8 files, ~200-300 LOC |
| Propose | `proposal.md` | archived | Intent, in/out scope, 5 IP capabilities (1 new, 4 modified), risks, dependencies, success criteria |
| Spec | `spec.md` | archived + synced to main spec | 5 FRs (FR-001..FR-005), 3 BRs (BR-001..BR-003), 10 Given/When/Then scenarios, error-handling matrix, FSM interaction table |
| Design | `design.md` | archived | 5 architecture decisions (guard location, validation strategy, guard pattern, signal timing, MVP scope), data-flow diagrams, file-change table, interface contracts |
| Tasks | `tasks.md` | archived | 14 tasks across 4 phases; single-PR delivery; 400-line budget risk: Low |
| Apply | `apply-progress.md` | archived | Strict TDD Red-Green-Refactor per task; 35 new tests (6 test files); 21 files changed; 98% coverage |
| Verify | `verify-report.md` | archived | PASS WITH WARNINGS — 5/5 FRs verified, 5/5 design decisions MATCH, 891 tests pass, 0 CRITICAL; 9 ruff WARNINGs (cosmetic, fixed pre-archive) |
| Archive | `archive-report.md` | this file + Engram | SDD cycle closed |

## Task Completion Gate

**Status**: PASSED (no reconciliation needed)

The persisted `tasks.md` artifact shows ALL 14 tasks checked `- [x]` across all 4 phases:

| Phase | Tasks | Complete |
|-------|-------|----------|
| Phase 1: Regression Mitigation (Pre-Flight) | 2 | 2/2 |
| Phase 2: Signal Infrastructure (IP-1, IP-5) | 4 | 4/4 |
| Phase 3: Service Guards (IP-2, IP-3, IP-4) | 6 | 6/6 |
| Phase 4: Integration Test + Verification | 2 | 2/2 |
| **Total** | **14** | **14/14** |

No stale unchecked checkboxes. No exceptional reconciliation was required — `sdd-apply` correctly updated the persisted tasks artifact.

## Verification Gate

**Status**: PASSED — no CRITICAL issues, all WARNINGs remediated pre-archive

| Check | Result | Details |
|-------|--------|---------|
| Verdict | PASS WITH WARNINGS → remediated | Warnings fixed pre-archive; 0 issues remaining |
| CRITICAL issues | None | — |
| Tasks total / complete | 14 / 14 | All phases verified |
| FRs verified | 5 / 5 | FR-001, FR-002, FR-003, FR-004, FR-005 |
| Design decisions MATCH | 5 / 5 | All design decisions followed (2 documented & justified deviations) |
| Tests passing | 891 passed, 5 skipped, 0 failed | 35 new + 856 regression |
| Coverage | ~98% (well above 80% floor) | All affected modules ≥ 83% |
| ruff (post-remediation) | 0 errors, 0 warnings | 9 cosmetic issues from Round 1 fixed via `ruff check --fix` |
| mypy | NOT RUN | Infrastructure constraint (no Docker/PostgreSQL for full env) — non-blocking |

Per archive rules: archive NEVER proceeds with CRITICAL verification issues. This change has none. The only original issues were 9 cosmetic ruff warnings (unused imports / import sort order) with no functional impact; the orchestrator confirmed they were remediated before archive.

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| `cross-module-integration` | Created (new main spec) | Full spec (5 FRs, 3 BRs, 10 scenarios) copied to `openspec/specs/cross-module-integration/spec.md` — no pre-existing main spec existed |

The `cross-module-integration` change uses a flat spec layout (`openspec/changes/cross-module-integration/spec.md`). The spec is a self-contained capability spec for the cross-module integration layer (signals + service guards); it does NOT use formal `## ADDED Requirements` / `## MODIFIED Requirements` delta sections against existing domain specs. As such, the existing domain main specs (`calls`, `advances`, `products`, `reports`, `project_workflow`) were NOT modified — this change ADDED a new integration layer at the boundaries between modules rather than modifying the domain-level requirements of each module. The new main spec documents the cross-cutting behavior as a first-class capability.

## Verification Outcomes (Round 1, pre-remediation)

### New Tests (35 tests across 6 files)

| Test File | Tests | Result |
|-----------|-------|--------|
| `apps/calls/tests/test_signals.py` | 6 | PASSED |
| `apps/progress/tests/test_project_state_guard.py` | 9 | PASSED |
| `apps/products/tests/test_project_state_guard.py` | 9 | PASSED |
| `apps/reports/tests/test_entity_validation.py` | 7 | PASSED |
| `apps/project_workflow/tests/test_workflow_completed_signal.py` | 3 | PASSED |
| `tests/integration/test_cross_module_flow.py` | 1 | PASSED |

### Regression Suite

| Module Group | Tests | Passed | Failed | Skipped |
|--------------|-------|--------|--------|---------|
| calls + project_workflow + integration | 358 | 358 | 0 | 5 |
| progress + products + reports | 533 | 533 | 0 | 0 |
| **Total** | **891** | **891** | **0** | **5** |

### Spec Compliance Matrix (all PASS)

| FR | Scenario(s) | Implementation | Test Status |
|----|-------------|---------------|-------------|
| FR-001 | Signal emitted on transition / No signal on failed transition | `call_state_changed.send()` in `_log_transition()` inside `transaction.atomic()` | PASS |
| FR-002 | Progress created for executing project / Rejected for pre-approval | `PROGRESS_ALLOWED_PROJECT_STATES` + `_validate_project_state_for_progress()` in `ProgressService.create()` | PASS |
| FR-003 | Product created for approved project / Rejected for pre-approval | `PRODUCT_ALLOWED_PROJECT_STATES` + `PermissionDenied` guard in `perform_create()` | PASS |
| FR-004 | Valid entity / Unresolvable 404 / Cross-institution 403 | `ReportRenderer.validate_entity()` with standardized `{"detail": "..."}` errors | PASS |
| FR-005 | Signal emitted on workflow completion / No auto-transition in MVP | `workflow_completed.send()` in `complete_workflow()` with lazy import | PASS |

### Documented Deviations (justified, spec-authoritative)

1. **IP-5 lazy import**: Lazy import of `workflow_completed` inside `complete_workflow()` to avoid circular dependency. Documented in code comment at `apps/project_workflow/services.py:193`.
2. **IP-2 `cerrado` included**: Design interface section showed `PROGRESS_ALLOWED_PROJECT_STATES` without `cerrado`, but spec FR-002 and tasks 3.2 explicitly include `cerrado`. Implementation follows spec (authoritative).

## Files Changed (21 files)

| File | Action | What Was Done |
|------|--------|---------------|
| `apps/calls/signals.py` | Created | `call_state_changed = django.dispatch.Signal()` |
| `apps/calls/apps.py` | Modified | Added `ready()` importing signals |
| `apps/calls/services.py` | Modified | Added `call_state_changed.send()` in `_log_transition()` |
| `apps/calls/tests/test_signals.py` | Created | 6 signal emission tests |
| `apps/project_workflow/signals.py` | Modified | Added `workflow_completed` signal definition |
| `apps/project_workflow/services.py` | Modified | Added `workflow_completed.send()` in `complete_workflow()` with lazy import |
| `apps/project_workflow/tests/test_workflow_completed_signal.py` | Created | 3 workflow signal tests |
| `apps/progress/services.py` | Modified | Replaced `_validate_project_not_terminal` with `_validate_project_state_for_progress()` |
| `apps/progress/tests/test_project_state_guard.py` | Created | 9 progress guard tests |
| `apps/progress/tests/test_services.py` | Modified | Updated old terminal test to `rechazado` + new error message |
| `apps/progress/tests/test_views.py` | Modified | Changed `_make_project` default status to `"en_ejecucion"` |
| `apps/products/views.py` | Modified | Added `PRODUCT_ALLOWED_PROJECT_STATES` + guard in `perform_create()` |
| `apps/products/tests/test_project_state_guard.py` | Created | 9 product guard tests |
| `apps/products/tests/conftest.py` | Modified | `ProductFactory` project status override to `"aprobado"` |
| `apps/products/tests/test_views.py` | Modified | `_make_project` default status to `"aprobado"` |
| `apps/products/tests/test_edge_cases.py` | Modified | `_make_project` default status to `"aprobado"` |
| `apps/reports/services.py` | Modified | Added `validate_entity()` method to `ReportRenderer` |
| `apps/reports/views.py` | Modified | Delegated entity validation to `ReportRenderer.validate_entity()` |
| `apps/reports/tests/test_entity_validation.py` | Created | 7 entity validation tests |
| `tests/integration/test_cross_module_flow.py` | Created | 1 end-to-end integration test |
| `openspec/specs/cross-module-integration/spec.md` | Created (archive) | New main spec synced from change spec |

## Files Archived

| Artifact | Status |
|----------|--------|
| `exploration.md` | ✅ |
| `proposal.md` | ✅ |
| `spec.md` | ✅ (also synced to `openspec/specs/cross-module-integration/spec.md`) |
| `design.md` | ✅ |
| `tasks.md` | ✅ (14/14 tasks complete — no reconciliation needed) |
| `apply-progress.md` | ✅ |
| `verify-report.md` | ✅ |
| `archive-report.md` | ✅ (this file) |
| `README.md` | ✅ (final status pointer) |

## Engram Persistence

The archive report is persisted to Engram under `topic_key: sdd/cross-module-integration/archive-report` (with `capture_prompt: false` per SDD artifact convention). Observation ID is recorded in the Engram save response.

## Source of Truth Updated

The following main spec now reflects the implemented cross-module behavior:
- `openspec/specs/cross-module-integration/spec.md` (NEW — capability spec for the integration layer)

Existing domain main specs (`calls`, `advances`, `products`, `reports`, `project_workflow`) are unchanged — this change introduced an integration layer between them rather than modifying domain-level requirements.

## Risks

- **LOW — Lazy import pattern (IP-5)**: `workflow_completed` is imported lazily inside `complete_workflow()` to avoid circular dependency. This is a documented deviation with an inline code comment; the pattern is safe but worth noting for future maintainers adding receivers.
- **NONE — Regression**: All 891 affected-module tests pass. Factory defaults were updated in Phase 1 before guards landed, preventing test breakage.
- **NONE — Coverage**: ~98% coverage across all affected modules, well above the 80% threshold.
- **NON-BLOCKING — mypy NOT RUN**: Full type-check requires Docker/PostgreSQL environment unavailable in the archive environment. Apply-progress and verify-report confirm functional correctness; mypy should be run in a complete staging environment but is not a blocking gate for this change.

## SDD Cycle Complete

The `cross-module-integration` change has been fully planned, implemented, verified, and archived. Ready for the next change.

## Next Recommended

`end` — the SDD cycle for `cross-module-integration` is closed.