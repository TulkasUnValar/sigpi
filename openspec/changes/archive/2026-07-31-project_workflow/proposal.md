# Proposal: Project Workflow — Approval Flow Module (§6.5)

## Intent

The projects module implements a 12-state FSM with transition guards and audit logging, but it tracks only **state**, not the **approval process**. There is no way to configure approval steps, enforce deadline SLAs per stage, validate minimum data completeness before approval, or provide a structured audit trail of who did what and when within a review cycle. This change adds a thin workflow layer on top of the existing Project FSM to formalize, track, and audit the approval process — starting with single-step director approval.

## Scope

### In Scope
- `WorkflowTemplate` — configurable approval steps per institution/center (MVP: one default template)
- `WorkflowStep` — role required, deadline days, sequence order
- `WorkflowInstance` — active workflow per project, linked to `Project` FK
- `WorkflowAction` — append-only audit of each action taken on a step
- Integration hook: auto-create `WorkflowInstance` when Project transitions to `enviado`
- Minimum-data completeness guard (CA-005) before director approval
- Basic deadline tracking (days elapsed, overdue flag)
- Single-step director approval (resolved decision — no committees, no multi-step chains)

### Out of Scope
- Notification delivery (email/in-app) — deferred to `notifications` module
- Evaluation committees with multiple reviewers
- Multi-step sequential/parallel approval chains
- Escalation rules (auto-escalate on deadline miss)
- Bulk batch approval
- Workflow designer UI (MVP uses seed/admin templates)
- Progress/reports workflow reuse (design for it, implement later)

## Capabilities

### New
- `project-workflow`: WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowAction models; service layer; API endpoints; deadline tracking; minimum-data guard; FSM integration hook

### Modified
- `projects`: Add signal/hook on `_log_transition` to create WorkflowInstance on `submit`; no schema change to Project model

## Approach

| Component | Implementation |
|-----------|---------------|
| Models | `InstitutionScopedModel` base; UUID PKs; append-only actions |
| FSM integration | Django signal on Project state change → create/advance WorkflowInstance |
| Service | `WorkflowService` with static methods (mirrors `ProjectService` pattern) |
| Permissions | Reuse `IsCenterDirectorForProject`; `HasRoleLevelOrHigher` for step roles |
| Audit | `AuditEventEmitter` with new event types (WORKFLOW_STEP_CREATED, WORKFLOW_ACTION_TAKEN, WORKFLOW_DEADLINE_MISSED) |
| Deadline | `deadline_days` on WorkflowStep; computed `deadline_date` on WorkflowInstance; overdue flag via queryset annotation |
| Data guard | `WorkflowService.check_minimum_data(project)` called before approve transition |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/project_workflow/` | New | Models, services, serializers, viewsets, signals, tests |
| `apps/projects/services.py` | Modified | Signal emission hook on `_log_transition` |
| `apps/accounts/audit.py` | Modified | New AuditEvent types for workflow |
| `config/urls.py` | Modified | Register `/api/workflows/` router |
| `config/settings.py` | Modified | Add `project_workflow` to `INSTALLED_APPS` |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| FSM/workflow state desync | Med | `transaction.atomic()` wrapping both; workflow creation is idempotent |
| Scope creep (committees, notifications) | Med | Strict OUT list; single-step template only |
| Notification gap (no delivery) | High | Log-only stub; explicit deferred to `notifications` module |
| Signal coupling to projects module | Low | Use Django signals (loose coupling); projects module unchanged at model level |

## Rollback Plan

Reverse migration drops all workflow tables. Remove from `INSTALLED_APPS`/router. Leaf module — no downstream consumers. Projects module unaffected (signal receiver removed, no model changes).

## Dependencies

- `projects` (archived) — FSM state triggers, Project FK target
- `accounts` — AuditEventEmitter, HasRoleLevelOrHigher, RLS
- `institutions` — InstitutionScopedModel, ResearchCenter scope
- `researchers` — Researcher FK for workflow actors
- `django-fsm` — state transition signals

## Success Criteria

- [ ] `WorkflowInstance` auto-created when Project transitions to `enviado`
- [ ] Single-step director approval completes full cycle (create → assign → approve/observe/reject)
- [ ] Minimum-data guard blocks approval when required fields are missing
- [ ] Deadline tracking correctly flags overdue instances
- [ ] `WorkflowAction` provides append-only audit trail per step
- [ ] No changes to Project model schema (only signal hook)
- [ ] Coverage ≥80%, strict TDD
- [ ] RLS restricts workflow tables by `institution_id`
