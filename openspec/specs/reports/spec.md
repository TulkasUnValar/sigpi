# Reports Specification

## Purpose

Generate on-demand PDF reports for projects, researchers, centers, and advances with preview, director approval, and audit trail.

## Requirements

### Requirement: Project Report (RF-050)

The system MUST generate a PDF report containing project general data, objectives, team, budget summary, results, and progress.

#### Scenario: Generate project report
- GIVEN a project exists and the user has read access
- WHEN GET `/api/reports/project/{id}/pdf/`
- THEN the system streams a valid PDF with project data

#### Scenario: Unauthorized project access
- GIVEN a user lacks read permission on the project
- WHEN GET `/api/reports/project/{id}/pdf/`
- THEN the system returns 403

### Requirement: Researcher Report (RF-051)

The system MUST generate a PDF report containing researcher profile, projects, and production summary.

#### Scenario: Generate researcher report
- GIVEN a researcher profile exists and the user has read access
- WHEN GET `/api/reports/researcher/{id}/pdf/`
- THEN the system streams a valid PDF with researcher data

### Requirement: Center Report (RF-052)

The system MUST generate a PDF report containing center data, project list, and aggregate statistics.

#### Scenario: Generate center report
- GIVEN a center exists and the user belongs to the same institution
- WHEN GET `/api/reports/center/{id}/pdf/`
- THEN the system streams a valid PDF with center data

### Requirement: Advances Report (RF-053)

The system MUST generate a PDF report containing activities, completion percentage, documents, and reviews.

#### Scenario: Generate advances report
- GIVEN a project with progress records exists
- WHEN GET `/api/reports/advances/{project_id}/pdf/`
- THEN the system streams a valid PDF with progress data

### Requirement: Preview (RF-056)

The system MUST provide an HTML preview matching the PDF output (WYSIWYG).

#### Scenario: Preview report
- GIVEN a valid report type and entity ID
- WHEN GET `/api/reports/{type}/{id}/preview/`
- THEN the system returns `{"html": "..."}` matching the PDF template

### Requirement: PDF Generation via WeasyPrint (RF-057)

The system MUST render Django templates to HTML and convert to PDF using WeasyPrint, streaming the result.

#### Scenario: PDF streaming
- GIVEN a valid report request
- WHEN the PDF endpoint is called
- THEN the system streams `FileResponse` with `Content-Type: application/pdf`

#### Scenario: Template rendering failure
- GIVEN a template context error
- WHEN PDF generation is attempted
- THEN the system returns 500 with a descriptive error

### Requirement: Audit (RF-058)

The system MUST emit `REPORT_GENERATED` and `REPORT_APPROVED` audit events for all report operations.

#### Scenario: Generation audit
- GIVEN a PDF is successfully generated
- WHEN the response is streamed
- THEN a `REPORT_GENERATED` audit event is emitted with user, report type, entity ID, and timestamp

#### Scenario: Approval audit
- GIVEN a report is approved
- WHEN the approval is persisted
- THEN a `REPORT_APPROVED` audit event is emitted with approver, report type, and timestamp

### Requirement: Authorized Data Only (RN-015)

The system MUST generate reports using only data the requesting user is authorized to access.

#### Scenario: Tenant-scoped data
- GIVEN a user from institution A requests a center report
- WHEN the center belongs to institution B
- THEN the system returns 403

### Requirement: Center Director Approval (RN-016)

The system MUST allow only the center director to approve reports for their center.

#### Scenario: Director approves
- GIVEN a center director for center C
- WHEN POST `/api/reports/{type}/{id}/approve/` for a report in center C
- THEN the system persists `ReportApproval` with date, approver, and version

#### Scenario: Non-director denied
- GIVEN a user who is not the center director
- WHEN POST `/api/reports/{type}/{id}/approve/`
- THEN the system returns 403

### Requirement: Pending Advances Guard (RN-017)

The system MUST block final report approval when the project has pending progress reports.

#### Scenario: Approval blocked
- GIVEN a project with unreviewed progress reports
- WHEN POST `/api/reports/project/{id}/approve/`
- THEN the system returns 409 with `"Pending progress reports must be reviewed"`

#### Scenario: Approval allowed
- GIVEN a project with all progress reports reviewed
- WHEN POST `/api/reports/project/{id}/approve/`
- THEN the system persists approval successfully

### Requirement: Approval Metadata (RN-018)

The system MUST persist approval date, approver, and report version on every approval.

#### Scenario: Metadata persisted
- GIVEN a successful approval
- WHEN `ReportApproval` is created
- THEN `approved_at`, `approved_by`, and `report_version` fields are non-null

## Frontend UI Requirements

### Requirement: Reports hub page (RF-001)

The frontend MUST expose a protected `/reports` page with a report-type selector and per-entity lists (projects, researchers, centers) showing report status indicators and action buttons, derived from existing list hooks.

#### Scenario: Hub renders entity lists
- GIVEN an authenticated user with CanGenerateReport and list hooks resolved
- WHEN the user navigates to `/reports`
- THEN the page shows the type selector and entity lists with status indicators

#### Scenario: Permission denied
- GIVEN a user without CanGenerateReport
- WHEN the user requests `/reports`
- THEN access is denied (role-gated, no API calls)

### Requirement: Report generator form (RF-002)

The frontend MUST provide a form where selecting a report type (project, researcher, center, advances) drives a dependent entity selector fed by existing hooks; `advances` MUST target a project entity.

#### Scenario: Dependent entity selector
- GIVEN report type `project` selected
- WHEN the entity selector renders
- THEN it lists projects from `useProjectsList`

#### Scenario: Advances targets projects
- GIVEN report type `advances` selected
- WHEN the entity selector renders
- THEN it lists projects, not advances

### Requirement: HTML preview (RF-003)

The frontend MUST render the HTML from `GET /api/reports/{type}/{id}/preview/` inside a sandboxed iframe via `srcDoc` without `allow-same-origin`.

#### Scenario: Preview renders
- GIVEN a selected entity and a 200 `{"html": "..."}` response
- WHEN "Vista previa" is clicked
- THEN the HTML renders in a sandboxed iframe

#### Scenario: Preview error
- GIVEN a 403/404/500 preview response
- WHEN the preview dialog opens
- THEN an error state is shown and no HTML renders

### Requirement: PDF download (RF-004)

The frontend MUST download the PDF via authenticated blob fetch (`fetch` → blob → objectURL → anchor click) from `GET /api/reports/{type}/{id}/pdf/`, with a pending state while generating.

#### Scenario: Blob download
- GIVEN a selected entity and session auth
- WHEN "Descargar PDF" is clicked
- THEN the file downloads as `{type}_report.pdf` via blob, not a plain href

#### Scenario: Generation pending
- GIVEN WeasyPrint generation in flight
- WHEN the download request is pending
- THEN the button shows pending state and actions are disabled

### Requirement: Approval flow (RF-005)

The frontend MUST allow center directors to approve via `POST /api/reports/{type}/{id}/approve/` and MUST surface a 409 RN-017 response verbatim as a toast without invalidating queries.

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

The frontend MUST add an "Informes" sidebar item linking to `/reports` and MUST include `/reports` in middleware `PROTECTED_PREFIXES`.

#### Scenario: Nav item visible
- GIVEN an authenticated user
- WHEN the sidebar renders
- THEN an "Informes" item navigates to `/reports`

#### Scenario: Unauthenticated redirect
- GIVEN an unauthenticated user
- WHEN `/reports` is requested
- THEN middleware redirects to login

## Business Rules (Frontend)

- **RB-001 (role gating)**: Preview/PDF require CanGenerateReport (role ≤ 4; admin level ≤ 2 bypass). Approve requires center director (role ≤ 3 + center membership; superuser bypass). Non-directors MUST NOT see or fire the approve action.
- **RB-002 (RN-017 409)**: A 409 from the approval endpoint MUST show the server message verbatim and MUST NOT invalidate entity queries.
- **RB-003 (institution scoping, RN-015)**: All API calls MUST send `X-Institution-ID`; the UI MUST offer only entities from the active institution's hooks, and 403 preview/PDF responses MUST show an error state.
- **RB-004 (no invented endpoints)**: Entity lists and statuses are derived from existing hooks; only preview/pdf/approve endpoints are called.

## Non-Functional Requirements

- PDF generation SHOULD complete in <5 seconds for reports under 50 pages.
- Test coverage MUST be ≥90% on `apps.reports`.
- Templates MUST use print-optimized CSS.
- Frontend Jest coverage MUST be ≥80% on `features/reports`; ESLint and `tsc --noEmit` green per PR.
- Download pending state MUST reflect the WeasyPrint <5s NFR.
- UI copy MUST be Spanish.
