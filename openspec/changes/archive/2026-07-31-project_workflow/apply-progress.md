# Apply Progress: project_workflow (SIGPI §6.5)

## Phase 1: Foundation — COMPLETE ✅

**What**: Implemented Phase 1 (Foundation) — created app skeleton, 4 models with constraints/indexes, 2 migrations (initial + RLS), signal definition, factory fixtures, and 32 TDD model/signal/factory tests.

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

**What**: Implemented Phase 2 (Core Services + Signal Receiver) — created WorkflowService, WorkflowTemplateService, signal receiver, permissions, signal emission in projects/services.py, and 52 TDD tests.

**Where**:
- `backend/apps/project_workflow/services.py`
- `backend/apps/project_workflow/permissions.py`
- `backend/apps/project_workflow/signals.py` (modified: added receiver)
- `backend/apps/project_workflow/apps.py` (modified: added ready() import)
- `backend/apps/project_workflow/tests/test_services.py`
- `backend/apps/project_workflow/tests/test_signals.py`
- `backend/apps/project_workflow/tests/test_permissions.py`
- `backend/apps/projects/services.py` (modified: signal emission + transaction.atomic())

### TDD Cycle Evidence (Phase 2)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1-2.2 | `test_services.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 8 cases | ✅ Clean |
| 2.3-2.8 | `test_services.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 15 cases | ✅ Clean |
| 2.9 | `test_signals.py` | Integration | ✅ 32/32 | ✅ Written | ✅ Passed | ✅ 7 cases | ✅ Clean |
| 2.10 | `test_signals.py` | Integration | ✅ 40/40 | ✅ Written | ✅ Passed | ✅ 2 cases | ✅ Clean |
| 3.2 (moved) | `test_permissions.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 5 cases | ✅ Clean |

## Phase 3: API Layer + Integration Tests — COMPLETE ✅

**What**: Implemented Phase 3 (API Layer + Integration Tests) — created 6 serializers, WorkflowInstanceFilter, 3 ViewSets with action endpoints, DefaultRouter + nested action URLs, and 56 TDD tests across serializers, views, filters, and RLS.

**Where**:
- `backend/apps/project_workflow/serializers.py` — NEW
- `backend/apps/project_workflow/filters.py` — NEW
- `backend/apps/project_workflow/views.py` — NEW
- `backend/apps/project_workflow/urls.py` — MODIFIED (replaced placeholder with routes)
- `backend/config/middleware/tenant.py` — MODIFIED (added `/api/workflows/` to tenant prefixes)
- `backend/apps/project_workflow/permissions.py` — MODIFIED (fixed UUID type mismatch in `_resolve_center_id`)
- `backend/apps/project_workflow/tests/test_serializers.py` — NEW
- `backend/apps/project_workflow/tests/test_views.py` — NEW
- `backend/apps/project_workflow/tests/test_filters.py` — NEW
- `backend/apps/project_workflow/tests/test_rls.py` — NEW
- `backend/apps/project_workflow/tests/test_permissions.py` — MODIFIED (fixed mock to use UUID objects)

### TDD Cycle Evidence (Phase 3)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `test_serializers.py` | Unit | ✅ 40/40 | ✅ Written | ✅ Passed | ✅ 14 cases | ✅ Clean |
| 3.3 | `test_filters.py` | Unit | ✅ 54/54 | ✅ Written | ✅ Passed | ✅ 9 cases | ✅ Clean |
| 3.4-3.5 | `test_views.py` | Integration | ✅ 63/63 | ✅ Written | ✅ Passed | ✅ 18 cases | ✅ Clean |
| 3.10 | `test_rls.py` | Unit + E2E | ✅ 81/81 | ✅ Written | ✅ Passed | ✅ 15 cases | ✅ Clean |

### Test Summary
- **Total tests written**: 56 (Phase 3) + 52 (Phase 2) + 32 (Phase 1) = 140 project_workflow tests
- **Total tests passing**: 143/143 (includes 3 new tests added in this batch)
- **Layers used**: Unit (110), Integration (28), E2E (5)
- **Approval tests** (refactoring): 1 — fixed `_resolve_center_id` UUID type mismatch
- **Pure functions created**: 2 (`get_step_count` serializer method, `filter_overdue` filter method)

### Deviations from Design
1. **URLs use `api/templates/` not `api/workflows/templates/`**: The `config/urls.py` include is at `api/`, so router-registered paths are `api/templates/` and `api/instances/`. The design spec mentioned `/workflows/templates/` but the config wiring makes it `/api/templates/`. This is consistent with other modules (projects uses `/api/projects/`, not `/api/workflows/projects/`).
2. **DefaultRouter instead of SimpleRouter**: Task explicitly requested DefaultRouter, which adds an API root view. This is a minor deviation from the projects module pattern (which uses SimpleRouter).
3. **`_resolve_center_id` return type**: Changed from `str(project.center_id)` to `project.center_id` (UUID object) to match real Django `values_list("id", flat=True)` behavior. This fixes a type mismatch that caused permission checks to fail in real requests while mock tests passed.

### Issues Found
- **Issue-01**: `HasRoleLevelOrHigher` is a utility class, not a `BasePermission` — cannot be instantiated with `()`. Must use `IsInstitutionAdmin()`, `IsCenterDirector()`, etc. Fixed in `views.py`.
- **Issue-02**: `IsWorkflowStepApprover._resolve_center_id()` returned `str(UUID)` while `membership.centers.values_list("id", flat=True)` returns UUID objects. This caused all real center-director permission checks to fail silently. Fixed by returning the raw UUID.
- **Issue-03**: Django/Python 3.14 template rendering bug on 404 pages (`copy(context)` fails). Avoided by using `reverse()` instead of hardcoded URLs in tests.

### Remaining Tasks
None — all 19 Phase 1+2+3 tasks are complete.

### Workload / PR Boundary
- Mode: feature-branch-chain
- Current work unit: PR 3 — Phase 3: API Layer + Integration Tests
- Boundary: Serializers, filters, ViewSets, URLs, admin verify, and all associated integration tests
- Estimated review budget impact: ~600 changed lines (above 400-line budget, PR 3 is the final slice)

### Status
19/19 tasks complete across all 3 phases. 143/143 tests passing. Ready for verify.
