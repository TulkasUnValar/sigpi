# Design: Project Workflow — Approval Flow (SIGPI §6.5)

## Technical Approach

Thin approval-workflow layer as a new Django app (`apps/project_workflow/`) sitting **on top of** the archived projects module. Integration is signal-based: `ProjectService._log_transition()` emits a `project_state_changed` Django signal; a receiver in `project_workflow/signals.py` creates/resets/cancels `WorkflowInstance` rows. Zero schema changes to the Project model. The workflow module is a leaf dependency — no downstream modules depend on it.

Spec reference: `openspec/changes/project_workflow/spec.md` (8 requirements, 7 business rules).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|-------------|-----------|
| ADR-1 | Project reference | FK → Project (`CASCADE`) | CharField UUID, GenericFK | Spec mandates FK; one-way dependency (workflow→projects) is safe; signals handle reverse direction |
| ADR-2 | FSM integration | Django `Signal` emitted from `_log_transition()` | django-fsm `post_transition` signal, direct import | Loose coupling; projects module unaware of workflow internals; `post_transition` from django-fsm lacks `triggered_by` context |
| ADR-3 | Atomicity | Wrap `_log_transition` callers in `transaction.atomic()` | Separate transactions, saga pattern | Spec WR-007 mandates atomicity; signal receiver + FSM transition roll back together on failure |
| ADR-4 | Model base class | Standalone models with `institution` FK | Inherit `InstitutionScopedModel` | InstitutionScopedModel carries `code`, `name`, `description`, 3-state FSM — none apply to workflow entities |
| ADR-5 | Service layer style | Static methods on `WorkflowService` | Instance methods, Django Manager | Matches `ProjectService` / `CallService` pattern exactly |
| ADR-6 | Minimum-data guard | Called inside workflow approve action (not FSM transition) | Guard inside Project.approve() | Keeps workflow logic in workflow module; projects module unchanged |
| ADR-7 | Workflow status FSM | Plain `CharField` with `TextChoices` (no django-fsm) | django-fsm `FSMField` | Workflow has 5 simple statuses, no complex transition guards; TextChoices is lighter and sufficient |

## Clean Architecture Layer Mapping

```
Entities (business rules, framework-free)
├── WorkflowInstanceStatus (TextChoices: pending, completed, observed, rejected, cancelled)
├── WorkflowActionType (TextChoices: create, approve, observe, reject, resubmit, cancel)
├── StepRole (TextChoices: center_director)
└── MINIMUM_DATA_FIELDS = {"methodology", "objectives", "expected_results"}

Use Cases (application rules)
├── WorkflowService — create_instance, approve, observe, reject, reset, cancel
├── WorkflowTemplateService — CRUD templates with steps
└── check_minimum_data(project) — pre-guard for approve

Interface Adapters (controllers, presenters, gateways)
├── WorkflowTemplateViewSet — ModelViewSet (CRUD)
├── WorkflowInstanceViewSet — list, retrieve + 3 action endpoints
├── WorkflowActionViewSet — create-only + list by instance
├── Serializers: Template, Step, Instance, Action (6 total)
├── WorkflowInstanceFilter — django-filter FilterSet
└── Permission: IsWorkflowStepApprover (reuses IsCenterDirectorForProject)

Frameworks & Drivers
├── Django ORM models (4 tables)
├── Signal receiver (project_state_changed)
├── RLS migration (0002_rls_policies.py)
├── URL routing (urls.py)
└── AppConfig (apps.py)
```

## Data Flow

```
PI submits Project
    │
    ▼
ProjectService.submit() ──→ project.submit() + save()
    │
    ▼
transaction.atomic() {
    _log_transition() ──→ ProjectStateLog + AuditEvent
                        ──→ project_state_changed.send()
                                │
                                ▼
                    signal receiver (project_workflow/signals.py)
                        ──→ WorkflowService.create_instance(project)
                            ├── find active WorkflowTemplate for center
                            ├── create WorkflowInstance (status=pending)
                            ├── set current_step = first WorkflowStep
                            ├── compute deadline_date = now + step.deadline_days
                            └── WorkflowAction(action=create)
}
    │
    ▼
Director approves
    │
    ▼
WorkflowService.approve(instance, user)
    ├── check_minimum_data(project) — guard
    ├── select_for_update() on instance
    ├── WorkflowAction(action=approve)
    ├── instance.status = completed
    └── AuditEventEmitter("WORKFLOW_ACTION_TAKEN")
```

## Data Model

### WorkflowTemplate (`project_workflow_workflowtemplate`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `institution` | FK → Institution | `CASCADE`, `related_name="workflow_templates"` |
| `center` | FK → ResearchCenter | `SET_NULL, null=True, blank=True` |
| `name` | CharField(100) | required |
| `description` | TextField | `blank=True` |
| `is_active` | BooleanField | `default=True` |
| `created_at` | DateTimeField | `auto_now_add` |
| `updated_at` | DateTimeField | `auto_now` |

**Constraints**: `UniqueConstraint(institution, name)`.
**Indexes**: `(institution, is_active)`.

### WorkflowStep (`project_workflow_workflowstep`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `template` | FK → WorkflowTemplate | `CASCADE`, `related_name="steps"` |
| `order` | PositiveIntegerField | required |
| `name` | CharField(100) | required |
| `description` | TextField | `blank=True` |
| `role_required` | CharField(30) | `choices=StepRole`, `default="center_director"` |
| `deadline_days` | PositiveIntegerField | `default=15`; CHECK `> 0` |

**Constraints**: `UniqueConstraint(template, order)`.

### WorkflowInstance (`project_workflow_workflowinstance`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `project` | FK → Project | `CASCADE`, `related_name="workflow_instances"` |
| `institution` | FK → Institution | `CASCADE` (denormalized for RLS) |
| `template` | FK → WorkflowTemplate | `PROTECT` |
| `current_step` | FK → WorkflowStep | `SET_NULL, null=True` |
| `status` | CharField(20) | `choices=WorkflowInstanceStatus`, `default="pending"` |
| `deadline_date` | DateTimeField | `null=True` |
| `completed_at` | DateTimeField | `null=True` |
| `created_at` | DateTimeField | `auto_now_add` |
| `updated_at` | DateTimeField | `auto_now` |

**Constraints**: Partial unique index — one active (`pending`/`observed`) instance per project.
**Indexes**: `(institution, status)`, `(project, status)`, `(deadline_date)`.

### WorkflowAction (`project_workflow_workflowaction`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `instance` | FK → WorkflowInstance | `CASCADE`, `related_name="actions"` |
| `step` | FK → WorkflowStep | `SET_NULL, null=True` |
| `action` | CharField(20) | `choices=WorkflowActionType` |
| `acted_by` | FK → User | `SET_NULL, null=True` |
| `observation_text` | TextField | `blank=True` |
| `metadata` | JSONField | `null=True, blank=True` |
| `created_at` | DateTimeField | `auto_now_add` |

**Append-only**: no update/delete endpoints (WR-002).
**Indexes**: `(instance, -created_at)`.

## Service Layer

### WorkflowService

```python
class WorkflowService:
    @staticmethod
    def create_instance(project) -> WorkflowInstance:
        """Idempotent: skip if active instance exists (WR-001).
        Find active template for project's center/institution.
        Set current_step = first step, compute deadline_date."""

    @staticmethod
    def approve(instance, user) -> WorkflowInstance:
        """Pre-guard: check_minimum_data(project).
        select_for_update + create WorkflowAction(approve) + status=completed."""

    @staticmethod
    def observe(instance, user, observation_text) -> WorkflowInstance:
        """select_for_update + create WorkflowAction(observe) + status=observed."""

    @staticmethod
    def reject(instance, user, reason) -> WorkflowInstance:
        """select_for_update + create WorkflowAction(reject) + status=rejected."""

    @staticmethod
    def reset_instance(instance, user) -> WorkflowInstance:
        """Resubmit: observed → pending + WorkflowAction(resubmit)."""

    @staticmethod
    def cancel_instance(instance, user) -> WorkflowInstance:
        """Terminal project states → status=cancelled."""

    @staticmethod
    def check_minimum_data(project) -> None:
        """Raise ValidationError if methodology/objectives/expected_results empty."""

    @staticmethod
    def annotate_overdue(qs):
        """Add is_overdue annotation: deadline_date < now AND status=pending."""
```

### WorkflowTemplateService

```python
class WorkflowTemplateService:
    @staticmethod
    def create(institution, name, steps_data, center=None) -> WorkflowTemplate:
        """Create template + ordered WorkflowStep rows atomically."""

    @staticmethod
    def update(template, **data) -> WorkflowTemplate: ...

    @staticmethod
    def delete(template) -> None:
        """Reject if active instances reference this template."""
```

## Signal Integration

### Signal Definition (`apps/projects/signals.py` — NEW file)

```python
import django.dispatch

project_state_changed = django.dispatch.Signal()
# Provides: project, from_state, to_state, triggered_by
```

### Signal Emission (`apps/projects/services.py` — MODIFY `_log_transition`)

Add at end of `_log_transition()`:
```python
from apps.projects.signals import project_state_changed
project_state_changed.send(
    sender=Project,
    project=project,
    from_state=from_state,
    to_state=to_state,
    triggered_by=user,
)
```

Wrap each FSM method in `ProjectService` with `transaction.atomic()` to ensure signal receiver + FSM transition are atomic (WR-007).

### Signal Receiver (`apps/project_workflow/signals.py`)

```python
@receiver(project_state_changed)
def on_project_state_change(sender, project, from_state, to_state, triggered_by, **kwargs):
    if to_state == "enviado" and from_state == "borrador":
        WorkflowService.create_instance(project)           # submit
    elif to_state == "enviado" and from_state == "observado":
        instance = WorkflowInstance.objects.filter(
            project=project, status__in=["observed", "pending"]
        ).first()
        if instance:
            WorkflowService.reset_instance(instance, triggered_by)  # resubmit
    elif to_state in ("rechazado", "cancelado", "cerrado"):
        instance = WorkflowInstance.objects.filter(
            project=project, status__in=["pending", "observed"]
        ).first()
        if instance:
            WorkflowService.cancel_instance(instance, triggered_by)  # terminal
```

## API Layer

### ViewSets

| ViewSet | Base | Actions | Notes |
|---------|------|---------|-------|
| `WorkflowTemplateViewSet` | `ModelViewSet` | CRUD | Nested steps via writable serializer |
| `WorkflowInstanceViewSet` | `GenericViewSet` + mixins | list, retrieve + `@action` approve/observe/reject | No create (signal-driven) |
| `WorkflowActionViewSet` | `CreateModelMixin` + `ListModelMixin` + `GenericViewSet` | create, list | Append-only; no update/delete (405) |

### Serializers (6)

| Serializer | Fields | Notes |
|-----------|--------|-------|
| `WorkflowTemplateListSerializer` | id, name, center, is_active, step_count | Lightweight list |
| `WorkflowTemplateSerializer` | All + nested steps (read/write) | Create/update with nested steps |
| `WorkflowStepSerializer` | id, order, name, role_required, deadline_days | Nested in template |
| `WorkflowInstanceSerializer` | All + is_overdue annotation + actions[] (read-only nested) | Detail includes action history |
| `WorkflowInstanceListSerializer` | id, project, status, deadline_date, is_overdue, current_step | Lightweight list |
| `WorkflowActionSerializer` | instance (RO from URL), step (RO), action, observation_text, acted_by (RO) | Create-only |

### URL Routes

```
/api/workflows/templates/                              GET, POST
/api/workflows/templates/{id}/                         GET, PATCH, DELETE
/api/workflows/instances/                              GET
/api/workflows/instances/{id}/                         GET
/api/workflows/instances/{id}/approve/                 POST
/api/workflows/instances/{id}/observe/                 POST  (body: observation_text)
/api/workflows/instances/{id}/reject/                  POST  (body: reason)
/api/workflows/instances/{id}/actions/                 GET, POST
```

### Filtering (`WorkflowInstanceFilter`)

| Filter | Type | Field |
|--------|------|-------|
| `project` | UUIDFilter | `project_id` |
| `status` | ChoiceFilter | `status` |
| `center` | UUIDFilter | `project__center_id` |
| `overdue` | BooleanFilter | Method filter: `deadline_date < now AND status=pending` |

## Security & Permissions

| Action | Permission Classes |
|--------|-------------------|
| Template CRUD | `IsAuthenticated`, `HasRoleLevelOrHigher(2)` (Admin+) |
| Instance list/retrieve | `IsAuthenticated` (RLS + queryset filtering) |
| Approve/Observe/Reject | `IsAuthenticated`, `IsWorkflowStepApprover` |

**`IsWorkflowStepApprover`** (new): Reuses `IsCenterDirectorForProject` logic — checks user's center membership against `instance.project.center_id`. Admin+ (level ≤ 2) bypasses.

**RLS**: Same pattern as projects — parent table (`workflowtemplate`, `workflowinstance`) with direct `institution_id`; child tables (`workflowstep`, `workflowaction`) via FK subquery.

## Migration Plan

| Migration | Depends On | Content |
|-----------|-----------|---------|
| `0001_initial.py` | `projects.0001`, `institutions.0001`, `accounts.0001` | 4 tables, constraints, indexes |
| `0002_rls_policies.py` | `0001_initial` | RLS on 4 tables |

### Config changes
- Add `"apps.project_workflow"` to `INSTALLED_APPS`
- Add `path("api/workflows/", include("apps.project_workflow.urls"))` to `config/urls.py`
- New file: `apps/projects/signals.py` (signal definition)
- Modify: `apps/projects/services.py` (signal emission + `transaction.atomic()`)
- Add workflow event types to `AuditEventType` enum or pass as strings (existing pattern)

## Testing Strategy

| Layer | What to Test | Approach | Target |
|-------|-------------|----------|--------|
| Unit | Model constraints, clean(), unique constraints | pytest-django, factory-boy | 90%+ |
| Unit | WorkflowService methods (create, approve, observe, reject, reset, cancel, check_minimum_data) | pytest, mock AuditEventEmitter | 90%+ |
| Unit | WorkflowTemplateService CRUD | pytest-django | 85%+ |
| Unit | Serializer validation, nested steps | pytest-django | 85%+ |
| Unit | Permission classes (IsWorkflowStepApprover) | pytest, parameterized | 85%+ |
| Integration | Signal flow: Project submit → WorkflowInstance created | pytest-django | 100% of signal branches |
| Integration | Signal flow: resubmit → instance reset | pytest-django | 100% |
| Integration | Signal flow: terminal state → instance cancelled | pytest-django | 100% |
| Integration | Atomicity: signal receiver failure rolls back FSM transition | pytest-django | 100% |
| Integration | ViewSet endpoints (CRUD + actions + filtering) | APIClient | 85%+ |
| E2E | RLS tenant isolation | PostgreSQL test DB | 100% of policies |
| Edge | Idempotent instance creation (no duplicates) | pytest-django | 100% |
| Edge | Minimum-data guard blocks approve | pytest-django | 100% |
| Edge | Overdue annotation accuracy | pytest-django, freezegun | 100% |

**Coverage floor**: ≥80% (per `config.yaml`).
**Test files**: `conftest.py`, `test_models.py`, `test_services.py`, `test_signals.py`, `test_serializers.py`, `test_views.py`, `test_permissions.py`, `test_filters.py`, `test_rls.py`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/project_workflow/__init__.py` | Create | Package init |
| `apps/project_workflow/apps.py` | Create | AppConfig |
| `apps/project_workflow/models.py` | Create | 4 models + 3 enums |
| `apps/project_workflow/services.py` | Create | WorkflowService, WorkflowTemplateService |
| `apps/project_workflow/serializers.py` | Create | 6 serializers |
| `apps/project_workflow/views.py` | Create | 3 ViewSets |
| `apps/project_workflow/permissions.py` | Create | IsWorkflowStepApprover |
| `apps/project_workflow/filters.py` | Create | WorkflowInstanceFilter |
| `apps/project_workflow/urls.py` | Create | Router + action paths |
| `apps/project_workflow/admin.py` | Create | Admin registration |
| `apps/project_workflow/signals.py` | Create | Signal receiver |
| `apps/project_workflow/migrations/0001_initial.py` | Create | 4 tables |
| `apps/project_workflow/migrations/0002_rls_policies.py` | Create | RLS policies |
| `apps/project_workflow/tests/` (9 files) | Create | Full test suite |
| `apps/projects/signals.py` | Create | `project_state_changed` signal definition |
| `apps/projects/services.py` | Modify | Signal emission in `_log_transition()` + `transaction.atomic()` wrappers |
| `config/settings/base.py` | Modify | Add `apps.project_workflow` to `INSTALLED_APPS` |
| `config/urls.py` | Modify | Add workflow URL include |

**Total**: ~25 new files, 3 modified files, 0 deleted.

## Open Questions

- [ ] None — all design decisions resolved by spec and existing patterns.
