# Tasks: Researchers Module (SIGPI §6.3)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,400 (4 models, 2 migrations, 2 services, 6 serializers, 4 viewsets, permissions, URLs, admin, ~550 lines of tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 5 PRs (see work units below) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models + Migration 0001 + Factories + Model tests | PR 1 | Base branch; all downstream PRs depend on this |
| 2 | Services + Migration 0002 (RLS) + Service/RLS tests | PR 2 | Depends on PR 1; business logic + security |
| 3 | Serializers + Permissions + URLs + Serializer/Permission/URL tests | PR 3 | Depends on PR 1+2; API contract without viewsets |
| 4 | ViewSets + Integration tests + URL wiring | PR 4 | Depends on PR 3; largest slice (~400 lines) |
| 5 | Admin registration + Full suite verification | PR 5 | Depends on PR 4; small cleanup slice (~60 lines) |

## Phase 1: Foundation — Models, Migration, Factories

- [x] 1.1 Create `backend/apps/researchers/__init__.py` (empty) and `backend/apps/researchers/apps.py` with `ResearchersConfig`. Add `apps.researchers` to `INSTALLED_APPS` in `backend/config/settings/base.py`. (~10 lines)
- [x] 1.2 Create `backend/apps/researchers/models.py`: `Researcher` model with UUID PK, `user` FK (nullable, unique), `institution` FK, `first_name`, `last_name`, `document_type`, `document_number`, `primary_email`, `phone`, `bio`, `academic_formation`, `is_active`, timestamps. Add `UniqueConstraint(institution, document_number)`, `DocumentTypeChoices`, `clean()` method. (~60 lines)
- [x] 1.3 Add `ResearcherAffiliation` model to `models.py`: UUID PK, `researcher` FK, `center`/`group`/`line` FKs (all nullable), `is_primary`. `clean()` validates at least one FK set, all FKs belong to researcher's institution, and only one `is_primary=True` per researcher. (~40 lines)
- [x] 1.4 Add `ExternalProfile` model to `models.py`: UUID PK, `researcher` FK, `provider` (ProviderChoices: cvlac, orcid, google_scholar, linkedin, researchgate), `url`. (~20 lines)
- [x] 1.5 Add `ResearcherAttachment` model to `models.py`: UUID PK, `researcher` FK, `name`, `type` (TypeChoices: cv, certificate, photo, other), `external_url`. (~20 lines)
- [x] 1.6 Generate migration `backend/apps/researchers/migrations/0001_initial.py`: CreateModel for 4 tables, AddIndex `(institution_id, is_active)` on Researcher, unique index on `user_id` WHERE NOT NULL. (~100 lines, auto-generated)
- [x] 1.7 Create `backend/apps/researchers/tests/__init__.py` and `backend/apps/researchers/tests/conftest.py` with factory-boy factories: `ResearcherFactory`, `ResearcherAffiliationFactory`, `ExternalProfileFactory`, `ResearcherAttachmentFactory`. (~80 lines)
- [x] 1.8 Write `backend/apps/researchers/tests/test_models.py`: unique constraint `(institution, document_number)`, `clean()` rejection for affiliation with no FK, cross-institution FK rejection, multiple primary affiliation rejection, `__str__` methods. (~120 lines)

## Phase 2: Service Layer + RLS Policies

- [x] 2.1 Create `backend/apps/researchers/services.py` with `ResearcherProfileService`: `create()`, `update()`, `deactivate()`, `calculate_completeness()` (counts mandatory fields populated / total * 100). (~50 lines)
- [x] 2.2 Add `ResearcherAffiliationService` to `services.py`: `add()`, `remove()`, `set_primary()` (atomic transaction: unset current primary, set new one). (~30 lines)
- [x] 2.3 Write `backend/apps/researchers/tests/test_services.py`: CRUD operations, completeness formula (missing fields → score < 100, all fields → 100), affiliation add/remove, set_primary atomicity, cross-institution affiliation rejection. (~80 lines)
- [x] 2.4 Create migration `backend/apps/researchers/migrations/0002_rls_policies.py`: Enable RLS + `tenant_isolation` + `superadmin_bypass` on 4 tables. Child tables use subquery via `researcher_id`. Follow `institutions/0003` pattern (RunPython, PostgreSQL-only guard). (~90 lines)
- [x] 2.5 Write `backend/apps/researchers/tests/test_rls.py`: migration structure tests (exists, has RunPython, depends on 0001), SQL contains expected tables and policies. Mark PostgreSQL-only enforcement tests with `@pytest.mark.skip`. (~50 lines)

## Phase 3: DRF API — Serializers, Permissions, URLs

- [x] 3.1 Create `backend/apps/researchers/permissions.py`: `IsResearcherOrReadOnly` (write: user is owning researcher or role ≤ 2; read: any authenticated in same institution). Re-export `IsInstitutionAdminOrReadOnly`, `IsSameInstitution` from accounts. (~40 lines)
- [x] 3.2 Create `backend/apps/researchers/serializers.py`: `ResearcherListSerializer` (id, name, institution, is_active, completeness_score), `ResearcherSerializer` (all fields + nested affiliations/profiles/attachments), `ResearcherCreateSerializer` (writable fields, institution injected by view), `ResearcherAffiliationSerializer`, `ExternalProfileSerializer`, `ResearcherAttachmentSerializer`. (~120 lines)
- [x] 3.3 Write `backend/apps/researchers/tests/test_serializers.py`: field validation, completeness_score output, nested serialization, provider/type choice validation, create serializer institution injection. (~80 lines)
- [x] 3.4 Write `backend/apps/researchers/tests/test_permissions.py`: role-based access matrix (superadmin, admin, director, researcher, authenticated), self-profile edit allowed, cross-institution denial, researcher read-only for non-owners. (~60 lines)
- [x] 3.5 Create `backend/apps/researchers/urls.py`: manual nested paths for `/researchers/`, `/researchers/{id}/affiliations/`, `/researchers/{id}/profiles/`, `/researchers/{id}/attachments/` with detail routes. (~40 lines)
- [x] 3.6 Write `backend/apps/researchers/tests/test_urls.py`: route resolution for all 8 URL patterns using `reverse()`. (~30 lines)

## Phase 4: ViewSets + Integration Tests

- [x] 4.1 Create `backend/apps/researchers/views.py`: `ResearcherViewSet` (list/create/retrieve/update/delete, `get_serializer_class` per action), `ResearcherAffiliationViewSet`, `ExternalProfileViewSet`, `ResearcherAttachmentViewSet`. Each scopes queryset by institution. Call services for create/update/delete. (~150 lines)
- [x] 4.2 Wire researchers URLs into `backend/config/urls.py`: `path("api/", include("apps.researchers.urls"))`. Update tenant middleware `TENANT_REQUIRED_PREFIXES` to include `/api/researchers/`. (~5 lines)
- [x] 4.3 Write `backend/apps/researchers/tests/test_views.py`: CRUD integration tests for researcher (list, create, retrieve, update, delete), nested affiliation/profile/attachment endpoints, error responses (409 duplicate document, 400 cross-institution affiliation, 400 multiple primary), permission tests per role, completeness_score in response. (~200 lines)

## Phase 5: Admin + Cleanup

- [x] 5.1 Create `backend/apps/researchers/admin.py`: register all 4 models with `list_display`, `search_fields`, `list_filter`, `raw_id_fields`. (~40 lines)
- [x] 5.2 Write `backend/apps/researchers/tests/test_admin.py`: verify all 4 models registered, admin classes have expected attributes. (~20 lines)
- [x] 5.3 Run full test suite, verify ≥80% coverage with `pytest --cov=apps.researchers`, run `ruff check` + `mypy` on all new files. Fix any linting/type issues.
