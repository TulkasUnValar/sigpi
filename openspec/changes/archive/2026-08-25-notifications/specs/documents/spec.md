# Delta for Documents Capability (Notifications Change)

Adds the `document_signed` signal emission required by the notifications module (RN-3, §13.5).

## MODIFIED Requirements

### Requirement: RF-D04 — Digital Signing (RF-063, RF-064)

The system MUST sign a document version by fetching its bytes from MinIO, computing SHA-256 server-side, and persisting signer, date, document, and hash. On successful signing, the system SHALL additionally emit a `document_signed` Django signal (distinct from the `DOCUMENT_SIGNED` audit event) carrying `document`, `version`, `signer`, and `sha256`, for the notifications module (RN-3).
(Previously: signing persisted signature data and emitted only the `DOCUMENT_SIGNED` audit event; no semantic `document_signed` signal existed.)

#### Scenario: Sign a version
- GIVEN an unsigned document version and a user with sign permission
- WHEN POST `/api/documents/{id}/versions/{v}/sign/`
- THEN the system stores `DigitalSignature` with `signer`, `signed_at`, server-computed `sha256`, sets `document.is_signed=true`, and emits `DOCUMENT_SIGNED`

#### Scenario: Hash integrity failure
- GIVEN object bytes fetched from MinIO differ from expected content (tampered or missing)
- WHEN the signing service computes SHA-256
- THEN the system aborts signing and returns 409

#### Scenario: Re-sign denied
- GIVEN a version that already has a `DigitalSignature`
- WHEN POST sign is attempted again
- THEN the system returns 409

#### Scenario: Signal emitted on sign
- GIVEN a sign operation succeeds
- WHEN the signing transaction commits
- THEN a `document_signed` signal is dispatched with `document`, `version`, `signer`, `sha256`

#### Scenario: No signal on failed sign
- GIVEN a sign attempt fails (hash mismatch or re-sign)
- WHEN the operation returns 409
- THEN no `document_signed` signal is emitted