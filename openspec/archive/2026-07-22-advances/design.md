# Design: SIGPI Advances/Progress Module (§6.5)

## Technical Approach

Standalone `apps.progress` bounded context implementing periodic progress reporting for research projects. Mirrors the proven `projects` module architecture: UUID PKs, `django-fsm` with `@transition` decorators (`protected=False`), service-layer FSM orchestration, institution-scoped querysets, dual audit (domain `ProgressStateLog` + global `AuditEvent`), metadata-only documents, and append-only review/state-log entities.

`ProgressReport` carries a 6-state FSM with 9 transitions. On approval, `ProgressService.approve()` updates the denormalized `Project.cumulative_progress` field — recalculated from the latest approved report, never summed.

## Architecture Decisions

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| App location | Standalone `apps.progress` | Sub-module in `projects` | **Standalone** | SPEC §6.5 defines advances as separate module; projects is archived and at capacity; distinct 6-state FSM prevents state confusion with Project's 12-state FSM. |
| `en_revision` state | Implicit (skip) | Explicit 6th state | **Explicit** | Spec requires director `accept_review()` step; mirrors Project FSM pattern; enables clean permission boundary. |
| Percentage semantics | Incremental (sum) | Cumulative (latest) | **Cumulative** | RF-049: "porcentaje de avance acumulado". On approval, `Project.cumulative_progress` = report's `cumulative_percentage`. No double-counting risk. |
| `rechazado` reversibility | Terminal | Reversible to `borrador` | **Reversible** | RN-P06: investigators correct and resubmit rejected advances. `return_to_draft()` from `rechazado`. |
| Permission reuse | Import `IsCenterDirectorForProject` from projects | Extract generic to accounts | **Import from projects** | Projects is stable; extraction adds risk for minimal gain. Accept soft coupling. |
| Nested vs top-level routes | Nested only | Top-level + nested shortcut | **Hybrid** | Top-level `/progress/?project={id}` for director dashboards; nested `/projects/{id}/progress/` read-only shortcut for project context. |
| Document storage | MinIO/S3 upload | Metadata-only `external_url` | **Metadata-only** | Matches `ProjectDocument` pattern; file upload infra deferred to post-MVP. |

## Data Model

```
Institution ──→ ProgressReport ←── Project (FK)
                     │
         ┌───────────┼───────────┐
         ↓           ↓           ↓
   ProgressReview  ProgressDocument  ProgressStateLog
```

### ProgressReport (`progress_progressreport`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK, `default=uuid4` |
| `institution` | `FK(Institution)` | `related_name='progress_reports'` |
| `project` | `FK(Project)` | `related_name='progress_reports'`, CASCADE |
| `created_by` | `FK(User)` | `related_name='created_progress_reports'` |
| `period_start` | `DateField` | required |
| `period_end` | `DateField` | required; DB CHECK `>= period_start` (RN-P02) |
| `description` | `TextField` | required |
| `cumulative_percentage` | `DecimalField(5,2)` | `0.00–100.00` (RN-P01); DB CHECK |
| `activities` | `TextField` | required |
| `difficulties` | `TextField` | `blank=True` |
| `next_steps` | `TextField` | `blank=True` |
| `status` | `FSMField` | `default='borrador'`, `protected=False` |
| `created_at` | `DateTimeField` | `auto_now_add` |
| `updated_at` | `DateTimeField` | `auto_now` |

**Indexes**: `(institution, status)`, `(project, status)`, `(created_by)`.

### ProgressReview (`progress_progressreview`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK |
| `progress_report` | `FK(ProgressReport)` | `related_name='reviews'`, CASCADE |
| `reviewed_by` | `FK(User)` | `SET_NULL, null=True` |
| `review_text` | `TextField` | required |
| `review_type` | `CharField(20)` | `choices=ProgressReviewType` (`observation`, `rejection`) |
| `created_at` | `DateTimeField` | `auto_now_add` |

**Append-only**: no update/delete endpoints (RN-P05).

### ProgressDocument (`progress_progressdocument`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK |
| `progress_report` | `FK(ProgressReport)` | `related_name='documents'`, CASCADE |
| `name` | `CharField(255)` | required |
| `doc_type` | `CharField(20)` | `choices=ProgressDocumentType` (`evidence`, `annex`, `report`, `other`) |
| `external_url` | `URLField(500)` | `blank=True` |
| `uploaded_at` | `DateTimeField` | `auto_now_add` |

### ProgressStateLog (`progress_progressstatelog`)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK |
| `progress_report` | `FK(ProgressReport)` | `related_name='state_logs'`, CASCADE |
| `from_state` | `CharField(30)` | required |
| `to_state` | `CharField(30)` | required |
| `triggered_by` | `FK(User)` | `SET_NULL, null=True` |
| `reason` | `TextField` | `blank=True` |
| `created_at` | `DateTimeField` | `auto_now_add` |

**Append-only**. Indexes: `(progress_report, -created_at)`, `(from_state, to_state)`.

### Project Model Delta

Add to `Project`:
- `cumulative_progress = DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))` — denormalized, updated by `ProgressService.approve()`.

## FSM Design

```
borrador ──submit()──→ enviado ──accept_review()──→ en_revision
    ↑                                                    │
    │                                    ┌───────────────┼───────────────┐
    │                                    ↓               ↓               ↓
    │                               aprobado       observado        rechazado
    │                              (terminal)          │               │
    │                                            resubmit()    return_to_draft()
    │                                                  │               │
    │                                                  ↓               ↓
    │                                             enviado         borrador
    │
    └── return_to_draft() ←── en_revision | observado
```

### Transition Table (9 transitions)

| # | Source | Target | Trigger | Guard | Side Effects |
|---|--------|--------|---------|-------|--------------|
| 1 | `borrador` | `enviado` | `submit()` | period valid; percentage valid | StateLog + AuditEvent |
| 2 | `enviado` | `en_revision` | `accept_review()` | `IsCenterDirectorForProject` | StateLog + AuditEvent |
| 3 | `en_revision` | `aprobado` | `approve()` | `IsCenterDirectorForProject` | Update `Project.cumulative_progress`; StateLog + AuditEvent |
| 4 | `en_revision` | `observado` | `observe(review_text)` | `IsCenterDirectorForProject` | Create `ProgressReview(observation)`; StateLog + AuditEvent |
| 5 | `en_revision` | `rechazado` | `reject(review_text)` | `IsCenterDirectorForProject` | Create `ProgressReview(rejection)`; StateLog + AuditEvent |
| 6 | `en_revision` | `borrador` | `return_to_draft()` | `IsCenterDirectorForProject` | StateLog + AuditEvent |
| 7 | `observado` | `enviado` | `resubmit()` | `IsProgressCreatorOrProjectMember` (creator) | StateLog + AuditEvent |
| 8 | `observado` | `borrador` | `return_to_draft()` | `IsCenterDirectorForProject` | StateLog + AuditEvent |
| 9 | `rechazado` | `borrador` | `return_to_draft()` | `IsProgressCreatorOrProjectMember` (creator) | StateLog + AuditEvent |

**Terminal**: `aprobado` — no outbound transitions (RN-P07).
**Non-terminal reject**: `rechazado` → `borrador` via `return_to_draft()` (RN-P06).

## Service Layer

### ProgressService

```python
class ProgressService:
    @staticmethod
    def create(project, user, **data) -> ProgressReport:
        """Validate project not terminal (RN-P09). Inject institution from project."""

    @staticmethod
    def update(report, **data) -> ProgressReport:
        """Reject if not borrador. Delegate to clean() + save()."""

    @staticmethod
    def delete(report) -> None:
        """Reject if not borrador."""

    # — FSM orchestration (9 methods) —
    @staticmethod
    def submit(report, user) -> ProgressReport: ...
    @staticmethod
    def accept_review(report, user) -> ProgressReport: ...
    @staticmethod
    def approve(report, user) -> ProgressReport:
        """Transition + update Project.cumulative_progress."""
    @staticmethod
    def observe(report, user, review_text) -> ProgressReport:
        """Transition + create ProgressReview(observation)."""
    @staticmethod
    def reject(report, user, review_text) -> ProgressReport:
        """Transition + create ProgressReview(rejection)."""
    @staticmethod
    def return_to_draft(report, user) -> ProgressReport: ...
    @staticmethod
    def resubmit(report, user) -> ProgressReport: ...

    @staticmethod
    def _log_transition(report, from_state, to_state, user, reason=""):
        """Create ProgressStateLog + emit AuditEvent(PROGRESS_STATE_CHANGE)."""
```

Each FSM method: (1) call `report.<transition>()`, (2) `report.save()`, (3) `_log_transition()`.

### ProgressDocumentService

```python
class ProgressDocumentService:
    @staticmethod
    def add(report, name, doc_type, external_url="") -> ProgressDocument: ...
    @staticmethod
    def update(document, **data) -> ProgressDocument: ...
    @staticmethod
    def remove(document) -> None: ...
```

Guard: parent report must be in `borrador` state for mutations.

## API Design

### ViewSets

| ViewSet | Base | Permissions | Notes |
|---------|------|-------------|-------|
| `ProgressViewSet` | `ModelViewSet` | Action-specific via `get_permissions()` | CRUD + 9 FSM `@action` endpoints |
| `ProgressDocumentViewSet` | `ModelViewSet` | `[IsAuthenticated, IsProgressCreatorOrProjectMember]` | Nested under `/progress/{pk}/documents/` |
| `ProgressReviewViewSet` | `ReadOnlyModelViewSet` | `[IsAuthenticated]` | Nested under `/progress/{pk}/reviews/` |
| `ProgressStateLogViewSet` | `ReadOnlyModelViewSet` | `[IsAuthenticated]` | Nested under `/progress/{pk}/state_history/` |

### Permission Classes

```python
class IsProgressCreatorOrProjectMember(BasePermission):
    """User is report.created_by OR is a ProjectMember of report.project.
    Admin+ (level ≤ 2) bypasses. Used for CRUD + submit/resubmit."""

# Reused from projects:
# IsCenterDirectorForProject — checks obj.project.center_id against membership.centers
```

### Permission Matrix

| Action | Superadmin | Admin | Director | PI | Co-Inv (creator) | Other |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| Create report | ✅ | ✅ | — | ✅ | ✅ (member) | — |
| Update (borrador) | ✅ | ✅ | — | ✅ (creator) | ✅ (creator) | — |
| Delete (borrador) | ✅ | ✅ | — | ✅ (creator) | — | — |
| Submit / Resubmit | ✅ | ✅ | — | ✅ (creator) | ✅ (creator) | — |
| Accept review | ✅ | ✅ | ✅ | — | — | — |
| Approve / Observe / Reject | ✅ | ✅ | ✅ | — | — | — |
| Return to draft (en_revision/observado) | ✅ | ✅ | ✅ | — | — | — |
| Return to draft (rechazado) | ✅ | ✅ | — | ✅ (creator) | — | — |
| Manage documents | ✅ | ✅ | — | ✅ (creator) | ✅ (creator) | — |
| View reviews / history | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (inst.) |

### URL Routing

```
/progress/                                      GET, POST
/progress/{id}/                                 GET, PATCH, DELETE
/progress/{id}/submit/                          POST
/progress/{id}/accept_review/                   POST
/progress/{id}/approve/                         POST
/progress/{id}/observe/                         POST  (body: review_text)
/progress/{id}/reject/                          POST  (body: review_text)
/progress/{id}/return_to_draft/                 POST
/progress/{id}/resubmit/                        POST
/progress/{id}/documents/                       GET, POST
/progress/{id}/documents/{did}/                 PATCH, DELETE
/progress/{id}/reviews/                         GET
/progress/{id}/state_history/                   GET
/projects/{id}/progress/                        GET  (read-only shortcut)
```

### Serializer Mapping

| Serializer | Use | Key Fields |
|-----------|-----|------------|
| `ProgressReportListSerializer` | List | id, project, status, cumulative_percentage, period_start, period_end, created_at |
| `ProgressReportSerializer` | Retrieve | All fields + nested documents, reviews (read-only) |
| `ProgressReportCreateSerializer` | Create/Update | Writable fields; institution + created_by injected by view |
| `ProgressDocumentSerializer` | Document CRUD | name, doc_type, external_url (report read-only from URL) |
| `ProgressReviewSerializer` | Review list (read-only) | reviewed_by, review_text, review_type, created_at |
| `ProgressStateLogSerializer` | State history (read-only) | from_state, to_state, triggered_by, reason, created_at |

### Filtering

```python
class ProgressReportFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=ProgressStatus.choices)
    project = django_filters.UUIDFilter(field_name="project_id")
    period_start_after = django_filters.DateFilter(field_name="period_start", lookup_expr="gte")
    period_start_before = django_filters.DateFilter(field_name="period_start", lookup_expr="lte")

    class Meta:
        model = ProgressReport
        fields = ["status", "project", "period_start_after", "period_start_before"]
```

## RLS Policies

4 new tables added to tenant isolation (mirroring `projects/migrations/0002_rls_policies.py`):

- **Parent** (`progress_progressreport`): direct `institution_id` column → `tenant_isolation` + `superadmin_bypass`.
- **Children** (`progress_progressreview`, `progress_progressdocument`, `progress_progressstatelog`): subquery via `progress_report_id` → `progress_progressreport.institution_id`.

## Migration Plan

| Migration | Depends On | Content |
|-----------|-----------|---------|
| `progress/0001_initial.py` | `projects.0001`, `accounts.0003` | Create 4 tables + CHECK constraints + indexes |
| `progress/0002_rls_policies.py` | `progress.0001` | RLS for 4 tables (parent + 3 children) |
| `projects/0003_add_cumulative_progress.py` | `projects.0002` | Add `cumulative_progress` DecimalField to Project |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| **Factories** | `ProgressReportFactory`, `ProgressReviewFactory`, `ProgressDocumentFactory`, `ProgressStateLogFactory` | factory-boy in `conftest.py`; reuse `ProjectFactory` from projects |
| **Model tests** | `clean()` validations (RN-P01, RN-P02), DB CHECK constraints, FSM `@transition` validity | pytest-django |
| **FSM tests** | All 9 valid transitions succeed; invalid transitions fail; `aprobado` blocks outbound; `rechazado` allows `return_to_draft` | State-scoped fixtures per state |
| **Service tests** | CRUD, all 9 FSM methods, `_log_transition` dual audit, `approve()` updates `Project.cumulative_progress`, guard enforcement | Unit; mock `AuditEventEmitter` |
| **Serializer tests** | Field validation, list vs detail, read-only nested, percentage boundary | DRF test utilities |
| **Permission tests** | Full role × action matrix (10 actions × 6 roles = 60 cells) | Fixture-based with role factories |
| **View tests** | CRUD + 9 FSM actions + nested routes + error responses (400, 403) | APIClient with authenticated users |
| **Admin tests** | Model registration, list_display, search_fields | Django admin test patterns |

**Coverage target**: ≥90% (pytest-cov). **TDD**: strict Red–Green–Refactor.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/progress/__init__.py` | Create | Package init |
| `backend/apps/progress/apps.py` | Create | `ProgressConfig` |
| `backend/apps/progress/models.py` | Create | 4 models + 3 enums (ProgressStatus, ProgressDocumentType, ProgressReviewType) + 9 FSM `@transition` methods |
| `backend/apps/progress/services.py` | Create | ProgressService (CRUD + 9 FSM + `_log_transition`), ProgressDocumentService |
| `backend/apps/progress/serializers.py` | Create | 6 serializers (list, detail, create, document, review, state_log) |
| `backend/apps/progress/views.py` | Create | 4 ViewSets: ProgressViewSet (CRUD + 9 actions), Document, Review (read-only), StateLog (read-only) |
| `backend/apps/progress/permissions.py` | Create | `IsProgressCreatorOrProjectMember`; import `IsCenterDirectorForProject` from projects |
| `backend/apps/progress/filters.py` | Create | `ProgressReportFilter` |
| `backend/apps/progress/urls.py` | Create | Top-level router + manual nested paths + projects nested shortcut |
| `backend/apps/progress/admin.py` | Create | Register all 4 models |
| `backend/apps/progress/migrations/0001_initial.py` | Create | 4 tables, CHECK constraints, indexes |
| `backend/apps/progress/migrations/0002_rls_policies.py` | Create | RLS for 4 tables |
| `backend/apps/progress/tests/__init__.py` | Create | Test package |
| `backend/apps/progress/tests/conftest.py` | Create | 4 factories + 6 state-scoped fixtures |
| `backend/apps/progress/tests/test_models.py` | Create | Model + FSM transition tests |
| `backend/apps/progress/tests/test_services.py` | Create | Service layer tests |
| `backend/apps/progress/tests/test_serializers.py` | Create | Serializer tests |
| `backend/apps/progress/tests/test_permissions.py` | Create | Permission matrix tests (60 cells) |
| `backend/apps/progress/tests/test_views.py` | Create | ViewSet + FSM action + nested route tests |
| `backend/apps/progress/tests/test_admin.py` | Create | Admin registration tests |
| `backend/apps/projects/models.py` | Modify | Add `cumulative_progress` field to Project |
| `backend/apps/projects/services.py` | Modify | Add `ProjectService.has_pending_progress_reports(project)` static helper |
| `backend/apps/projects/migrations/0003_add_cumulative_progress.py` | Create | Migration for new field |
| `backend/config/settings/base.py` | Modify | Add `"apps.progress"` to `LOCAL_APPS` |
| `backend/config/urls.py` | Modify | Add `path("api/", include("apps.progress.urls"))` |
| `backend/apps/accounts/audit.py` | Modify | Add `PROGRESS_STATE_CHANGE` to `AuditEventType` |

## Open Questions

- [ ] Should `return_to_draft()` from `en_revision` also accept a `reason` parameter for director context? Current design: no reason (mirrors projects pattern).
- [ ] Should the `/projects/{id}/progress/` nested shortcut be a dedicated ViewSet or reuse `ProgressViewSet` with `get_queryset` override? Recommendation: reuse `ProgressViewSet` with `project_pk` kwarg filtering.
