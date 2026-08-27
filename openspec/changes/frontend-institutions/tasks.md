# Tasks: Frontend Institutions Module (SIGPI §6.1)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1000–1150 total (PR1 ~350–400, PR2 ~350–400, PR3 ~300–350) |
| 400-line budget risk | High (aggregate); Medium per-PR |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 (stacked to main) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation + root list/tree + Institution CRUD + FSM bar + MSW + nav | PR 1 | `cd frontend; jest __tests__/features/institutions --coverage` | MSW dev: open `/institutions`, expand tree, run FSM | Delete `features/institutions`, key factory, nav item; no backend impact |
| 2 | Sede/Facultad/Center CRUD + tree children | PR 2 | `cd frontend; jest __tests__/features/institutions --coverage` | MSW dev: create sede/center via nested routes | Revert PR 2 files; PR 1 tree intact |
| 3 | Group/Line CRUD + tree polish | PR 3 | `cd frontend; jest __tests__/features/institutions --coverage` | MSW dev: leaf CRUD + keyboard nav | Revert PR 3 files; PR 2 intact |

## Dependencies Graph

```
PR1: 1.1 types → 1.2 schemas → 1.3 query-keys → 1.4 api → 1.5 fsm → 1.6 queries → 1.7 mutations → 1.8-1.10 UI → 1.11 exports → 1.12 fixtures → 1.13 MSW → 1.14 routes → 1.15 nav → 1.16 tests → 1.17 gate
PR2: PR1 → 2.1 queries → 2.2 mutations → 2.3 configs/forms → 2.4 routes → 2.5 tree → 2.6 tests → 2.7 gate
PR3: PR2 → 3.1 queries → 3.2 mutations → 3.3 configs/forms → 3.4 routes → 3.5 polish → 3.6 tests → 3.7 gate
```

## PR 1 — Foundation + Root (RF-F01/F02/F04/F06; RNF-01/02/03)

- [x] 1.1 [M] Create `frontend/features/institutions/types.ts`: 6 entity interfaces, `Page`, `EntityKind`, `InstitutionTreeNode`, `EntityConfig`, `FsmAction`.
- [x] 1.2 [M] Create `frontend/features/institutions/schemas.ts`: one Zod schema per entity; optional `sede`; contact fields.
- [x] 1.3 [S] Add `institutions` factory to `frontend/lib/query-keys.ts` mirroring `projects` (`list(scope,kind,parentId)`, `detail`).
- [x] 1.4 [S] Add `sendInstitutionId` opt-out to `frontend/lib/api.ts` (default true); institutions feature omits `X-Institution-ID`.
- [x] 1.5 [M] Create `frontend/features/institutions/fsm.ts`: activate/deactivate/archive + `getEntityActions(state,roles)`; archived terminal.
- [x] 1.6 [M] Create `frontend/features/institutions/queries.ts`: root list/detail hooks (`scope=null`, no membership needed) + DRF `next` pagination helper.
- [x] 1.7 [M] Create `frontend/features/institutions/mutations.ts`: CRUD + FSM hooks; invalidate `institutions.all` on success only.
- [x] 1.8 [M] Create `frontend/features/institutions/EntityForm.tsx`: RHF+zodResolver+`setError`; 400 errors keep values (RF-F02 duplicate code).
- [x] 1.9 [M] Create `frontend/features/institutions/{FsmActionBar,EntityDetail}.tsx`: actions from fsm.ts, ConfirmDialog on destructive, StatusBadge (RF-F04 archived terminal).
- [x] 1.10 [L] Create `frontend/features/institutions/InstitutionTree.tsx`: recursive `tree`/`treeitem`, `aria-expanded`, roving focus, keyboard nav (RNF-01).
- [x] 1.11 [S] Create `frontend/features/institutions/index.ts` exports.
- [x] 1.12 [M] Create `frontend/fixtures/institutions.ts` + wire `frontend/fixtures/index.ts`: 6-entity seed.
- [x] 1.13 [M] Add MSW handlers in `frontend/mocks/handlers.ts`: institutions CRUD/FSM + nested pages; existing handlers stay green.
- [x] 1.14 [M] Create `frontend/app/institutions/{page,new,[id]/page,[id]/edit}`: tree, EmptyState bootstrap (no membership), forms.
- [x] 1.15 [S] Add role-gated "Estructura institucional" to `frontend/components/shell/Sidebar.tsx` (RF-F06).
- [x] 1.16 [L] RED tests in `frontend/__tests__/features/institutions/`: tree a11y, CRUD flows, bootstrap, nav, 409 guard (≥80%; tree ≥90%).
- [x] 1.17 [S] Gate: `eslint`, `tsc --noEmit`, `jest --coverage` green (RNF-03).

## PR 2 — Sede/Facultad/ResearchCenter (RF-F03, RF-F05)

- [x] 2.1 [M] Extend `queries.ts`: sede/facultad/center hooks keyed by (institution, parentId); enabled with both.
- [x] 2.2 [M] Extend `mutations.ts`: nested-URL CRUD for 3 entities; invalidate `institutions.all`.
- [x] 2.3 [M] Add EntityConfigs (admin threshold; center `parent_type` institution|sede|facultad) + form/detail field extensions.
- [x] 2.4 [M] Create routes `app/institutions/[id]/sedes|facultades|centers/**`; parent from params, never in body.
- [x] 2.5 [M] Tree: render child levels under nodes with per-node actions.
- [x] 2.6 [L] RED tests: admin creates sede, center→facultad nesting, delete-with-children 409, RoleGuard denial (RF-F05).
- [x] 2.7 [S] Gate: `eslint` + `tsc --noEmit` + coverage green.

## PR 3 — ResearchGroup/ResearchLine + Polish (RF-F03 leaf; RNF completion)

- [x] 3.1 [M] Extend `queries.ts`: group/line hooks (`/api/centers/{pk}/groups/`, `/api/groups/{pk}/lines/`).
- [x] 3.2 [M] Extend `mutations.ts`: group/line CRUD; invalidate `institutions.all`.
- [x] 3.3 [M] Add group/line configs (director threshold) + leaf form/detail fields.
- [x] 3.4 [M] Create routes `.../centers/[centerId]/groups/**` and `.../groups/[groupId]/lines/**`.
- [x] 3.5 [M] Tree polish: leaf render, unknown-status badge fallback, per-level EmptyState, axe pass (RNF-01).
- [x] 3.6 [L] RED tests: leaf CRUD, 3-level keyboard nav, archived terminal; aggregate ≥80%.
- [x] 3.7 [S] Gate: full suite (`eslint`, `tsc`, `jest --coverage`) green.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| PR1/PR2 near 400-line ceiling | Shared EntityConfig-driven components; trim slice if diff exceeds budget |
| WCAG tree a11y + coverage floor (tree ≥90%) | Recursive disclosure primitive + keyboard nav; test-first (strict TDD) |
| `/api/` vs `/api/v1/` prefix unconfirmed | Apply verifies live API prefix before wiring (design open question) |
| Status enum mismatch (active/deactivated/archived) | Consume verbatim with fallback badge; verify against live API |
