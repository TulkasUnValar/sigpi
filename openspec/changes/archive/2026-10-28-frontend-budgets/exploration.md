# Exploration: Frontend Budgets Module

## Current State

### Backend Status
- ✅ `apps.budgets` is complete and archived (2026-08-24-budgets)
- 5 entities: Budget (OneToOne→Project), BudgetLine, FundingSource, BudgetExecution, BudgetAttachment
- Full CRUD with RN-020 enforcement (execution ≤ approved)
- Summary endpoint for IND-007/008/009 indicators
- 2040 tests passing, 90.2% coverage
- RLS policies enforced

### Frontend Status
- ❌ Zero budgets UI exists
- No references to `/api/budgets/` in frontend code
- No routes, components, or types defined

## Patterns to Follow

### Established Conventions
Based on analysis of `frontend-calls`, `frontend-researchers`, `frontend-projects`, and `frontend-institutions`:

1. **Feature-sliced architecture**: All logic in `features/{module}/`, thin routes in `app/{module}/`
2. **TanStack Query**: `queryKeys` factory, custom hooks for queries/mutations
3. **Forms**: RHF + zod validation, Spanish UI copy
4. **Authorization**: `RoleGuard` component, role-based UI gating
5. **MSW**: Fixtures + handlers for testing
6. **Managers**: Separate components for nested entities (e.g., `DocumentsManager`, `ProjectsManager`)
7. **Status badges**: `StatusBadge` component with FSM states
8. **Error handling**: `ApiError` → `getErrorMessage` → Toaster

### Decimal Handling
- Backend uses `DecimalField(max_digits=14, decimal_places=2)`
- Backend serializes as strings (e.g., `"1000.00"`)
- Frontend must:
  - Parse strings to numbers for display/calculation
  - Format with `Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' })`
  - Send back as strings in API calls
  - Use string representation in forms to avoid floating-point errors

### Nested Routes Pattern
Based on calls/researchers:
- `/budgets` — list
- `/budgets/new` — create
- `/budgets/[id]` — detail with tabs
- `/budgets/[id]/edit` — edit
- `/budgets/[id]/lines/[lid]` — line detail
- `/budgets/[id]/lines/[lid]/executions` — executions list/form

### Query Keys Structure
```typescript
export const queryKeys = {
  budgets: {
    all: ['budgets'] as const,
    lists: () => [...queryKeys.budgets.all, 'list'] as const,
    list: (filters: BudgetFilters) => [...queryKeys.budgets.lists(), filters] as const,
    details: () => [...queryKeys.budgets.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.budgets.details(), id] as const,
    lines: (budgetId: string) => [...queryKeys.budgets.detail(budgetId), 'lines'] as const,
    executions: (lineId: string) => ['budget-executions', lineId] as const,
    sources: (projectId: string) => ['funding-sources', projectId] as const,
    attachments: (budgetId: string) => [...queryKeys.budgets.detail(budgetId), 'attachments'] as const,
    summary: (budgetId: string) => [...queryKeys.budgets.detail(budgetId), 'summary'] as const,
  },
}
```

## Risks and Mitigations

### Decimal Precision
- **Risk**: Floating-point errors in calculations (e.g., `0.1 + 0.2 = 0.30000000000000004`)
- **Mitigation**: Use string representation in forms/API; parse to number only for display; use `Intl.NumberFormat` for formatting

### RN-020 Enforcement
- **Risk**: User confusion when execution is rejected
- **Mitigation**: Show executed vs approved clearly in UI; provide specific error message; authorization dialog for director+

### Nested Route Complexity
- **Risk**: Complex routing with multiple levels of nesting
- **Mitigation**: Follow established pattern from calls; use clear URL structure; separate managers for each nested entity

### Authorization Flow
- **Risk**: Director authorization for over-execution is complex UX
- **Mitigation**: Use ConfirmDialog pattern from calls; require explicit confirmation; record authorized_by/authorized_at

## Dependencies

### Existing Components to Reuse
- `RoleGuard` — role-based access control
- `StatusBadge` — FSM status display
- `ConfirmDialog` — destructive action confirmation
- `Skeleton` — loading states
- `EmptyState` — empty list display
- `Toaster` — error/success messages
- `AuthenticatedLayout` — authenticated route wrapper
- `FsmActionBar` — FSM transitions (not needed for budgets, but pattern reference)

### Backend API Endpoints
- `GET/POST /api/budgets/`
- `GET/PATCH/DELETE /api/budgets/{id}/`
- `GET/POST /api/budgets/{id}/lines/`
- `GET/PATCH/DELETE /api/budgets/{id}/lines/{lid}/`
- `GET/POST /api/budgets/{id}/lines/{lid}/executions/`
- `GET/POST /api/projects/{id}/funding-sources/`
- `GET/PATCH/DELETE /api/projects/{id}/funding-sources/{sid}/`
- `GET/POST /api/budgets/{id}/attachments/`
- `GET/PATCH/DELETE /api/budgets/{id}/attachments/{aid}/`
- `GET /api/budgets/{id}/summary/`

## Approach

### 3-PR Sliced Delivery
Following the established pattern:

**PR1 — Foundation + Budget CRUD**
- Types, schemas, constants, permissions
- Query keys, queries, mutations
- Budget CRUD (list, create, detail, edit)
- Summary indicators
- Sidebar integration
- Base MSW handlers/tests

**PR2 — Nested Managers**
- BudgetLinesManager (rubros CRUD)
- FundingSourcesManager (sources CRUD)
- AttachmentsManager (metadata-only CRUD)
- Nested routes
- Manager tests

**PR3 — Execution + Authorization**
- BudgetExecutionsManager
- RN-020 validation UI
- Authorization dialog for over-execution
- Execution routes
- Polish and verification

## Open Questions

1. **Auth store role mapping**: Does the auth store emit `director_centro` as `director`? Need to verify or add alias in `permissions.ts`.

2. **Backend Decimal format**: Need to verify that backend serializes Decimal as strings (not numbers). Check serializer in `apps/budgets/serializers.py`.

3. **Currency format**: Should we use COP (Colombian Peso) or leave it generic? Backend doesn't specify currency, only Decimal precision.

4. **Execution authorization flow**: Should the authorization be a separate route or a dialog within the execution form? Decision: Use ConfirmDialog pattern (simpler, matches calls).

5. **Line deletion with executions**: Backend enforces 409; should we show executions count in delete confirmation? Decision: Yes, show "This line has X executions" in ConfirmDialog.

## Success Criteria

- [ ] All 5 entities have full CRUD UI
- [ ] RN-020 enforcement is clear in UI (executed vs approved)
- [ ] Director authorization flow works for over-execution
- [ ] Summary indicators display correctly (IND-007/008/009)
- [ ] Decimal precision is correct (no floating-point errors)
- [ ] Jest coverage ≥80%
- [ ] `tsc --noEmit` green
- [ ] ESLint green
- [ ] Spanish UI copy throughout
- [ ] Role gating works (admin/director create, researcher read-only)
