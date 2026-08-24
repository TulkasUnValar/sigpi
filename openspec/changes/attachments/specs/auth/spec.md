# Delta for Auth

## MODIFIED Requirements

### Requirement: FR-007 — Auth Audit Events

The system MUST emit audit events for login, logout, role change, permission denied, report generation, report approval, document upload, document signing, and minutes creation.

(Previously: login, logout, role change, permission denied, report generation, and report approval only)

#### Scenario: Successful login audit
- GIVEN a user logs in successfully
- WHEN the session is created
- THEN an audit event is emitted with user, timestamp, IP, auth source, and institution

#### Scenario: Document upload audit
- GIVEN a document version is confirmed
- WHEN the upload is persisted
- THEN a `DOCUMENT_UPLOADED` audit event is emitted with user, document ID, and version

#### Scenario: Document signing audit
- GIVEN a document version is signed
- WHEN the signature is persisted
- THEN a `DOCUMENT_SIGNED` audit event is emitted with signer, document ID, version, and sha256

#### Scenario: Minutes creation audit
- GIVEN a Minutes row is created
- WHEN the minutes are persisted
- THEN a `MINUTES_CREATED` audit event is emitted with user, minutes ID, and acta type

## ADDED Requirements

### Requirement: Document Audit Event Types

The system MUST extend the `AuditEventType` enum with `DOCUMENT_UPLOADED`, `DOCUMENT_SIGNED`, and `MINUTES_CREATED` values.

#### Scenario: Event types available
- GIVEN the auth module is loaded
- WHEN `AuditEventType` is inspected
- THEN `DOCUMENT_UPLOADED`, `DOCUMENT_SIGNED`, and `MINUTES_CREATED` are valid enum members

#### Scenario: Legacy event types preserved
- GIVEN the extended enum
- WHEN existing values are inspected
- THEN `LOGIN`, `LOGOUT`, `REPORT_GENERATED`, and all prior members remain valid