# Tasks: SIGPI Advances/Progress Module (§6.5)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~4,200 (source ~1,500 + tests ~2,700) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-always |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No (delivery resolved — feature-branch-chain, PR 1 of 4)
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models, migrations, project delta, config wiring, model tests | PR 1 | Base = feature/advances; ~1,200 lines |
| 2 | Service layer, permissions, service + permission tests | PR 2 | Base = PR 1 branch; ~1,100 lines |
| 3 | Serializers, filters, views, URLs, serializer + view tests | PR 3 | Base = PR 2 branch; ~1,500 lines |
| 4 | Admin registration, admin tests | PR 4 | Base = PR 3 branch; ~200 lines |

## Phase 1: Foundation — Models, Migrations, Config

- [x] 1.1 Create `backend/apps/progress/__init__.py` and `apps.py` with `ProgressConfig`
- [x] 1.2 Add `"apps.progress"` to `LOCAL_APPS` in `backend/config/settings/base.py`
- [x] 1.3 Add `PROGRESS_STATE_CHANGE` to `AuditEventType` in `backend/apps/accounts/audit.py`
- [x] 1.4 Create `backend/apps/progress/models.py`: `ProgressStatus`, `ProgressDocumentType`, `ProgressReviewType` enums; `ProgressReport` model with 9 `@transition` FSM methods, `clean()` (RN-P01, RN-P02), indexes
- [x] 1.5 Add `ProgressReview`, `ProgressDocument`, `ProgressStateLog` models to `models.py` (append-only, FK CASCADE)
- [x] 1.6 Add `cumulative_progress` DecimalField(5,2) to `Project` in `backend/apps/projects/models.py`
- [x] 1.7 Create `progress/migrations/0001_initial.py` — 4 tables, CHECK constraints, indexes
- [x] 1.8 Create `progress/migrations/0002_rls_policies.py` — RLS for parent + 3 child tables
- [x] 1.9 Create `projects/migrations/0003_add_cumulative_progress.py`
- [x] 1.10 Add `path("api/", include("apps.progress.urls"))` to `backend/config/urls.py`
- [x] 1.11 Create `tests/conftest.py` — `ProgressReportFactory`, `ProgressReviewFactory`, `ProgressDocumentFactory`, `ProgressStateLogFactory` + 6 state-scoped fixtures
- [x] 1.12 **TDD RED**: Write `tests/test_models.py` — model validation (RN-P01, RN-P02), DB CHECK constraints, all 9 valid FSM transitions, invalid transition rejection, `aprobado` terminal guard
- [x] 1.13 **TDD GREEN**: Verify all model tests pass; fix any model issues

## Phase 2: Service Layer + Permissions

- [ ] 2.1 Create `backend/apps/progress/permissions.py` — `IsProgressCreatorOrProjectMember`; import `IsCenterDirectorForProject` from projects
- [ ] 2.2 **TDD RED**: Write `tests/test_permissions.py` — full role × action matrix (6 roles × 10 actions = 60 cells)
- [ ] 2.3 **TDD GREEN**: Implement permission classes; verify all permission tests pass
- [ ] 2.4 Create `backend/apps/progress/services.py` — `ProgressService.create()`, `update()`, `delete()` with borrador guard and project-not-terminal guard (RN-P09)
- [ ] 2.5 Add 9 FSM orchestration methods to `ProgressService`: `submit`, `accept_review`, `approve`, `observe`, `reject`, `return_to_draft`, `resubmit` + `_log_transition` (StateLog + AuditEvent)
- [ ] 2.6 Implement `approve()` side effect: update `Project.cumulative_progress` from report's `cumulative_percentage` (RN-P08)
- [ ] 2.7 Implement `observe()`/`reject()` side effects: create `ProgressReview` with correct `review_type`
- [ ] 2.8 Create `ProgressDocumentService` — `add()`, `update()`, `remove()` with borrador-state guard
- [ ] 2.9 Add `ProjectService.has_pending_progress_reports(project)` to `backend/apps/projects/services.py`
- [ ] 2.10 **TDD RED**: Write `tests/test_services.py` — CRUD guards, all 9 FSM methods, `_log_transition` dual audit, `approve()` updates project progress, document borrador guard
- [ ] 2.11 **TDD GREEN**: Verify all service tests pass

## Phase 3: DRF API — Serializers, Views, URLs, Filters

- [ ] 3.1 Create `backend/apps/progress/serializers.py` — `ProgressReportListSerializer`, `ProgressReportSerializer`, `ProgressReportCreateSerializer`, `ProgressDocumentSerializer`, `ProgressReviewSerializer`, `ProgressStateLogSerializer`
- [ ] 3.2 Create `backend/apps/progress/filters.py` — `ProgressReportFilter` (status, project, period_start range)
- [ ] 3.3 **TDD RED**: Write `tests/test_serializers.py` — field validation, percentage boundary, list vs detail, read-only nested
- [ ] 3.4 **TDD GREEN**: Verify serializer tests pass
- [ ] 3.5 Create `backend/apps/progress/views.py` — `ProgressViewSet` (ModelViewSet, CRUD + 9 `@action` FSM endpoints, action-specific `get_permissions()` and `get_serializer_class()`)
- [ ] 3.6 Add `ProgressDocumentViewSet` (ModelViewSet, nested under progress), `ProgressReviewViewSet` (ReadOnly), `ProgressStateLogViewSet` (ReadOnly)
- [ ] 3.7 Create `backend/apps/progress/urls.py` — top-level router + nested document/review/state_history paths + `/projects/{id}/progress/` shortcut
- [ ] 3.8 **TDD RED**: Write `tests/test_views.py` — CRUD + 9 FSM actions + nested routes + error responses (400, 403, 405) per spec scenarios
- [ ] 3.9 **TDD GREEN**: Verify all view tests pass

## Phase 4: Admin + Integration

- [ ] 4.1 Create `backend/apps/progress/admin.py` — register all 4 models with `list_display`, `search_fields`, `list_filter`
- [ ] 4.2 **TDD RED**: Write `tests/test_admin.py` — model registration, list_display, search_fields verification
- [ ] 4.3 **TDD GREEN**: Verify admin tests pass
- [ ] 4.4 Run full test suite: `cd backend; python -m pytest apps/progress/ --cov=apps.progress --cov-report=term-missing` — verify ≥90% coverage
