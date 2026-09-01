# Design: Frontend Researchers Module

## Technical Approach

Add an institution-scoped, read-first `features/researchers` module following the existing projects/advances query and mutation conventions. Next.js App Router pages remain thin composition layers; TanStack Query owns all API state, React Hook Form + zod owns form state, and Zustand supplies the active institution and roles. UI copy remains Spanish. The backend is unchanged.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Feature boundary | Keep researcher types, schemas, queries, mutations, authorization metadata, and reusable components under `features/researchers`. | Avoid putting domain behavior in route pages; no new global store is needed because server state belongs to Query. |
| Detail data | Use one researcher detail query plus dedicated nested list queries for affiliations, profiles, and attachments. | Dedicated nested keys allow targeted refetches while the mutation helper invalidates the complete researcher tree. |
| Lifecycle | Model only `deactivate` in `fsm.ts`; expose it through a researcher action component and `ConfirmDialog`. Reactivation is an edit PATCH with `is_active`. | Do not invent activate/archive/me endpoints that the backend does not provide. |
| Forms | Use researcher-specific RHF forms with zod schemas, mapping `ApiError` 400 field errors through `setError` and other errors to Sonner. | Reuse the proven error behavior without forcing the generic institution field model onto nested researcher data. |

## Data Flow

```text
Auth (active institution/roles) → Query hook → api.ts → DRF API
                                      ↓
                             page/components
Mutation → DRF → invalidate researchers.all → list/detail/nested refetch
```

`useResearchersList({page})` consumes `Page<ResearcherList>` (25/page). `useResearcherDetail(id)` and nested hooks pass `institutionId` to `api`. Affiliation selectors use the existing institution hierarchy queries for center → group → line dependency and clear downstream values when a parent changes. The projects wizard receives `Page<ResearcherList>` and maps `results` to `{id, full_name}`; it intentionally does not fetch page 2.

## File Layout and Changes

```text
frontend/features/researchers/
  index.ts types.ts schemas.ts queries.ts mutations.ts fsm.ts
  CompletenessBar.tsx ResearcherForm.tsx ResearcherList.tsx
  ResearcherDetail.tsx AffiliationsManager.tsx
  ExternalProfilesManager.tsx AttachmentsManager.tsx
frontend/app/researchers/
  page.tsx new/page.tsx [id]/page.tsx [id]/edit/page.tsx
```

Modify `frontend/lib/query-keys.ts` with institution-scoped list/detail/nested factories; `components/shell/Sidebar.tsx` with an authenticated Investigadores item; `components/shared/StatusBadge.tsx` with the inactive researcher mapping; `fixtures/index.ts`, new `fixtures/researchers.ts`, and `mocks/handlers.ts` for four entities and mutations; `features/projects/queries.ts` and `app/projects/new/page.tsx` for pagination mapping. Add focused Jest/RTL tests under `frontend/__tests__/features/researchers/` and update relevant projects/sidebar/status tests.

## Component Breakdown

- `page.tsx`: paginated table, completeness bars, status badges, row links/actions, empty state.
- `new/page.tsx`: role-gated create form; successful POST routes to detail.
- `[id]/page.tsx`: header, status, completeness, edit/deactivate controls, four Tabs; Overview uses `ResearcherDetail`.
- `[id]/edit/page.tsx`: editable profile fields and `is_active` switch, gated by admin or linked self.
- Nested managers: inline create/delete; affiliation primary action disables for the current primary; profile provider and attachment type are constrained selects; attachments render external links only.

## PR Slice Boundaries

1. **PR1 foundation** — types/schemas/queries/mutations/fsm, list/create/detail overview/edit/completeness/deactivate, sidebar/status, base fixtures/handlers and tests.
2. **PR2 nested managers** — affiliations with dependent selects and primary semantics, profiles, metadata-only attachments, fixtures/handlers/tests.
3. **PR3 wizard fix and polish** — paginated `useResearchers()` and `results` mapping, accessibility/UX polish, full lint/type/test/coverage verification.

Each slice has an autonomous UI/API contract, focused tests, and rollback by reverting its feature branch. The aggregate is expected to exceed the 400-line review budget; stacked-to-main delivery is therefore required.

## Testing Strategy

Unit-test schemas, authorization, completeness states, query-key structure, and pagination mapping. RTL-test each route, role gate, field-error handling, confirmation flow, dependent selects, primary switching, and metadata-only links. MSW tests cover paginated envelopes, CRUD, nested endpoints, duplicate/cross-institution errors, and invalidation. Run Jest coverage (branch floor 80%), ESLint, and `tsc --noEmit` per slice.

## Threat Matrix

N/A — no shell, subprocess, VCS/PR automation, executable classification, or process-integration boundary is introduced. App routing is ordinary Next.js page routing and has no dynamic command boundary.

## Migration / Rollout

No migration required. Roll out by merging the three feature-branch slices; revert each independently. No feature flag or backend data migration is needed.

## Open Questions

- [ ] Confirm the final backend display field names if the archived serializer changes before implementation; current design uses the recorded `ResearcherList` and `ResearcherSerializer` contract.
