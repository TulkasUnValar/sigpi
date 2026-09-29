# Proposal: Frontend Projects Module Completion

## Intent

`projects` is the only MVP frontend module without full parity: no edit route, no `useUpdateProject`, no extracted components, no barrel export. Every other module (calls, products, advances, reports, researchers, institutions) ships list/detail/create/edit pages, extracted components, barrels, and tests. Backend `PATCH /api/projects/{id}/` already works (RF-028, RN-011) — the frontend just never calls it.

## Scope

### In Scope
- PR1: Extract `ProjectList` + `ProjectDetail`; add barrel `index.ts`
- PR2: Extract `ProjectWizard` (604 lines, behavior-preserving)
- PR3: `useUpdateProject` + `ProjectForm` (RHF+zod) + `/projects/[id]/edit` route + tests
- Client-side edit gating for non-terminal states (backend 403 backstop)

### Out of Scope
- Fixing wizard's dead team/documents steps (pre-existing bug — separate follow-up change)
- Backend changes (none needed)
- Wizard reuse for edit (dedicated `ProjectForm`; see exploration sub-decision)

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `projects-ui` (frontend-mvp): add edit capability — update mutation, edit route, extracted components, barrel export. Existing list/detail/wizard/FSM requirements unchanged.

## Approach

Extract-first, then edit, as 3 chained PRs (each within the 400-line budget):
1. **PR1 Structure**: extract `ProjectList`/`ProjectDetail` (pages become thin wrappers), add barrel + `index.test.ts`; keep list/detail page tests green as regression.
2. **PR2 Wizard**: behavior-preserving extraction of `ProjectWizard` from `new/page.tsx`; update wizard test imports to barrel.
3. **PR3 Edit**: `useUpdateProject` (PATCH, invalidate `["projects"]` + `["dashboard"]`), `ProjectForm` (RHF+zod, create/edit-shared), edit route seeded from `useProjectDetail`, edit link on detail, tests (mutations/edit-page/project-form).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/features/projects/mutations.ts` | Modified | add `useUpdateProject` |
| `frontend/features/projects/index.ts` | New | barrel export |
| `frontend/features/projects/{ProjectList,ProjectDetail,ProjectWizard,ProjectForm}.tsx` | New | extracted components |
| `frontend/app/projects/{page,[id]/page,new/page}.tsx` | Modified | thin wrappers |
| `frontend/app/projects/[id]/edit/page.tsx` | New | edit route |
| `frontend/__tests__/features/projects/*` | Modified/New | regression + mutations/edit-page/project-form/index tests |
| Backend | — | none |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Wizard extraction (604 lines) breaks behavior | Med | mechanical move; `wizard.test.tsx` safety net |
| Dead team/documents steps (pre-existing) | Known | out of scope; flagged for follow-up |
| Edit gate mismatch (RN-011: any non-terminal state) | Med | client gate matches backend; 403 backstop |
| No MSW PATCH handler for edit tests | Med | jest-mock `@/lib/api` (wizard test pattern) |
| Stale cache after edit | Low | reuse `invalidateProjects` |
| ~2,800–3,100 lines vs 400-line budget | High | resolved: 3 chained PRs; sdd-tasks forecasts per slice |

## Rollback Plan

Each chained PR reverts independently: reverting PR1/PR2 restores the inline pages; reverting PR3 removes only the edit route + mutation. Backend is untouched — no schema or data risk; PATCH is additive on an existing endpoint.

## Dependencies

- Chain order PR1 → PR2 → PR3 (later PRs build on extracted components).
- Existing projects tests (list/detail/wizard) as extraction regression safety net.

## Success Criteria

- [ ] `/projects/[id]/edit` exists and PATCHes via `useUpdateProject`
- [ ] All 4 components extracted; pages are thin wrappers; barrel exports resolve
- [ ] `useUpdateProject` invalidates `["projects"]` + `["dashboard"]`
- [ ] New tests green (mutations/edit-page/project-form/index); existing page tests unchanged
- [ ] 3 chained PRs, each ≤400 changed lines; coverage ≥80% per slice
