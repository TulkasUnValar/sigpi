# Documents UI - Phase 1: Core Flow (Upload + List + Download)

## Context
Backend is 100% complete (models, services, MinIO storage, 240 tests, 97.4% coverage).
This phase implements the frontend core flow for document management.

## Scope (Phase 1)
- **Upload flow**: presign→PUT→confirm handshake with MinIO presigned URLs
- **Document list**: paginated list with filters (doc_type, entity, is_signed)
- **Document detail**: view versions, download
- **Navigation**: sidebar entry
- **NOT included**: sign action, minutes UI (Phase 2)

## Tasks

### T1: API helpers
**Files:**
- `frontend/lib/storage-upload.ts` - presigned PUT upload helper
- `frontend/lib/download.ts` - extend to handle absolute presigned URLs

**Requirements:**
- `presignUpload(uploadUrl: string, file: File)`: PUT to MinIO URL (no creds/CSRF)
- `openPresignedUrl(url: string)`: open absolute URL in new tab
- Handle errors (403, 409 conflict, network failures)

**Estimated:** ~80 lines

### T2: Feature structure
**Files:**
- `frontend/features/documents/types.ts` - Document, DocumentVersion, DocumentType
- `frontend/features/documents/constants.ts` - doc type labels, entity types
- `frontend/features/documents/schemas.ts` - zod schemas for upload metadata
- `frontend/features/documents/queries.ts` - list, detail, versions queries
- `frontend/features/documents/mutations.ts` - upload, confirm, re-upload
- `frontend/features/documents/permissions.ts` - role ≤6 write
- `frontend/features/documents/index.ts` - barrel export

**Requirements:**
- Follow existing pattern from `features/reports/`
- Query keys: `queryKeys.documents.list`, `queryKeys.documents.detail`, `queryKeys.documents.versions`
- Mutations invalidate document queries on success

**Estimated:** ~400 lines

### T3: Upload components
**Files:**
- `frontend/features/documents/UploadDialog.tsx` - file picker + metadata form + upload progress
- `frontend/features/documents/UploadButton.tsx` - trigger button with role check

**Requirements:**
- File picker with drag-and-drop
- Metadata form: filename (auto-filled), doc_type (select from 12 types), entity link (optional)
- Upload progress bar
- Success/error states
- Validate file size (100MB max, per spec SHOULD)

**Estimated:** ~300 lines

### T4: List components
**Files:**
- `frontend/features/documents/DocumentsList.tsx` - paginated list with filters
- `frontend/features/documents/DocumentsFilters.tsx` - filter panel (doc_type, entity, is_signed)
- `frontend/features/documents/DocumentsTable.tsx` - table with columns (name, type, entity, uploaded, signed, actions)

**Requirements:**
- Pagination (25/page, consistent with other lists)
- Filters: doc_type (multi-select), entity (text search), is_signed (boolean)
- Row actions: view detail, download
- Role-based: hide upload button if role >6

**Estimated:** ~350 lines

### T5: Detail components
**Files:**
- `frontend/features/documents/DocumentDetail.tsx` - full document view
- `frontend/features/documents/VersionHistory.tsx` - version list with download links
- `frontend/features/documents/DocumentHeader.tsx` - metadata + status badges

**Requirements:**
- Display metadata (name, type, entity, uploaded_by, created_at)
- Version history list (version number, uploaded_at, size, download link)
- Status badges (signed, latest version)
- Download button (uses presigned GET)

**Estimated:** ~250 lines

### T6: Routes
**Files:**
- `frontend/app/documents/page.tsx` - list page
- `frontend/app/documents/[id]/page.tsx` - detail page

**Requirements:**
- Wrap in AuthenticatedLayout
- Role-gated (role ≤6 for access)
- Loading/error states
- Breadcrumbs

**Estimated:** ~100 lines

### T7: Navigation
**Files:**
- `frontend/components/shell/Sidebar.tsx` - add Documents entry

**Requirements:**
- Add FileText icon + "Documentos" label
- Position: after Reports, before Search (or similar logical position)
- Role-gated (hide if role >6)

**Estimated:** ~10 lines

### T8: Tests
**Files:**
- `frontend/__tests__/features/documents/queries.test.ts`
- `frontend/__tests__/features/documents/mutations.test.ts`
- `frontend/__tests__/features/documents/UploadDialog.test.tsx`
- `frontend/__tests__/features/documents/DocumentsList.test.tsx`
- `frontend/__tests__/features/documents/DocumentDetail.test.tsx`
- `frontend/__tests__/features/documents/page.test.tsx`

**Requirements:**
- Mock presign/confirm flow (MSW or jest.mock)
- Test upload success/error paths
- Test list pagination + filters
- Test detail view + version history
- Test role-based access
- Test download URL handling

**Estimated:** ~600 lines

### T9: Query keys integration
**Files:**
- `frontend/lib/query-keys.ts` - add documents factory

**Requirements:**
```typescript
documents: {
  all: ['documents'] as const,
  list: (filters: DocumentFilters) => [...queryKeys.documents.all, 'list', filters] as const,
  detail: (id: string) => [...queryKeys.documents.all, 'detail', id] as const,
  versions: (id: string) => [...queryKeys.documents.all, 'versions', id] as const,
}
```

**Estimated:** ~20 lines

## Implementation Order
1. T9 (query keys) - foundation
2. T1 (API helpers) - foundation
3. T2 (feature structure) - foundation
4. T3 (upload components) - core flow
5. T4 (list components) - core flow
6. T5 (detail components) - core flow
7. T6 (routes) - integration
8. T7 (navigation) - integration
9. T8 (tests) - validation

## Acceptance Criteria
- [ ] User can upload a document (presign→PUT→confirm)
- [ ] User can view document list with filters
- [ ] User can view document detail with version history
- [ ] User can download a document (presigned GET)
- [ ] Sidebar has Documents entry (role-gated)
- [ ] All tests pass (unit + integration)
- [ ] TypeScript compiles without errors
- [ ] ESLint passes
- [ ] Prettier formatting applied

## Estimated Total
- **Files:** ~20-22
- **Lines:** ~2,100-2,200
- **Complexity:** Medium-High (presigned upload flow)

## Out of Scope (Phase 2)
- Sign action UI
- Minutes CRUD UI
- Signature badge component
- Digital signature detail view

## Notes
- Backend API is stable and tested (97.4% coverage)
- Follow existing patterns from `features/reports/` and `features/advances/`
- Use existing UI primitives (Button, Card, Dialog, Table, etc.)
- Handle presigned URLs carefully (absolute URLs, no CSRF/creds)
- RF-066 immutability: signed documents cannot be edited (hide/disable actions)
