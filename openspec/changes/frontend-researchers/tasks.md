# Tasks: Frontend Researchers Module

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,400–1,800 (across 3 PRs) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 foundation → PR2 nested managers → PR3 wizard fix + polish |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation: types/schemas/queries/mutations/fsm; list/create/detail-overview/edit/completeness/deactivate; sidebar + StatusBadge; MSW base | PR1 | `cd frontend; jest features/researchers __tests__/features/researchers --coverage` | `npm run dev` → `/researchers`, `/researchers/new`, `/researchers/{id}` | Revert `features/researchers/*`, `app/researchers/*`, `query-keys.ts` researchers factory, `Sidebar.tsx`, `StatusBadge.tsx`, `fixtures/researchers.ts` |
| 2 | Nested managers: affiliations (dependent selects + primary), external profiles, metadata-only attachments + fixtures/handlers | PR2 | `cd frontend; jest features/researchers --coverage` | `/researchers/{id}` Affiliations/Profiles/Attachments tabs | Revert `AffiliationsManager.tsx`, `ExternalProfilesManager.tsx`, `AttachmentsManager.tsx`, their fixtures/handlers |
| 3 | Wizard pagination fix + polish + verify | PR3 | `cd frontend; jest features/projects app/projects/new --coverage` | `/projects/new` team/PI step | Revert `features/projects/queries.ts` `useResearchers()`, `app/projects/new/page.tsx` mapping |

## Phase 1: Foundation (PR1)

- [x] 1.1 Create `features/researchers/types.ts` — `ResearcherList`, `ResearcherSerializer` (`user`, `primary_email`, nested arrays), `Page<ResearcherList>`-compatible list item, create/patch payloads.
- [x] 1.2 Create `features/researchers/schemas.ts` — zod create/edit schemas matching `ResearcherCreateSerializer`; map `ApiError` 400 field errors via `setError`.
- [x] 1.3 Create `features/researchers/fsm.ts` — model only `deactivate` state transition (no activate/archive/me).
- [x] 1.4 Add `researchers` factory to `lib/query-keys.ts` — institution-scoped `all/lists/list/detail` + nested keys.
- [x] 1.5 Create `features/researchers/queries.ts` — `useResearchersList({page})` (25/page), `useResearcherDetail(id)`, nested hooks; pass `institutionId` to `api`.
- [x] 1.6 Create `features/researchers/mutations.ts` — create, patch (with `is_active` reactivation), deactivate; invalidate `researchers.all` after any mutation.
- [x] 1.7 Create `features/researchers/CompletenessBar.tsx` — 0–100 indicator with complete/incomplete states (score 40 → incomplete).
- [x] 1.8 Create `features/researchers/ResearcherList.tsx` + `app/researchers/page.tsx` — paginated table, bars, StatusBadge, row actions, empty state with create action.
- [x] 1.9 Create `features/researchers/ResearcherForm.tsx` + `app/researchers/new/page.tsx` — director+ (level ≤ 3) gate; POST redirects to `/researchers/{id}`; duplicate-document field error, no redirect.
- [x] 1.10 Create `features/researchers/ResearcherDetail.tsx` + `app/researchers/[id]/page.tsx` — header, status, completeness, four Tabs, edit/deactivate controls; Overview renders profile fields.
- [x] 1.11 Create `app/researchers/[id]/edit/page.tsx` — PATCH (self or admin+, gated on detail `user`); `is_active` toggle for reactivation.
- [x] 1.12 Create deactivate action component + ConfirmDialog wiring (admin+, level ≤ 2); hide for non-admin.
- [x] 1.13 Add `investigadores` sidebar item in `components/shell/Sidebar.tsx` for every authenticated role; map researcher `inactive` in `components/shared/StatusBadge.tsx`.
- [x] 1.14 Add `fixtures/researchers.ts`, register in `fixtures/index.ts`, add `mocks/handlers.ts` researcher handlers (paginated envelope, CRUD, deactivate, duplicate/cross-institution errors).
- [x] 1.15 Write Jest/RTL tests under `__tests__/features/researchers/` covering list/create/detail/edit/completeness/deactivate, role gates, field errors, invalidation; update sidebar/status tests. Coverage ≥80%, `tsc --noEmit` green.

## Phase 2: Nested Managers (PR2)

- [x] 2.1 Create `features/researchers/AffiliationsManager.tsx` — inline create/delete; dependent selects center → group → line (clear downstream on parent change); at least one FK.
- [x] 2.2 Primary semantics — first affiliation auto-primary (`is_primary=True`); `set_primary` POST `/affiliations/{aff_id}/set_primary/` demoting prior; toggle disabled when already primary.
- [x] 2.3 Cross-institution target → surface 400 detail via Toaster; POST `/affiliations/`.
- [x] 2.4 Create `features/researchers/ExternalProfilesManager.tsx` — `{provider, url}` with provider ∈ cvlac/orcid/google_scholar/linkedin/researchgate; nested POST/DELETE `/profiles/`; list refresh.
- [x] 2.5 Create `features/researchers/AttachmentsManager.tsx` — metadata only `{name, type (cv|certificate|photo|other), external_url}`, no upload; rendered as external link; nested POST/DELETE.
- [x] 2.6 Wire three managers into `[id]/page.tsx` tabs (Affiliations, External profiles, Attachments).
- [x] 2.7 Add MSW fixtures/handlers for affiliations, profiles, attachments (nested CRUD, primary switching, cross-institution 400).
- [x] 2.8 Jest/RTL tests for dependent selects, primary switching, metadata-only links, nested mutation invalidation; coverage ≥80%.

## Phase 3: Wizard Fix + Polish + Verify (PR3)

- [x] 3.1 RED test — `features/projects/queries.ts` `useResearchers()` returns `Page<ResearcherList>`; wizard maps `results` to `{id, full_name}`, not raw envelope.
- [x] 3.2 Update `features/projects/queries.ts` `useResearchers()` to fetch `Page<ResearcherList>` (25/page, no page 2 fetch).
- [x] 3.3 Update `app/projects/new/page.tsx` team/PI selects to consume `results` mapping; only first page options offered, no crash.
- [x] 3.4 Add matching MSW researchers handler for the wizard (paginated envelope).
- [x] 3.5 Accessibility/UX polish pass on researchers routes (focus, aria, loading/empty states).
- [x] 3.6 Full verification — `jest --coverage` (branch ≥80%), ESLint, `tsc --noEmit` across all three slices; confirm the researchers-ui and projects-ui acceptance criteria.

## PR Boundaries and Rollback Plan

| PR | Scope | Merge target | Rollback |
|----|-------|--------------|----------|
| PR1 | Foundation (files 1.1–1.15) | main | Revert PR1 commit/feature branch; researchers UI and sidebar item disappear, projects unaffected |
| PR2 | Nested managers (2.1–2.8) | main | Revert PR2; Overview/edit remain, tabs fall back to placeholders |
| PR3 | Wizard fix + polish (3.1–3.6) | main | Revert PR3; wizard falls back to prior researcher mapping (bug resurfaces, no data loss) |

Each PR is an autonomous slice with its own verification; reverting one does not require reverting others. No migration or feature flag needed.
