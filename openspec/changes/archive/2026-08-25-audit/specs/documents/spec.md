# Delta for Documents — Audit (RF-106)

## ADDED Requirements

### Requirement: RF-D09 — Sensitive Download Auditing (RF-106)

The system MUST emit a `DOCUMENT_DOWNLOADED` audit event (`action=DOWNLOAD`, `event_type=DOCUMENT_DOWNLOADED`) whenever a presigned GET URL is issued via the `download` or `version_detail` document actions, capturing the acting user, `document_id`, `version`, and institution.

#### Scenario: Latest-version download
- GIVEN an authorized user requests `GET /api/documents/{id}/download/`
- WHEN the presigned GET URL is issued
- THEN an AuditEvent `DOCUMENT_DOWNLOADED` is emitted with `document_id`, `version`, `user`, and `institution_id`

#### Scenario: Version-detail download
- GIVEN a user requests `GET /api/documents/{id}/versions/{v}/`
- WHEN the presigned GET URL is issued
- THEN a `DOCUMENT_DOWNLOADED` event is emitted for that `version`

#### Scenario: Storage failure (no event)
- GIVEN MinIO is unreachable
- WHEN `download`/`version_detail` returns 503
- THEN no `DOCUMENT_DOWNLOADED` event is emitted (no download was issued)

## MODIFIED Requirements

### Requirement: Audit Requirements

The system MUST emit, via `AuditEventEmitter`: `DOCUMENT_UPLOADED` (user, document_id, version), `DOCUMENT_SIGNED` (signer, document_id, version, sha256), and `MINUTES_CREATED` (user, minutes_id, acta_type); and `DOCUMENT_DOWNLOADED` (user, document_id, version) on presigned GET issuance per RF-106 (RF-D09). See the audit spec for the `AuditEventType` extension.
(Previously: only upload, sign, and minutes events were specified.)
