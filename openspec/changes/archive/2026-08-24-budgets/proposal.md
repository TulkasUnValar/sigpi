# Proposal: Budget Module (Presupuesto — SIGPI §6.9)

## Intent

SIGPI has no budget tracking capability. This change delivers a project-scoped budget module: one Budget per project, budget lines, funding sources, execution records, and metadata-only attachments, plus query and summary endpoints feeding the reports module (RN-022, IND-007/008/009).

## Scope

### In Scope
- New `backend/apps/budgets/` app (models, serializers, views, urls, filters, permissions, services, tests, admin)
- RF-B01–B05: CRUD for Budget, BudgetLine, FundingSource, BudgetExecution, BudgetAttachment
- RF-B06: query by project / institution / status
- RF-B07: summary endpoint for reports (RN-022)
- RN-020: execution ≤ approved per line unless authorized (`authorized_by`/`authorized_at`; Director de centro or custom permission)
- RN-021: audit via `AuditEventEmitter` — `BUDGET_CREATED`, `BUDGET_UPDATED`, `BUDGET_EXECUTION_ADDED`
- RLS via per-app `0002_rls_policies.py`; UUID PKs; denormalized `institution_id`

### Out of Scope
- File upload (metadata-only `external_url` per MVP precedent)
- Budget FSM — status derives from project FSM
- Meilisearch indexing; frontend pages; Superset integration

## Capabilities

### New Capabilities
- `budgets`: CRUD for the 5 budget entities, query by project/institution/status, and summary endpoint with authorization and audit

### Modified Capabilities
- `auth`: extend `AuditEventType` with 3 new budget event types
- `reports`: RF-050 project report budget summary consumes budgets summary endpoint (replaces placeholder)

## Approach

Standalone app mirroring `products`/`calls` patterns. `Budget` OneToOne→`Project`; `FundingSource` FK→`Project`; `BudgetLine` FK→`Budget`; `BudgetExecution` FK→`BudgetLine` (+ authorization fields); `BudgetAttachment` FK→`Budget`. DRF ViewSets + SimpleRouter nested routes, django-filter, `IsSameInstitution`/`HasRoleLevelOrHigher`, service layer enforcing RN-020, per-app RLS migration, `AuditEventEmitter`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/budgets/` | New | Full app incl. tests |
| `backend/config/settings/base.py` | Modified | Register `apps.budgets` |
| `backend/config/urls.py` | Modified | Include `/api/budgets/` |
| `backend/apps/accounts/audit.py` | Modified | Add 3 event types |
| `backend/apps/accounts/migrations/0004_rls_policies.py` | Modified | Add budget tables |
| `backend/apps/reports/` | Modified | Budget summary context (RN-022) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| RLS tables forgotten | Low | Apply checklist; migration review |
| RN-020 bypass via direct FK writes | Med | Service-only mutation; dedicated tests |
| Reports contract break | Med | Summary endpoint tests before template wiring |

## Rollback Plan

Remove `apps.budgets` from `INSTALLED_APPS` and `urls.py`; delete app directory; revert audit event types, RLS entries, and reports template/context. `Budget*` tables dropped with app.

## Dependencies

- `projects` (Budget parent), `institutions` (scoping), `accounts` (permissions/audit), `reports` (RN-022 consumer)

## Success Criteria

- [ ] CRUD for all 5 entities, institution-scoped
- [ ] RN-020 enforced: over-execution rejected unless authorized
- [ ] RN-021 events emitted on create/update/execution
- [ ] RLS isolation verified
- [ ] Summary endpoint renders in project report
- [ ] ≥90% coverage on `apps.budgets`

## Proposal Question Round

1. Money precision: `DecimalField` — confirm max_digits/decimal_places; any currency field needed?
2. RF-B06 status filter values — derive from project FSM states, or explicit budget status?
3. BudgetExecution scope — always line-level, or allow budget-level entries?
