# Tasks: Project Workflow — Approval Flow (SIGPI §6.5)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1500-1800 (25 new files, 3 modified, 9 test files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Core Services + Signals) → PR 3 (API + Integration) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models, migrations, RLS, app config, signal definition, fixtures | PR 1 | Base: feature/workflow-tracker; ~350 lines; tests included |
| 2 | WorkflowService, WorkflowTemplateService, signal receiver, permissions + tests | PR 2 | Base: PR 1 branch; ~380 lines; depends on PR 1 |
| 3 | Serializers, ViewSets, URLs, filters, admin, integration tests | PR 3 | Base: PR 2 branch; ~750+ lines; depends on PR 2 |

## Phase 1: Foundation (Models, Migrations, Config)

- [x] 1.1 Create `apps/project_workflow/__init__.py`, `apps.py` (AppConfig name="apps.project_workflow")
- [x] 1.2 Create `apps/project_workflow/models.py` with 3 enums (WorkflowInstanceStatus, WorkflowActionType, StepRole) and 4 models: WorkflowTemplate (FK institution/center, UniqueConstraint institution+name), WorkflowStep (FK template, order, deadline_days CHECK >0), WorkflowInstance (FK project/template/current_step, denormalized institution, status, deadline_date, partial unique index active per project), WorkflowAction (FK instance/step/acted_by, append-only, JSONField metadata)
- [x] 1.3 Create `apps/project_workflow/migrations/__init__.py` and `0001_initial.py` (4 tables, constraints, indexes)
- [x] 1.4 Create `apps/project_workflow/migrations/0002_rls_policies.py` (RLS on all 4 tables — parent via institution_id, child via FK subquery)
- [x] 1.5 Modify `config/settings/base.py`: add `"apps.project_workflow"` to INSTALLED_APPS
- [x] 1.6 Modify `config/urls.py`: add `path("api/workflows/", include("apps.project_workflow.urls"))`
- [x] 1.7 Create `apps/project_workflow/signals.py` with `project_state_changed = django.dispatch.Signal()` (provides: project, from_state, to_state, triggered_by) — **note**: placed in `project_workflow` (not `projects`) per constraint to avoid modifying archived projects module
- [x] 1.8 Create `apps/project_workflow/tests/__init__.py`, `conftest.py` (WorkflowTemplateFactory, WorkflowStepFactory, WorkflowInstanceFactory, WorkflowActionFactory)
- [x] 1.9 Write `apps/project_workflow/tests/test_models.py`: model constraints, clean() validation, UniqueConstraint, append-only guard, TextChoices defaults (RED→GREEN)

## Phase 2: Core Services + Signal Integration

- [x] 2.1 Create `apps/project_workflow/services.py` with `WorkflowService.create_instance()` — idempotent (WR-001), find active template for center/institution, set current_step=first step, compute deadline_date (WR-005), create WorkflowAction(create)
- [x] 2.2 Add `WorkflowService.check_minimum_data()` — raise ValidationError if methodology/objectives/expected_results empty (CA-005, WR-004)
- [x] 2.3 Add `WorkflowService.approve()` — select_for_update + check_minimum_data guard + WorkflowAction(approve) + status=completed + AuditEvent
- [x] 2.4 Add `WorkflowService.observe()` — select_for_update + WorkflowAction(observe, observation_text) + status=observed
- [x] 2.5 Add `WorkflowService.reject()` — select_for_update + WorkflowAction(reject, reason) + status=rejected
- [x] 2.6 Add `WorkflowService.reset_instance()` — observed→pending + WorkflowAction(resubmit); `cancel_instance()` — status=cancelled
- [x] 2.7 Add `WorkflowService.annotate_overdue()` — is_overdue annotation: deadline_date < now AND status=pending
- [x] 2.8 Add `WorkflowTemplateService` — create (template+steps atomically), update, delete (reject if active instances)
- [x] 2.9 Create `apps/project_workflow/signals.py` with `on_project_state_change` receiver: submit→create_instance, resubmit→reset_instance, terminal→cancel_instance
- [x] 2.10 Modify `apps/projects/services.py`: emit `project_state_changed.send()` at end of `_log_transition()`, wrap FSM callers in `transaction.atomic()` (WR-007)

## Phase 3: API Layer + Integration Tests

- [x] 3.1 Create `apps/project_workflow/serializers.py` with 6 serializers: WorkflowTemplateListSerializer, WorkflowTemplateSerializer (nested steps read/write), WorkflowStepSerializer, WorkflowInstanceSerializer (nested actions, is_overdue), WorkflowInstanceListSerializer, WorkflowActionSerializer (create-only, RO instance/step/acted_by)
- [x] 3.2 Create `apps/project_workflow/permissions.py` with `IsWorkflowStepApprover` — reuses IsCenterDirectorForProject logic, admin+ bypass (completed in Phase 2)
- [x] 3.3 Create `apps/project_workflow/filters.py` with `WorkflowInstanceFilter` (project, status, center, overdue boolean method filter)
- [x] 3.4 Create `apps/project_workflow/views.py` with WorkflowTemplateViewSet (ModelViewSet, admin+ only), WorkflowInstanceViewSet (list/retrieve + @action approve/observe/reject), WorkflowActionViewSet (create+list only, no update/delete → 405)
- [x] 3.5 Create `apps/project_workflow/urls.py` with DefaultRouter + action paths
- [x] 3.6 Create `apps/project_workflow/admin.py` with model registration
- [x] 3.7 Write `apps/project_workflow/tests/test_services.py`: all WorkflowService methods, idempotency (WR-001), minimum-data guard (WR-004), select_for_update, annotate_overdue with freezegun (RED→GREEN)
- [x] 3.8 Write `apps/project_workflow/tests/test_signals.py`: signal flow submit→create, resubmit→reset, terminal→cancel, atomicity rollback (WR-007)
- [x] 3.9 Write `apps/project_workflow/tests/test_views.py`: endpoint CRUD + actions + filtering + permission matrix + 405 on action update/delete (WF-006)
- [x] 3.10 Write `apps/project_workflow/tests/test_serializers.py`, `test_permissions.py`, `test_filters.py`, `test_rls.py`

## Implementation Order

Phase 1 → Phase 2 → Phase 3 (strict dependency order). Strict TDD: write failing test first per service method, then minimal implementation, then refactor. Signal integration tasks (2.9-2.10) come after services so receiver can call WorkflowService directly.

## PR Boundaries (Feature Branch Chain — pending user decision)

**PR 1** (Phase 1): Targets `feature/workflow-tracker`. Delivers models, migrations, RLS, config, signal definition, model tests. ~350 lines.
**PR 2** (Phase 2): Targets PR 1 branch. Delivers services + signal receiver + permissions + service/signal tests. ~380 lines.
**PR 3** (Phase 3): Targets PR 2 branch. Delivers API layer + integration tests. ~750+ lines.

Only `feature/workflow-tracker` merges to main after all 3 PRs are reviewed.
