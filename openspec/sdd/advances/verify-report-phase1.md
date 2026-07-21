# Verification Report: SIGPI Advances/Progress Module — Phase 1

| Field | Value |
|-------|-------|
| Change | `advances` (SIGPI §6.5) |
| Phase | 1 — Foundation (Models + Migrations + Config + Model Tests) |
| Mode | openspec (file-based) |
| Strict TDD | Active (`cd backend; python -m pytest`) |
| Verifier | sdd-verify sub-agent |
| Date | 2026-07-20 |

## 1. Completeness Table

| Dimension | Status | Notes |
|-----------|--------|-------|
| Task completion | **PASS** | 13/13 tasks checked (100%) |
| Spec correctness | **PASS** | All 4 models match spec §Data Model; 6 FSM states; 9 transitions |
| Design coherence | **PASS** | Implementation matches design.md; minor naming cosmetic difference only |
| Runtime evidence | **PASS** | 57/57 progress tests pass; 977/977 existing tests pass (0 regressions) |
| Lint | **PASS** | Ruff clean — all checks passed |
| Coverage | **PASS** | 98% total; models.py at 100% |

## 2. Build / Tests / Coverage Evidence

### Test Execution

| Command | Result | Duration |
|---------|--------|----------|
| `python -m pytest apps/progress/ -v --tb=short` | **57 passed**, 0 failed | 4.66s |
| `python -m pytest apps/accounts/ apps/institutions/ apps/researchers/ apps/projects/ -q --tb=line` | **977 passed**, 9 skipped, 0 failed | 460.43s |
| `python -m ruff check apps/progress/` | **All checks passed** | <1s |

### Coverage Report (`--cov=apps.progress --cov-report=term-missing`)

| File | Stmts | Miss | Cover | Missing |
|------|-------|------|-------|---------|
| `apps/progress/__init__.py` | 0 | 0 | 100% | — |
| `apps/progress/apps.py` | 5 | 0 | 100% | — |
| `apps/progress/migrations/0001_initial.py` | 9 | 0 | 100% | — |
| `apps/progress/migrations/0002_rls_policies.py` | 22 | 3 | 86% | 94, 99-100 (PostgreSQL-only branches) |
| `apps/progress/models.py` | 119 | 0 | **100%** | — |
| `apps/progress/tests/conftest.py` | 69 | 6 | 91% | 127, 133, 139, 145, 151, 157 (state fixtures for Phase 2+) |
| `apps/progress/tests/test_models.py` | 480 | 0 | 100% | — |
| `apps/progress/urls.py` | 2 | 2 | 0% | 10-12 (stub — Phase 3) |
| **TOTAL** | **706** | **11** | **98%** | — |

**Coverage note**: RLS migration misses are PostgreSQL-only code paths (no-op on SQLite test DB). URL stub is intentionally empty for Phase 1. State-scoped fixtures are prepared for Phase 2+ service/view tests.

## 3. Spec Compliance Matrix

### Data Model (spec §Data Model)

| Entity | Field | Spec | Implementation | Status |
|--------|-------|------|----------------|--------|
| **ProgressReport** | `id` | UUID PK | `UUIDField(default=uuid4, PK)` | **COMPLIANT** |
| | `institution` | FK→Institution | `FK(Institution, CASCADE, related_name='progress_reports')` | **COMPLIANT** |
| | `project` | FK→Project | `FK(Project, CASCADE, related_name='progress_reports')` | **COMPLIANT** |
| | `created_by` | FK→User | `FK(User, CASCADE, related_name='created_progress_reports')` | **COMPLIANT** |
| | `period_start` | DateField | `DateField()` | **COMPLIANT** |
| | `period_end` | DateField | `DateField()` | **COMPLIANT** |
| | `description` | TextField | `TextField()` | **COMPLIANT** |
| | `cumulative_percentage` | Decimal(5,2) | `DecimalField(max_digits=5, decimal_places=2)` | **COMPLIANT** |
| | `activities` | TextField | `TextField()` | **COMPLIANT** |
| | `difficulties` | TextField, blank | `TextField(blank=True)` | **COMPLIANT** |
| | `next_steps` | TextField, blank | `TextField(blank=True)` | **COMPLIANT** |
| | `status` | FSMField | `FSMField(default=BORRADOR, protected=False)` | **COMPLIANT** |
| | `created_at` | auto | `DateTimeField(auto_now_add=True)` | **COMPLIANT** |
| | `updated_at` | auto | `DateTimeField(auto_now=True)` | **COMPLIANT** |
| | DB table | `progress_progressreport` | `db_table = "progress_progressreport"` | **COMPLIANT** |
| | CHECK: percentage | `0 <= cumulative_percentage <= 100` | `CheckConstraint(name='check_progress_percentage_range')` | **COMPLIANT** |
| | CHECK: dates | `period_end >= period_start` | `CheckConstraint(name='check_progress_period_dates')` | **COMPLIANT** |
| | Indexes | (inst,status), (project,status), (created_by) | 3 indexes registered | **COMPLIANT** |
| **ProgressReview** | `id` | UUID PK | `UUIDField(default=uuid4, PK)` | **COMPLIANT** |
| | `progress_report` | FK→ProgressReport | `FK(ProgressReport, CASCADE, related_name='reviews')` | **COMPLIANT** |
| | `reviewed_by` | FK→User, SET_NULL | `FK(User, SET_NULL, null=True, blank=True)` | **COMPLIANT** |
| | `review_text` | TextField | `TextField()` | **COMPLIANT** |
| | `review_type` | CharField choices | `CharField(20, choices=ProgressReviewType)` | **COMPLIANT** |
| | `created_at` | auto | `DateTimeField(auto_now_add=True)` | **COMPLIANT** |
| | DB table | `progress_progressreview` | `db_table = "progress_progressreview"` | **COMPLIANT** |
| **ProgressDocument** | `id` | UUID PK | `UUIDField(default=uuid4, PK)` | **COMPLIANT** |
| | `progress_report` | FK→ProgressReport | `FK(ProgressReport, CASCADE, related_name='documents')` | **COMPLIANT** |
| | `name` | CharField(255) | `CharField(max_length=255)` | **COMPLIANT** |
| | `doc_type` | CharField choices | `CharField(20, choices=ProgressDocumentType)` | **COMPLIANT** |
| | `external_url` | URLField(500), blank | `URLField(max_length=500, blank=True)` | **COMPLIANT** |
| | `uploaded_at` | auto | `DateTimeField(auto_now_add=True)` | **COMPLIANT** |
| | DB table | `progress_progressdocument` | `db_table = "progress_progressdocument"` | **COMPLIANT** |
| **ProgressStateLog** | `id` | UUID PK | `UUIDField(default=uuid4, PK)` | **COMPLIANT** |
| | `progress_report` | FK→ProgressReport | `FK(ProgressReport, CASCADE, related_name='state_logs')` | **COMPLIANT** |
| | `from_state` | CharField(30) | `CharField(max_length=30)` | **COMPLIANT** |
| | `to_state` | CharField(30) | `CharField(max_length=30)` | **COMPLIANT** |
| | `triggered_by` | FK→User, SET_NULL | `FK(User, SET_NULL, null=True, blank=True)` | **COMPLIANT** |
| | `reason` | TextField, blank | `TextField(blank=True)` | **COMPLIANT** |
| | `created_at` | auto | `DateTimeField(auto_now_add=True)` | **COMPLIANT** |
| | DB table | `progress_progressstatelog` | `db_table = "progress_progressstatelog"` | **COMPLIANT** |
| | Indexes | (report,-created_at), (from,to) | 2 indexes registered | **COMPLIANT** |
| **Project** (delta) | `cumulative_progress` | DecimalField(5,2), default=0.00 | `DecimalField(max_digits=5, decimal_places=2, default=0.00)` | **COMPLIANT** |

### Enumerations (spec §Enumerations)

| Enum | Spec Values | Implementation | Status |
|------|-------------|----------------|--------|
| `ProgressStatus` | borrador, enviado, en_revision, observado, aprobado, rechazado | 6 values match exactly | **COMPLIANT** |
| `ProgressDocumentType` | evidence, annex, report, other | 4 values match exactly | **COMPLIANT** |
| `ProgressReviewType` | observation, rejection | 2 values match exactly | **COMPLIANT** |

### FSM Specification (spec §FSM — 6 states, 9 transitions)

| # | Source | Target | Trigger | Test | Status |
|---|--------|--------|---------|------|--------|
| 1 | `borrador` | `enviado` | `submit()` | `test_submit_borrador_to_enviado` | **COMPLIANT** |
| 2 | `enviado` | `en_revision` | `accept_review()` | `test_accept_review_enviado_to_en_revision` | **COMPLIANT** |
| 3 | `en_revision` | `aprobado` | `approve()` | `test_approve_en_revision_to_aprobado` | **COMPLIANT** |
| 4 | `en_revision` | `observado` | `observe()` | `test_observe_en_revision_to_observado` | **COMPLIANT** |
| 5 | `en_revision` | `rechazado` | `reject()` | `test_reject_en_revision_to_rechazado` | **COMPLIANT** |
| 6 | `en_revision` | `borrador` | `return_to_draft()` | `test_return_to_draft_from_en_revision` | **COMPLIANT** |
| 7 | `observado` | `enviado` | `resubmit()` | `test_resubmit_observado_to_enviado` | **COMPLIANT** |
| 8 | `observado` | `borrador` | `return_to_draft()` | `test_return_to_draft_from_observado` | **COMPLIANT** |
| 9 | `rechazado` | `borrador` | `return_to_draft()` | `test_return_to_draft_from_rechazado` | **COMPLIANT** |

**Terminal state**: `aprobado` blocks all 7 outbound transitions — verified by `test_aprobado_blocks_all_transitions`.

**Invalid transitions**: 6 invalid transition tests confirm `TransitionNotAllowed` is raised.

### Business Rules Coverage (Phase 1 scope)

| Rule | Description | Test Coverage | Status |
|------|-------------|---------------|--------|
| RN-P01 | `cumulative_percentage` 0–100 | 4 tests (negative, >100, zero, 100) + CHECK constraint test | **COVERED** |
| RN-P02 | `period_end >= period_start` | 3 tests (reversed, equal, valid) + CHECK constraint test | **COVERED** |
| RN-P04 | FSM transitions logged in StateLog | Deferred to Phase 2 (service layer) | **DEFERRED** |
| RN-P05 | ProgressReview/StateLog append-only | Model structure verified; no update/delete endpoints (Phase 3) | **STRUCTURAL** |
| RN-P06 | `rechazado` reversible to `borrador` | `test_return_to_draft_from_rechazado` | **COVERED** |
| RN-P07 | `aprobado` is terminal | `test_aprobado_blocks_all_transitions` (7 transitions blocked) | **COVERED** |

## 4. Design Coherence Table

| Design Decision | Implementation | Status |
|----------------|----------------|--------|
| Standalone `apps.progress` | `apps/progress/` with own models, migrations, tests | **COHERENT** |
| 6-state FSM with explicit `en_revision` | 6 states in `ProgressStatus`; `accept_review()` transition exists | **COHERENT** |
| Cumulative percentage semantics | `cumulative_percentage` field on ProgressReport; `Project.cumulative_progress` delta field | **COHERENT** |
| `rechazado` reversible | `return_to_draft()` accepts `rechazado` as source | **COHERENT** |
| `protected=False` on FSMField | `FSMField(default=BORRADOR, protected=False)` | **COHERENT** |
| Metadata-only documents | `ProgressDocument` has `external_url` (URLField), no file field | **COHERENT** |
| RLS: parent + 3 child tables | `0002_rls_policies.py` covers all 4 tables | **COHERENT** |
| `return_to_draft()` single method for 3 sources | `source=[EN_REVISION, OBSERVADO, RECHAZADO]` — idiomatic django-fsm | **COHERENT** |

## 5. Correctness Table

| Check | Evidence | Status |
|-------|----------|--------|
| All 57 model tests pass | pytest output: `57 passed` | **PASS** |
| No regressions (977 existing tests) | pytest output: `977 passed, 9 skipped` | **PASS** |
| Ruff lint clean | `All checks passed!` | **PASS** |
| Migrations consistent | `0001_initial.py` creates 4 tables; `0002_rls_policies.py` adds RLS; `projects/0003` adds delta field | **PASS** |
| Settings wired | `apps.progress` in `LOCAL_APPS` at position 5 | **PASS** |
| URLs wired | `path("api/", include("apps.progress.urls"))` in root urls.py | **PASS** |
| AuditEventType extended | `PROGRESS_STATE_CHANGE` added to enum | **PASS** |
| TDD discipline followed | Tests written before/during implementation; 57 tests cover all model behavior | **PASS** |

## 6. Issues

### CRITICAL

None.

### WARNING

None.

### SUGGESTION

| # | Issue | Detail |
|---|-------|--------|
| S-1 | Migration filename cosmetic | Design says `0003_add_cumulative_progress.py`, actual is `0003_project_cumulative_progress.py`. Django auto-generated name. No functional impact. |
| S-2 | `blank=True` on nullable FK fields | `reviewed_by` and `triggered_by` have `blank=True` in addition to `null=True`. This is correct Django practice for admin/form compatibility. Design only specified `SET_NULL, null=True`. |
| S-3 | State-scoped fixtures unused | 6 fixtures in conftest.py (lines 124-157) show 91% coverage — they're intentionally prepared for Phase 2+ service/view tests. |

## 7. Regressions

| Module | Before Phase 1 | After Phase 1 | Delta |
|--------|----------------|---------------|-------|
| accounts | All pass | All pass | None |
| institutions | All pass | All pass | None |
| researchers | All pass | All pass | None |
| projects | All pass (66 tests) | All pass (66 tests) | None |
| **progress** | N/A (new) | **57 pass** | +57 new tests |
| **Total** | 977 passed, 9 skipped | **1034 passed, 9 skipped** | +57 |

## 8. Final Verdict

### **PASS**

Phase 1 of the SIGPI Advances/Progress module is fully compliant with spec and design. All 13 tasks are complete, all 57 model tests pass, no regressions detected, ruff is clean, and coverage is 98% (models.py at 100%).

## 9. Recommendation for Phase 2

**PROCEED** — Phase 1 foundation is solid. Phase 2 (Service Layer + Permissions) can begin with confidence:

1. **Service layer** (`services.py`): Implement `ProgressService` with CRUD + 9 FSM orchestration methods + `_log_transition` (StateLog + AuditEvent dual audit).
2. **Permissions** (`permissions.py`): Implement `IsProgressCreatorOrProjectMember`; import `IsCenterDirectorForProject` from projects.
3. **Side effects**: `approve()` must update `Project.cumulative_progress`; `observe()`/`reject()` must create `ProgressReview`.
4. **Helper**: Add `ProjectService.has_pending_progress_reports(project)` to projects/services.py.
5. **TDD discipline**: Write failing tests first (test_services.py, test_permissions.py), then implement.

### Key artifacts ready for Phase 2

- State-scoped fixtures (`progress_borrador`, `progress_enviado`, etc.) are prepared in conftest.py.
- `PROGRESS_STATE_CHANGE` AuditEventType is available for `_log_transition`.
- All 9 FSM `@transition` methods are tested and working.
- `Project.cumulative_progress` field is ready for service-layer updates.
