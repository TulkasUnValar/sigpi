# Design: Documents, Minutes and Digital Signatures

## Technical Approach

Add `backend/apps/documents`, following the UUID models, explicit `clean()` validation, institution denormalization, DRF viewsets/actions, and service-layer business rules used by calls, products, and reports. Files never transit Django: presign creates a private MinIO object key, the client uploads with S3, and confirm records metadata only. Signing fetches the confirmed object through the storage backend, computes SHA-256, and locks the document.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Entity binding | Nullable explicit FKs to Project, Progress, Call, ResearchProduct, and Report, plus `entity_type`/`entity_id` validation | GenericForeignKey weakens referential integrity and RLS; explicit fields match the spec and existing generic Report pattern. |
| Versioning | `DocumentVersion` FK with unique `(document, version)`; `Document.current_version` is derived/maintained from the latest row | In-place integer history loses upload metadata; the FK preserves immutable upload history. |
| Storage | `django-storages` `S3Boto3Storage` targeting MinIO; private bucket; 30-minute PUT and 15-minute GET presigns | Direct boto3 couples services to MinIO and bypasses Django storage configuration. |
| Signature relation | `DigitalSignature.document_version` FK, exposing document and version through that relation; one signature per version | Duplicating document and version FKs permits inconsistent rows. |
| Immutability | Service guard plus model `clean()` raises `ValidationError` when any version is signed | API-only checks are bypassable by admin/scripts; DB-only checks cannot inspect object state conveniently. |

## Data Flow

```text
presign → Document + pending object key → client PUT MinIO
       → confirm → HEAD/object metadata → DocumentVersion → audit
       → sign → GET bytes → SHA-256 → DigitalSignature → lock
```

`DocumentService` resolves and validates the target entity's institution, allocates the next version, confirms the issued key/object existence, and emits `DOCUMENT_UPLOADED`. `SignatureService` rejects missing/already-signed versions, hashes server-side, creates the signature atomically, sets `is_signed`, and emits `DOCUMENT_SIGNED`. `MinutesService` validates acta type, project/institution consistency, creates the row, and emits `MINUTES_CREATED`.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/documents/{apps,models,serializers,views,urls,filters,services,admin}.py` | Create | Models, presign/confirm/version/sign/download/type APIs, filtering, and domain services. |
| `backend/apps/documents/tests/` | Create | Factories, API/service tests, RLS checks, and storage fakes/mocks. |
| `backend/apps/documents/migrations/0001_initial.py` | Create | Five models, constraints, indexes, and fixed document types. |
| `backend/apps/documents/migrations/0002_rls_policies.py` | Create | PostgreSQL tenant and superadmin policies. |
| `backend/apps/accounts/audit.py` and next audit migration | Modify/Create | Add the three event types; migrate the existing audit choice column. |
| `backend/config/settings/base.py`, `backend/config/urls.py` | Modify | Install app, S3/MinIO environment settings, and documents/minutes routes. |
| `backend/pyproject.toml`, `docker-compose.yml` | Modify | Add `boto3`, `django-storages`, and private MinIO service/volume/env wiring. |

## Interfaces / Contracts

Endpoints: `/api/documents/types/`, `/presign/`, `/{id}/confirm/`, CRUD, `/{id}/versions/`, version detail/download, `/{id}/versions/{v}/sign/`, `/api/minutes/` CRUD. Use `IsAuthenticated`, `IsSameInstitution`, and role level ≤6 for writes; auditors remain read-only, while reads are institution-scoped. Presign returns `upload_url`, `object_key`, and `document_id`; failures map to 400/403/404/409/503 per spec.

RLS enables `tenant_isolation` and `superadmin_bypass` on Document and Minutes via `institution_id`; Version and Signature use FK subqueries through Document/Version. SQLite migrations are no-ops, matching existing RLS migrations.

## Testing Strategy

Use factory-boy factories for institutions, memberships, users, entities, documents, versions, and signatures. Unit-test service validation, version allocation, hash mismatch, duplicate signing, and immutability. API-test permissions, endpoint status/error contracts, filters, and presign responses. Mock `S3Boto3Storage`/boto3 for deterministic PUT/HEAD/GET flows; mark real MinIO tests integration and run against Compose. Verify PostgreSQL RLS separately; enforce the configured 80% coverage floor.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no execution of documentation paths | No test |
| Git repository selection | N/A — no Git automation | No test |
| Commit state | N/A — no commit automation | No test |
| Push state | N/A — no push automation | No test |
| PR commands | N/A — no PR automation | No test |

## Migration / Rollout

Apply documents `0001_initial` then `0002_rls_policies`; add the next accounts migration for audit choices (the proposal's `accounts 0004` reference is stale because migrations through `0006` already exist). Add MinIO/config before enabling upload routes. Existing metadata-only attachment apps remain untouched. No data migration is required.

## Open Questions

- [ ] Confirm exact Progress model label/relationship name before migration generation.
- [ ] Confirm production bucket credentials and endpoint policy outside development Compose.
