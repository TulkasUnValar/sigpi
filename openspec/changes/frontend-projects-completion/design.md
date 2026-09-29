# Design: Frontend Projects Module Completion

## Technical Approach

Complete projects by following the established products/advances feature-module pattern: feature components and server-state hooks live under `frontend/features/projects/`; App Router files become thin data/loading wrappers. PR1 and PR2 are mechanical extractions. PR3 adds a dedicated RHF edit form, preserving the existing wizard for creation. The backend contract is unchanged.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Component boundary | `features/projects/{ProjectList,ProjectDetail,ProjectWizard,ProjectForm}.tsx`; routes only compose them | Keep UI inline in routes | Matches products/advances and makes the barrel/test surface explicit. |
| Edit form | Dedicated `ProjectForm`, shared create/edit schema rules, RHF + `Controller` for shadcn selects | Reuse the five-step wizard | Edit is scalar-only and must never submit members/documents; a dedicated form avoids wizard state leakage. |
| Server state | TanStack Query hooks; mutation reuses `invalidateProjects` | Local cache/manual refetch | Existing projects mutation convention guarantees both `['projects']` and `['dashboard']` invalidation. |
| Test transport | `jest-mock` for `@/lib/api` in hook/component tests | MSW | Existing projects/products tests mock the API module directly; this keeps deterministic assertions for PATCH payloads and errors. |

## Component Architecture and Contracts

- `ProjectList` (`features/projects/ProjectList.tsx`): `interface ProjectListProps {}`; owns filter/pagination UI and calls `useProjectsList`/`useCenters`.
- `ProjectDetail` (`features/projects/ProjectDetail.tsx`): `interface ProjectDetailProps { id: string }`; owns detail tabs, FSM bar, and the conditional edit link. Use `useProjectDetail`, observations, history, and auth roles; show `/projects/${id}/edit` for non-admin users unless status is `cerrado`, `rechazado`, or `cancelado` (the API remains the backstop).
- `ProjectWizard` (`features/projects/ProjectWizard.tsx`): `interface ProjectWizardProps {}`; move the current 604-line implementation without behavior changes.
- `ProjectForm` (`features/projects/ProjectForm.tsx`): `interface ProjectFormProps { project: ProjectDetail }`; RHF defaults are derived from `project`, and dependent options come from `useCenters`, `useGroups(center)`, `useLines(group)`, and `useResearchers`.
- Add `UpdateProjectPayload` to `features/projects/types.ts`, containing only `title`, `abstract`, `objectives`, `methodology`, `expected_results`, `keywords`, `start_date`, `estimated_end_date`, `center`, `group`, `line`, and `principal_investigator`.
- `features/projects/index.ts` re-exports all four components, project hooks/mutations, schemas, and public types. `app/projects/page.tsx`, `[id]/page.tsx`, and `new/page.tsx` import through this barrel; add `[id]/edit/page.tsx`.

## State and Data Flow

`EditPage(id) -> useProjectDetail(id) -> ProjectForm(project) -> useForm(defaultValues) -> buildUpdatePayload(values) -> useUpdateProject(id) -> PATCH /api/projects/{id}/`.

The payload explicitly maps writable scalar fields and converts empty `group`/`line` to `null`; it must exclude `project`, `members`, and `documents`. `useUpdateProject` passes the active institution scope, calls `invalidateProjects` only on success, and leaves caches untouched on failure. RHF `setError` maps `ApiError.fieldErrors` for known fields on 400; 403 shows a Sonner error and stays on the form. Successful mutation shows success feedback and routes to `/projects/${id}`. Changing center resets group and line; changing group resets line.

## File Changes and PR Boundaries

| PR | Exact authored files (additions/modifications) | Finish gate |
|---|---|---|
| 1 Structure | `features/projects/ProjectList.tsx`, `ProjectDetail.tsx`, `index.ts`; `app/projects/page.tsx`, `app/projects/[id]/page.tsx`; `__tests__/features/projects/index.test.ts` | Existing list/detail tests plus barrel test; ≤400 changed lines. |
| 2 Wizard | `features/projects/ProjectWizard.tsx`; `app/projects/new/page.tsx`; `__tests__/features/projects/wizard.test.tsx` | Wizard regression and `tsc --noEmit`; ≤400 changed lines (mechanical move may require line-count review). |
| 3 Edit | `features/projects/ProjectForm.tsx`, `mutations.ts`, `schemas.ts`, `types.ts`, `index.ts`; `app/projects/[id]/page.tsx`, `app/projects/[id]/edit/page.tsx`; `__tests__/features/projects/mutations.test.tsx`, `project-form.test.tsx`, `edit-page.test.tsx` | Jest coverage ≥80%, `tsc --noEmit`, all project regressions; ≤400 changed lines. |

## Testing Strategy

Use Jest + React Testing Library and strict TDD. `index.test.ts` verifies public exports. Existing list/detail/wizard tests remain regression tests after extraction. `mutations.test.tsx` uses a QueryClient wrapper and mocked `api.patch` to assert URL, institution scope, exact payload, both invalidations on success, and none on failure. `project-form.test.tsx` covers zod rejection, dependent-select resets, 400 `setError`, 403 toast/no redirect, and writable-field exclusion. `edit-page.test.tsx` mocks `useParams`, detail GET, and PATCH to cover loading/not-found, detail seeding, successful redirect, terminal edit gating, and error behavior. MSW is not introduced because no project test infrastructure uses it.

## Threat Matrix

Routing is applicable because `/projects/[id]/edit` is added; all other boundaries are N/A.

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable documentation classification | No test. |
| Git repository selection | N/A — no VCS automation | No test. |
| Commit state | N/A — no commit automation | No test. |
| Push state | N/A — no push automation | No test. |
| PR commands | N/A — no PR command execution | No test. |
| Route boundary | Applicable — new edit route | Safe: valid `id` loads the form; failure: loading/not-found remains in-page. RED: `edit-page.test.tsx` covers both. |

## Migration / Rollout

No migration required. Roll out in chain order PR1 → PR2 → PR3; each PR reverts independently.

## Open Questions

None.
