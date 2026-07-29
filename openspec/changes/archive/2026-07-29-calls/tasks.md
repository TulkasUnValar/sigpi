# Tasks: Calls / Convocatorias Module (SIGPI §6.8)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1200-1500 (23 new files, 2 modified, 9 test files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Services) → PR 3 (API + Integration) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models, migrations, RLS, app config + tests | PR 1 | Base: feature/calls-tracker; ~320 lines; tests included |
| 2 | Services (CallService, CallDocumentService, CallProjectService) + tests | PR 2 | Base: PR 1 branch; ~270 lines; depends on PR 1 |
| 3 | API layer (ViewSets, serializers, permissions, filters, URLs) + integration tests | PR 3 | Base: PR 2 branch; ~600+ lines; depends on PR 2 |

## Phase 1: Foundation (Models, Migrations, Config)

- [x] 1.1 Create `backend/apps/calls/__init__.py`, `apps.py` (AppConfig name="apps.calls")
- [x] 1.2 Create `backend/apps/calls/models.py` with enums (CallStatus, CallType, CallDocumentType) and 4 models: Call (6-state FSM, 4 nullable dates, CHECK constraints), CallDocument, CallProject (UniqueConstraint), CallStateLog
- [x] 1.3 Add FSM `@transition` decorators to Call model (open_call, close_call, start_evaluation, publish_results, archive)
- [x] 1.4 Create `backend/apps/calls/migrations/__init__.py` and `0001_initial.py` (4 tables, constraints, indexes)
- [x] 1.5 Create `backend/apps/calls/migrations/0002_rls_policies.py` (RLS on all 4 tables, tenant_isolation + superadmin_bypass)
- [x] 1.6 Modify `backend/config/settings.py`: add `"apps.calls"` to INSTALLED_APPS
- [x] 1.7 Create `backend/apps/calls/tests/__init__.py`, `conftest.py` (CallFactory, CallDocumentFactory, CallProjectFactory, state fixtures)
- [x] 1.8 Write `backend/apps/calls/tests/test_models.py`: model constraints, clean() validation, FSM transitions (RED→GREEN)
- [x] 1.9 Write `backend/apps/calls/tests/test_rls.py`: RLS tenant isolation (PostgreSQL only)

## Phase 2: Core Services

- [x] 2.1 Create `backend/apps/calls/services.py` with CallService (CRUD + 6 FSM methods using select_for_update + _log_transition)
- [x] 2.2 Add CallDocumentService (add, update, remove with terminal state guard)
- [x] 2.3 Add CallProjectService (link with state guard abierta-only, unlink)
- [x] 2.4 Write `backend/apps/calls/tests/test_services.py`: service methods, select_for_update, audit logging, guards (RED→GREEN)

## Phase 3: API Layer + Integration

- [x] 3.1 Create `backend/apps/calls/serializers.py` with 6 serializers (CallListSerializer, CallSerializer, CallDocumentSerializer, CallProjectSerializer, CallProjectCreateSerializer, CallStateLogSerializer)
- [x] 3.2 Create `backend/apps/calls/permissions.py` with CanManageCall (object-level institution check)
- [x] 3.3 Create `backend/apps/calls/filters.py` with CallFilter (status, call_type, title search, date ranges)
- [x] 3.4 Create `backend/apps/calls/views.py` with 4 ViewSets (CallViewSet + 5 FSM @actions, CallDocumentViewSet, CallProjectViewSet, CallStateLogViewSet)
- [x] 3.5 Create `backend/apps/calls/urls.py` with router + nested routes (documents, projects, state_history)
- [x] 3.6 Create `backend/apps/calls/admin.py` with model registration
- [x] 3.7 Modify `backend/config/urls.py`: add calls URL include at `/api/calls/`
- [x] 3.8 Write `backend/apps/calls/tests/test_serializers.py`: validation rules (type/entity, date ordering)
- [x] 3.9 Write `backend/apps/calls/tests/test_permissions.py`: role checks, institution match
- [x] 3.10 Write `backend/apps/calls/tests/test_views.py`: endpoint integration (CRUD + FSM + nested routes + filtering + errors)
- [x] 3.11 Write `backend/apps/calls/tests/test_filters.py`: filter correctness (all dimensions)
- [x] 3.12 Write `backend/apps/calls/tests/test_urls.py`: URL resolution

## Implementation Order

Phase 1 → Phase 2 → Phase 3 (strict dependency order). Each phase includes tests. Strict TDD: write failing test first, then minimal implementation, then refactor.

## PR Boundaries (Feature Branch Chain)

**PR 1** (Phase 1): Targets `feature/calls-tracker`. Delivers models, migrations, RLS, app config, model tests. ~320 lines.
**PR 2** (Phase 2): Targets PR 1 branch. Delivers services + service tests. ~270 lines.
**PR 3** (Phase 3): Targets PR 2 branch. Delivers API layer + integration tests. ~600+ lines.

Only `feature/calls-tracker` merges to main after all 3 PRs are reviewed.
