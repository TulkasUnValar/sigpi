# Tasks: Frontend Calls Module (calls-ui)

## Review Workload Forecast

| PR | Slice | Est. lines | 400-line risk |
|----|-------|------------|---------------|
| PR1 | Foundation | ~1,600 | High |
| PR2 | Nested managers + delete | ~670 | High |
| PR3 | Filters + polish + verify | ~310 | Medium |
| Total | | ~2,580 | High |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

Delivery strategy: auto-chain

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation slice | PR 1 | `cd frontend; jest __tests__/features/calls; tsc --noEmit` | MSW: `/calls`, `/calls/new`, `/calls/{id}` | revert PR1 merge |
| 2 | Nested managers + delete | PR 2 | `cd frontend; jest __tests__/features/calls/managers` | `/calls/{id}` tabs, MSW | revert PR2 merge |
| 3 | Filters + polish + verify | PR 3 | `cd frontend; jest --coverage; tsc --noEmit; eslint .` | `/calls` filters via MSW | revert PR3 merge |

## PR1 — Foundation

- [x] 1.1 RED `routes.test.tsx`: 4 routes + auth boundary. ~70 ln
- [x] 1.2 `types.ts`+`constants.ts`+`permissions.ts`: DRF-mirror types, Spanish labels, canManageCall+alias. AC: tsc green. ~180 ln
- [x] 1.3 `fsm.ts`: getCallActions(state, roles). AC: filtered by role+state. ~60 ln
- [x] 1.4 `schemas.ts`+`schemas.test` (RED): conditional entity, date order. AC: 4 scenarios. ~150 ln
- [x] 1.5 `lib/query-keys.ts`+`queries.ts`+`queries.test` (RED): calls factory, 5 hooks. AC: keys, api-mocked. ~190 ln
- [x] 1.6 `StatusBadge.tsx`+`Sidebar.tsx`: 3 FSM statuses, "Convocatorias". AC: badge/nav. ~25 ln
- [x] 1.7 `mutations.ts`+`mutations.test` (RED): 8 mutations, invalidate root, errors. AC: invalidation/403/409. ~120 ln
- [x] 1.8 `fixtures/calls.ts`+`index.ts`+`mocks/handlers.ts`: list/create/FSM handlers. AC: Page envelope; open_call→abierta. ~150 ln
- [x] 1.9 `CallList.tsx`+`app/calls/page.tsx`: table, empty state, filter UI, gated CTA. AC: list/empty. ~180 ln
- [x] 1.10 `CallForm.tsx`+`new/page.tsx`+`[id]/edit/page.tsx`: shared form, create redirect, read-only edit. AC: create/edit. ~230 ln
- [x] 1.11 `CallDetail.tsx`+`[id]/page.tsx`+`FsmActionBar.tsx`: Overview tab shell, 5 transitions, archive dialog, Toaster. AC: detail/FSM. ~260 ln

## PR2 — Nested Managers + Delete Gate

- [x] 2.1 `DocumentsManager.tsx`: metadata-only CRUD. AC: metadata + delete-refresh. ~140 ln
- [x] 2.2 `ProjectsManager.tsx`: link/unlink, abierta-only, 409. AC: link/hidden/dup. ~150 ln
- [x] 2.3 `StateHistoryManager.tsx`: read-only logs. AC: renders, no mutations. ~60 ln
- [x] 2.4 Delete gate `CallDetail.tsx`: borrador+zero projects, dialog, redirect. AC: confirm/hidden. ~40 ln
- [x] 2.5 `managers.test.tsx` (RED): RTL managers+gate + nested fixtures. AC: handler tests. ~280 ln

## PR3 — Filters + Polish + Verify

- [ ] 3.1 Filter wiring `CallList.tsx` → refetch + `list.test.tsx` (RED). AC: status/type, pagination. ~200 ln
- [ ] 3.2 Polish: skeletons, error/empty states, a11y labels. ~60 ln
- [ ] 3.3 Verify: coverage ≥80%, tsc, ESLint. AC: floor met. ~50 ln

## PR Boundaries & Rollback

- PR1 targets main; PR2/PR3 stack on PR1/PR2, each merging to main in order; rebase child diffs showing prior slices.
- Rollback: frontend-only, no migration; revert merges in reverse (PR3 → PR2 → PR1).
- Open question: auth store emits `director_centro` as `director`? else alias in `permissions.ts` (1.2).