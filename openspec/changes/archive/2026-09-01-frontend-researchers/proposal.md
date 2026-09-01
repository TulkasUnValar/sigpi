# Proposal: Frontend Researchers Module (SIGPI §6.3)

## Intent

The researchers backend (4 entities, 207 tests) is complete and archived, but the frontend has zero management UI, and the projects wizard calls the API with a pagination bug that crashes against the real endpoint. This change delivers `features/researchers` plus the wizard fix.

## Scope

### In Scope
- `features/researchers` module (types, schemas, queries, mutations, fsm) + routes: list, `/new`, `/[id]` detail (Overview, Affiliations, External profiles, Attachments tabs), `/[id]/edit`
- Completeness 0–100 bar (custom); single `deactivate` (admin+, destructive → ConfirmDialog); reactivation via edit-form `is_active` toggle
- Affiliations manager (dependent selects center→group→line, `is_primary` + set_primary); external profiles & attachments (metadata-only) managers
- MSW fixtures/handlers + Jest ≥80%; Sidebar "Investigadores"; StatusBadge active/inactive
- Fix `useResearchers()` in `features/projects/queries.ts` for paginated `Page<ResearcherList>` (crashes against real API)

### Out of Scope
- Any backend change; file uploads (attachments metadata-only); `activate`/`archive` actions; `/researchers/me/`; automatic CvLAC sync

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `researchers-ui`: list, create, detail with nested managers (affiliations, external profiles, attachments), edit, completeness, deactivate, institution-scoped server state

### Modified Capabilities
- `projects-ui`: fix `useResearchers()` to consume the paginated researcher list so the create-wizard PI selector works against the real API (masked by api-module mocks)

## Approach

**Sliced read-first delivery** (exploration Approach 1): 3 chained PRs within 400-line budget — (1) foundation + list + create + detail overview + completeness + deactivate + Sidebar/StatusBadge + MSW; (2) affiliations/external profiles/attachments managers + fixtures; (3) wizard pagination fix + polish + verify. Reuse institutions/advances patterns; no FSM → no FsmActionBar.

## Affected Areas

- **New**: `frontend/features/researchers/**`, `frontend/app/researchers/**`
- **Modified**: `lib/query-keys.ts` (factory); `features/projects/queries.ts` + `app/projects/new/page.tsx` (pagination); `components/shell/Sidebar.tsx`, `shared/StatusBadge.tsx`; `mocks/handlers.ts` + `fixtures/researchers.ts` (MSW)
- **Backend**: none

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Projects wizard bug must be fixed | High | PR3 mandatory; MSW researchers handler |
| No reactivate/me endpoints | Med | Edit-form toggle; match `researcher.user === currentUser.id` |
| Affiliation edge cases | Med | Surface `detail` via Toaster; dependent selects constrain targets |
| 400-line review budget exceeded | Med | 3 chained PRs; sizes forecast in sdd-tasks |

## Rollback Plan

Feature-branch chain: revert each PR independently — no backend/data impact; wizard fix revert restores mock-masked behavior.

## Dependencies

None new: TanStack Query, RHF + zod, shadcn/ui, Zustand, MSW present. Backend researchers API (complete, archived).

## Success Criteria

- [ ] Users can list, create, view (tabs), and edit researchers; completeness bar reflects score; deactivate works via ConfirmDialog
- [ ] Affiliations support dependent selects + exactly-one-primary; cross-institution errors surface
- [ ] Projects wizard loads researcher options against the real API; Jest ≥80%, `tsc --noEmit` green; Sidebar nav role-gated
