# SIGPI UX/UI & Backend Audit Improvements

## Objective
Implement all improvements identified in the full-stack audit, covering backend security/consistency, frontend i18n coverage, and UI consistency.

## Scope
- Backend: rate limiting, error format unification, register URL registration
- Frontend i18n: migrate ~100 hardcoded Spanish strings to messages/*.json
- UI: error boundaries, not-found, layout fixes, LocaleSwitcher tokens

## Constraints
- Maintain backwards compatibility where possible
- Follow existing patterns (DRF for backend, shadcn/ui for frontend)
- All tests must pass after changes

## Tasks

### Phase 1: Backend (Security + Consistency) ✅
- [x] T1.1: Add DRF throttle classes for login/register endpoints
- [x] T1.2: Create global exception handler for unified error format
- [x] T1.3: Register `register_view` in `apps/accounts/urls.py`
- [x] T1.4: Convert FBVs to use `@api_view` for throttle compatibility

### Phase 2: Frontend i18n ✅
- [x] T2.1: Add missing translation sections to messages/es.json and messages/en.json (dashboard, calls, search, reports, analytics, documents, institutions, researchers, advances)
- [x] T2.2: Migrate hardcoded strings in dashboard/page.tsx
- [x] T2.3: Migrate hardcoded strings in CallList.tsx, ResearcherList.tsx, AdvanceList.tsx
- [x] T2.4: Migrate hardcoded strings in SearchBar, SearchResults, SearchFilters, ReportHub, DocumentsList
- [x] T2.5: Migrate hardcoded strings in InstitutionTree.tsx
- [x] T2.6: Migrate hardcoded strings in all institutions/** and researchers/** pages
- [x] T2.7: Migrate hardcoded aria-labels in Sidebar, Drawer, Topbar, RoleGuard

### Phase 3: UI Consistency ✅
- [x] T3.1: Create app/[locale]/error.tsx with error boundary
- [x] T3.2: Create app/[locale]/not-found.tsx
- [x] T3.3: Create app/[locale]/loading.tsx
- [x] T3.4: Fix /me, /logout, /switch-institution pages (wrap in layout or style properly)
- [x] T3.5: LocaleSwitcher: use ui/button + design tokens instead of hardcoded colors
- [x] T3.7: Add font provider (next/font Inter)
- [x] T3.8: Add skip-to-content link in [locale]/layout.tsx

## Verification
- Backend: run `pytest` — all tests pass ✅ (2768 passed, 1 preexisting env-dependent failure)
- Frontend: `npm run lint` clean, `npm run build` succeeds ✅
- Visual: login page, dashboard, and at least 2 CRUD pages look consistent ✅
- i18n: switch to EN, verify no Spanish strings remain on migrated pages ✅

## Notes
- `apps/search/tests/test_config.py::TestMeilisearchSettings::test_url_defaults_to_localhost` fails because Docker sets `MEILISEARCH_URL=http://meilisearch:7700`. Preexisting issue, not related to these changes.
