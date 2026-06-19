# Tasks: Institutions & Research Structure (6.1)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,550 (6 models, 2 migrations, service layer, 6 serializers, 6 viewsets, permissions, URLs, admin, ~640 lines of tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 5 PRs (see work units below) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models + Migration 0002 + Factories + Model tests | PR 1 | Base branch; all downstream PRs depend on this |
| 2 | LifecycleService + Migration 0003 (RLS) + Service/RLS tests | PR 2 | Depends on PR 1; self-contained business logic + security |
| 3 | Serializers + Permissions + URL routing + Serializer tests | PR 3 | Depends on PR 1+2; API contract without viewsets |
| 4 | ViewSets + ViewSet integration tests | PR 4 | Depends on PR 3; largest slice (~450 lines) |
| 5 | Admin expansion + Tenant middleware wiring | PR 5 | Depends on PR 4; small cleanup slice (~56 lines) |

## Phase 1: Foundation — Models, Migration, Factories

- [x] 1.1 Add `django-fsm>=3.0` to `backend/pyproject.toml` dependencies. Run `pip install django-fsm`. (~2 lines)
- [x] 1.2 Create `InstitutionScopedModel` abstract mixin in `backend/apps/institutions/models.py` with `institution` FK, `code`, `name`, `description`, `status` (FSMField), `is_active`, `UniqueConstraint(institution, code)`. (~25 lines)
- [x] 1.3 Expand `Institution` model: add `description`, `address`, `contact_email`, `contact_phone`, `logo_url`, `status` (FSMField default="active"). Add FSM transitions: `activate`, `deactivate`, `archive`. (~30 lines modified)
- [x] 1.4 Expand `ResearchCenter` model: add `description`, `contact_email`, `contact_phone`, `status` (FSMField), `sede` FK (nullable), `facultad` FK (nullable). Replace name-unique constraint with `(institution, code)`. Add FSM transitions. (~35 lines modified)
- [x] 1.5 Create `Sede` model (inherits InstitutionScopedMeta pattern). FK to `Institution`. Fields: `code`, `name`, `description`, `status`, `is_active`. FSM transitions. (~30 lines)
- [x] 1.6 Create `Facultad` model. FKs: `institution` (required), `sede` (nullable). Same field pattern + FSM. `clean()` validates sede belongs to same institution. (~35 lines)
- [x] 1.7 Create `ResearchGroup` model. FKs: `institution`, `center` (required). Same field pattern + FSM. (~25 lines)
- [x] 1.8 Create `ResearchLine` model. FKs: `institution`, `group` (required). Same field pattern + FSM. (~25 lines)
- [x] 1.9 Generate migration `0002_expand_hierarchy.py`: AddField on Institution + ResearchCenter, CreateModel for Sede/Facultad/ResearchGroup/ResearchLine, AddIndex `(institution_id, status)` on each sub-entity. (~100 lines, auto-generated)
- [x] 1.10 Create `backend/apps/institutions/tests/conftest.py` with factory-boy factories for all 6 entities. (~80 lines)
- [x] 1.11 Write `backend/apps/institutions/tests/test_models.py`: test `clean()` parent-chain validation, FSM transitions (valid/invalid), `UniqueConstraint` enforcement, `__str__` methods. (~120 lines)

## Phase 2: Service Layer + RLS Policies

- [x] 2.1 Create `backend/apps/institutions/services.py` with `InstitutionLifecycleService`: `activate()`, `deactivate()` (guard: no active children), `archive()` (guard: no active children, terminal). Include `_has_active_children()` resolver using the child resolution map from design. (~80 lines)
- [x] 2.2 Write `backend/apps/institutions/tests/test_services.py`: test each transition (activate/deactivate/archive), guard rejection with active children (409), reactivation from deactivated, archive terminality. (~100 lines)
- [x] 2.3 Create migration `backend/apps/institutions/migrations/0003_rls_policies.py`: RLS for `institutions_sede`, `institutions_facultad`, `institutions_researchgroup`, `institutions_researchline` + update existing `institutions_researchcenter` RLS. Follow `accounts/0004` pattern (RunPython, PostgreSQL-only guard). (~90 lines)
- [x] 2.4 Write `backend/apps/institutions/tests/test_rls.py`: test migration structure (exists, has RunPython, depends on 0002), SQL contains expected tables, tenant_isolation + superadmin_bypass policies present. Mark PostgreSQL-only enforcement tests with `@pytest.mark.skip`. (~60 lines)

## Phase 3: DRF API — Serializers, Permissions, URLs

- [x] 3.1 Create `backend/apps/institutions/permissions.py`: `IsSuperadmin` (Institution CRUD), `IsInstitutionAdmin` (Sede/Facultad/Center CRUD), `IsCenterDirector` (Group/Line CRUD), `IsSameInstitution` (read access). (~50 lines)
- [x] 3.2 Create `backend/apps/institutions/serializers.py`: `ModelSerializer` for each of the 6 entities. Nested read serializers for parent display (e.g., Sede shows institution name). Validate `(institution, code)` uniqueness. Validate parent-chain institution consistency. (~120 lines)
- [x] 3.3 Write `backend/apps/institutions/tests/test_serializers.py`: test code uniqueness validation, parent mismatch rejection, nested read output, status field read-only. (~80 lines)
- [x] 3.4 Create `backend/apps/institutions/urls.py`: DRF `SimpleRouter` for Institution, nested paths for Sede/Facultad/Center under `/institutions/{id}/`, nested paths for Group under `/centers/{id}/`, nested paths for Line under `/groups/{id}/`, lifecycle `@action` routes. (~60 lines)

## Phase 4: DRF API — ViewSets + Integration Tests

- [x] 4.1 Create `backend/apps/institutions/views.py`: 6 `ModelViewSet` classes. Each scopes `get_queryset()` by `institution_id`. Institution viewset: superadmin-only. Sede/Facultad/Center: institution-admin. Group/Line: center-director. Add `@action` for activate/deactivate/archive calling `InstitutionLifecycleService`. (~200 lines)
- [x] 4.2 Wire institutions URLs into `backend/config/urls.py`: `path("api/", include("apps.institutions.urls"))`. (~3 lines)
- [x] 4.3 Update `backend/config/middleware/tenant.py`: add `/api/institutions/` to `TENANT_REQUIRED_PREFIXES`. (~1 line)
- [x] 4.4 Write `backend/apps/institutions/tests/test_views.py`: CRUD integration tests for all 6 entities (list, create, retrieve, update, delete), lifecycle endpoint tests (activate/deactivate/archive + error cases), permission tests (cross-institution access denied, role-based rejection), nested route tests. (~250 lines)

## Phase 5: Admin + Cleanup

- [x] 5.1 Expand `backend/apps/institutions/admin.py`: register Sede, Facultad, ResearchGroup, ResearchLine with `list_display`, `search_fields`, `list_filter`, `raw_id_fields`. Update Institution/ResearchCenter admin to show new fields (`status`, `description`). (~50 lines)
- [x] 5.2 Run full test suite, verify ≥80% coverage, run `ruff check` + `mypy` on all new files. Fix any linting/type issues.
