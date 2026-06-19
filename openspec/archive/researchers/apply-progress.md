# Apply Progress: Researchers Module (SIGPI §6.3)

## Session Info

- **Date**: 2026-06-19
- **Phase**: 1 of 5 — Foundation: Models, Migration, Factories, Model Tests
- **Mode**: Strict TDD
- **Test runner**: pytest (SQLite in-memory, PYTEST_RUNNING=true)

## Status

**Phase 1 — COMPLETE** | 8/8 tasks done | 31 tests passing

## TDD Cycle Evidence

| Task | RED (test written first) | GREEN (implementation passes) | REFACTOR |
|------|--------------------------|-------------------------------|----------|
| 1.1 | N/A (scaffold — infra config) | App scaffold + INSTALLED_APPS | N/A |
| 1.2–1.5 | `test_models.py` + `conftest.py` → `ModuleNotFoundError: No module named 'apps.researchers.models'` | All 4 models implemented in `models.py` | `ForeignKey(unique=True)` → `OneToOneField` per Django warning |
| 1.6 | N/A (auto-generated) | `makemigrations researchers` generated `0001_initial.py` with 4 tables, indexes, UniqueConstraint | N/A |
| 1.7 | `conftest.py` → same ModuleNotFoundError (shared RED phase with 1.2) | Factories created with correct `SelfAttribute` for institution sharing | `ResearcherAffiliationFactory` fixed to share institution via `SelfAttribute` |
| 1.8 | All 31 tests written → RED (import fails) | All 31 tests GREEN after model implementation | N/A |

## Task Completion

- [x] **1.1** App scaffold: `__init__.py`, `apps.py` (ResearchersConfig), `apps.researchers` in INSTALLED_APPS
- [x] **1.2** Researcher model: UUID PK, user OneToOneField (nullable), institution FK, first_name, last_name, document_type (DocumentTypeChoices), document_number, primary_email, phone, bio, academic_formation, is_active, created_at, updated_at. UniqueConstraint(institution, document_number). __str__ → "first_name last_name"
- [x] **1.3** ResearcherAffiliation model: UUID PK, researcher FK, center/group/line FKs (nullable), is_primary, created_at. clean() validates: at least one FK, same institution, one primary. save() calls full_clean().
- [x] **1.4** ExternalProfile model: UUID PK, researcher FK, provider (ProviderChoices), url, created_at. __str__ → "provider_display — researcher_name"
- [x] **1.5** ResearcherAttachment model: UUID PK, researcher FK, name, type (AttachmentTypeChoices), external_url, created_at. __str__ → "name (type_display)"
- [x] **1.6** Migration 0001_initial.py: 4 CreateModel operations, AddIndex on (institution, is_active), AddConstraint unique_document_per_institution
- [x] **1.7** Factories in conftest.py: ResearcherFactory, ResearcherAffiliationFactory (with institution sharing via SelfAttribute), ExternalProfileFactory, ResearcherAttachmentFactory
- [x] **1.8** test_models.py: 31 tests covering unique constraint, clean() rejection (no FK, cross-institution, multiple primary), __str__, choice validation, factory behavior

## Test Results

```
apps/researchers/tests/test_models.py — 31 passed in 2.44s
```

| Test Class | Tests | Status |
|------------|-------|--------|
| TestResearcherFields | 8 | ✅ |
| TestResearcherFactory | 3 | ✅ |
| TestResearcherAffiliationFields | 9 | ✅ |
| TestResearcherAffiliationFactory | 2 | ✅ |
| TestExternalProfileFields | 4 | ✅ |
| TestResearcherAttachmentFields | 5 | ✅ |

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/apps/researchers/__init__.py` | Created | 4 |
| `backend/apps/researchers/apps.py` | Created | 9 |
| `backend/apps/researchers/models.py` | Created | 219 |
| `backend/apps/researchers/migrations/0001_initial.py` | Created (auto) | 103 |
| `backend/apps/researchers/tests/__init__.py` | Created | 0 |
| `backend/apps/researchers/tests/conftest.py` | Created | 72 |
| `backend/apps/researchers/tests/test_models.py` | Created | 419 |
| `backend/config/settings/base.py` | Modified (+1 line) | 1 |
| `openspec/changes/researchers/tasks.md` | Modified (checkboxes) | 8 |

**Total**: ~835 lines (migration auto-generated ~103, test code ~490, model code ~219, scaffold ~13)

## Deviations from Design

| Design Element | Deviation | Reason |
|---|---|---|
| `user FK (unique=True)` on Researcher | Changed to `OneToOneField` | Django issues `fields.W342` warning — `ForeignKey(unique=True)` is equivalent to `OneToOneField`; using `OneToOneField` is the canonical form |
| Migration: unique index on `user_id WHERE NOT NULL` | Not included in migration | SQLite in-memory test DB does not support partial indexes. PostgreSQL partial unique index will be added later via RLS migration when `is_postgresql()` guard is available. The `OneToOneField` already enforces uniqueness at the Python/Django level. |
| `Researcher` inherits from `InstitutionScopedModel` (spec) | Standalone model (design) | Per design decision table: `InstitutionScopedModel` carries `code`, `name`, `description`, `status` FSM — none apply to researcher profiles |

## Issues Found

- **Coverage DB lock**: Could not generate `--cov-report` due to locked `.coverage` SQLite database from parallel pytest run. All 31 tests pass individually. Coverage verification deferred to Phase 2 or standalone run.
- **Institutions migration 0004**: `makemigrations` auto-generated an unrelated institutions migration (`0004_alter_facultad_status_...`) due to django-fsm deprecation changes. This should be reviewed separately — not part of researchers scope.
- **UserFactory missing**: `apps.accounts.tests.conftest.UserFactory` does not exist yet. ResearcherFactory avoids depending on it; `test_factory_with_user` creates users directly via `User.objects.create_user()`.

## Next Phase

Phase 2: Service Layer + RLS Policies (tasks 2.1–2.5) — depends on Phase 1 complete.
