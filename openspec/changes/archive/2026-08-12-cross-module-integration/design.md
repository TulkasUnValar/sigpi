# Design: Cross-Module Integration

## Technical Approach

Wire SIGPI's 9 modules via the **hybrid pattern** established in the proposal: Django signals for event notifications (loose coupling), service-level guards for hard validation constraints. All integration points piggyback on existing `_log_transition()` methods and `perform_create()` hooks — no schema changes, no migrations.

The existing `project_state_changed` signal pattern in `project_workflow/signals.py` (line 25) serves as the reference implementation for IP-1 and IP-5.

## Architecture Decisions

| Decision | Choice | Alternative | Rationale |
|----------|--------|-------------|-----------|
| IP-3 guard location | View `perform_create` (no new service file) | New `products/services.py` | Products module has no service layer; creating one for a single guard is overengineering. Guard is 4 lines in the existing `perform_create`. |
| IP-4 validation strategy | Refactor existing view helpers into service guard | Keep validation in views only | `_get_entity_institution_id` and `_check_institution_access` already exist in `reports/views.py` but bypass the service layer. Moving to `ReportRenderer` ensures enforcement regardless of entry point. |
| IP-2 guard pattern | Replace `_validate_project_not_terminal` with state-set check in `ProgressService.create()` | Add signal receiver on `project_state_changed` | Signal receiver can't block creation (it fires after transition). Guard must be in the creation path. The existing `_validate_project_not_terminal` only blocks terminal states — insufficient per FR-002. |
| Signal emission timing | Inside `transaction.atomic()`, after DB write | After `transaction.atomic()` block | Matches existing `project_state_changed` pattern (line 296, `projects/services.py`). Receivers run inside the transaction — if they fail, the transition rolls back. |
| IP-5 MVP scope | Signal emission only, no auto-transition receiver | Auto-transition to `en_ejecucion` | Spec FR-005 explicitly defers auto-transition. Signal exists for future consumers. |

## Data Flow

### Project Approval → Downstream Reactions (IP-2, IP-3, IP-5)

```
Director approves project
    │
    ▼
ProjectService.approve()
    ├── project.approve()  (FSM: en_revision → aprobado)
    ├── project.save()
    └── _log_transition()
         ├── ProjectStateLog created
         ├── AuditEvent emitted
         └── project_state_changed.send()
              │
              ├── on_project_state_change()  [project_workflow/signals.py]
              │    └── WorkflowService.advance_step() → complete_workflow()
              │         └── workflow_completed.send()  ← IP-5 (new)
              │              └── (no-op receiver for MVP)
              │
              └── (future: progress receiver could pre-validate)
                   
User creates ProgressReport
    └── ProgressService.create()
         └── _validate_project_state_for_progress()  ← IP-2 (new guard)
              └── blocks if status ∉ {en_ejecucion, suspendido, finalizado, en_cierre}

User creates ResearchProduct  
    └── ResearchProductViewSet.perform_create()
         └── _validate_project_state_for_product()  ← IP-3 (new guard)
              └── blocks if status ∉ {aprobado, en_ejecucion, suspendido, finalizado, en_cierre}
```

### Call FSM → Signal Emission (IP-1)

```
CallService.open_call() / close_call() / start_evaluation() / ...
    └── _log_transition()
         ├── CallStateLog created
         ├── AuditEvent emitted
         └── call_state_changed.send()  ← IP-1 (new)
              └── (no receiver in MVP — future: notify linked projects)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/calls/signals.py` | Create | Define `call_state_changed = django.dispatch.Signal()` |
| `backend/apps/calls/apps.py` | Modify | Add `ready()` importing `apps.calls.signals` |
| `backend/apps/calls/services.py` | Modify | Add `call_state_changed.send()` in `_log_transition()` (3 lines) |
| `backend/apps/progress/services.py` | Modify | Replace `_validate_project_not_terminal` with `_validate_project_state_for_progress` in `create()` |
| `backend/apps/products/views.py` | Modify | Add project-state guard in `perform_create()` (6 lines) |
| `backend/apps/reports/services.py` | Modify | Add `validate_entity()` method to `ReportRenderer` with standardized errors |
| `backend/apps/reports/views.py` | Modify | Delegate entity validation to `ReportRenderer.validate_entity()`, align error format to `{"detail": "..."}` |
| `backend/apps/project_workflow/signals.py` | Modify | Define `workflow_completed` signal + emit in new receiver on workflow completion |
| `backend/apps/project_workflow/services.py` | Modify | Emit `workflow_completed` in `complete_workflow()` (2 lines) |
| `backend/apps/calls/tests/test_signals.py` | Create | Unit tests for `call_state_changed` emission |
| `backend/apps/progress/tests/test_project_state_guard.py` | Create | Unit tests for IP-2 guard |
| `backend/apps/products/tests/test_project_state_guard.py` | Create | Unit tests for IP-3 guard |
| `backend/apps/project_workflow/tests/test_workflow_completed_signal.py` | Create | Unit tests for IP-5 emission |
| `backend/tests/integration/test_cross_module_flow.py` | Create | End-to-end integration test |

## Interfaces / Contracts

### IP-1: `call_state_changed` Signal

```python
# Defined in: apps/calls/signals.py
call_state_changed = django.dispatch.Signal()
# Provides: call, from_state, to_state, triggered_by
```

### IP-2: Progress State Guard

```python
# In: apps/progress/services.py
PROGRESS_ALLOWED_PROJECT_STATES = frozenset({
    "en_ejecucion", "suspendido", "finalizado", "en_cierre",
})

def _validate_project_state_for_progress(project):
    if project.status not in PROGRESS_ALLOWED_PROJECT_STATES:
        raise ValidationError(
            "Progress reports require the project to be in execution or later states."
        )
```

### IP-3: Products State Guard

```python
# In: apps/products/views.py (inside perform_create)
PRODUCT_ALLOWED_PROJECT_STATES = frozenset({
    "aprobado", "en_ejecucion", "suspendido", "finalizado", "en_cierre",
})
# Raises: PermissionDenied("Products can only be linked to approved or active projects.")
```

### IP-5: `workflow_completed` Signal

```python
# Defined in: apps/project_workflow/signals.py
workflow_completed = django.dispatch.Signal()
# Provides: project_id, instance_id, triggered_by
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | IP-1 signal emitted with correct kwargs on each Call FSM transition | `mock.patch` on `call_state_changed.send`, assert called with `from_state`, `to_state`, `call`, `triggered_by` |
| Unit | IP-2 guard blocks progress for projects in borrador/enviado/en_revision/observado/aprobado | `ProgressService.create()` with projects in each blocked state → `ValidationError`; allowed states → success |
| Unit | IP-3 guard blocks products for projects in borrador/enviado/en_revision/observado | `perform_create` with projects in each blocked state → `PermissionDenied`; allowed states → success |
| Unit | IP-4 entity validation returns 404/403 with correct `{"detail": "..."}` format | `ReportRenderer.validate_entity()` with invalid UUID, cross-institution UUID, valid UUID |
| Unit | IP-5 signal emitted when `WorkflowService.complete_workflow()` runs | `mock.patch` on `workflow_completed.send`, assert called with `project_id` |
| Integration | Full flow: Call open → Project linked → Approved → Execution → Progress → Product → Report | `@pytest.mark.integration` test using factories, exercising the real signal chain |
| **Regression audit** | Existing products tests | `ProjectFactory` defaults to `status="borrador"` — ALL product tests creating products will break. Fix: add `status="aprobado"` to `ProductFactory` or test-level overrides. |
| **Regression audit** | Existing progress tests | Same issue — `ProgressReportFactory` creates projects in `borrador`. Fix: override `status="en_ejecucion"` in `ProgressReportFactory` or test fixtures. |

## Migration / Rollout

No migration required. All changes are additive Python code — no schema or data changes. Single PR, single revert point.

**Regression risk**: HIGH for products/progress tests. The `ProjectFactory` defaults to `status="borrador"` (line 74 of `projects/tests/conftest.py`). After IP-2/IP-3 land, any test creating a product or progress report against a default factory project will fail. Mitigation: update `ProductFactory` and `ProgressReportFactory` to use `status="aprobado"` and `status="en_ejecucion"` respectively as defaults, or add `pytest.fixture` overrides.

## Decisions (Open Questions Resolved)

- **IP-2 allowed states include `cerrado`**: Per FR-002 spec line 37, `cerrado` is explicitly listed as an allowed state for progress creation. The existing terminal-only guard (`_validate_project_not_terminal`) is replaced with an explicit state-set check: `project.status in {"en_ejecucion", "suspendido", "finalizado", "en_cierre", "cerrado"}`.
- **IP-4 error format uses `{"detail": "..."}`**: Per FR-004 spec lines 81/87. If reports currently uses `{"error": "..."}`, refactor to DRF-standard `{"detail": "..."}` to align with spec and project-wide conventions.
