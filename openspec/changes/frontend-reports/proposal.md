# Proposal: Frontend Reports Module (SIGPI §6.6)

## Intent

Backend `apps.reports` (preview/PDF/approve) is complete and archived, yet the frontend has zero reports surface: no `/reports` route, no nav item, no API client. Users cannot generate, preview, download, or approve report PDFs from the app. This change delivers a dedicated reports hub reusing the established module pattern (`features/{module}` + App Router pages + MSW + Jest ≥80%).

## Scope

### In Scope
- `features/reports` module: types, constants, permissions, queries, mutations, `queryKeys.reports`
- `lib/download.ts`: authenticated blob download (fetch → blob → objectURL → anchor click)
- `/reports` page: generator form (type select → entity selector) fed by existing hooks
- Preview dialog: sandboxed iframe via `srcDoc` (WYSIWYG with PDF)
- PDF download with pending state (WeasyPrint <5s NFR)
- Approval action (director/admin only) with verbatim 409 RN-017 toast
- Reports list / approval queue DERIVED from entity lists (projects, researchers, centers) with status indicators + action buttons
- Sidebar "Informes" item + middleware `PROTECTED_PREFIXES`; MSW fixtures/handlers

### Out of Scope
- Backend changes (`apps.reports` archived; no invented endpoints)
- Standalone reports registry / status-history views (no list API exists)
- Report template management (`ReportTemplate` has no API surface)
- Bulk PDF generation

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `reports-ui`: Frontend reports module — generator form, sandboxed HTML preview, authenticated PDF download, director approval, derived report-status lists

### Modified Capabilities
- None (backend `reports` spec unchanged; `frontend-mvp` untouched)

## Approach

Dedicated reports hub (exploration Approach 1), delivered as 3 chained PRs within the 400-line budget (delivery strategy: auto-chain). Reuse module pattern: query-key factory + X-Institution-ID, RoleGuard, MSW, Jest ≥80%, Spanish UI. Preview renders raw Django HTML in a sandboxed iframe; download uses blob fetch (plain href fails under session auth); approval is a role-gated POST with verbatim 409.

| Slice | PR Scope | Est. Lines |
|---|---|---|
| 1 | Foundation: download.ts, module core, queryKeys.reports, MSW, Sidebar, middleware, `/reports` page | ~350–400 |
| 2 | PreviewDialog (sandboxed iframe) + download wiring + states | ~300–350 |
| 3 | Approval + director gating + derived entity-list queue | ~300–350 |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/features/reports/**` | New | module files |
| `frontend/app/reports/**` | New | page routes |
| `frontend/lib/download.ts` | New | blob download utility |
| `frontend/lib/query-keys.ts` | Modified | `reports` key factory |
| `frontend/components/shell/Sidebar.tsx` | Modified | "Informes" nav item |
| `frontend/middleware.ts` | Modified | PROTECTED_PREFIXES |
| `frontend/mocks/`, `frontend/fixtures/` | Modified | MSW handlers + fixtures |
| Backend | None | no changes |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| No list/status API — derived lists only | Med | Derive from existing hooks; never invent endpoints |
| PDF download auth (plain href returns 401) | High | blob fetch with credentials; MSW binary mock |
| HTML preview XSS | Med | sandboxed iframe, no `allow-same-origin` |
| WeasyPrint latency (<5s NFR) | Med | pending state; disable actions while generating |
| 400-line budget exceeded | Med | 3 chained PRs; forecast in sdd-tasks |

## Rollback Plan

Revert each chained PR independently (remove feature files, routes, nav item, key factory, middleware prefix) — UI-only, zero backend/data impact. PR #1 rolls back by deleting `features/reports` + nav entry.

## Dependencies

- Backend `apps.reports` API (complete, archived): preview/PDF/approve endpoints
- Existing hooks: `useProjectsList`, `useResearchersList`, `useCenters`

## Success Criteria

- [ ] Users generate, preview, and download PDFs for all 4 report types from `/reports`
- [ ] Directors/admins can approve; non-directors see 403; 409 RN-017 shows verbatim toast
- [ ] Entity lists show report status indicators and action buttons (derived, no new endpoint)
- [ ] Blob download works under session auth (not plain href)
- [ ] Jest coverage ≥80%; ESLint + `tsc --noEmit` green per PR
