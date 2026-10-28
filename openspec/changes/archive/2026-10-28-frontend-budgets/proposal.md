# Proposal: Frontend Budgets Module (SIGPI §6.9)

## Intent

The `apps.budgets` backend (5 entities, archived 2026-08-24) is complete with full CRUD, execution tracking, and summary endpoints, but the frontend has zero budgets UI. This change delivers `features/budgets` + routes so users can manage project budgets, lines (rubros), funding sources, execution records, and attachments.

## Scope

### In Scope
- `features/budgets` (types, schemas, constants, permissions, queries, mutations) + routes `/budgets`, `/budgets/new`, `/budgets/[id]`, `/budgets/[id]/edit`, `/budgets/[id]/lines/[lid]`, `/budgets/[id]/lines/[lid]/executions`
- **Budget management**: create one budget per project, edit approved_amount, view summary (approved/executed/balance)
- **Budget lines**: CRUD rubros with approved_amount per line
- **Funding sources**: CRUD sources linked to project (one or more per RN-019)
- **Budget execution**: record executions per line, validate RN-020 (sum ≤ approved), authorize over-execution (director+), surface 400 on overrun without authorization
- **Attachments**: metadata-only CRUD (name, doc_type, external_url)
- **Summary view**: IND-007/008/009 indicators (approved/executed/balance) consumable by reports (RN-022)
- Role gating: admin/director can create/update; researcher read-only; director can authorize over-execution
- MSW fixtures/handlers; Sidebar "Presupuesto"; Jest ≥80%, `tsc --noEmit`

### Out of Scope
- Backend changes; file uploads (metadata-only); budget reports/statistics UI; notifications integration (budget_overrun_attempted signal handling deferred)

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `budgets-ui`: budget CRUD, line CRUD, funding source CRUD, execution tracking with RN-020 validation, attachment metadata, summary indicators, institution-scoped server state, shell integration

### Modified Capabilities
- None — no spec-level behavior change elsewhere

## Approach

Sliced read-first delivery (3 chained PRs mirroring calls/researchers):
- **PR1** — foundation (types/schemas/constants/query-keys) + budget CRUD + summary + Sidebar
- **PR2** — lines + funding sources + attachments + nested routes
- **PR3** — execution tracking + RN-020 validation + authorization flow + polish + verify

Backend untouched; zod mirrors backend serializer validation (Decimal 14,2, date ordering, RN-020 enforcement).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/features/budgets/**` | New | module + `frontend/app/budgets/**` routes |
| `frontend/lib/query-keys.ts` | Modified | `budgets` factory (list/detail/lines/executions/sources/attachments/summary) |
| `frontend/components/shell/Sidebar.tsx` | Modified | "Presupuesto" nav item (admin/director/researcher) |
| `frontend/mocks/handlers.ts` + `frontend/fixtures/budgets.ts` | Modified/New | MSW |
| Backend | — | none |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Exceeds 400-line review budget | High | 3 chained PRs; sizes forecast in tasks |
| Decimal precision errors | Med | Use string representation in forms, parse to Decimal in API |
| RN-020 validation UX | Med | Surface 400 clearly, show executed vs approved in UI |
| Over-execution authorization complexity | Med | Separate dialog for authorization, require director role |
| Nested route complexity (lines/executions) | Med | Clear route structure, reuse patterns from calls managers |

## Rollback Plan

Feature-branch chain: revert each PR independently; frontend-only, no data/backend impact.

## Dependencies

None new: backend budgets API complete; TanStack Query, RHF + zod, shadcn/ui, MSW, Zustand present; projects `FsmActionBar` pattern reused for execution authorization.

## Success Criteria

- [ ] Budget CRUD works end-to-end with correct role gating (admin/director create, researcher read-only)
- [ ] Lines CRUD with approved_amount per rubro
- [ ] Funding sources CRUD (one or more per project, RN-019)
- [ ] Execution tracking with RN-020 validation (sum ≤ approved), over-execution authorization flow
- [ ] Attachments metadata-only CRUD
- [ ] Summary endpoint consumed (approved/executed/balance indicators)
- [ ] Jest ≥80%, `tsc --noEmit` green; "Presupuesto" nav present for authenticated roles
