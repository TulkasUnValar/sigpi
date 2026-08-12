# Cross-Module Integration Specification

## Purpose

Wire SIGPI's 9 MVP modules for end-to-end flow: Call → Project → Approval → Progress → Products → Report. No schema changes — signals for event notifications, service guards for hard constraints.

## Integration Points

| IP | Domain | Pattern | Description |
|----|--------|---------|-------------|
| IP-1 | calls | Signal | Emit `call_state_changed` on FSM transitions |
| IP-2 | advances | Signal receiver | Guard progress creation by project state |
| IP-3 | products | Service guard | Guard product creation by project state |
| IP-4 | reports | Service guard | Validate `entity_id` resolution + institution ownership |
| IP-5 | project_workflow | Signal receiver | Optional workflow completion → execution signal |

## Functional Requirements

### FR-001: Call Lifecycle Signal (IP-1)

The system MUST emit a `call_state_changed` signal after every successful Call FSM transition, carrying `call_id`, `from_state`, `to_state`, and `triggered_by`.

#### Scenario: Signal emitted on transition

- GIVEN a Call transitioning from `borrador` to `abierta`
- WHEN `_log_transition()` completes inside `transaction.atomic()`
- THEN `call_state_changed` is dispatched with `call_id`, `from_state="borrador"`, `to_state="abierta"`, `triggered_by=user`

#### Scenario: No signal on failed transition

- GIVEN a Call in `borrador`
- WHEN a non-director attempts `open_call()`
- THEN the transition is rejected AND no signal is emitted

### FR-002: Progress Creation Guard (IP-2)

The system MUST reject progress report creation unless the linked Project is in `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, or `cerrado`.

#### Scenario: Progress created for executing project

- GIVEN a Project in `en_ejecucion`
- WHEN a ProjectMember creates a ProgressReport
- THEN the ProgressReport is created

#### Scenario: Progress rejected for pre-approval project

- GIVEN a Project in `borrador`
- WHEN a user attempts to create a ProgressReport
- THEN 403 `{"detail":"Progress reports require the project to be in execution or later states."}`

### FR-003: Products Creation Guard (IP-3)

The system MUST reject product creation unless the linked Project is in `aprobado`, `en_ejecucion`, `suspendido`, `finalizado`, `en_cierre`, or `cerrado`.

#### Scenario: Product created for approved project

- GIVEN a Project in `aprobado`
- WHEN a user creates a ResearchProduct
- THEN the product is created

#### Scenario: Product rejected for pre-approval project

- GIVEN a Project in `enviado`
- WHEN a user attempts to create a ResearchProduct
- THEN 403 `{"detail":"Products can only be linked to approved or active projects."}`

### FR-004: Report Entity Integrity (IP-4)

The system MUST resolve `entity_id` to an existing entity and verify it belongs to the same institution before generating a report.

#### Scenario: Valid entity resolution

- GIVEN a valid `entity_id` referencing a Project in the user's institution
- WHEN report generation is requested
- THEN the report is generated

#### Scenario: Unresolvable entity

- GIVEN an `entity_id` that does not match any known entity
- WHEN report generation is requested
- THEN 404 `{"detail":"Entity not found."}`

#### Scenario: Cross-institution entity

- GIVEN an `entity_id` referencing an entity in a different institution
- WHEN report generation is requested
- THEN 403 `{"detail":"Entity does not belong to your institution."}`

### FR-005: Workflow Completion Signal (IP-5)

The system MUST emit a `workflow_completed` signal when a WorkflowInstance reaches `completed` status. Auto-transition to `en_ejecucion` is OPTIONAL; for MVP the transition remains manual via `start_execution()`.

#### Scenario: Signal emitted on workflow completion

- GIVEN a WorkflowInstance in `pending`
- WHEN the director approves and instance transitions to `completed`
- THEN `workflow_completed` is dispatched with `project_id`

#### Scenario: No auto-transition in MVP

- GIVEN a WorkflowInstance reaches `completed`
- WHEN the signal is received
- THEN the project status is NOT automatically changed (manual `start_execution()` required)

## Business Rules

| Code | Rule |
|------|------|
| BR-001 | Progress reports SHALL NOT be created for projects in `borrador`, `enviado`, `en_revision`, `observado`, `rechazado`, or `cancelado`. |
| BR-002 | Products SHALL NOT be created for projects in `borrador`, `enviado`, `en_revision`, `observado`, `rechazado`, or `cancelado`. |
| BR-003 | Report `entity_id` MUST resolve to an existing entity AND belong to the requesting user's institution. |

## Error Handling

| Guard Violation | HTTP Status | Response |
|-----------------|-------------|----------|
| Progress creation in pre-execution project | 403 | `{"detail":"Progress reports require the project to be in execution or later states."}` |
| Product creation in pre-approval project | 403 | `{"detail":"Products can only be linked to approved or active projects."}` |
| Report entity not found | 404 | `{"detail":"Entity not found."}` |
| Report entity cross-institution | 403 | `{"detail":"Entity does not belong to your institution."}` |
| Signal emission on failed FSM transition | N/A | Signal is NOT emitted (guard prevents transition) |

## Test Strategy

| Category | Scope |
|----------|-------|
| **New tests** | Signal emission (IP-1, IP-5), project-state guards (IP-2, IP-3), entity validation (IP-4) |
| **Existing tests to audit** | `products` tests creating products for projects in early states — update fixture status to `aprobado`+ |
| **Existing tests unaffected** | `calls` FSM tests (signal is additive), `advances` FSM tests (guard is on creation only), `reports` tests using valid entity IDs |
| **Integration test** | End-to-end: Call open → Project linked → Approved → Execution started → Progress created → Product registered → Report generated |
| **Markers** | `@pytest.mark.integration` for cross-module tests |

## FSM Interaction

| FSM | Signal Emitted | Downstream Effect |
|-----|---------------|-------------------|
| Call FSM | `call_state_changed` after each transition | Future: notify linked projects (no receiver in MVP) |
| Project FSM | `project_state_changed` (existing) | IP-2 receiver checks `to_state` to allow/block progress creation |
| Workflow FSM | `workflow_completed` on `completed` | IP-5 optional receiver (no-op in MVP) |

Guards are evaluated AFTER FSM transition succeeds. If a guard blocks a downstream action (e.g., progress creation), the upstream FSM state is NOT rolled back — the guard prevents the new entity creation, not the state transition.
