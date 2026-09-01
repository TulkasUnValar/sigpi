# Proposal: Frontend Calls Module (SIGPI §6.8)

## Intent

The `apps.calls` backend (4 entities, 6-state FSM, archived 2026-07-29) is complete, but the frontend has zero calls UI — no references to the API exist. This change delivers `features/calls` + routes so users can list, filter, create, manage, and drive convocatorias through their lifecycle.

## Scope

### In Scope
- `features/calls` (types, schemas, constants, fsm, queries, mutations, permissions) + routes `/calls`, `/calls/new`, `/calls/[id]` (4 tabs), `/calls/[id]/edit`
- List: paginated table + status/call_type filters (PR1) + RoleGuard-gated create CTA
- FSM bar: 5 transitions (`open_call|close_call|start_evaluation|publish_results|archive`) reusing the projects `FsmActionBar` pattern; `archive` terminal/destructive → ConfirmDialog
- Delete (director+): gated to `borrador` + zero linked CallProjects; ConfirmDialog
- Managers: Documents (metadata-only CRUD), Projects (link/unlink), State history (read-only)
- MSW fixtures/handlers; Sidebar "Convocatorias"; StatusBadge `abierta|en_evaluacion|resultados_publicados`; Jest ≥80%, `tsc --noEmit`

### Out of Scope
- Backend changes; file uploads; call reports/statistics; external publication; projects-wizard fix (pagination bug already merged)

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `calls-ui`: list + filters, create, 4-tab detail, edit, 5 FSM transitions, delete gating, institution-scoped server state, shell integration (Sidebar + StatusBadge), MSW/coverage

### Modified Capabilities
- None — no spec-level behavior change elsewhere (wizard pagination fix already merged)

## Approach

Sliced read-first delivery (exploration Approach 1), 3 chained PRs mirroring researchers:
- **PR1** — foundation (types/schemas/constants/query-keys/StatusBadge/Sidebar) + list + filters + create + detail Overview + FSM bar + MSW list/create/FSM
- **PR2** — Documents (metadata-only), Projects link/unlink, State history tabs + delete (projects-count gate) + fixtures/handlers
- **PR3** — polish + verification (Jest ≥80%, `tsc --noEmit`)

Backend untouched; zod conditional validation (external_entity, date ordering) mirrors backend serializer rules.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/features/calls/**` | New | module + `frontend/app/calls/**` routes |
| `frontend/lib/query-keys.ts` | Modified | `calls` factory (list/detail/documents/projects/stateHistory) |
| `frontend/components/shell/Sidebar.tsx` | Modified | "Convocatorias" nav item (all roles) |
| `frontend/components/shared/StatusBadge.tsx` | Modified | calls FSM status entries |
| `frontend/mocks/handlers.ts` + `frontend/fixtures/calls.ts` | Modified/New | MSW |
| Backend | — | none |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Exceeds 400-line review budget | Med | 3 chained PRs; sizes forecast in sdd-tasks |
| Destructive UX (archive/delete) | Med | ConfirmDialog; surface 409/403 via getErrorMessage |
| Validation mismatch → 400s | Med | zod mirrors backend serializer rules exactly |
| `director_centro` role-name mapping | Low | confirm with auth contract in design (consistent with researchers) |

## Rollback Plan

Feature-branch chain: revert each PR independently; frontend-only, no data/backend impact.

## Dependencies

None new: backend calls API complete; TanStack Query, RHF + zod, shadcn/ui, MSW, Zustand present; projects `FsmActionBar` + institutions types reused.

## Success Criteria

- [ ] List (with status/type filters), create, 4-tab detail, edit, 5 FSM transitions, and gated delete work end-to-end with correct role gating
- [ ] Documents metadata-only; project link conflicts (409) surface; state history read-only
- [ ] Jest ≥80%, `tsc --noEmit` green; "Convocatorias" nav present for all authenticated roles
