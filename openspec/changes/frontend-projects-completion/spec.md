# Delta Spec: Frontend Projects Module Completion (projects-ui)

Delta for the `projects-ui` capability in `openspec/specs/frontend-mvp/spec.md`. Backend untouched — `PATCH /api/projects/{id}/` (RF-028, RN-011) already exists. Existing list/detail/wizard/FSM requirements are unchanged; PR1/PR2 are behavior-preserving extractions, PR3 adds the edit capability. All requirements below are ADDED.

## ADDED Requirements

| Code | PR | Requirement |
|------|----|-------------|
| FR-01 | 1 | The module MUST export a barrel `index.ts` re-exporting components, hooks, and types; pages and tests SHALL import from the barrel (calls/products pattern). |
| FR-02 | 1 | The module MUST extract `ProjectList` and `ProjectDetail` from the inline pages; routes MUST consume them with unchanged behavior. |
| FR-03 | 2 | The module MUST extract `ProjectWizard` from `new/page.tsx` behavior-preserving; the create route and wizard tests SHALL consume it with unchanged behavior. |
| FR-04 | 3 | The system MUST expose `useUpdateProject(id)` issuing `PATCH /api/projects/{id}/` with writable scalar fields; on success it MUST invalidate `["projects"]` and `["dashboard"]` via `invalidateProjects`. |
| FR-05 | 3 | `/projects/[id]/edit` MUST render a shared `ProjectForm` (RHF + zod) seeded from `useProjectDetail`, PATCHing only writable scalar fields (no `project`, `members`, `documents`), with the same zod rules as create. |
| FR-06 | 3 | The detail page MUST render an `Editar` link gated to non-terminal states (RN-011: not `cerrado`/`rechazado`/`cancelado`) for non-admins; the backend 403 SHALL remain the backstop. |
| FR-07 | 3 | `ProjectForm` MUST validate with zod, render dependent selects (center→group→line, PI), map 400 field errors via `setError`, and redirect to detail on success. |
| FR-08 | 1–3 | The module MUST reach test parity — barrel, mutations (update), edit-page, project-form tests — with existing list/detail/wizard tests green as regression; Jest coverage ≥80% and `tsc --noEmit` green per PR. |

## Scenarios by PR

### PR1 — Structure (FR-01, FR-02, FR-08)

#### Scenario: Barrel resolves

- GIVEN the module is imported
- WHEN `features/projects/index.ts` resolves
- THEN components, hooks, and types export and `index.test.ts` passes

#### Scenario: Extraction preserves behavior

- GIVEN `/projects` and `/projects/[id]` render through `ProjectList`/`ProjectDetail`
- WHEN the existing list-page/detail-page tests run
- THEN they pass unchanged (regression)

### PR2 — Wizard (FR-03, FR-08)

#### Scenario: Wizard moves intact

- GIVEN `/projects/new` renders through `ProjectWizard`
- WHEN the wizard test suite runs
- THEN all steps and submit behave exactly as before

### PR3 — Edit (FR-04–FR-08)

#### Scenario: Edit link on detail

- GIVEN a non-terminal project and a non-admin viewer
- WHEN the detail actions render
- THEN an `Editar` link appears linking to `/projects/[id]/edit`

#### Scenario: Form seeds from detail

- GIVEN `/projects/[id]/edit` loads for a non-terminal project
- WHEN the form renders
- THEN values come from `useProjectDetail` and dependent selects (center→group→line, PI) are populated

#### Scenario: Save PATCHes and invalidates

- GIVEN a valid edit form
- WHEN submit succeeds
- THEN `PATCH /api/projects/{id}/` sends writable scalar fields, `["projects"]` + `["dashboard"]` invalidate, and the app redirects to the detail

#### Scenario: Edit hidden in terminal state

- GIVEN a project in `cerrado` (or `rechazado`/`cancelado`) and a non-admin viewer
- WHEN the detail renders
- THEN no `Editar` link renders (backend 403 remains the backstop)

#### Scenario: 400 field errors map to form

- GIVEN the server returns 400 with field errors
- WHEN the PATCH rejects
- THEN each field error maps via `setError` and neither redirect nor cache invalidation occurs

#### Scenario: 403 terminal-state block

- GIVEN a PATCH attempt on a terminal project (gate bypassed or admin flow)
- WHEN the server responds 403
- THEN an error toast renders and the form stays on the edit page

## Data Contract

| Endpoint | Method | Frontend use |
|----------|--------|--------------|
| `/projects/{id}/` | PATCH | Edit (FR-05); writable scalar fields: `title`, `abstract`, `objectives`, `methodology`, `expected_results`, `keywords`, `start_date`, `estimated_end_date`, `center`, `group`, `line`, `principal_investigator`; MUST NOT send `project`, `members`, `documents` |

Invalidation: `useUpdateProject` reuses `invalidateProjects` — both `["projects"]` and `["dashboard"]` on success; NOT invalidated on failure.

## Error Handling

| Error | Status | Frontend behavior |
|---|---|---|
| Field validation | 400 | zod validates first; server field errors → `setError` per field |
| Terminal-state PATCH | 403 | error toast; no redirect, no invalidation |

## UI/UX Notes

- **Edit gating** matches RN-011 (any non-terminal state), unlike advances' borrador-only gate.
- **Dependent selects** reuse `useCenters`/`useGroups`/`useLines`; changing parent resets descendant values.
- **Form shape** mirrors `AdvanceForm`/`ProductForm` (RHF + zod, create/edit-shared schema rules); `Editar` link sits in the detail action area.
