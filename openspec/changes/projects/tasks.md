# Tasks: Projects Module (SIGPI §6.4)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,000 (5 models, 3 enums, 2 migrations, 3 services, 7 serializers, 5 viewsets, 4 permissions, filters, URLs, admin, ~700 lines of tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 5 PRs (see work units below) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models + Migration 0001 + Factories + Model/FSM tests | PR 1 | Base branch; all downstream PRs depend on this |
| 2 | Services + Migration 0002 (RLS) + Service/RLS tests | PR 2 | Depends on PR 1; business logic + security |
| 3 | Serializers + Permissions + Filters + URLs + tests | PR 3 | Depends on PR 1+2; API contract without viewsets |
| 4 | ViewSets + Integration tests + URL wiring in config | PR 4 | Depends on PR 3; largest slice (~450 lines) |
| 5 | Admin + config cleanup + full suite verification | PR 5 | Depends on PR 4; small cleanup slice (~80 lines) |

## Phase 1: Foundation — Models, Migration, Factories

- [x] 1.1 Create `backend/apps/projects/__init__.py` (empty) and `backend/apps/projects/apps.py` with `ProjectsConfig(name="apps.projects")`. (~10 lines)
- [x] 1.2 Create `backend/apps/projects/models.py`: Define `ProjectStatus` (TextChoices, 12 states), `ProjectRole` (TextChoices, 4 roles), `ProjectDocumentType` (TextChoices, 5 types). (~30 lines)
- [x] 1.3 Add `Project` model to `models.py`: UUID PK, `institution` FK, `center` FK (RN-008), `group` FK (null), `line` FK (null), `principal_investigator` FK (RN-007), title, abstract, objectives, methodology, expected_results, keywords, start_date, estimated_end_date, actual_end_date (null), `status` FSMField(default='borrador', protected=False), is_active, timestamps. `clean()` validates RN-007, RN-008, RN-013, hierarchy integrity (group/line belong to same center chain). DB CHECK constraints via `Meta.constraints`. Indexes: `(institution, status)`, `(center, status)`, `(principal_investigator)`. (~100 lines)
- [x] 1.4 Add FSM `@transition` methods to `Project`: `submit()` (borrador→enviado), `accept_review()` (enviado→en_revision), `approve()` (en_revision→aprobado), `observe()` (en_revision→observado), `return_to_draft()` (en_revision/observado→borrador), `reject()` (en_revision→rechazado), `resubmit()` (observado→enviado), `start_execution()` (aprobado→en_ejecucion), `suspend()` (en_ejecucion→suspendido), `resume()` (suspendido→en_ejecucion), `finalize()` (en_ejecucion→finalizado), `initiate_closure()` (finalizado→en_cierre), `close()` (en_cierre→cerrado), `cancel()` (any non-terminal→cancelado). (~80 lines)
- [x] 1.5 Add `ProjectMember` model: UUID PK, `project` FK (CASCADE), `researcher` FK (non-null), `role` CharField(choices=ProjectRole), `joined_at`. `UniqueConstraint(project, researcher)`. (~20 lines)
- [x] 1.6 Add `ProjectDocument` model: UUID PK, `project` FK (CASCADE), `name`, `doc_type` CharField(choices=ProjectDocumentType), `external_url` URLField(500), `uploaded_at`. (~15 lines)
- [x] 1.7 Add `ProjectObservation` model: UUID PK, `project` FK (CASCADE), `observed_by` FK(User, SET_NULL), `observation_text`, `created_at`. Append-only (RN-014). (~15 lines)
- [x] 1.8 Add `ProjectStateLog` model: UUID PK, `project` FK (CASCADE), `from_state`, `to_state`, `triggered_by` FK(User, SET_NULL), `reason` (blank), `created_at`. Indexes: `(project, -created_at)`, `(from_state, to_state)`. (~20 lines)
- [x] 1.9 Generate migration `backend/apps/projects/migrations/0001_initial.py`: CreateModel for 5 tables, DB CHECK constraints (`estimated_end_date >= start_date`, `actual_end_date IS NULL OR actual_end_date >= start_date`), indexes. Depends on `accounts.0003`, `institutions.0002`, `researchers.0001`. (~120 lines, auto-generated)
- [x] 1.10 Create `backend/apps/projects/tests/__init__.py` and `backend/apps/projects/tests/conftest.py` with factory-boy factories: `ProjectFactory`, `ProjectMemberFactory`, `ProjectDocumentFactory`, `ProjectObservationFactory`, `ProjectStateLogFactory`. Include state fixtures: `project_in_each_state` (12 fixtures using `factory.PostGeneration` or direct status override). (~100 lines)
- [x] 1.11 Write `backend/apps/projects/tests/test_models.py`: `clean()` validation tests (missing PI → ValidationError, missing center → ValidationError, end_date < start_date → ValidationError, group not in center chain → ValidationError), UniqueConstraint on `(project, researcher)`, DB CHECK constraint enforcement, `__str__` methods, enum choice validation. (~120 lines)
- [x] 1.12 Write FSM transition tests in `test_models.py`: every valid transition succeeds (15 transitions); invalid transitions raise `TransitionNotAllowed` (e.g., submit from `cerrado`); terminal states (`cerrado`, `rechazado`, `cancelado`) block all outbound transitions. (~80 lines)

### TDD Evidence: Phase 1

- RED: Tests for `clean()` validations, unique constraints, DB CHECK constraints, and all 15 FSM transitions written BEFORE model implementation.
- GREEN: Models + migration pass all tests.
- Refactor: Review model code for DRY, clean `Meta` classes, consistent `related_name` patterns.

## Phase 2: Service Layer + RLS Policies

- [x] 2.1 Create `backend/apps/projects/services.py` with `ProjectService.create()`: validate RN-007 (PI non-null), RN-008 (center non-null), RN-009 (PI affiliated with center via `ResearcherAffiliation`), RN-013 (dates). Set `status='borrador'`, inject `institution` from `center.institution`. (~40 lines)
- [x] 2.2 Add `ProjectService.update()`: reject if terminal (RN-011), delegate to `project.full_clean()` + `project.save()`. (~15 lines)
- [x] 2.3 Add 15 FSM orchestration methods to `ProjectService`: `submit()`, `accept_review()`, `approve()`, `observe()` (creates `ProjectObservation`), `return_to_draft()` (NO observation), `reject()`, `resubmit()`, `start_execution()`, `suspend(reason)`, `resume()`, `finalize(actual_end_date)`, `initiate_closure()`, `close()`, `cancel(reason)`. Each: call model transition → save → `_log_transition()`. (~120 lines)
- [x] 2.4 Add `ProjectService._log_transition()`: create `ProjectStateLog` row + emit `AuditEvent` via `AuditEventEmitter(event_type="PROJECT_STATE_CHANGE", ...)`. (~20 lines)
- [x] 2.5 Add `ProjectMemberService`: `add()` (validate project not terminal, enforce unique constraint), `update()` (validate parent not terminal), `remove()` (validate parent not terminal). (~30 lines)
- [x] 2.6 Add `ProjectDocumentService`: `add()`, `update()`, `remove()` — same terminal-state guard pattern as members. (~25 lines)
- [x] 2.7 Write `backend/apps/projects/tests/test_services.py`: `ProjectService.create()` with valid data, missing PI, missing center, PI not affiliated (RN-009), invalid dates (RN-013). `update()` on terminal project raises. All 15 FSM methods: valid transition succeeds + creates `ProjectStateLog` + emits `AuditEvent`; invalid transition raises. `observe()` creates `ProjectObservation`; `return_to_draft()` does NOT. `cancel()` from terminal raises. Member/Document service CRUD + terminal guard. Mock `AuditEventEmitter` for isolation. (~200 lines)
- [x] 2.8 Create migration `backend/apps/projects/migrations/0002_rls_policies.py`: Enable RLS + `tenant_isolation` + `superadmin_bypass` on 5 tables. Parent (`projects_project`): direct `institution_id`. Children (member, document, observation, state_log): subquery via `project_id`. Follow `researchers/0002` pattern (RunPython, PostgreSQL-only guard). (~90 lines)
- [x] 2.9 Write `backend/apps/projects/tests/test_rls.py`: migration structure tests (exists, has RunPython, depends on 0001), SQL contains expected 5 tables and policies. Mark PostgreSQL-only enforcement tests with `@pytest.mark.skip`. (~50 lines)

### TDD Evidence: Phase 2

- RED: Service tests written BEFORE `services.py` implementation. RLS migration tests written BEFORE migration.
- GREEN: All service methods pass; RLS migration structure validated.
- Refactor: Extract common terminal-state guard into helper if duplicated.

## Phase 3: DRF API — Serializers, Permissions, URLs, Filters

- [ ] 3.1 Create `backend/apps/projects/permissions.py`: `IsProjectOwnerOrCoInvestigator` (PI or co_investigator member; Admin+ bypasses), `IsCenterDirectorForProject` (user's membership includes project's center with Director role), `CanCreateProjectInCenter` (Researcher level ≤ 4 AND `ResearcherAffiliation` with target center), `IsProjectEditable` (object-level: False if terminal AND user not Admin+). (~80 lines)
- [ ] 3.2 Create `backend/apps/projects/serializers.py`: `ProjectListSerializer` (id, title, status, center, principal_investigator, start_date, created_at), `ProjectSerializer` (all fields + nested members/documents read-only), `ProjectCreateSerializer` (writable fields; institution injected by view), `ProjectMemberSerializer`, `ProjectDocumentSerializer`, `ProjectObservationSerializer` (read-only), `ProjectStateLogSerializer` (read-only). (~150 lines)
- [ ] 3.3 Create `backend/apps/projects/filters.py`: `ProjectFilter` (django-filter FilterSet) with `status` (ChoiceFilter), `center` (UUIDFilter), `start_date_after` (DateFilter gte), `start_date_before` (DateFilter lte), `keywords` (CharFilter icontains). (~25 lines)
- [ ] 3.4 Create `backend/apps/projects/urls.py`: manual nested paths — 22 URL patterns: `/projects/` (list/create), `/projects/{id}/` (retrieve/update/destroy), 16 FSM action POST endpoints, `/projects/{id}/members/` + detail, `/projects/{id}/documents/` + detail, `/projects/{id}/observations/`, `/projects/{id}/state_history/`. (~60 lines)
- [ ] 3.5 Write `backend/apps/projects/tests/test_serializers.py`: field validation (required fields, choice validation), nested member/document serialization in `ProjectSerializer`, `ProjectCreateSerializer` institution injection, read-only fields in observation/state_log serializers. (~80 lines)
- [ ] 3.6 Write `backend/apps/projects/tests/test_permissions.py`: full role × action matrix (6 roles × 15 actions = 90 cells). Test `IsProjectOwnerOrCoInvestigator` (PI allowed, CI allowed, other denied, admin bypass), `IsCenterDirectorForProject` (director of project's center allowed, other center denied), `CanCreateProjectInCenter` (affiliated researcher allowed, non-affiliated denied), `IsProjectEditable` (non-terminal allowed, terminal denied for non-admin). (~120 lines)
- [ ] 3.7 Write `backend/apps/projects/tests/test_urls.py`: route resolution for all 22 URL patterns using `reverse()`. Verify nested paths, FSM action paths, detail routes. (~40 lines)

### TDD Evidence: Phase 3

- RED: Serializer, permission, and URL tests written BEFORE implementation files.
- GREEN: All serializer validations pass; full permission matrix (90 cells) green; all 22 URLs resolve.
- Refactor: Extract shared permission patterns if duplicated.

## Phase 4: ViewSets + Integration Tests

- [ ] 4.1 Create `backend/apps/projects/views.py`: `ProjectViewSet` with `get_serializer_class()` (list→List, retrieve→Detail, create/update→Create), `get_permissions()` per action, queryset scoped by `request.active_membership.institution`, `filter_backends` = [DjangoFilterBackend, SearchFilter, OrderingFilter], `filterset_class=ProjectFilter`, `search_fields=['title', 'abstract', 'keywords']`, `ordering_fields=['title', 'start_date', 'created_at', 'status']`. (~60 lines)
- [ ] 4.2 Add 16 FSM `@action(detail=True, methods=['post'])` to `ProjectViewSet`: `submit`, `accept_review`, `approve`, `observe` (reads `observation_text`), `return_to_draft`, `reject`, `resubmit`, `start_execution`, `suspend` (reads `reason`), `resume`, `finalize` (reads `actual_end_date`), `initiate_closure`, `close`, `cancel` (reads `reason`). Each calls corresponding `ProjectService` method. (~100 lines)
- [ ] 4.3 Add nested ViewSets to `views.py`: `ProjectMemberViewSet` (list/create/update/destroy, scoped to parent project, enforces `IsProjectEditable` on parent), `ProjectDocumentViewSet` (same pattern), `ProjectObservationViewSet` (read-only list), `ProjectStateLogViewSet` (read-only list). Each extracts `project_id` from URL kwargs. (~100 lines)
- [ ] 4.4 Wire projects URLs into `backend/config/urls.py`: `path("api/", include("apps.projects.urls"))`. Add `apps.projects` to `LOCAL_APPS` in `backend/config/settings/base.py`. Add `django_filters` to `INSTALLED_APPS` if missing. (~5 lines)
- [ ] 4.5 Write `backend/apps/projects/tests/test_views.py`: CRUD integration tests (list, create with RN-009 validation, retrieve, update, delete if borrador), 16 FSM action endpoint tests (valid transitions succeed, invalid return 400, wrong role returns 403), nested member/document CRUD (add, update role, remove; add doc, update, remove), observation list (read-only, no POST/PUT/DELETE), state_history list (read-only), error responses (400 missing PI, 400 PI not affiliated, 403 terminal mutation, 409 duplicate member). (~250 lines)

### TDD Evidence: Phase 4

- RED: View tests written BEFORE viewset implementation.
- GREEN: All CRUD, FSM action, nested route, and error response tests pass.
- Refactor: Extract common viewset patterns (parent project lookup, terminal guard) into mixins if duplicated.

## Phase 5: Admin + Cleanup

- [ ] 5.1 Create `backend/apps/projects/admin.py`: register all 5 models with `list_display`, `search_fields`, `list_filter`, `raw_id_fields`. `ProjectAdmin` includes `list_filter=['status', 'center', 'institution']`, `search_fields=['title', 'keywords']`. (~50 lines)
- [ ] 5.2 Write `backend/apps/projects/tests/test_admin.py`: verify all 5 models registered, admin classes have expected `list_display` and `list_filter` attributes. (~25 lines)
- [ ] 5.3 Modify `backend/apps/accounts/permissions.py`: remove `IsProjectOwnerOrCoInvestigator` (moved to `projects/permissions.py`). Verify no other module imports it from accounts. (~5 lines)
- [ ] 5.4 Add `django-filter` to `backend/pyproject.toml` dependencies if not present. (~1 line)
- [ ] 5.5 Run full test suite: `pytest --cov=apps.projects` (verify ≥80% coverage), `ruff check backend/apps/projects/`, `ruff format --check backend/apps/projects/`. Fix any linting issues. Verify no regressions in accounts, institutions, researchers test suites.

### TDD Evidence: Phase 5

- RED: Admin registration tests written BEFORE `admin.py`.
- GREEN: All admin tests pass; full suite green; coverage ≥80%.
- Refactor: Final pass on code quality, docstrings, import ordering.

## Verification Checklist

- [ ] All tests passing: `pytest` exits 0 across full suite (accounts + institutions + researchers + projects)
- [ ] Coverage ≥80%: `pytest --cov=apps.projects --cov-report=term-missing` shows ≥80% for `apps.projects`
- [ ] Ruff clean: `ruff check backend/apps/projects/` and `ruff format --check backend/apps/projects/` exit 0
- [ ] No regressions: accounts, institutions, researchers test suites unchanged and passing
- [ ] All spec requirements have tests:
  - [ ] RF-027 (Create project) → test_views.py, test_services.py
  - [ ] RF-028 (Update project) → test_views.py, test_permissions.py
  - [ ] RF-029 (Project metadata) → test_serializers.py, test_views.py
  - [ ] RF-030 (Hierarchy association) → test_models.py, test_services.py
  - [ ] RF-031 (Assign PI) → test_models.py (RN-007), test_services.py (RN-009)
  - [ ] RF-032 (Co-investigators) → test_views.py, test_services.py
  - [ ] RF-033 (Students/seedbeds/collaborators) → test_views.py, test_models.py
  - [ ] RF-034 (Manage dates) → test_models.py (RN-013), test_services.py
  - [ ] RF-035 (FSM lifecycle) → test_models.py (15 transitions), test_services.py
  - [ ] RF-036 (Document metadata) → test_views.py, test_services.py
  - [ ] RF-037 (Submit for review) → test_views.py, test_services.py
  - [ ] RF-038 (Director review actions) → test_views.py, test_services.py, test_permissions.py
  - [ ] RF-039 (Advanced filtering) → test_views.py (filter params)
  - [ ] RN-011 (Terminal immutability) → test_permissions.py, test_services.py, test_views.py
  - [ ] RN-012 (State audit log) → test_services.py (ProjectStateLog + AuditEvent)
  - [ ] RN-014 (Observations append-only) → test_views.py (no update/delete endpoints)
  - [ ] RLS policies → test_rls.py
