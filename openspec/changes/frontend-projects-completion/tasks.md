# Tasks: Frontend Projects Module Completion

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | PR1 ~850 raw (~115 effective w/ rename detection) · PR2 ~1,220 raw (~20 effective) · PR3 ~880 authored. Total ~2,950 raw / ~1,015 effective |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 |
| Delivery strategy | single-pr |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Extract ProjectList/ProjectDetail + barrel; thin pages | PR1 | `npm test -- __tests__/features/projects/index.test.ts __tests__/features/projects/list-page.test.tsx __tests__/features/projects/detail-page.test.tsx` | `npm run dev` — smoke `/projects`, `/projects/p1` | Revert 5 files; pages restore inline UI |
| 2 | Extract ProjectWizard; thin new page | PR2 | `npm test -- __tests__/features/projects/wizard.test.tsx` | `npm run dev` — walk `/projects/new` wizard | Revert 2 files; wizard back inline |
| 3 | useUpdateProject + ProjectForm + edit route + tests | PR3 | `npm test -- __tests__/features/projects/mutations.test.tsx __tests__/features/projects/project-form.test.tsx __tests__/features/projects/edit-page.test.tsx` | `npm run dev` — edit `/projects/p1`, verify PATCH + redirect | Revert 8 files; detail loses edit link |

## PR1 — Structure (FR-01, FR-02)

- [x] 1.1 RED: create `__tests__/features/projects/index.test.ts` asserting barrel exports (ProjectList, ProjectDetail, hooks, types) — fails until barrel exists
- [x] 1.2 Create `frontend/features/projects/ProjectList.tsx` (`ProjectListProps {}`) — move filter/pagination/table UI + `useProjectsList`/`useCenters` from `app/projects/page.tsx` (read-only)
- [x] 1.3 Create `frontend/features/projects/ProjectDetail.tsx` (`ProjectDetailProps { id: string }`) — move tabs/FSM-bar UI from `app/projects/[id]/page.tsx` (read-only)
- [x] 1.4 Create `frontend/features/projects/index.ts` barrel re-exporting components, hooks, types (products pattern)
- [x] 1.5 Rewrite `app/projects/page.tsx` and `app/projects/[id]/page.tsx` to consume the barrel, behavior unchanged
- [x] 1.6 Gate: existing `list-page.test.tsx`/`detail-page.test.tsx` pass unchanged, `npx tsc --noEmit`, coverage ≥80% (FR-08)

## PR2 — Wizard (FR-03)

- [ ] 2.1 Create `frontend/features/projects/ProjectWizard.tsx` — move 604-line wizard from `app/projects/new/page.tsx` (read-only) with zero behavior change
- [ ] 2.2 Rewrite `app/projects/new/page.tsx` as thin wrapper rendering `ProjectWizard` via barrel
- [ ] 2.3 Update `__tests__/features/projects/wizard.test.tsx` to import `ProjectWizard` from barrel, assertions unchanged
- [ ] 2.4 Gate: wizard suite green, `npx tsc --noEmit` (FR-08)

## PR3 — Edit (FR-04…FR-08)

- [ ] 3.1 RED: write `__tests__/features/projects/mutations.test.tsx` — PATCH URL, institution scope, exact payload, both invalidations on success, none on failure (FR-04)
- [ ] 3.2 Add `UpdateProjectPayload` to `frontend/features/projects/types.ts` (writable scalars only; no `project`/`members`/`documents`)
- [ ] 3.3 Add `useUpdateProject(id)` to `frontend/features/projects/mutations.ts` reusing `invalidateProjects`
- [ ] 3.4 RED (route threat case): write `__tests__/features/projects/edit-page.test.tsx` — loading/not-found in-page, detail seeding, success redirect, terminal edit gating
- [ ] 3.5 Add `app/projects/[id]/edit/page.tsx` (products edit-page pattern) consuming `useProjectDetail` + `ProjectForm` via barrel
- [ ] 3.6 Add gated `Editar` link to `ProjectDetail` actions (non-admin; not `cerrado`/`rechazado`/`cancelado`) (FR-06)
- [ ] 3.7 RED: write `__tests__/features/projects/project-form.test.tsx` — zod rejection, dependent-select resets, 400 `setError`, 403 toast/no redirect, writable-field exclusion (FR-05/FR-07)
- [ ] 3.8 Add edit schema rules to `frontend/features/projects/schemas.ts`; create `frontend/features/projects/ProjectForm.tsx` (RHF + Controller selects, `buildUpdatePayload` mapping empty group/line → null) (FR-05/FR-07)
- [ ] 3.9 Extend `frontend/features/projects/index.ts` exports (ProjectForm, useUpdateProject, UpdateProjectPayload)
- [ ] 3.10 Gate: all projects tests green, coverage ≥80%, `npx tsc --noEmit` (FR-08)

## Review

- [ ] 4.1 Confirm each PR diff stays ≤400 changed lines (rename-aware review); escalate to `size:exception` if raw count blocks
- [ ] 4.2 Verify no test imports page internals directly — all consume the barrel (FR-01)
