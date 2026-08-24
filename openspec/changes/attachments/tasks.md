# Tasks: Attachments, Acts and Digital Signature (documents module)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,400 (add+del) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | MinIO infra: compose, deps, settings, storage, app scaffold | PR 1 | `python -m pytest apps/documents/tests/test_storage.py -k presign` | `docker compose up -d minio`; presign smoke | Remove compose svc, deps, STORAGES, storage.py |
| 2 | Models + migrations 0001 + admin + model tests | PR 2 | `python -m pytest apps/documents/tests/test_models.py` | `makemigrations --check --dry-run` on PG | Drop documents tables; revert INSTALLED_APPS |
| 3 | RLS 0002 + audit types + migration | PR 3 | `python -m pytest apps/documents/tests/test_rls.py apps/accounts/tests/` | PG `set sigpi.institution_id` session vars | Revert 0002_rls_policies + accounts audit migration |
| 4 | Services + serializers + permissions + filters + unit tests | PR 4 | `python -m pytest apps/documents/tests/test_services.py apps/documents/tests/test_serializers.py apps/documents/tests/test_permissions.py apps/documents/tests/test_filters.py` | pytest-django, mocked MinIOStorage | Revert services/serializers/permissions/filters |
| 5 | Views + urls + API tests + e2e | PR 5 | `python -m pytest apps/documents/tests/` | Compose MinIO e2e: presign→PUT→confirm→sign→query | Revert urls.py + views.py wiring |

## Phase 1: Infrastructure (PR 1)

- [x] 1.1 `docker-compose.yml`: add `minio` service (ports 9000/9001, volume, healthcheck, env)
- [x] 1.2 `backend/pyproject.toml`: add `boto3` + `django-storages`
- [x] 1.3 `backend/config/settings/base.py`: `apps.documents` in INSTALLED_APPS; `STORAGES` MinIO default; endpoint/key/secret/bucket + presign expiry settings
- [x] 1.4 `backend/apps/documents/apps.py`: `DocumentsConfig`
- [x] 1.5 `backend/apps/documents/storage.py`: `MinIOStorage(S3Boto3Storage)` — private bucket, `documents/{institution}/{document}/v{version}/` prefix, 30m PUT / 15m GET

## Phase 2: Models & Migrations (PR 2)

- [x] 2.1 `backend/apps/documents/models.py`: DocumentType (12 codes), Document (UUID, institution, nullable entity FKs, doc_type, is_signed), DocumentVersion (unique `(document, version)`, sha256 64-hex), DigitalSignature (unique per version), Minutes (4 acta types); `clean()` immutability guard
- [x] 2.2 Seed migration: 12 DocumentType rows
- [x] 2.3 Generate `migrations/0001_initial.py` with constraints/indexes
- [x] 2.4 `admin.py`: register 5 models; signed docs read-only
- [x] 2.5 RED→GREEN `tests/test_models.py`: clean() immutability, sha256 format, version uniqueness, acta_type choices

## Phase 3: RLS & Audit (PR 3)

- [x] 3.1 `migrations/0002_rls_policies.py`: tenant_isolation + superadmin_bypass on Document/Minutes (institution_id); FK-subquery policies on Version/Signature; PG-only
- [x] 3.2 `accounts/audit.py`: add DOCUMENT_UPLOADED, DOCUMENT_SIGNED, MINUTES_CREATED + migration 0007
- [x] 3.3 RED→GREEN `tests/test_rls.py`: isolation + superadmin bypass (PG CI)

## Phase 4: Services, Serializers, Permissions, Filters (PR 4)

- [ ] 4.1 `services.py`: DocumentService (presign key issue, confirm key-match → 409, version bump, entity institution check, DOCUMENT_UPLOADED); SignatureService (GET→SHA-256→sign→lock; 409 hash mismatch/re-sign; DOCUMENT_SIGNED); MinutesService (acta validate, MINUTES_CREATED)
- [ ] 4.2 `serializers.py`: Document, DocumentVersion, DigitalSignature, Minutes, DocumentType
- [ ] 4.3 `permissions.py`: write role level ≤6; reads IsSameInstitution; IsAuditor read-only
- [ ] 4.4 `filters.py`: DocumentFilter (doc_type, entity, is_signed); MinutesFilter (acta_type, project)
- [ ] 4.5 RED→GREEN unit tests: services (hash mismatch, re-sign, signed bump → 409), serializers, permissions, filters

## Phase 5: Views, URLs & Integration (PR 5)

- [ ] 5.1 `views.py`: ViewSets + actions — types, presign, confirm, CRUD (immutable → 409), versions list/re-upload, version detail + GET presign, sign, download; minutes CRUD
- [ ] 5.2 `urls.py` + `backend/config/urls.py`: mount `/api/documents/`, `/api/minutes/`
- [ ] 5.3 RED→GREEN API tests: error contract 400/403/404/409/503; presign→confirm→sign flows; `is_signed` filter
- [ ] 5.4 Integration: Compose MinIO e2e (presign→PUT→confirm→sign→query); coverage ≥80% on `apps.documents`; ruff + mypy clean