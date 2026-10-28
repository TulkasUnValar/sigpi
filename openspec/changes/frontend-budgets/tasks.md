# Tasks: Frontend Budgets Module (budgets-ui)

## Review Workload Forecast

| PR | Slice | Est. lines | 400-line risk |
|----|-------|------------|---------------|
| PR1 | Foundation + Budget CRUD | ~1,800 | High |
| PR2 | Nested managers | ~1,400 | High |
| PR3 | Execution + authorization | ~1,100 | High |
| Total | | ~4,300 | High |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Delivery strategy: auto-chain

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation + Budget CRUD | PR 1 | `cd frontend; jest __tests__/features/budgets; tsc --noEmit` | MSW: `/budgets`, `/budgets/new`, `/budgets/{id}` | revert PR1 merge |
| 2 | Nested managers | PR 2 | `cd frontend; jest __tests__/features/budgets/managers` | `/budgets/{id}` tabs, MSW | revert PR2 merge |
| 3 | Execution + authorization | PR 3 | `cd frontend; jest __tests__/features/budgets/executions` | `/budgets/{id}/lines/{lid}/executions`, MSW | revert PR3 merge |

## PR1 — Foundation + Budget CRUD

- [ ] 1.1 RED `routes.test.tsx`: 4 routes + auth boundary. ~70 ln
- [ ] 1.2 `types.ts`+`constants.ts`+`permissions.ts`: DRF-mirror types, Spanish labels, canManageBudget+alias. AC: tsc green. ~200 ln
- [ ] 1.3 `schemas.ts`+`schemas.test` (RED): Decimal validation, project required, date ordering. AC: 5 scenarios. ~180 ln
- [ ] 1.4 `lib/query-keys.ts`+`queries.ts`+`queries.test` (RED): budgets factory, 6 hooks (list, detail, summary, sources). AC: keys, api-mocked. ~220 ln
- [ ] 1.5 `Sidebar.tsx`: "Presupuesto" nav item (all roles). AC: nav visible. ~10 ln
- [ ] 1.6 `mutations.ts`+`mutations.test` (RED): 6 mutations (budget CRUD, source CRUD), invalidate root, errors. AC: invalidation/403/409. ~150 ln
- [ ] 1.7 `fixtures/budgets.ts`+`index.ts`+`mocks/handlers.ts`: list/create/summary handlers. AC: Page envelope; Decimal strings. ~180 ln
- [ ] 1.8 `BudgetList.tsx`+`app/budgets/page.tsx`: table, empty state, filter UI (project/status), gated CTA. AC: list/empty. ~200 ln
- [ ] 1.9 `BudgetForm.tsx`+`new/page.tsx`+`[id]/edit/page.tsx`: shared form (project select, name, approved_amount), create redirect, read-only edit. AC: create/edit. ~250 ln
- [ ] 1.10 `BudgetDetail.tsx`+`BudgetSummary.tsx`+`[id]/page.tsx`: Overview tab with summary indicators (IND-007/008/009), edit/delete controls. AC: detail/summary. ~280 ln
- [ ] 1.11 Verify: coverage ≥80%, tsc, ESLint. AC: floor met. ~50 ln

## PR2 — Nested Managers ✅

- [x] 2.1 `BudgetLinesManager.tsx`: CRUD rubros with approved_amount; show sum vs budget approved_amount. AC: create/edit/delete/sum warning. ~220 ln
- [x] 2.2 `FundingSourcesManager.tsx`: CRUD sources (name, amount); show total vs budget approved_amount. AC: create/edit/delete/coverage %. ~200 ln
- [x] 2.3 `AttachmentsManager.tsx`: metadata-only CRUD (name, doc_type, external_url). AC: metadata + delete-refresh. ~150 ln
- [x] 2.4 `managers.test.tsx` (RED): RTL managers + nested fixtures. AC: handler tests, validation. ~350 ln
- [x] 2.5 Nested routes: `[id]/lines/[lid]/page.tsx`, update detail tabs. AC: routing. ~80 ln
- [x] 2.6 Verify: coverage ≥80%, tsc, ESLint. AC: floor met. ~50 ln

## PR3 — Execution + Authorization + Polish

- [ ] 3.1 `BudgetExecutionsManager.tsx`: list executions per line; show executed sum vs approved; amount input with validation. AC: list/sum/decimal. ~200 ln
- [ ] 3.2 RN-020 validation: surface 400 clearly; show executed vs approved in UI. AC: error message. ~60 ln
- [ ] 3.3 Authorization dialog: ConfirmDialog for over-execution; require director role; record authorized_by/authorized_at. AC: confirm/cancel. ~120 ln
- [ ] 3.4 Execution route: `[id]/lines/[lid]/executions/page.tsx`, execution form. AC: routing/form. ~100 ln
- [ ] 3.5 `executions.test.tsx` (RED): RN-020 enforcement, authorization flow, 400 handling, Decimal precision. AC: 8 scenarios. ~250 ln
- [ ] 3.6 Polish: skeletons, error/empty states, a11y labels, Decimal formatting (Intl.NumberFormat). ~100 ln
- [ ] 3.7 Verify: coverage ≥80%, tsc, ESLint. AC: floor met. ~50 ln

## PR Boundaries & Rollback

- PR1 targets main; PR2/PR3 stack on PR1/PR2, each merging to main in order; rebase child diffs showing prior slices.
- Rollback: frontend-only, no migration; revert merges in reverse (PR3 → PR2 → PR1).
- Open questions:
  - Auth store emits `director_centro` as `director`? else alias in `permissions.ts` (1.2).
  - Backend Decimal serialization format (string vs number)? verify in 1.7.

## Apply Status

- PR1: NOT STARTED
- PR2: COMPLETED
- PR3: NOT STARTED
