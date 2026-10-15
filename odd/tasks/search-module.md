# Search Module (Meilisearch) - Task Document

## Overview
Implement full-text search across projects, researchers, products, calls, and advances using Meilisearch.

## Context
- Backend infrastructure exists but `reindex_search` command is missing (only .pyc remains)
- Without this command, indexes are never configured and search cannot work
- Frontend search feature needs to be built from scratch
- Meilisearch is already running in Docker (port 7700)

## Scope
- 5 indexes: projects, researchers, products, calls, advances
- Full-text search with filters (institution, center, status, year, line, type)
- Tenant isolation (institution-scoped)
- Frontend UI with search bar, results, filters

## Tasks

### Phase 1: Backend (reindex_search command) ✅ COMPLETE

- [x] **Task 1: Create reindex_search management command**
  - ✅ File: `backend/apps/search/management/commands/reindex_search.py` (125 lines)
  - ✅ Creates/ensures the 5 indexes
  - ✅ Applies `INDEX_CONFIG` searchable + filterable attributes
  - ✅ Backfills existing rows per index (RLS-aware, iterate institutions)
  - ✅ Supports `--index <name>` and `--recreate` flags
  - ✅ Idempotent operation
  - ✅ Critical fix: `primary_key` must be keyword argument

- [x] **Task 2: Create tests for reindex_search**
  - ✅ File: `backend/apps/search/tests/test_reindex.py` (8 tests)
  - ✅ Test index creation, settings application, backfill, flags
  - ✅ Mock Meilisearch client
  - ✅ 74 tests passing, 2 skipped (RLS integration)

- [x] **Task 3: Run reindex and verify**
  - ✅ Command executed successfully in Docker
  - ✅ All 5 indexes created in Meilisearch
  - ✅ Search API responding correctly

### Phase 2: Frontend (search feature)

- [ ] **Task 4: Create search feature structure**
  - Files:
    - `frontend/features/search/queries.ts` (useSearch hook)
    - `frontend/features/search/types.ts` (Meili SearchResults shape)
    - `frontend/features/search/constants.ts` (index metadata, route mapping)
    - `frontend/features/search/index.ts` (barrel export)
  - Estimated: ~100 lines

- [ ] **Task 5: Create search UI components**
  - Files:
    - `frontend/features/search/SearchBar.tsx` (input + index selector)
    - `frontend/features/search/SearchResults.tsx` (result cards with highlighting)
    - `frontend/features/search/SearchFilters.tsx` (filter panel)
  - Use existing UI primitives (Card, Input, Badge, Button)
  - Estimated: ~250 lines

- [ ] **Task 6: Create search page**
  - File: `frontend/app/search/page.tsx`
  - Thin adapter over AuthenticatedLayout
  - Integrate SearchBar, SearchResults, SearchFilters
  - Handle loading/empty/error states
  - Estimated: ~100 lines

- [ ] **Task 7: Integrate search into navigation**
  - Add "Búsqueda" entry to Sidebar NAV_ITEMS
  - Add query key factory to `lib/query-keys.ts`
  - Estimated: ~30 lines

- [ ] **Task 8: Create frontend tests**
  - Files:
    - `frontend/__tests__/features/search/queries.test.ts`
    - `frontend/__tests__/features/search/SearchBar.test.tsx`
    - `frontend/__tests__/features/search/SearchResults.test.tsx`
    - `frontend/__tests__/features/search/page.test.tsx`
  - Estimated: ~300 lines

## Acceptance Criteria
- [ ] `reindex_search` command creates all 5 indexes
- [ ] Index settings match `INDEX_CONFIG` (searchable/filterable attributes)
- [ ] Existing data is indexed and searchable
- [ ] Frontend search page is accessible via navigation
- [ ] Full-text search works across all 5 entity types
- [ ] Filters work (institution, center, status, year, line, type)
- [ ] Tenant isolation enforced (users see only their institution's data)
- [ ] All tests pass (backend + frontend)
- [ ] Search results link to entity detail pages

## Dependencies
- None (Meilisearch already running in Docker)

## Estimated Effort
- Backend: ~250 lines (2 tasks)
- Frontend: ~780 lines (5 tasks)
- Total: ~1,030 lines

## Risks
- RLS context in reindex command (must use `tenant_context` wrapper)
- Meilisearch client connection in reindex (follow existing `get_client()` pattern)
- Frontend result rendering (need to map Meili hits to detail routes)
