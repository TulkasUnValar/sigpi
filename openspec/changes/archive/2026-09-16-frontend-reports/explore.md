# Exploration: Frontend Reports Module (SIGPI §6.6)

## Current State

### Backend `apps.reports` — COMPLETE (archived)

Verified in `backend/apps/reports/` (`models.py`, `serializers.py`, `permissions.py`, `services.py`, `views.py`, `urls.py`):

- **3 models**: `Report` (generic `report_type` + `entity_id` UUID, denormalized `institution`, `status`, `version`, `created_by`), `ReportApproval` (history/metadata: `approved_by`, `approved_at`, `report_version`), `ReportTemplate` (no API surface — ignore).
- **4 report types**: `project`, `researcher`, `center`, `advances` (advances targets a **Project** entity_id).
- **4 statuses**: `draft`, `generated`, `approved`, `rejected` (statuses only meaningful server-side; no list/query endpoint exposes them).
- **3 endpoints** (no list, no status/history, no approval-queue endpoint):
  - `GET /api/reports/{type}/{id}/preview/` → `{"html": "..."}`
  - `GET /api/reports/{type}/{id}/pdf/` → `FileResponse` (PDF stream, `as_attachment=False`, filename `{type}_report.pdf`); side effect: creates `Report(status=generated, version=1)` + emits `REPORT_GENERATED` audit
  - `POST /api/reports/{type}/{id}/approve/` → `200 {"status":"approved","report_id","approval_id"}` | `409` RN-017 guard | `403` non-director
- **Permissions**:
  - Preview/PDF: `IsAuthenticated` + `CanGenerateReport` (role level ≤ 4; admin+ level ≤ 2 bypass; SAFE_METHODS pass at view level; object-level same-institution, RN-015). 404 on unknown entity, 403 cross-institution, 500 on render failure.
  - Approve: `IsAuthenticated` + manual center-director check (level ≤ 3 + center membership via `active_membership`; superuser bypass; `researcher` type only requires any center membership). RN-017: project-type approval returns 409 `"Pending progress reports must be reviewed"` when the project has pending progress reports.
- **Auth transport**: Django session cookie (`credentials: "include"`) + `X-Institution-ID` header.

### Frontend — GREENFIELD for reports

- Zero references to the reports API in `frontend/` (only package-lock noise and unrelated comments).
- No `/reports` route, no nav item, not in `middleware.ts` `PROTECTED_PREFIXES`.
- Four frontend modules already merged to main establish the feature pattern: `features/{module}/{types,constants,schemas,permissions,queries,mutations,*.tsx}` + thin App Router pages + `AuthenticatedLayout` + institution-scoped TanStack Query (`queryKeys` factory + `X-Institution-ID`) + MSW fixtures/handlers + Jest/RTL ≥80% + Spanish UI copy + `fsm.ts`/`FsmActionBar` action pattern (calls/advances/institutions) + `RoleGuard`/role checks via `useAuthStore().roles`.

### Key gaps discovered (no existing frontend pattern)

1. **No authenticated binary download utility.** Attachments (`AttachmentsManager`, `DocumentsManager`, `ExternalProfilesManager`) link to `external_url` hrefs (MinIO/presigned — no auth needed). The PDF endpoint requires session auth + tenant header; a plain `<a href>`/`window.open` drops cookies cross-origin (`localhost:8000`). A new `lib/download.ts` (fetch → blob → objectURL → anchor click) is required.
2. **No HTML-preview rendering pattern.** Preview returns raw server-rendered Django HTML (single source of truth for the PDF — WYSIWYG). Must be rendered in a sandboxed iframe via `srcDoc`.
3. **No "reports list" backend API.** The mission's UI scope (list of generated reports, approval queue) cannot be backed by any endpoint. The UI MUST derive reportable entities from existing list hooks (`useProjectsList`, `useResearchersList`, `useCenters`) or descope. Do NOT invent endpoints — backend is archived.

## Affected Areas

- `frontend/features/reports/` (new) — feature module: `types.ts`, `constants.ts` (type/status label maps), `queries.ts` (preview query), `mutations.ts` (approve), `permissions.ts` (role gating helpers), `ReportGeneratorForm.tsx`, `ReportActions.tsx`, `PreviewDialog.tsx`, `index.ts`.
- `frontend/lib/download.ts` (new) — authenticated blob-download helper (fetch with credentials + `X-Institution-ID`, `URL.createObjectURL`, anchor click, cleanup).
- `frontend/lib/query-keys.ts` — add `reports` key factory (institution-scoped, mirroring `products`).
- `frontend/app/reports/page.tsx` (new) — thin App Router page wrapping `AuthenticatedLayout` + `ReportGeneratorForm`.
- `frontend/components/shell/Sidebar.tsx` — add "Informes" nav item; extend the director-only "Aprobaciones" section.
- `frontend/middleware.ts` — add `/reports` to `PROTECTED_PREFIXES`.
- `frontend/fixtures/reports.ts` + `frontend/fixtures/index.ts` (new) — report fixtures (entity ids must align with existing fixture ids — products PR3 hit this mismatch).
- `frontend/mocks/handlers.ts` — MSW handlers for the 3 endpoints, incl. binary PDF (`HttpResponse` with Blob/arrayBuffer).
- `frontend/__tests__/features/reports/` (new) — Jest tests.
- Entity option reuse (no changes): `frontend/features/projects/queries.ts` (`useProjectsList`, `useCenters`), `frontend/features/researchers/queries.ts` (`useResearchersList`) — feed the generator form selectors.
- Shared components (reuse, no changes): `components/ui/dialog.tsx` (exists), `ConfirmDialog`, `StatusBadge`, `EmptyState`, `Skeleton`, `RoleGuard`, `Card`, `Select`, `Button`, sonner `Toaster`.

## API Contract

| Method | Path | Success | Errors | Permission | Side effects |
|---|---|---|---|---|---|
| GET | `/api/reports/{type}/{id}/preview/` | `200 {"html": "<string>"}` | 400 invalid type; 403 cross-institution (RN-015); 404 entity not found/invalid UUID; 500 render failure | `IsAuthenticated` + `CanGenerateReport` (level ≤ 4; admin+ bypass; SAFE_METHODS) | none |
| GET | `/api/reports/{type}/{id}/pdf/` | `200` `application/pdf` stream (`Content-Disposition: inline`, `filename={type}_report.pdf`) | same as preview | same as preview | creates `Report(status=generated, version=1)`; emits `REPORT_GENERATED` audit |
| POST | `/api/reports/{type}/{id}/approve/` | `200 {"status":"approved","report_id":"<uuid>","approval_id":"<uuid>"}` | 400 invalid type; 403 `"You must be a center director to approve reports."`; 404; 409 `"Pending progress reports must be reviewed"` (RN-017, project type only) | `IsAuthenticated` + director check (level ≤ 3 + center membership; superuser bypass) | creates/updates `Report(status=approved)` + `ReportApproval`; emits `REPORT_APPROVED` audit |

- `{type}` ∈ `project | researcher | center | advances`; `{id}` is a UUID (advances = project UUID).
- Request transport: session cookie (`credentials: "include"`) + `X-Institution-ID` (already handled by `frontend/lib/api.ts`).
- **Explicit non-contract**: there is NO `GET /api/reports/` list, NO report status/history endpoint, and NO pending-approvals query for reports.

## UI Scope

1. **Nav + routing**: "Informes" sidebar item → `/reports`; `/reports` in middleware protect list; director-only "Aprobaciones" section extension (role-gated).
2. **Report generator form** (`/reports` page): report-type select (4 types, Spanish labels) → dependent entity selector (projects for `project`/`advances`, researchers for `researcher`, centers for `center`) fed by existing list hooks → action row: **Vista previa** (opens preview modal), **Descargar PDF** (blob download), **Aprobar** (director/admin only, gated by role).
3. **Preview modal**: `Dialog` + sandboxed `<iframe srcDoc={html}>` (no scripts; print CSS fidelity = WYSIWYG with the PDF).
4. **Download action**: `lib/download.ts`; pending/disabled state while WeasyPrint generates server-side (<5s NFR); success toast.
5. **Approval**: role-gated button (director/admin), POST approve; 409 RN-017 message surfaced verbatim via Toaster; success toast with report/approval ids.
6. **"List of generated reports" / "approval queue"**: NOT backend-backed — derive reportable entities from existing entity lists (projects/researchers/centers) and attach report actions per row; flag this scope decision for the proposal phase.
7. **MSW + fixtures + Jest**: handlers for the 3 endpoints (binary PDF mock), fixtures aligned with existing entity fixture ids, coverage ≥80%.

## Special Considerations

- **PDF download auth**: must be fetch → blob → objectURL (credentials + `X-Institution-ID`). Plain anchor/window.open breaks cross-origin session cookies.
- **HTML preview safety**: server-rendered HTML rendered in a sandboxed iframe (`sandbox=""`, `srcDoc`); treat as untrusted-ish (Django-escaped, but still no script execution surface).
- **Role gating**: preview/download available to every authenticated same-institution role (level ≤ 4); approve strictly director/admin (level ≤ 3 + center membership). Frontend gating is UX only — backend enforces 403.
- **409 guard (RN-017)**: project-type approval blocked with pending progress reports — verbatim error surface, no cache invalidation on failure (established mutation convention).
- **Institution scoping**: all queries/mutations pass `activeInstitution.id` → `X-Institution-ID`; query keys institution-scoped; institution switch clears cache (existing auth-store behavior).
- **No list API**: do not invent endpoints; UI derives entity lists from existing hooks.
- **Fixture id alignment**: reports fixtures must reference existing project/researcher/center fixture ids (products PR3 had `r1` vs `r-1` mismatch).
- **Test runner**: jest runs via Windows node (`node ./node_modules/jest/bin/jest.js --config jest.config.js`), documented gotcha in this WSL setup.

## Approaches

1. **Dedicated reports hub (recommended)** — `/reports` page with generator form + preview modal + download + approve; entity pickers reuse existing list hooks; reportable entities derived from entity lists.
   - Pros: single surface; follows the established feature-module pattern exactly (products/calls/researchers); reusable shared components; no cross-module page surgery; clean 3-PR slicing.
   - Cons: "reports list" is a derived entity list, not a true generated-reports registry (no status/history shown).
   - Effort: Medium (~1,200–1,600 lines across 3 PRs; chained).

2. **Embed actions in entity pages** — attach report actions (preview/download/approve) to existing project/researcher/center detail pages instead of a hub.
   - Pros: actions live where the entity context is richest; no picker duplication.
   - Cons: spreads the feature across 3 modules (higher touch surface, more cross-module test churn); still no reports registry; weaker discoverability of the feature as a whole.
   - Effort: High.

3. **Extend the backend** (report list/status/approval-queue endpoints) to back a true reports registry.
   - Pros: complete "list of generated reports" + approval queue with real statuses.
   - Cons: contradicts the archived-backend constraint; reopens backend spec/design/apply; larger scope.
   - Effort: High (backend + frontend).

## Recommendation

**Approach 1** — dedicated `features/reports` module on `/reports`, following the products/calls conventions verbatim (types/constants/queries/mutations, queryKeys factory, MSW, Spanish UI). New `lib/download.ts` for the authenticated PDF download and a sandboxed-iframe `PreviewDialog` for the HTML preview. Approval gated to director/admin with verbatim 409 handling. **PR slices (auto-chain, 400-line budget, risk High → chained):**

- **PR 1 — Foundation + generator form**: `lib/download.ts`, `features/reports/{types,constants,permissions,queries,mutations}.ts`, `queryKeys.reports`, MSW fixtures + handlers, Sidebar item, middleware protect, `/reports` page + `ReportGeneratorForm` (type + entity selectors + action row).
- **PR 2 — Preview + download**: `PreviewDialog` (sandboxed iframe), download wiring with pending/error states, generator-form UX polish, Jest coverage for both.
- **PR 3 — Approval + director gating**: approve mutation, role-gated button + 409 verbatim handling, director queue section derived from entity lists, tests, polish.

## Risks

- **No list/status API for reports** — "list of generated reports" and "approval queue" cannot show real statuses; must derive from entity lists or be descoped. Do NOT invent endpoints.
- **PDF download auth** — plain anchor/window.open drops cookies cross-origin; blob-fetch utility is mandatory.
- **HTML preview** — sandboxed iframe required; WYSIWYG fidelity must survive (print CSS in server HTML).
- **WeasyPrint latency** — PDF generated server-side per request (<5s NFR); download UX needs pending state; preview + download double-render cost.
- **RN-017 409** — must surface verbatim; approval strictly director/admin.
- **Fixture id alignment + MSW binary PDF** — gotcha from products PR3 (r1 vs r-1); MSW must mock the PDF as binary.
- **Middleware** — forgetting `/reports` in `PROTECTED_PREFIXES` leaves the page accessible pre-auth.

## Ready for Proposal

**Yes** — next phase `sdd-propose`. The orchestrator should tell the user: the reports backend is complete and archived; the frontend is greenfield; the single scope decision to settle at proposal is how to handle the "list of generated reports / approval queue" — derive from entity lists (recommended, no backend change) or descope to generator + actions only.
