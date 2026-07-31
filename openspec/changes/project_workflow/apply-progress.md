# Apply Progress: project_workflow (SIGPI §6.5)

## Phase 1: Foundation — COMPLETE ✅

**What**: Implemented Phase 1 (Foundation) of the project_workflow change for SIGPI §6.5 — created app skeleton, 4 models with constraints/indexes, 2 migrations (initial + RLS), signal definition, factory fixtures, and 32 TDD model/signal/factory tests.

**Where**:
- `backend/apps/project_workflow/__init__.py`
- `backend/apps/project_workflow/apps.py`
- `backend/apps/project_workflow/models.py`
- `backend/apps/project_workflow/admin.py`
- `backend/apps/project_workflow/signals.py`
- `backend/apps/project_workflow/urls.py`
- `backend/apps/project_workflow/migrations/0001_initial.py`
- `backend/apps/project_workflow/migrations/0002_rls_policies.py`
- `backend/apps/project_workflow/tests/conftest.py`
- `backend/apps/project_workflow/tests/test_models.py`
- `backend/config/settings/base.py`
- `backend/config/urls.py`

## Phase 2: Core Services + Signal Integration — COMPLETE ✅

**What**: Implemented Phase 2 (Core Services + Signal Receiver) of the project_workflow change — created WorkflowService, WorkflowTemplateService, signal receiver, permissions, signal emission in projects/services.py, and 52 TDD tests.

**Where**:
- `backend/apps/project_workflow/services.py` — NEW
- `backend/apps/project_workflow/permissions.py` — NEW
- `backend/apps/project_workflow/signals.py` — MODIFIED (added receiver)
- `backend/apps/project_workflow/apps.py` — MODIFIED (added ready() import)
- `backend/apps/project_workflow/tests/test_services.py` — NEW
- `backend/apps/project_workflow/tests/test_signals.py` — NEW
- `backend/apps/project_workflow/tests/test_permissions.py` — NEW
- `backend/apps/projects/services.py` — MODIFIED (signal emission + transaction.atomic())

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1-2.2 | `test_services.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 8 cases | ✅ Clean |
| 2.3-2.8 | `test_services.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 15 cases | ✅ Clean |
| 2.9 | `test_signals.py` | Integration | ✅ 32/32 | ✅ Written | ✅ Passed | ✅ 7 cases | ✅ Clean |
| 2.10 | `test_signals.py` | Integration | ✅ 40/40 | ✅ Written | ✅ Passed | ✅ 2 cases | ✅ Clean |
| 3.2 (moved) | `test_permissions.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 5 cases | ✅ Clean |

### Test Summary
- **Total tests written**: 52 (Phase 2) + 32 (Phase 1) = 84 project_workflow tests
- **Total tests passing**: 84/84
- **Layers used**: Unit (72), Integration (12), E2E (0)
- **Approval tests** (refactoring): None — no refactoring tasks
- **Pure functions created**: 2 (`validate_step_order`, `annotate_overdue`)

### Deviations from Design
1. **Minimum-data fields**: Prompt asked to check all 8 fields (title, abstract, objectives, methodology, expected_results, keywords, center, PI). Design.md only listed 3 (methodology, objectives, expected_results). Implemented all 8 per prompt, but removed tests for `center` and `PI` since those are DB-level NOT NULL and can never be empty in practice.
2. **`borrador` from `observado`**: Prompt said "reset to first step" for `borrador` from `observado`. Spec and design do not mention this — resubmit goes to `enviado`, not `borrador`. Skipped this case; no test covers it.
3. **`rechazado` handling**: Prompt said "mark instance cancelled" for `rechazado`. Design/spec say `status=rejected`. Implemented `reject()` with `status=rejected` per design.
4. **`advance_step` / `complete_workflow`**: Prompt introduced these as separate methods not in design.md. Implemented them as granular decomposition that maps to design's `approve()` in single-step workflow.

### Issues Found
- None — all tests pass, no regressions in existing projects tests (275 passed).

### Remaining Tasks (Phase 3)
- [ ] 3.1 Serializers (6 serializers)
- [ ] 3.3 Filters
- [ ] 3.4 ViewSets + action endpoints
- [ ] 3.5 URLs
- [ ] 3.6 Admin registration
- [ ] 3.7-3.10 API/integration tests

### Workload / PR Boundary
- Mode: feature-branch-chain
- Current work unit: PR 2 — Phase 2: Core Services + Signal Receiver
- Boundary: Services, signals, permissions, and all associated tests
- Estimated review budget impact: ~380 lines (within 400-line budget per task forecast)

### Status
10/10 Phase 2 tasks complete. 1/10 Phase 3 tasks complete (permissions moved forward). Ready for verify.
