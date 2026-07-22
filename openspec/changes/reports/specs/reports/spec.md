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

## Non-Functional Requirements

- PDF generation SHOULD complete in <5 seconds for reports under 50 pages.
- Test coverage MUST be ≥90% on `apps.reports`.
- Templates MUST use print-optimized CSS.
