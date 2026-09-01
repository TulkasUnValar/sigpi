# Apply Progress — frontend-researchers (PR1 + PR2 + PR3)

**Status**: PR1 complete (15/15, tasks 1.1–1.15). PR2 complete (8/8, tasks 2.1–2.8). PR3 complete (6/6, tasks 3.1–3.6).
**Branch**: PR1 on `feature/frontend-researchers-pr1` (off `main`); PR2 on `feature/frontend-researchers-pr2` (off `feature/frontend-researchers-pr1`); PR3 on `feature/frontend-researchers-pr3` (off `feature/frontend-researchers-pr2`). No PRs created.
**Mode**: Strict TDD (runner `cd frontend; jest --passWithNoTests`).
**Date**: 2026-09-01

---

## PR1: Foundation (Complete — preserved)

**Status**: PR1 complete (15/15 tasks, tasks 1.1–1.15).
**Branch**: `feature/frontend-researchers-pr1` (off `main`) — work-unit commits only, no PR created.

### Executive Summary (PR1)

Implemented the PR1 foundation slice of the researchers module per the
`researchers-ui` spec and design: institution-scoped data layer (types,
schemas, fsm, query keys, queries, mutations, permissions), the four
routes (`/researchers`, `/researchers/new`, `/researchers/{id}`,
`/researchers/{id}/edit`), completeness bar, deactivate ConfirmDialog
flow, shell integration (sidebar `Investigadores` for every role +
`inactive` StatusBadge mapping), and MSW fixtures/handlers. All gates
green: 75 suites / 535 tests, coverage ≥80% (lines 92.8, branches 88.03,
functions 82.92, statements 91.91), `tsc --noEmit` clean, ESLint and
Prettier clean. Also repaired the repo's broken pre-commit hooks.

### TDD Cycle Evidence (PR1)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | types.ts (validated via `tsc --noEmit`) | Structural | N/A (new) | ➖ type-only | ✅ tsc clean | ➖ Single | ➖ None needed |
| 1.2 | `__tests__/features/researchers/schemas.test.ts` | Unit | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 4 cases | ➖ None needed |
| 1.3 | `__tests__/features/researchers/fsm.test.ts` | Unit | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 4 cases | ➖ None needed |
| 1.4 | `__tests__/features/researchers/query-keys.test.ts` | Unit | ✅ 448 baseline | ✅ Written | ✅ 4/4 | ✅ 3 cases | ➖ None needed |
| 1.5 | `__tests__/features/researchers/queries.test.tsx` | Unit | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 3 cases | ✅ test fix (page=1 qs) |
| 1.6 | `__tests__/features/researchers/mutations.test.tsx` | Unit | N/A (new) | ✅ Written | ✅ 3/3 | ✅ 3 cases | ➖ None needed |
| 1.7 | `__tests__/features/researchers/CompletenessBar.test.tsx` | Unit | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 3 cases | ➖ None needed |
| 1.8 | `__tests__/features/researchers/ResearcherList.test.tsx` + `list-page.test.tsx` | Component | N/A (new) | ✅ Written | ✅ 10/10 | ✅ 4 cases | ✅ aria-label→text |
| 1.9 | `__tests__/features/researchers/ResearcherForm.test.tsx` + `new-page.test.tsx` | Component | N/A (new) | ✅ Written | ✅ 8/8 | ✅ 4 cases | ✅ test defaults fix |
| 1.10 | `__tests__/features/researchers/ResearcherDetail.test.tsx` + `detail-page.test.tsx` | Component | N/A (new) | ✅ Written | ✅ 10/10 | ✅ 3 cases | ➖ None needed |
| 1.11 | `__tests__/features/researchers/edit-page.test.tsx` | Component | N/A (new) | ✅ Written | ✅ 4/4 | ✅ 4 cases | ➖ None needed |
| 1.12 | `__tests__/features/researchers/DeactivateResearcherButton.test.tsx` + `permissions.test.ts` | Component | N/A (new) | ✅ Written | ✅ 13/13 | ✅ 4 cases | ✅ mock-clear fix |
| 1.13 | `__tests__/components/shared/StatusBadge.test.tsx` + `__tests__/components/shell/shell.test.tsx` | Unit | ✅ 448 baseline | ✅ Written | ✅ 23/23 | ✅ 3 cases | ➖ None needed |
| 1.14 | `__tests__/features/researchers/fixtures.test.ts` | Unit | N/A (new) | ✅ Written | ✅ 4/4 | ✅ 4 cases | ➖ None needed |
| 1.15 | All `__tests__/features/researchers/*` + `index.test.ts` | Mixed | ✅ 448 baseline | ✅ Written | ✅ 83/83 | ✅ full | ✅ prettier pass |

### Work Unit Evidence (PR1)

| Evidence | Required value |
|---|---|
| Focused test command and result | `jest __tests__/features/researchers --runInBand` → 17 suites, 83 tests passed |
| Runtime harness command/scenario and result | `jest --coverage --runInBand` (full) → 75 suites / 535 passed; All files 91.91 stmts / 88.03 branch / 82.92 funcs / 92.8 lines; `tsc --noEmit` clean; eslint clean; prettier clean. `npm run dev` not executed in this env (RTL + mocked api layer, matching repo pattern) |
| Rollback boundary | Revert `feature/frontend-researchers-pr1` (or the 4 work-unit commits): removes `features/researchers/*`, `app/researchers/*`, `lib/query-keys.ts` researchers factory, `Sidebar.tsx` item, `StatusBadge.tsx` inactive mapping, `fixtures/researchers.ts`, researcher handlers, and researchers tests. Projects/institutions unaffected |

---

## PR2: Nested Managers (Complete)

**Status**: PR2 complete (8/8 tasks, tasks 2.1–2.8).
**Branch**: `feature/frontend-researchers-pr2` (off `feature/frontend-researchers-pr1`) — work-unit commits only, no PR created.

### Executive Summary (PR2)

Implemented the PR2 nested-managers slice per the `researchers-ui` spec
and design: three manager components wired into the researcher detail
tabs (`AffiliationsManager` with dependent center → group → line selects
and primary semantics, `ExternalProfilesManager`, `AttachmentsManager`
metadata-only), nested mutations (create/delete/set_primary) that
invalidate the researchers cache, new fixtures + MSW nested handlers
(CRUD, primary switching, cross-institution 400), and full Jest/RTL
coverage including a detail-page wiring test. All gates green: 80 suites /
569 tests (full suite), researchers module coverage ≥80% (97.34 stmts /
85.46 branch / 81.36 funcs / 98.02 lines), `tsc --noEmit` clean, ESLint
clean, Prettier clean.

### TDD Cycle Evidence (PR2)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1 | `AffiliationsManager.test.tsx` | Component | N/A (new) | ✅ Written | ✅ 8/8 | ✅ 3 cases | ✅ userEvent fix |
| 2.2 | `AffiliationsManager.test.tsx` (primary + set_primary + disable) | Component | N/A (new) | ✅ Written | ✅ (see 2.1) | ✅ 3 cases | ➖ None |
| 2.3 | `AffiliationsManager.test.tsx` (cross-institution 400 → Toaster) | Component | N/A (new) | ✅ Written | ✅ 1/1 | ➖ Single | ➖ None |
| 2.4 | `ExternalProfilesManager.test.tsx` (6 tests) | Component | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 4 cases | ✅ link-role fix |
| 2.5 | `AttachmentsManager.test.tsx` (6 tests) | Component | N/A (new) | ✅ Written | ✅ 6/6 | ✅ 4 cases | ✅ link-role fix |
| 2.6 | `detail-page.test.tsx` (wiring test: tabs render managers) | Component | ✅ PR1 baseline | ✅ Written | ✅ 1/1 | ➖ Single | ➖ None |
| 2.7 | `fixtures.test.ts` (nested fixtures integrity) + nested mutations | Unit | ✅ PR1 baseline | ✅ Written | ✅ 7/7 | ✅ 3 cases | ➖ None |
| 2.8 | `nested-mutations.test.tsx` + `managers-helpers.test.ts` (validation helpers) | Mixed | N/A (new) | ✅ Written | ✅ 8/8 | ✅ full | ✅ prettier |

### Test Summary (PR2)

- **Total tests written (PR2)**: 34 new (nested-mutations 7, AffiliationsManager 8, ExternalProfilesManager 6, AttachmentsManager 6, managers-helpers 4, fixtures +1, detail-page wiring +1, index barrel — some counted in suites)
- **Full suite**: 80 suites / 569 tests passing
- **Layers used**: Component (RTL managers + wiring), Unit (helpers, fixtures, nested mutations)
- **Approval tests**: 0 — no refactoring tasks in PR2
- **Pure functions created**: `hasAffiliationSelection`, `isFirstAffiliation`, `affiliationLabel`, `profileFormValid`, `attachmentFormValid`

### Work Unit Evidence (PR2)

| Evidence | Required value |
|---|---|
| Focused test command and result | `jest __tests__/features/researchers --runInBand` → 22 suites, 117 tests passed |
| Runtime harness command/scenario and result | `jest --coverage --runInBand` (full) → 80 suites / 569 passed; researchers module 97.34 stmts / 85.46 branch / 81.36 funcs / 98.02 lines; `tsc --noEmit` clean; eslint clean; prettier --check clean. `npm run dev` not executed in this env (managers exercised via RTL + mocked api layer, matching repo pattern) |
| Rollback boundary | Revert `feature/frontend-researchers-pr2` (or the PR2 work-unit commits): removes `AffiliationsManager.tsx`, `ExternalProfilesManager.tsx`, `AttachmentsManager.tsx`, `constants.ts`, nested mutations/types, nested fixtures + handlers, manager tests, and the tab wiring in `[id]/page.tsx`. PR1 Overview/edit and PR3 wizard unaffected |

### Files Changed (PR2)

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/features/researchers/types.ts` | Modified | Added `CreateAffiliationPayload`, `CreateExternalProfilePayload`, `CreateAttachmentPayload` |
| `frontend/features/researchers/constants.ts` | Created | `PROFILE_PROVIDERS`, `ATTACHMENT_TYPES`, labels for both |
| `frontend/features/researchers/mutations.ts` | Modified | Nested mutations: `useCreateAffiliation`, `useDeleteAffiliation`, `useSetPrimaryAffiliation`, `useCreateExternalProfile`, `useDeleteExternalProfile`, `useCreateAttachment`, `useDeleteAttachment`; all invalidate `["researchers"]` |
| `frontend/features/researchers/AffiliationsManager.tsx` | Created | Dependent selects center → group → line (clear downstream), auto-primary first affiliation, set_primary toggle (disabled for primary), delete, cross-institution 400 → Toaster |
| `frontend/features/researchers/ExternalProfilesManager.tsx` | Created | Inline create/delete for `{provider, url}` (provider ∈ cvlac/orcid/google_scholar/linkedin/researchgate) |
| `frontend/features/researchers/AttachmentsManager.tsx` | Created | Metadata-only `{name, type, external_url}` inline create/delete, rendered as external link |
| `frontend/features/researchers/index.ts` | Modified | Exported managers, nested mutations, constants, validation helpers |
| `frontend/app/researchers/[id]/page.tsx` | Modified | Wired the three managers into the Affiliations / Perfiles externos / Adjuntos tabs (replaced read-only nested lists) |
| `frontend/fixtures/researchers.ts` | Modified | Added `fixtureAffiliations`, `fixtureExternalProfiles`, `fixtureAttachments` |
| `frontend/fixtures/index.ts` | Modified | Registered the nested fixtures |
| `frontend/mocks/handlers.ts` | Modified | Added nested researcher stores + handlers: affiliations (list/create w/ cross-institution 400/delete/set_primary), profiles (list/create/delete), attachments (list/create/delete) |
| `frontend/__tests__/features/researchers/nested-mutations.test.tsx` | Created | 7 tests covering nested mutation endpoints + invalidation |
| `frontend/__tests__/features/researchers/AffiliationsManager.test.tsx` | Created | 8 tests: list/primary, dependent selects, set_primary, delete, cross-institution 400 |
| `frontend/__tests__/features/researchers/ExternalProfilesManager.test.tsx` | Created | 6 tests: render link, empty, create+clear, disabled gate, delete |
| `frontend/__tests__/features/researchers/AttachmentsManager.test.tsx` | Created | 6 tests: render link, empty, create+clear, disabled gate, delete |
| `frontend/__tests__/features/researchers/managers-helpers.test.ts` | Created | 4 unit tests for validation/formatting helpers |
| `frontend/__tests__/features/researchers/fixtures.test.ts` | Modified | Nested fixtures integrity test |
| `frontend/__tests__/features/researchers/detail-page.test.tsx` | Modified | Wiring test: tabs render the three managers |
| `openspec/changes/frontend-researchers/tasks.md` | Modified | Tasks 2.1–2.8 marked `[x]` |

### Deviations from Design (PR2)

1. **Native `<select>` for the dependent/constrained selects** instead of the shadcn Radix `Select`. The repo has no Radix-Select RTL precedent and jsdom dropdown testing is flaky; native selects are equally "constrained selects", fully accessible, and deterministically testable. Consistent with the design's intent (constrained select options).
2. **Affiliation list renders FK ids** (e.g. `center-1 · group-1 · line-1`) rather than resolving to names. The API's `ResearcherAffiliationSerializer` exposes only FK ids; resolving arbitrary existing affiliations to names would require loading every group/line parent, which is out of scope. The create form resolves the current selection's names via the hierarchy hooks.

### Issues Found (PR2)

- `tsc --noEmit` flagged two `noUncheckedIndexedAccess` issues in the new tests (`primaryButtons[1]`, `fixtureResearchers[0]`); fixed with non-null assertions.
- Radix Select dropdown interaction is not reliably testable in jsdom (no repo precedent); chose native selects (see deviations).
- The `msw/node` module-resolution limitation (documented in PR1) still applies — nested handlers are exercised by the runtime dev flow and validated via fixtures integrity, not MSW-in-jest.

---

## PR3: Wizard Fix + Polish + Verify (Complete)

**Status**: PR3 complete (6/6 tasks, tasks 3.1–3.6).
**Branch**: `feature/frontend-researchers-pr3` (off `feature/frontend-researchers-pr2`) — 3 work-unit commits, no PR created.

### Executive Summary (PR3)

Fixed the projects-wizard researcher pagination bug and applied a11y polish
per the `projects-ui` delta spec and design. `useResearchers()` in
`features/projects/queries.ts` now consumes the paginated
`Page<ResearcherList>` envelope from `/api/researchers/` (was typed as a bare
`ResearcherOption[]`, which crashed the wizard against the real paginated
API), and `app/projects/new/page.tsx` maps `results` to `{id, full_name}`
options — first page only, no page-2 fetch. The wizard's MSW researchers
handler already existed from PR1 (paginated envelope); added a fixtures
contract test proving the seeded rows map to the wizard's option shape. A11y
polish on the researchers routes: polite live region for the list loading
state, semantic table name + `scope=col` headers, polite pagination region,
and `aria-describedby` linking field errors to their inputs. All gates green:
81 suites / 578 tests (full suite), coverage ≥80% on every axis (whole-project
92.31 stmts / 87.87 branch / 81.3 funcs / 93.28 lines), `tsc --noEmit` clean,
ESLint clean, Prettier clean.

### TDD Cycle Evidence (PR3)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 | `__tests__/features/projects/queries.test.tsx` | Unit | ✅ 27/145 | ✅ Written (runtime fail + `tsc` type-contract fail) | ✅ 2/2 | ✅ 2 cases | ✅ mock-clear + capture fix |
| 3.2 | `queries.test.tsx` (useResearchers) | Unit | ✅ 27/145 | ✅ `tsc` TS2322 on `Page<ResearcherList>` | ✅ Passed | ✅ (see 3.1) | ✅ removed dead import |
| 3.3 | `__tests__/features/projects/wizard.test.tsx` | Component | ✅ 27/145 | ✅ Crash (`researchers.map is not a function`) | ✅ 7/7 | ✅ 3 cases | ✅ isolated call count |
| 3.4 | `__tests__/features/researchers/fixtures.test.ts` | Unit | ✅ PR2 baseline | ✅ Added option-contract test | ✅ 6/6 | ✅ 2 cases | ➖ None needed |
| 3.5 | `list-page.test.tsx` + `ResearcherList.test.tsx` + `ResearcherForm.test.tsx` | Component | ✅ PR2 baseline | ✅ 4 RED | ✅ 8/8, 7/7, 6/6 | ✅ 4 cases | ➖ None needed |
| 3.6 | Full `jest --coverage` + `tsc` + ESLint + Prettier | Mixed | ✅ 155/155 focused | N/A (verification) | ✅ 578/578 | ✅ full | ✅ prettier pass |

### Test Summary (PR3)

- **Full suite**: 81 suites / 578 tests passing
- **Layers used**: Unit (query contract, fixtures), Component (wizard RTL, list page, list/form a11y)
- **Approval tests**: 0 — no refactoring of behavior in PR3 (the wizard mapping was a bug fix, not a refactor)
- **Pure functions created**: 0 (mapping uses an existing pure `map` in the page)
- **New tests added (PR3)**: 10 (2 query, 3 wizard scenarios, 1 fixtures option-contract, 4 a11y)

### Work Unit Evidence (PR3)

| Evidence | Required value |
|---|---|
| Focused test command and result | `jest __tests__/features/projects __tests__/features/researchers --runInBand` → 28 suites, 155 tests passed |
| Runtime harness command/scenario and result | `jest --coverage --passWithNoTests --runInBand` (full) → 81 suites / 578 passed; All files 92.31 stmts / 87.87 branch / 81.3 funcs / 93.28 lines; `tsc --noEmit` clean (exit 0); eslint clean; prettier --check clean. `npm run dev` not executed in this env (wizard + researchers exercised via RTL + mocked api layer, matching repo pattern) |
| Rollback boundary | Revert `feature/frontend-researchers-pr3` (or the 3 PR3 work-unit commits): `useResearchers()` falls back to `ResearcherOption[]`, wizard mapping reverts, and a11y attributes revert. PR1/PR2 unaffected; no data loss (wizard bug resurfaces only) |

### Files Changed (PR3)

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/features/projects/queries.ts` | Modified | `useResearchers()` now fetches `Page<ResearcherList>` (was `ResearcherOption[]`); removed unused import |
| `frontend/app/projects/new/page.tsx` | Modified | Maps `results` to `{id, full_name}` options via `useMemo`; PI/team selects use `researcherOptions`; default PI uses `researcherOptions[0]` |
| `frontend/__tests__/features/projects/queries.test.tsx` | Created | Paginated contract (count/next/previous/results) + "never fetches page 2" |
| `frontend/__tests__/features/projects/wizard.test.tsx` | Modified | Researchers mock returns paginated envelope; 3 scenarios (PI options from results, team options, page-2 not fetched) |
| `frontend/app/researchers/page.tsx` | Modified | Loading skeletons wrapped in `role="status"` with accessible label |
| `frontend/features/researchers/ResearcherList.tsx` | Modified | `aria-label` on table, `scope="col"` headers, `aria-live="polite"` pagination count |
| `frontend/features/researchers/ResearcherForm.tsx` | Modified | Field errors carry stable ids; inputs link via `aria-describedby` (incl. document_type select) |
| `frontend/__tests__/features/researchers/list-page.test.tsx` | Modified | Loading announced via `role="status"` test |
| `frontend/__tests__/features/researchers/ResearcherList.test.tsx` | Modified | Table name/headers + polite pagination region tests |
| `frontend/__tests__/features/researchers/ResearcherForm.test.tsx` | Modified | `aria-describedby` field-error test |
| `frontend/__tests__/features/researchers/fixtures.test.ts` | Modified | Option-contract test (seeded rows map to `{id, full_name}` with unique ids) |
| `openspec/changes/frontend-researchers/tasks.md` | Modified | Tasks 3.1–3.6 marked `[x]` |

### Deviations from Design (PR3)

None — implementation matches design. The design specified `useResearchers()`
fetching `Page<ResearcherList>` and the wizard mapping `results` to
`{id, full_name}` with no page-2 fetch; implemented exactly. The MSW
researchers handler for the wizard was already present from PR1 (paginated
envelope), so task 3.4 was satisfied by adding the fixture option-contract
test rather than a redundant new handler.

### Issues Found (PR3)

- The wizard previously crashed because `researchersQuery.data` was the
  paginated envelope object, not an array — `researchers.map is not a
  function`. Fixed by mapping `results` in the page.
- Test-hygiene: mock call history accumulates across tests within a file;
  added `jest.clearAllMocks()` (queries.test.tsx) and a targeted `mockClear`
  (wizard.test.tsx page-2 case).
- The `msw/node` module-resolution limitation (documented PR1/PR2) still
  applies — the wizard's MSW researcher handler is exercised by the runtime
  dev flow and validated via the fixtures contract test, not MSW-in-jest.

---

## Remaining Tasks

None — all PR3 tasks (3.1–3.6) complete. Change `frontend-researchers` is
fully implemented across PR1, PR2, PR3.

## Workload / PR Boundary (cumulative)

- Mode: stacked PR slice (auto-chain, stacked-to-main)
- PR1 work unit: Foundation (tasks 1.1–1.15) — commits on `feature/frontend-researchers-pr1`
- PR2 work unit: Nested managers (tasks 2.1–2.8) — commits on `feature/frontend-researchers-pr2`
- PR3 work unit: Wizard fix + polish + verify (tasks 3.1–3.6) — commits on `feature/frontend-researchers-pr3` (3 work-unit commits: `c65ca78` wizard pagination, `96732db` a11y + handler contract, `27ef617` polite pagination region)
- Estimated review budget impact: PR3 ~250 authored lines (within the 400-line budget; the aggregate across all three PRs exceeds it by design of the approved 3-PR auto-chain split)
- Rollback: revert each PR branch independently

## Status

PR1: 15/15 complete. PR2: 8/8 complete. PR3: 6/6 complete. All 29 tasks done. Ready for review of the PR3 slice (then archive).
