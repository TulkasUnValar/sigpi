# Frontend Reports UI Specification (SIGPI §6.6)

## Purpose

Deliver the frontend reports surface for the archived `apps.reports` backend: a protected `/reports` hub where users generate, preview, download, and approve PDF reports (project, researcher, center, advances) with Spanish UI, reusing the established module pattern (`features/{module}` + App Router + MSW + Jest ≥80%).

## Requirements

### Requirement: Reports hub page (RF-001)

The system MUST expose a protected `/reports` page with a report-type selector and per-entity lists (projects, researchers, centers) showing report status indicators and action buttons, derived from existing list hooks.

#### Scenario: Hub renders entity lists
- GIVEN an authenticated user with CanGenerateReport and list hooks resolved
- WHEN the user navigates to `/reports`
- THEN the page shows the type selector and entity lists with status indicators

#### Scenario: Permission denied
- GIVEN a user without CanGenerateReport
- WHEN the user requests `/reports`
- THEN access is denied (role-gated, no API calls)

### Requirement: Report generator form (RF-002)

The system MUST provide a form where selecting a report type (project, researcher, center, advances) drives a dependent entity selector fed by existing hooks; `advances` MUST target a project entity.

#### Scenario: Dependent entity selector
- GIVEN report type `project` selected
- WHEN the entity selector renders
- THEN it lists projects from `useProjectsList`

#### Scenario: Advances targets projects
- GIVEN report type `advances` selected
- WHEN the entity selector renders
- THEN it lists projects, not advances

### Requirement: HTML preview (RF-003)

The system MUST render the HTML from `GET /api/reports/{type}/{id}/preview/` inside a sandboxed iframe via `srcDoc` without `allow-same-origin`.

#### Scenario: Preview renders
- GIVEN a selected entity and a 200 `{"html": "..."}` response
- WHEN "Vista previa" is clicked
- THEN the HTML renders in a sandboxed iframe

#### Scenario: Preview error
- GIVEN a 403/404/500 preview response
- WHEN the preview dialog opens
- THEN an error state is shown and no HTML renders

### Requirement: PDF download (RF-004)

The system MUST download the PDF via authenticated blob fetch (`fetch` → blob → objectURL → anchor click) from `GET /api/reports/{type}/{id}/pdf/`, with a pending state while generating.

#### Scenario: Blob download
- GIVEN a selected entity and session auth
- WHEN "Descargar PDF" is clicked
- THEN the file downloads as `{type}_report.pdf` via blob, not a plain href

#### Scenario: Generation pending
- GIVEN WeasyPrint generation in flight
- WHEN the download request is pending
- THEN the button shows pending state and actions are disabled

### Requirement: Approval flow (RF-005)

The system MUST allow center directors to approve via `POST /api/reports/{type}/{id}/approve/` and MUST surface a 409 RN-017 response verbatim as a toast without invalidating queries.

#### Scenario: Director approves
- GIVEN a center director and a reportable entity
- WHEN "Aprobar" is clicked
- THEN the POST succeeds and the entity status indicator updates

#### Scenario: Non-director denied
- GIVEN a user without director role
- WHEN the entity list renders
- THEN the approve action is hidden/disabled (no API call)

#### Scenario: RN-017 409 guard
- GIVEN a project with pending progress reports
- WHEN the approval POST returns 409
- THEN the toast shows "Pending progress reports must be reviewed" verbatim and queries are NOT invalidated

### Requirement: Sidebar navigation (RF-006)

The system MUST add an "Informes" sidebar item linking to `/reports` and MUST include `/reports` in middleware `PROTECTED_PREFIXES`.

#### Scenario: Nav item visible
- GIVEN an authenticated user
- WHEN the sidebar renders
- THEN an "Informes" item navigates to `/reports`

#### Scenario: Unauthenticated redirect
- GIVEN an unauthenticated user
- WHEN `/reports` is requested
- THEN middleware redirects to login

## Business Rules

- **RB-001 (role gating)**: Preview/PDF require CanGenerateReport (role ≤ 4; admin level ≤ 2 bypass). Approve requires center director (role ≤ 3 + center membership; superuser bypass). Non-directors MUST NOT see or fire the approve action.
- **RB-002 (RN-017 409)**: A 409 from the approval endpoint MUST show the server message verbatim and MUST NOT invalidate entity queries.
- **RB-003 (institution scoping, RN-015)**: All API calls MUST send `X-Institution-ID`; the UI MUST offer only entities from the active institution's hooks, and 403 preview/PDF responses MUST show an error state.
- **RB-004 (no invented endpoints)**: Entity lists and statuses are derived from existing hooks; only preview/pdf/approve endpoints are called.

## Out of Scope

- Backend changes to `apps.reports` (archived; no invented endpoints)
- Standalone reports registry / status-history views (no list API exists)
- Report template management (`ReportTemplate` has no API surface)
- Bulk PDF generation

## Non-Functional Requirements

- Jest coverage MUST be ≥80% on `features/reports`; ESLint and `tsc --noEmit` green per PR
- Download pending state MUST reflect the WeasyPrint <5s NFR
- UI copy MUST be Spanish
