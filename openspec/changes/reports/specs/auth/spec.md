# Delta for Auth

## MODIFIED Requirements

### Requirement: FR-007 — Auth Audit Events

The system MUST emit audit events for login, logout, role change, permission denied, report generation, and report approval.

(Previously: login, logout, role change, and permission denied only)

#### Scenario: Successful login audit
- GIVEN a user logs in successfully
- WHEN the session is created
- THEN an audit event is emitted with user, timestamp, IP, auth source, and institution

#### Scenario: Report generation audit
- GIVEN a user generates a PDF report
- WHEN the PDF is streamed successfully
- THEN a `REPORT_GENERATED` audit event is emitted with user, report type, entity ID, and timestamp

#### Scenario: Report approval audit
- GIVEN a center director approves a report
- WHEN the approval is persisted
- THEN a `REPORT_APPROVED` audit event is emitted with approver, report type, entity ID, and timestamp

## ADDED Requirements

### Requirement: Report Audit Event Types

The system MUST extend `AuditEventType` enum with `REPORT_GENERATED` and `REPORT_APPROVED` values.

#### Scenario: Event type available
- GIVEN the auth module is loaded
- WHEN `AuditEventType` is inspected
- THEN `REPORT_GENERATED` and `REPORT_APPROVED` are valid enum members
