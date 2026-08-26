# Design: Budget Module

## Technical Approach

Create `backend/apps/budgets`, mirroring products/calls: UUID Django models, institution-filtered DRF viewsets, django-filter, manual nested URLs, and a service layer for business rules. Budget is `Project` `OneToOne`; executions are always line-level. Status is a plain `CharField`, not an FSM.

## Architecture Decisions

| Decision | Choice and rationale |
|---|---|
| Money | `DecimalField(max_digits=14, decimal_places=2)`, non-negative validator and database check; avoids float errors and follows the resolved spec. |
| Lifecycle | Choices `draft`, `approved`, `executed`, `closed`; explicit data is required, so no FSM. |
| Tenant inheritance | Budget has `institution`; child RLS policies traverse parent FKs, matching calls and avoiding mutable duplicate tenant fields. FundingSource traverses Project. |
| Enforcement | `BudgetService` owns mutation, authorization and audit inside `transaction.atomic`; views never bypass it. |

## Data Flow

`Request → scoped ViewSet/serializer → BudgetService → ORM transaction → AuditEventEmitter`

`Project report → BudgetSummaryService → aggregates → approved/executed/balance`

## Model Contract

- **Budget**: UUID PK, `project OneToOne`, `institution FK`, `name`, `approved_amount`, `status`, `created_at`, `updated_at`; unique project, `(institution,status)` index.
- **BudgetLine**: UUID PK, `budget FK`, `name`, `approved_amount`, timestamps; indexes on `budget` and `(budget,name)`.
- **FundingSource**: UUID PK, `project FK`, `name`, `amount`, timestamps; index on project; multiple sources allowed.
- **BudgetExecution**: UUID PK, `line FK`, `amount`, `executed_at`, nullable `authorized_by FK(User, SET_NULL)`, nullable `authorized_at`, timestamps; index `(line,executed_at)`.
- **BudgetAttachment**: UUID PK, `budget FK`, `name`, `doc_type`, required `external_url`, `created_at`; metadata only, index on budget.

All money fields use the resolved precision and non-negative checks. FKs cascade with parents except authorization user (`SET_NULL`).

## API and Permissions

Expose `/api/budgets/` (GET/POST), `/api/budgets/{id}/` (GET/PATCH/DELETE), nested line and attachment list/detail routes, nested line execution list/detail routes, `/api/projects/{project_pk}/funding-sources/` list/detail routes, and `/api/budgets/{id}/summary/` GET. Use simple-router for Budget and manual nested paths like products. Serializers make parent and tenant fields read-only; views resolve parents before children and apply project/institution/status filters.

Authenticated users read only their active institution; superusers bypass, using queryset filtering plus `IsSameInstitution`. Superadmin, Institution Admin and Center Director (role level ≤3) mutate; researchers read only. Center Directors additionally require project-center membership. Execution overrun requires both authorization fields and Director-or-higher or the custom budget-authorization permission. Duplicate budget returns 409; unauthorized overrun returns 400; foreign objects are hidden as 404.

## Services, Audit and Reports

`BudgetService` validates project institution, performs atomic create/update/delete and execution writes, locks/rechecks the line before summing executions, and enforces RN-020 (`sum ≤ line.approved_amount` unless authorized). It emits `BUDGET_CREATED`, `BUDGET_UPDATED`, or `BUDGET_EXECUTION_ADDED` through `AuditEventEmitter`, with entity, amount and authorization details.

`BudgetSummaryService.for_budget()` returns Decimal-compatible `{approved, executed, balance}` where approved is Budget amount, executed is the aggregate of line executions, and balance is their difference. Missing budget returns `None`; reports adds an absent/empty conditional `budget_summary` to project context (RN-022).

## RLS and Migrations

`0001_initial.py` creates all five tables, FKs, checks, indexes and one-to-one uniqueness. `0002_rls_policies.py` enables `tenant_isolation` and `superadmin_bypass` on every table: Budget checks its institution; lines, executions and attachments subquery Budget; FundingSource subqueries Project. Reverse drops policies and disables RLS. Both follow calls and no-op on SQLite. Register the app in settings and `/api/` in config URLs; add the three audit choices and report wiring.

## Testing Strategy

Add factories for institutions, memberships/roles, projects, users, budgets, lines and executions. Test model constraints and uniqueness; every endpoint, nested-parent isolation, filters and exact errors; all role actions; Director center scope; RN-020 authorized/unauthorized and atomic concurrent boundaries; audit payloads; summary math and missing-budget report behavior. Verify migration SQLite no-op and PostgreSQL RLS policies. Maintain ≥90% `apps.budgets` coverage.

## Threat Matrix

Routing is changed, but no shell, executable classification, Git, push or PR boundary exists:

| Boundary | Applicability | Safe/failure behavior | RED test |
|---|---|---|---|
| Documentation-like paths | N/A — no executable paths | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

## Migration / Rollout

Run migrations, deploy routes, then enable report consumption. No feature flag or data migration. Rollback removes app/routes, report wiring, audit choices and budget tables.

## Open Questions

None; all proposal questions are resolved by the approved spec.
