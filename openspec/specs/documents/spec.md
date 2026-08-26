# Documents Specification (SIGPI §6.7)

## Purpose

Manage institutional documents, actas, attachments, and digital signatures for projects, advances, reports, products, and calls: MinIO-backed storage via S3 API, presigned uploads, versioning, SHA-256 signing, signed-document queries, and immutability of signed documents (RF-059..RF-066).

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **DocumentType** | `code`, `label` | 12 fixed types per SPEC §6.7 (below) |
| **Document** | `id` (UUID), `institution` (FK, denormalized), `project` (FK, nullable), `entity_type` + `entity_id` (explicit nullable FKs: advance/report/product/call), `doc_type` (FK), `title`, `is_signed`, `created_by`, `created_at` | Explicit FK set, no GenericForeignKey; `institution_id` denormalized for RLS |
| **DocumentVersion** | `id`, `document` (FK), `version` (int ≥ 1), `object_key`, `sha256`, `size_bytes`, `mime_type`, `uploaded_by`, `uploaded_at` | `UniqueConstraint(document, version)`; sha256 MUST be 64-char lowercase hex |
| **DigitalSignature** | `id`, `document_version` (FK), `signer` (FK User), `signed_at`, `sha256`, `signer_metadata` (JSON) | One per version; signing locks the version |
| **Minutes** | `id`, `acta_type` (4 values), `project` (FK, optional), `institution` (FK), `document` (FK), `created_by`, `created_at` | acta_type ∈ inicio/comite/aprobacion/cierre; `institution_id` denormalized |

### Document Types (12, per SPEC §6.7)

`acta_inicio`, `acta_comite`, `acta_aprobacion`, `acta_cierre`, `formulacion_proyecto`, `informe_parcial`, `informe_final`, `evidencia_producto`, `presupuesto`, `carta_aval`, `certificacion`, `otro`.

## Functional Requirements

### Requirement: RF-D01 — Presigned Upload (RF-059, RF-060, RF-061)

The system MUST store documents in MinIO via the S3 API using backend-issued presigned PUT URLs; the backend MUST NOT receive file bytes.

#### Scenario: Issue presigned URL
- GIVEN an authenticated user with write access to the target entity's institution
- WHEN POST `/api/documents/presign/` with `{doc_type, entity_type, entity_id, filename, content_type}`
- THEN the system returns `{upload_url, object_key, document_id}` with an expiring presigned PUT URL

#### Scenario: Unauthorized entity
- GIVEN a user whose active institution differs from the entity's institution
- WHEN POST `/api/documents/presign/`
- THEN the system returns 403

#### Scenario: Confirm upload
- GIVEN the frontend uploaded the object to MinIO with the issued `object_key`
- WHEN POST `/api/documents/{id}/confirm/` with `{object_key}`
- THEN the system creates `DocumentVersion` v1 with `uploaded_by`, `uploaded_at`, and emits `DOCUMENT_UPLOADED`

#### Scenario: Confirm with wrong key
- GIVEN a confirm with an `object_key` not issued for this document
- WHEN POST `/api/documents/{id}/confirm/`
- THEN the system returns 409 and records no version

### Requirement: RF-D02 — Metadata Recording (RF-062)

The system MUST record uploader, date, related entity, document type, and version for every stored document.

#### Scenario: Metadata persisted
- GIVEN a confirmed upload
- WHEN the version row is inspected
- THEN `uploaded_by`, `uploaded_at`, `doc_type`, `entity_type`/`entity_id`, and `version` are non-null

#### Scenario: Invalid document type
- GIVEN a `doc_type` not among the 12 defined types
- WHEN POST `/api/documents/presign/`
- THEN the system returns 400

### Requirement: RF-D03 — Version Control

The system MUST create a new `DocumentVersion` row and increment the version integer on each re-upload.

#### Scenario: Re-upload bumps version
- GIVEN an unsigned document with v1
- WHEN POST `/api/documents/{id}/versions/` + confirm
- THEN the system creates v2 and `document.current_version` becomes 2

#### Scenario: Version ordering
- GIVEN a document with multiple versions
- WHEN GET `/api/documents/{id}/versions/`
- THEN versions are returned in descending order with full metadata

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
### Requirement: RF-D05 — Signed Document Queries (RF-065)

The system MUST allow querying signed documents with their signature metadata.

#### Scenario: Filter signed documents
- GIVEN documents with and without signatures
- WHEN GET `/api/documents/?is_signed=true`
- THEN the response contains only signed documents with `signer`, `signed_at`, and `sha256`

#### Scenario: No signed documents
- GIVEN an institution with no signed documents
- WHEN GET `/api/documents/?is_signed=true`
- THEN the response is an empty list

### Requirement: RF-D06 — Signed Document Immutability (RF-066)

The system MUST reject modification, deletion, and version bumps of signed documents at both service and model layers.

#### Scenario: Update rejected
- GIVEN a signed document
- WHEN PATCH `/api/documents/{id}/` or DELETE is attempted
- THEN the system returns 409 with `"Signed documents are immutable"`

#### Scenario: Version bump rejected
- GIVEN a signed document
- WHEN POST `/api/documents/{id}/versions/`
- THEN the system returns 409

#### Scenario: Unsigned remains mutable
- GIVEN an unsigned document
- WHEN PATCH or DELETE is attempted
- THEN the system applies the change

### Requirement: RF-D07 — Minutes (RF-059)

The system MUST allow creating actas of four types (inicio, comité, aprobación, cierre) linked to a project (optional) and an institution, backed by a Document.

#### Scenario: Create acta
- GIVEN a project and an uploaded `Document` of type acta_*
- WHEN POST `/api/minutes/` with `{acta_type, project_id, document_id}`
- THEN the system creates a `Minutes` row linked to the document and emits `MINUTES_CREATED`

#### Scenario: Invalid acta type
- GIVEN an `acta_type` outside the four defined values
- WHEN POST `/api/minutes/`
- THEN the system returns 400

#### Scenario: Signed acta immutable
- GIVEN a `Minutes` whose document version is signed
- WHEN an update or delete is attempted
- THEN the system returns 409

### Requirement: RF-D08 — Document Types

The system MUST expose the 12 document types from SPEC §6.7 as the authoritative, closed choice set.

#### Scenario: List types
- GIVEN an authenticated user
- WHEN GET `/api/documents/types/`
- THEN the response lists exactly the 12 types with codes and labels

#### Scenario: Unknown type rejected
- GIVEN a document with an undefined type code
- WHEN the document is created
- THEN the system returns 400

## API Contract

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/documents/types/` | GET | Session | List 12 doc types |
| `/api/documents/presign/` | POST | Session | Issue presigned PUT URL |
| `/api/documents/{id}/confirm/` | POST | Session | Record version after upload |
| `/api/documents/` | GET / POST* | Session | List (filters: doc_type, entity, is_signed) / new upload |
| `/api/documents/{id}/` | GET / PATCH / DELETE | Session | Detail / metadata update / delete (unsigned only) |
| `/api/documents/{id}/versions/` | GET / POST* | Session | List versions / re-upload |
| `/api/documents/{id}/versions/{v}/` | GET | Session | Version detail + presigned GET download |
| `/api/documents/{id}/versions/{v}/sign/` | POST | Session | Sign version |
| `/api/documents/{id}/download/` | GET | Session | Presigned GET URL |
| `/api/minutes/` | GET / POST | Session | List / create actas |
| `/api/minutes/{id}/` | GET / PATCH / DELETE | Session | Acta detail / update / delete (signed → 409) |

*POST on list/versions starts the presign flow; no file bytes transit the backend.

## MinIO/S3 Contract

- Storage MUST use django-storages S3 backend against MinIO; the bucket MUST be private.
- Object keys MUST follow `documents/{institution_id}/{document_id}/v{version}/{filename}`.
- Presigned PUT URLs MUST expire within 30 minutes; presigned GET URLs MUST expire within 15 minutes.
- At sign time the backend MUST fetch object bytes and compute SHA-256 server-side; frontend-supplied hashes MUST NOT be trusted.
- Upload size SHOULD be capped at 100 MB.

## Authorization

- Write actions (presign, confirm, sign, minutes-create) MUST require an authenticated user with role level ≤ 6 in the document's institution (all roles except Auditor, per SPEC §6.7 permissions table).
- Reads MUST be allowed for any authenticated member of the institution; `IsSameInstitution` MUST be enforced on every document/minutes object.
- Auditors MUST be read-only (`IsAuditor`).

## Audit Requirements

The system MUST emit, via `AuditEventEmitter`: `DOCUMENT_UPLOADED` (user, document_id, version), `DOCUMENT_SIGNED` (signer, document_id, version, sha256), and `MINUTES_CREATED` (user, minutes_id, acta_type). See the auth delta spec for the `AuditEventType` extension.

## RLS Requirements

`documents_document` and `documents_minutes` MUST carry denormalized `institution_id` with `tenant_isolation` + `superadmin_bypass` policies; `documents_documentversion` and `documents_digitalsignature` MUST be covered via FK subqueries to their parent, following the existing RLS migration pattern.

## Error Handling

| Error | Status | Response |
|---|---|---|
| Invalid entity/type/filename | 400 | `{"detail": "..."}` |
| Confirm with unissued object_key | 409 | `{"detail": "Object key mismatch"}` |
| Sign/modify signed document | 409 | `{"detail": "Signed documents are immutable"}` |
| Re-sign signed version | 409 | `{"detail": "Version already signed"}` |
| Hash mismatch at sign time | 409 | `{"detail": "Integrity check failed"}` |
| Nonexistent document/version | 404 | `{"detail": "Not found"}` |
| MinIO unreachable | 503 | `{"detail": "Storage unavailable"}` |
| Cross-institution access | 403 | `{"detail": "..."}` |

## Acceptance Criteria

- [ ] All RF-D01..RF-D08 scenarios pass under pytest.
- [ ] Presign → upload → confirm → sign → query flow works end-to-end against the MinIO compose service.
- [ ] Signed-document mutation is rejected at both service and model (`clean()`) layers.
- [ ] `DOCUMENT_UPLOADED`, `DOCUMENT_SIGNED`, `MINUTES_CREATED` events are queryable in `AuditEvent`.
- [ ] RLS policies verified in PostgreSQL CI (`test_rls.py`).
- [ ] Coverage on `apps.documents` ≥ 80%.

## Non-Functional Requirements

- Presign response SHOULD complete in <300 ms; sign-time GET + hash SHOULD complete in <5 s for files ≤ 50 MB.
- DB stores metadata only — object bytes MUST NOT be stored in PostgreSQL.