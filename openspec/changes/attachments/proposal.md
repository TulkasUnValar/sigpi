# Proposal: Attachments, Acts and Digital Signature (SIGPI §6.7)

## Intent

SIGPI has no real document capability: 6 metadata-only attachment models (name + doc_type + external_url) with no user, version, hash, or signed flag; no MinIO; no actas. This change delivers a new `documents` app — generic Document/Version/Signature/Minutes models, presigned MinIO uploads, SHA-256 signing, RF-066 immutability — satisfying RF-059..RF-066.

## Scope

### In Scope
- New `backend/apps/documents/`: `DocumentType`, `Document`, `DocumentVersion`, `DigitalSignature`, `Minutes` (+ serializers, views, urls, filters, services, admin, tests)
- RF-059/060: upload actas + generic attachments for projects, advances, reports, products, calls
- RF-061: MinIO via S3 API — presigned URL upload flow
- RF-062: metadata (user, date, entity, doc_type, version)
- RF-063/064: SHA-256 hash + signer metadata signing; RF-065: signed-document queries
- RF-066: service-level immutability for signed documents
- RLS via `0004_rls_policies.py` extension; audit via `AuditEventEmitter` (DOCUMENT_UPLOADED, DOCUMENT_SIGNED, MINUTES_CREATED)
- Infra: minio service in docker-compose.yml; boto3 + django-storages in pyproject/settings

### Out of Scope
- Touching existing 6 attachment models (back-compat; 2040+ tests stay green)
- Budget/researcher attachments
- PDF embedding of digitized signature (hash-only MVP)
- Certified external signature provider (EXC-05)

## Capabilities

### New Capabilities
- `documents`: generic Document/DocumentVersion/DigitalSignature — presigned upload, versioning, signing, signed queries, immutability
- `minutes`: Minutes model (acta_inicio/comite/aprobacion/cierre), FK→Project (optional) + Institution (RLS)

### Modified Capabilities
- `auth`: extend `AuditEventType` with DOCUMENT_UPLOADED, DOCUMENT_SIGNED, MINUTES_CREATED

## Approach

New app mirroring `calls`/`products` patterns. Upload: backend issues presigned PUT URL → frontend uploads to MinIO → backend confirms metadata + hash. Signing: service hashes object bytes (WeasyPrint output or uploaded file) + signer metadata → DigitalSignature tied to (Document, version). Version integer incremented on re-upload; signed docs reject version bump/update (FSM terminal-guard pattern). Permissions reuse `accounts/permissions.py` (Superadmin/Admin institucional/Director centro/Investigador/Coinvestigador).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/documents/` | New | Full app incl. tests |
| `backend/config/settings/base.py` | Modified | INSTALLED_APPS + MinIO storage |
| `backend/config/urls.py` | Modified | /api/documents/, /api/minutes/ |
| `backend/apps/accounts/audit.py` | Modified | 3 audit event types |
| `backend/apps/accounts/migrations/0004_rls_policies.py` | Modified | documents tables |
| `docker-compose.yml` | Modified | minio service |
| `pyproject.toml` | Modified | boto3, django-storages |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| MinIO absent in CI/dev → storage tests fail | High | compose service + test storage override |
| Hash trust: frontend-reported vs backend-computed | Med | Verify via GET object at sign time |
| RF-066 bypass via ORM/admin | Med | Service guards + model clean() + tests |
| Generic entity refs widen permission scope | Med | Denormalized institution_id + explicit FK set |
| Doc-type count mismatch (12 vs 13) | Low | Confirm in spec phase |

## Rollback Plan

Remove `apps.documents` from INSTALLED_APPS/urls; delete app dir; revert audit types, RLS entries, settings storage, compose minio, pyproject deps. MinIO bucket content can remain; DB rows dropped with app.

## Dependencies

- `projects` (Minutes FK, optional), `institutions` (RLS), `accounts` (permissions/audit), `reports` (WeasyPrint bytes as signable input), MinIO infra

## Success Criteria

- [ ] RF-059..RF-066 scenarios pass
- [ ] Presigned upload + metadata recording works end-to-end
- [ ] Signing records signer/date/hash; signed docs queryable
- [ ] Signed document mutation rejected
- [ ] Audit events emitted; RLS verified
- [ ] ≥80% coverage on `apps.documents`

## Proposal Question Round

1. Doc-type count: SPEC §6.7 table lists 12 types; exploration said 13 — confirm the authoritative list.
2. Hash verification: trust frontend-sent SHA-256, or backend GET-verify at sign time (extra MinIO read)?
3. Document↔entity binding: GenericForeignKey vs explicit nullable FK set — which for permission scoping?
4. Version strategy: new `DocumentVersion` row per upload, or in-place version bump on `Document`?