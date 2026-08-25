# Tasks: SIGPI Frontend MVP — Dashboard, Projects & Advances

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1900 (3 slices: 750 / 750 / 400) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (shell+dashboard) → PR 2 (projects) → PR 3 (advances) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation + shell + dashboard | PR 1 | `cd frontend; jest shell dashboard` | `npm run dev` + login (real DRF) | revert deps + `lib/api.ts`/`middleware.ts` |
| 2 | Projects module | PR 2 | `cd frontend; jest projects` | wizard create→submit→detail | remove `features/projects` + routes |
| 3 | Advances module + fixtures | PR 3 | `cd frontend; jest advances` | nested list→approve flow | remove `features/advances` + routes |

## Phase 1: Foundation & Shell (PR 1)

- [x] 1.1 Add deps to `frontend/package.json`: TanStack Query v5, React-19 Radix/shadcn, next-themes, react-hook-form, zod, MSW. (~40) Test: React 19 compat spike mounts. Risk: shadcn×React19.
- [x] 1.2 RED: `frontend/__tests__/lib/errors.test.ts` — `{detail}`/field-error normalize to `ApiError`. (~30)
- [x] 1.3 Create `frontend/lib/api.ts` (JSON/multipart, CSRF, credentials), `frontend/lib/query-keys.ts`, `frontend/lib/errors.ts`. (~120) Test: contract assertions.
- [x] 1.4 RED: `frontend/__tests__/components/shell/*` — responsive sidebar/drawer, role guard 403. (~40)
- [x] 1.5 Create `frontend/components/ui/*` + `shared/*` (StatusBadge, ConfirmDialog, EmptyState, Skeleton, Toaster). (~150) Test: WCAG a11y roles.
- [x] 1.6 Create `frontend/components/shell/*` (sidebar, drawer, topbar, layout, guards). (~150) Test: breakpoint, guard.
- [x] 1.7 Wire `frontend/app/layout.tsx` (providers) + `frontend/middleware.ts` (protect dashboard/projects). (~40) Test: middleware redirect.
- [x] 1.8 Modify `frontend/store/auth.ts` — invalidate scoped queries on institution switch. (~30) Test: switch refetch.

## Phase 2: Dashboard (PR 1)

- [x] 2.1 RED: KPI selectors from `/projects/`,`/progress/` (role-aware director vs investigator). (~40)
- [x] 2.2 Create `frontend/features/dashboard/**` (queries, selectors) + `frontend/app/dashboard/page.tsx`. (~120) Test: director queue, investigator KPIs.
- [x] 2.3 Slice-1 integration: `frontend/mocks/*` MSW handlers + Jest coverage ≥80%, raise branch threshold to 80. (~80)

## Phase 3: Projects (PR 2)

- [x] 3.1 RED: `frontend/__tests__/features/projects/*` — list pagination, detail tabs, wizard validation, FSM visibility/confirm. (~80)
- [x] 3.2 Create `frontend/features/projects` (schemas, queries, mutations, `FsmActionBar` w/ 14 transitions). (~200) Risk: FSM map→403s.
- [x] 3.3 Create list page (pagination, filters status/center/line/year/search). (~120) Test: 25/page from `next`.
- [x] 3.4 Create detail page (tabs: overview, team, documents, observations, history). (~120) Test: tabs + StatusBadge.
- [x] 3.5 Create multi-step wizard `/projects/new` (basic→center/group/line→team→documents→review). (~180) Test: submit→POST→redirect.
- [x] 3.6 Slice-2 integration: MSW + coverage ≥80%, lint + typecheck. (~60)

## Phase 4: Advances (PR 3)

- [x] 4.1 RED: `frontend/__tests__/features/advances/*` — nested list, cumulative %, create, director approve/reject-confirm. (~70)
- [x] 4.2 Create `frontend/features/advances` (schemas, queries, mutations, 6-transition FSM bar). (~160)
- [x] 4.3 Create nested list `/projects/[id]/advances` + detail + create form. (~140) Test: approve→invalidate dashboard/progress.
- [x] 4.4 Create `frontend/fixtures/*` seed adapter (non-empty dashboard/projects/advances). (~60) Test: fixtures present.

## Phase 5: Cross-cutting Verification

- [ ] 5.1 Confirm DRF ordering param names (open question) before table impl. (~0) Risk: unknown.
- [x] 5.2 Per-PR: `jest --coverage` ≥80%, ESLint, `tsc --noEmit` green. (~30)

## Notes

- Acceptance: each task ships RED→GREEN→REFACTOR; commit per work unit.
- Rollback per PR: revert slice branch; foundation revert = deps + git-restore `lib/api.ts`/`middleware.ts`.
