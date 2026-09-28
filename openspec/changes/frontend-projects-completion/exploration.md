# Exploration: Frontend Projects Module Completion (SIGPI §6.4)

## Current State

### Backend `apps.projects` — COMPLETE (archived; spec/design/tasks/verify all green)

Verified against `backend/apps/projects/views.py` + `serializers.py`:

- `ProjectViewSet` (ModelViewSet) exposes `list`, `retrieve`, `create`, `partial_update`/`update`, `destroy`, and 16 FSM action endpoints.
- **`PATCH /api/projects/{id}/` is fully implemented** — `ProjectCreateSerializer` is returned for both `create` and `partial_update`, and `perform_update` delegates to `ProjectService.update` (terminal-state guard for non-admin: RN-011). The frontend simply never calls it.
- Update permission: `IsProjectOwnerOrCoInvestigator` (PI, co-investigator, admin, superadmin).
- Nested `ProjectMemberViewSet` (`/projects/{pk}/members/`) and `ProjectDocumentViewSet` (`/projects/{pk}/documents/`) expose full CRUD — the create serializer deliberately has **no nested writes** ("members and documents are managed through their own dedicated nested endpoints").
- Writable scalar fields for create AND update: `title, abstract, objectives, methodology, expected_results, keywords, start_date, estimated_end_date, center, group, line, principal_investigator`.

**No backend work is needed for this change.**

### Frontend `projects` — INCOMPLETE (the only MVP module without full parity)

**Feature layer (`features/projects/`) — partially complete:**

| File | Status |
|---|---|
| `types.ts` | ✅ Complete (incl. `CreateProjectPayload`) |
| `queries.ts` | ✅ Complete (list, detail, observations, history, centers, groups, lines, researchers) |
| `schemas.ts` | ✅ Complete (4 step schemas + `ProjectDraft`) |
| `fsm.ts` | ✅ Complete (14 actions, `getProjectActions`, `isDestructiveAction`) |
| `FsmActionBar.tsx` | ✅ Exists (94 lines, consumed by detail page) |
| `mutations.ts` | ⚠️ Only `useCreateProject` + `useProjectTransition` — **NO `useUpdateProject`** |
| `index.ts` | ❌ Missing — no barrel export |

**Pages (`app/projects/`) — all inline, no extracted components:**

| Route | File | Lines | Component needed |
|---|---|---|---|
| `/projects` | `page.tsx` | 204 | `ProjectList` |
| `/projects/[id]` | `[id]/page.tsx` | 185 | `ProjectDetail` |
| `/projects/new` | `new/page.tsx` | 604 | `ProjectWizard` |
| `/projects/[id]/edit` | — | ❌ **does not exist** | `ProjectForm` (edit) |

**Tests (`__tests__/features/projects/`) — 6 files exist** (correction to the pre-discovery's implied "no tests"): `fsm.test.ts`, `schemas.test.ts`, `queries.test.tsx`, `list-page.test.tsx`, `detail-page.test.tsx`, `wizard.test.tsx`. They cover the **inline pages and hooks** — there are NO tests for an update mutation, an edit route, a barrel export, or any extracted component (they don't exist yet).

## Gap Analysis: projects vs. completed modules

| Capability | calls/products/advances/researchers/institutions | projects | Delta |
|---|---|---|---|
| Dedicated list/detail/create/edit pages | ✅ all four | ❌ no edit route | +1 route |
| Query hooks (TanStack) | ✅ | ✅ | — |
| Mutations: create/update/delete/FSM | ✅ | ⚠️ create + FSM only | +`useUpdateProject` |
| Extracted feature components | ✅ (List/Detail/Form/Managers) | ❌ all inline | +`ProjectList`, `ProjectDetail`, `ProjectWizard`, `ProjectForm` |
| Barrel `index.ts` | ✅ | ❌ | +1 file |
| Tests incl. edit/update/barrel/components | ✅ | ❌ | +mutation/edit/index/form tests |

## Affected Areas

- `frontend/features/projects/mutations.ts` — add `useUpdateProject(id)` (PATCH `/api/projects/{id}/`, invalidate `["projects"]` + `["dashboard"]`, per the existing `invalidateProjects` pattern).
- `frontend/features/projects/index.ts` — NEW barrel (pattern: `features/advances/index.ts`, `features/products/index.ts`).
- `frontend/features/projects/ProjectList.tsx` — NEW, extracted from `app/projects/page.tsx` (pattern: `ProductList`, `AdvanceList`).
- `frontend/features/projects/ProjectDetail.tsx` — NEW, extracted from `app/projects/[id]/page.tsx` (tabs + FsmActionBar + StatusBadge).
- `frontend/features/projects/ProjectWizard.tsx` — NEW, extracted from `app/projects/new/page.tsx` (5-step wizard, 604 lines — the risky one).
- `frontend/features/projects/ProjectForm.tsx` — NEW edit form (pattern: `ProductForm`, `AdvanceForm`).
- `frontend/app/projects/page.tsx`, `frontend/app/projects/[id]/page.tsx`, `frontend/app/projects/new/page.tsx` — become thin wrappers importing from the barrel.
- `frontend/app/projects/[id]/edit/page.tsx` — NEW route (seed from `useProjectDetail`, PATCH, redirect to detail).
- `frontend/__tests__/features/projects/*` — new `mutations.test.tsx` (update), `edit-page.test.tsx`, `index.test.ts`, `project-form.test.tsx`; existing page tests stay as regression for the extraction.
- `frontend/types.ts` / `schemas.ts` — optional `UpdateProjectPayload`/`projectEditSchema` (or reuse the create payload shape, as advances does).
- Backend: **NO changes**.

## Approaches

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| 1 | **Extract-first, then edit** (PR1: List/Detail + barrel; PR2: Wizard; PR3: edit mutation + form + route + tests) | Extraction is mechanical; existing page tests keep behavior honest; edit builds on clean components; matches the `frontend-advances-completion` sequencing | Edit value lands last | Medium |
| 2 | **Edit-first, then extract** | Fastest user-visible value (edit is the biggest functional gap) | Edit form imports from inline pages or duplicates wizard logic; extraction later churns both pages and tests | Med/High |
| 3 | **Reuse the wizard for edit** (seed draft from detail, PATCH on submit) | One create/edit UX; reuses step components | Wizard is 5-step create UX (review step, POST-only submit, PI defaults to first researcher); team/documents steps are dead UI in create AND would be dead in edit (backend PATCH rejects nested writes); ~600 lines of stateful wizard complexity for a scalar-field edit; diverges from the established ProductForm/AdvanceForm pattern | High |

### Sub-decision: wizard reuse vs. simpler edit form

**Recommendation: a dedicated `ProjectForm` for edit, NOT wizard reuse.** Rationale:
- The edit surface is exactly the 12 writable scalar fields + dependent selects (center→group→line, PI) — the same shape `AdvanceForm`/`ProductForm` already prove with RHF + zod.
- The wizard's team/documents steps CANNOT be persisted through `PATCH /projects/{id}/` (no nested writes); reusing the wizard for edit inherits a create-only UX with dead steps.
- The wizard uses a controlled `useState` draft + per-step validation; `ProjectForm` uses RHF + zod — mixing both patterns in one flow adds no value for a single-page edit.

## Recommendation

**Approach 1 (extract-first, then edit), 3 chained PRs**, following the completed modules verbatim:

1. **PR 1 — Structure**: extract `ProjectList` + `ProjectDetail` from the inline pages (pages become thin wrappers), add barrel `index.ts`; keep the existing `list-page`/`detail-page` tests green as regression; add `index.test.ts`.
2. **PR 2 — Wizard parity**: extract `ProjectWizard` from `new/page.tsx` (the 604-line extraction — behavior-preserving), update `wizard.test.tsx` imports to the barrel.
3. **PR 3 — Edit parity**: add `useUpdateProject` + `ProjectEditPayload`, build `ProjectForm` (RHF + zod, create/edit-shared), add `/projects/[id]/edit` route, gate edit visibility client-side (non-terminal states for non-admin; backend 403 backstop), add `mutations`/`edit-page`/`project-form` tests.

### Most critical tests (priority order)

1. **`useUpdateProject` mutation test** — PATCH path, payload shape, invalidation of `["projects"]` + `["dashboard"]` (mirrors `mutations.test.tsx` in advances/products).
2. **`edit-page.test.tsx`** — seeds from detail, PATCH fires with writable fields, redirects to detail; terminal-state gate hides the form/button (backend 403 backstop).
3. **`index.test.ts` (barrel)** — exports resolve (the pattern every completed module uses as its cheapest parity gate).
4. **Extraction regression** — existing `list-page`/`detail-page`/`wizard` tests must stay green against the extracted components (behavior unchanged).
5. **`project-form.test.tsx`** — dependent selects (center→group→line), PI options, 400 field-error mapping via `setError` (pattern: `ProductForm`/`AdvanceForm`).

## Size Estimate (changed lines, additions + deletions)

| Slice | Scope | Est. changed lines |
|---|---|---|
| PR 1 | ProjectList (~200) + ProjectDetail (~185) + barrel (~55) + page rewrites (~60) + test updates (~60) + `index.test.ts` (~55) | **~700** |
| PR 2 | ProjectWizard moved (~604 + ~574 deletions) + page rewrite (~30) + wizard test import updates (~20) | **~1,230** |
| PR 3 | `useUpdateProject` (~30) + payload/schema (~40) + `ProjectForm` (~300) + edit route (~80) + detail edit link (~10) + tests (~450) | **~910** |
| **Total** | | **~2,800–3,100** |

**400-line budget risk: HIGH.** The preflight declares `delivery_strategy: single-pr`, which conflicts with this size. `sdd-tasks` MUST forecast this and recommend chained/stacked PRs (as `frontend-advances-completion` did: 3 PRs, ~2,150 lines). The orchestrator should confirm the delivery strategy with the user before `sdd-propose`.

## Risks

1. **Wizard extraction (604 lines) is the risk centerpiece**: it defines 5 local step components (`BasicFields`, `ClassificationFields`, `TeamFields`, `DocumentsFields`, `ReviewFields`) plus a `Field` helper — the move must be behavior-preserving. The existing `wizard.test.tsx` (254 lines) is the safety net; keep it green.
2. **Wizard team/documents steps are DEAD UI (pre-existing)**: `handleSubmit` builds `CreateProjectPayload` (no `members`/`documents`), so steps 2–3 validate data that is silently discarded; the backend explicitly rejects nested writes on PATCH. This change must NOT try to fix it via the wizard (out of scope) — flag to the user as a pre-existing gap; the proper fix (MembersManager/DocumentsManager on detail, like advances' `DocumentsManager`) is a follow-up change.
3. **Edit gating semantics**: the backend allows PATCH on any **non-terminal** state (RN-011) for PI/co-investigator — NOT just `borrador` (unlike advances). Client-side gate must match (hide edit for terminal states unless admin), with the backend 403 as backstop.
4. **No MSW handler for `PATCH /api/projects/:id/`** in `mocks/handlers.ts` — edit tests must either add it or follow the existing projects tests' pattern (jest-mock `@/lib/api` directly, as `wizard.test.tsx` does).
5. **Delivery-strategy conflict**: ~2,800–3,100 changed lines vs. a 400-line review budget and a declared `single-pr` strategy — chained PRs are required; escalate to the orchestrator.
6. **Query-key discipline**: `useUpdateProject` MUST reuse `invalidateProjects` (both `["projects"]` and `["dashboard"]`) or detail/list/dashboard go stale after edit.

## Ready for Proposal

**Yes** — with two things the orchestrator should tell the user before `sdd-propose`:

1. **Delivery strategy**: single-pr conflicts with the estimated ~2,800–3,100 lines; recommend switching to chained PRs (3 slices, each within budget).
2. **Known pre-existing gap**: the wizard's team/documents steps collect but never submit member/document data; fixing it (nested-endpoint managers on the detail page) is a separate follow-up change, not part of this completion.

## Recommended Change Name

`frontend-projects-completion` (per OpenSpec convention, matching `frontend-advances-completion`).
