# Proposal: Frontend Institutions Module (SIGPI §6.1)

## Intent

The institutions backend (6-entity hierarchy + lifecycle FSM, 245 tests) is complete and archived, but the frontend has **zero management UI** for it — the projects wizard is the only consumer of the institutions API. Superadmins/admins/directors cannot create, edit, or manage the institutional structure (Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine) from the app. This change delivers the full `features/institutions` module: hierarchy tree, CRUD at every level, FSM lifecycle actions, and navigation integration.

## Scope

### In Scope
- `features/institutions` module: types, zod schemas, queries, mutations, fsm table
- `institutions` query-key factory in `lib/query-keys.ts` + institution-scoped invalidation
- Hierarchical tree view (custom recursive component, WCAG 2.1 AA) with StatusBadge + per-node actions
- CRUD forms (RHF + zod) and detail views for all 6 entities, parent injected via URL
- FsmActionBar (activate/deactivate/archive) with ConfirmDialog on destructive actions
- Role-gated writes (superadmin > admin > director) via existing RoleGuard
- MSW fixtures/handlers + Jest coverage ≥80%
- Sidebar nav item "Estructura institucional"

### Out of Scope
- Any backend change (API is complete for this module)
- Drag-and-drop re-parenting (no backend move API exists)
- Completeness-validation indicators (backend has no such capability)
- Bulk import/export of entities
- Deep links from projects module to centers

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `institutions-ui`: Frontend module for managing the 6-entity institutional hierarchy — tree visualization, per-level CRUD, FSM lifecycle actions, role-gated writes, institution-scoped server state

### Modified Capabilities
- None (backend `institutions` spec is unchanged; `frontend-mvp` requirements untouched)

## Approach

**Sliced read-first delivery** (exploration Approach 1, recommended): 3 chained PRs within the 400-line review budget, each independently verifiable. Reuse projects/advances patterns verbatim: `fsm.ts` + FsmActionBar, ConfirmDialog, StatusBadge, EmptyState, query-key factories, MSW, coverage ≥80%. Typed per-entity config drives shared form/tree logic — no over-abstraction. Tenant scoping relies on the auth store's `activeInstitution` (session is source of truth; `X-Institution-ID` is vestigial). Mutations POST to nested URLs (parent from URL, not body); 409 lifecycle/duplicate errors surface via Toaster.

| Slice | PR Scope | Est. Lines |
|---|---|---|
| 1 | Foundation (types/schemas/queries/mutations/fsm) + institutions list/tree + Institution CRUD + FSM bar + MSW + nav item | ~350–400 |
| 2 | Sede / Facultad / ResearchCenter CRUD + tree integration | ~350–400 |
| 3 | ResearchGroup / ResearchLine CRUD + tree polish | ~300–350 |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/features/institutions/**` | New | types, schemas, queries, mutations, fsm, InstitutionTree, EntityForm, EntityDetail, FsmActionBar |
| `frontend/app/institutions/**` | New | list/tree, detail, create/edit routes |
| `frontend/lib/query-keys.ts` | Modified | add `institutions` key factory |
| `frontend/components/shell/Sidebar.tsx` | Modified | role-gated nav item |
| `frontend/mocks/handlers.ts` + `frontend/fixtures/` | Modified | MSW fixtures for 6 entities |
| Backend | None | no changes expected |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Custom tree component violates WCAG 2.1 AA or coverage floor | Med | Recursive disclosure primitive w/ keyboard nav + aria roles; Jest ≥80% per PR |
| Superadmin bootstrap: first institution with no memberships | Med | Institutions list must not require `activeInstitution`; hide selector when ≤1 institution |
| FSM 409s ("Deactivate or archive children first.") confuse users | Med | Surface backend `detail` verbatim via Toaster; disable invalid transitions in FsmActionBar |
| 400-line review budget exceeded | Med | 3 chained PRs; slice sizes forecast in sdd-tasks |
| Tenant scoping drift (session vs header) | Low | All queries keyed off auth store `activeInstitution`; switch clears cache |

## Rollback Plan

Feature-branch chain: revert each PR independently (remove feature files, route, nav item, key factory) — no backend or data impact. PR #1 rolls back by deleting `features/institutions` foundation + nav entry; UI-only, zero migration risk.

## Dependencies

- None new: TanStack Query, RHF + zod, shadcn/ui, Zustand, MSW already present
- Backend institutions API (complete, archived)

## Success Criteria

- [ ] Users can view the full hierarchy tree with expand/collapse and status badges
- [ ] Superadmins/admins/directors can create, edit, and delete entities at their permission level
- [ ] Lifecycle transitions work with correct guards; 409s surface clearly via Toaster
- [ ] Archived entities show as terminal (no reactivate action)
- [ ] Jest coverage ≥80%; ESLint + `tsc --noEmit` green per PR
- [ ] Tree component passes WCAG 2.1 AA checks
- [ ] Sidebar nav item role-gated and functional

## Recommended First Slice

**PR 1**: `features/institutions` foundation + institutions list/tree + Institution CRUD + FSM bar + MSW fixtures + nav item (~350–400 lines).
