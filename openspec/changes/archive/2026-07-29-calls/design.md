# Design: Calls / Convocatorias Module (SIGPI §6.8)

## Technical Approach

Implement the Calls module as a standalone Django app (`apps/calls/`) following the established projects module pattern: django-fsm for lifecycle, static service layer for orchestration, DRF ModelViewSet with nested routes, and RLS for tenant isolation. The module is a leaf dependency — no downstream modules depend on it.

Spec reference: `openspec/changes/calls/spec.md` (5 requirements, 6-state FSM, 6 transitions).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|-------------|-----------|
| ADR-1 | FSM library | `django-fsm` (existing) | Custom state machine, django-model-utils | Consistency with projects module; battle-tested; `@transition` decorators provide declarative guards |
| ADR-2 | Service layer style | Static methods on `CallService` | Instance methods, Django Manager | Matches `ProjectService` pattern exactly; views never call `@transition` directly |
| ADR-3 | Race condition prevention | `select_for_update()` in service FSM methods | Optimistic locking, application-level mutex | Spec mandates it; simpler than optimistic locking; PostgreSQL-native |
| ADR-4 | Audit log model | `CallStateLog` (mirrors `ProjectStateLog`) | Reuse global `AuditEvent` only | Queryable per-call history; global `AuditEvent` for cross-module consistency |
| ADR-5 | Project association | `CallProject` through-model with `UniqueConstraint(project)` | Simple M2M, separate FK on Project | One call per project at DB level; extensible for future metadata (submission_date, status) |
| ADR-6 | Nested routes | Manual `path()` (no `drf-nested-routers`) | `drf-nested-routers` package | Matches projects pattern; avoids extra dependency |
| ADR-7 | Call scope | Institution-scoped (no center/group/line) | Center-scoped like projects | Spec defines calls at institution level; simpler entity |

## Clean Architecture Layer Mapping

```
Entities (business rules, framework-free)
├── CallStatus (TextChoices enum — 6 states)
├── CallType (TextChoices enum — internal/external)
├── CallDocumentType (TextChoices enum)
└── TERMINAL_STATES = {"archivada"}

Use Cases (application rules)
├── CallService — CRUD + 6 FSM transitions + _log_transition
├── CallDocumentService — document CRUD with terminal guard
└── CallProjectService — project linking with state guard (abierta only)

Interface Adapters (controllers, presenters, gateways)
├── CallViewSet — ModelViewSet + 6 @action FSM endpoints
├── CallDocumentViewSet — nested ModelViewSet
├── CallProjectViewSet — nested ModelViewSet (create, list, destroy)
├── CallStateLogViewSet — read-only
├── CallSerializer / CallListSerializer / CallCreateSerializer
├── CallDocumentSerializer / CallProjectSerializer / CallStateLogSerializer
├── CallFilter — django-filter FilterSet
└── Permission classes: IsCallDirector, CanManageCall

Frameworks & Drivers
├── Django ORM models (Call, CallDocument, CallProject, CallStateLog)
├── RLS migration (0002_rls_policies.py)
├── URL routing (urls.py)
├── AppConfig (apps.py)
└── Admin registration (admin.py)
```

## Data Flow

```
HTTP Request
    │
    ▼
TenantMiddleware ──→ injects active_membership + institution_id
    │
    ▼
CallViewSet.get_queryset() ──→ institution-scoped filter
    │
    ▼
Permission check (IsAuthenticated + role-based)
    │
    ▼
CallService.open_call(call, user)
    │
    ├── select_for_update() on Call row
    ├── call.open_call()  [django-fsm @transition]
    ├── call.save()
    ├── CallStateLog.objects.create(...)
    └── AuditEventEmitter().emit("CALL_STATE_CHANGE", ...)
    │
    ▼
CallSerializer ──→ JSON Response
```

## Data Model

### Call

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `institution` | FK → Institution | `CASCADE`, `related_name="calls"` |
| `title` | CharField(255) | required |
| `description` | TextField | required |
| `call_type` | CharField(20) | `choices=CallType` |
| `external_entity` | CharField(255) | `blank=True, default=""` |
| `submission_start` | DateField | `null=True, blank=True` |
| `submission_end` | DateField | `null=True, blank=True` |
| `evaluation_start` | DateField | `null=True, blank=True` |
| `evaluation_end` | DateField | `null=True, blank=True` |
| `status` | FSMField | `default="borrador", protected=False` |
| `created_at` | DateTimeField | `auto_now_add` |
| `updated_at` | DateTimeField | `auto_now` |

**CHECK constraints:**
- `check_internal_no_entity`: `call_type='internal' → external_entity=''`
- `check_external_has_entity`: `call_type='external' → external_entity!=''`
- `check_submission_dates`: when both non-null, `submission_end >= submission_start`
- `check_evaluation_dates`: when both non-null, `evaluation_end >= evaluation_start`

**Indexes:**
- `idx_call_inst_status`: `(institution, status)`
- `idx_call_type`: `(call_type)`
- `idx_call_submission_start`: `(submission_start)`

### CallDocument

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `call` | FK → Call | `CASCADE`, `related_name="documents"` |
| `name` | CharField(255) | required |
| `doc_type` | CharField(20) | `choices=CallDocumentType` |
| `external_url` | URLField(500) | required |
| `created_at` | DateTimeField | `auto_now_add` |

### CallProject

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `call` | FK → Call | `CASCADE`, `related_name="call_projects"` |
| `project` | FK → Project | `CASCADE`, `related_name="call_associations"` |
| `linked_at` | DateTimeField | `auto_now_add` |

**Constraints:**
- `UniqueConstraint(fields=["project"], name="unique_call_per_project")`

### CallStateLog

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | UUIDField (PK) | `default=uuid4` |
| `call` | FK → Call | `CASCADE`, `related_name="state_logs"` |
| `from_state` | CharField(30) | |
| `to_state` | CharField(30) | |
| `triggered_by` | FK → User | `SET_NULL, null=True` |
| `reason` | TextField | `blank=True` |
| `created_at` | DateTimeField | `auto_now_add` |

**Indexes:**
- `idx_call_statelog_time`: `(call, -created_at)`

## Service Layer

### CallService

```python
class CallService:
    @staticmethod
    def create(institution, user, **data) -> Call:
        """Validate type/entity rules, create with status=borrador."""

    @staticmethod
    def update(call, **data) -> Call:
        """Reject if terminal (archivada). Delegate to full_clean + save."""

    @staticmethod
    def delete(call) -> None:
        """Reject if not borrador or has linked projects."""

    # FSM methods — all use select_for_update
    @staticmethod
    def open_call(call, user) -> Call:
        """borrador → abierta. select_for_update + _log_transition."""

    @staticmethod
    def close_call(call, user) -> Call:
        """abierta → cerrada."""

    @staticmethod
    def start_evaluation(call, user) -> Call:
        """cerrada → en_evaluacion."""

    @staticmethod
    def publish_results(call, user) -> Call:
        """en_evaluacion → resultados_publicados."""

    @staticmethod
    def archive(call, user) -> Call:
        """cerrada|resultados_publicados → archivada (terminal)."""

    @staticmethod
    def _log_transition(call, from_state, to_state, user, reason=""):
        """Create CallStateLog + emit AuditEvent("CALL_STATE_CHANGE")."""
```

**`select_for_update` pattern** (each FSM method):
```python
@staticmethod
def open_call(call, user):
    from django.db import transaction
    with transaction.atomic():
        locked = Call.objects.select_for_update().get(pk=call.pk)
        from_state = locked.status
        locked.open_call()  # django-fsm @transition
        locked.save()
        CallService._log_transition(locked, from_state, locked.status, user)
        return locked
```

### CallDocumentService

```python
class CallDocumentService:
    @staticmethod
    def add(call, name, doc_type, external_url) -> CallDocument:
        """Reject if call is terminal (archivada)."""

    @staticmethod
    def update(document, **data) -> CallDocument:
        """Reject if parent call is terminal."""

    @staticmethod
    def remove(document) -> None:
        """Reject if parent call is terminal."""
```

### CallProjectService

```python
class CallProjectService:
    @staticmethod
    def link(call, project) -> CallProject:
        """Reject if call not abierta. UniqueConstraint catches duplicates."""

    @staticmethod
    def unlink(call_project) -> None:
        """Delete the association."""
```

## API Layer

### ViewSets

| ViewSet | Base | Actions | Serializer Resolution |
|---------|------|---------|----------------------|
| `CallViewSet` | `ModelViewSet` | CRUD + 5 FSM `@action` (open_call, close_call, start_evaluation, publish_results, archive) | list→`CallListSerializer`, create/update→`CallCreateSerializer`, else→`CallSerializer` |
| `CallDocumentViewSet` | `ModelViewSet` | CRUD nested | `CallDocumentSerializer` |
| `CallProjectViewSet` | `ModelViewSet` | list, create, destroy (no update) | `CallProjectSerializer` |
| `CallStateLogViewSet` | `ReadOnlyModelViewSet` | list only | `CallStateLogSerializer` |

### Serializers (6)

| Serializer | Fields | Notes |
|-----------|--------|-------|
| `CallListSerializer` | id, title, call_type, status, submission_start, submission_end, created_at | Lightweight for list |
| `CallSerializer` | All fields + nested documents, call_projects | Full detail, read-only nested |
| `CallCreateSerializer` | Writable fields; institution read-only | Validates type/entity rules, date ordering |
| `CallDocumentSerializer` | id, call (RO), name, doc_type, external_url, created_at (RO) | |
| `CallProjectSerializer` | id, call (RO), project, linked_at (RO) | project writable FK |
| `CallStateLogSerializer` | All fields read-only | |

### Permissions

| Action | Permission Classes |
|--------|-------------------|
| list, retrieve | `IsAuthenticated` |
| create | `IsAuthenticated`, `HasRoleLevelOrHigher(3)` (director_centro+) |
| update, partial_update | `IsAuthenticated`, `HasRoleLevelOrHigher(3)`, `CanManageCall` |
| destroy | `IsAuthenticated`, `HasRoleLevelOrHigher(3)`, `CanManageCall` |
| FSM transitions (all 5) | `IsAuthenticated`, `HasRoleLevelOrHigher(3)` (director_centro+) |
| documents CRUD | `IsAuthenticated`, `HasRoleLevelOrHigher(3)` |
| projects link/unlink | `IsAuthenticated`, `HasRoleLevelOrHigher(3)` |
| state_logs list | `IsAuthenticated` |

**`CanManageCall`**: Object-level — verifies the call belongs to the user's institution. Admin+ (level ≤ 2) bypasses.

### URL Routes

```
/api/calls/                                          GET, POST
/api/calls/{id}/                                     GET, PATCH, DELETE
/api/calls/{id}/open_call/                           POST
/api/calls/{id}/close_call/                          POST
/api/calls/{id}/start_evaluation/                    POST
/api/calls/{id}/publish_results/                     POST
/api/calls/{id}/archive/                             POST
/api/calls/{id}/documents/                           GET, POST
/api/calls/{id}/documents/{did}/                     PATCH, DELETE
/api/calls/{id}/projects/                            GET, POST
/api/calls/{id}/projects/{pid}/                      DELETE
/api/calls/{id}/state_history/                       GET
```

### Filtering (`CallFilter`)

| Filter | Type | Field |
|--------|------|-------|
| `status` | ChoiceFilter | `status` (CallStatus choices) |
| `call_type` | ChoiceFilter | `call_type` (CallType choices) |
| `external_entity` | CharFilter (icontains) | `external_entity` |
| `submission_start_after` | DateFilter (gte) | `submission_start` |
| `submission_start_before` | DateFilter (lte) | `submission_start` |
| `institution` | UUIDFilter | `institution_id` |

Search: `title`, `description`. Ordering: `title`, `submission_start`, `created_at`, `status`.

## RLS Policy Design

Follows the exact pattern from `projects/migrations/0002_rls_policies.py`:

**Parent table** (`calls_call`):
```sql
ALTER TABLE calls_call ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON calls_call
    USING (institution_id = current_setting('sigpi.institution_id')::uuid);
CREATE POLICY superadmin_bypass ON calls_call
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
```

**Child tables** (`calls_calldocument`, `calls_callproject`, `calls_callstatelog`):
```sql
-- Subquery via call_id → calls_call.institution_id
CREATE POLICY tenant_isolation ON {child_table}
    USING (call_id IN (
        SELECT id FROM calls_call
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));
CREATE POLICY superadmin_bypass ON {child_table}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
```

## State Transition Implementation

FSM transitions on the `Call` model use `@transition` decorators:

```python
@transition(field=status, source="borrador", target="abierta")
def open_call(self): ...

@transition(field=status, source="abierta", target="cerrada")
def close_call(self): ...

@transition(field=status, source="cerrada", target="en_evaluacion")
def start_evaluation(self): ...

@transition(field=status, source="en_evaluacion", target="resultados_publicados")
def publish_results(self): ...

@transition(field=status, source=["cerrada", "resultados_publicados"], target="archivada")
def archive(self): ...
```

Invalid transitions raise `TransitionNotAllowed` → caught in ViewSet → 409 response.

## Error Handling & Validation Strategy

| Layer | Validation | Error Format |
|-------|-----------|-------------|
| Serializer | Type/entity rules, date ordering, required fields | `400 {"field": ["message"]}` |
| Model `clean()` | Same rules at model level (defense in depth) | `ValidationError` → `400` |
| Service | Terminal state guard, state-specific guards (abierta for link) | `ValidationError` → `400/403` |
| django-fsm | Invalid source state | `TransitionNotAllowed` → `409` |
| Permission | Role level, institution match | `403` |
| RLS | Cross-institution access | `404` (not 403, prevents enumeration) |
| UniqueConstraint | Duplicate project association | `IntegrityError` → `409` |

## Testing Strategy

| Layer | What to Test | Approach | Target |
|-------|-------------|----------|--------|
| Unit | Model constraints, clean() validation, FSM transitions | pytest-django, factory-boy | 90%+ |
| Unit | Service methods (create, update, FSM orchestration, guards) | pytest, mock AuditEventEmitter | 90%+ |
| Unit | Serializer validation (type/entity rules, date ordering) | pytest-django | 85%+ |
| Unit | Permission classes (role checks, institution match) | pytest, parameterized | 85%+ |
| Integration | ViewSet endpoints (CRUD + FSM actions + nested routes) | pytest-django, APIClient | 85%+ |
| Integration | Filter correctness (all dimensions) | pytest-django | 80%+ |
| E2E | RLS tenant isolation (cross-institution denied) | pytest, PostgreSQL | 100% of policies |

**Coverage floor**: ≥80% overall (per `openspec/config.yaml` `tdd_policy`).

**Test files**:
- `tests/conftest.py` — factories (CallFactory, CallDocumentFactory, CallProjectFactory, CallStateLogFactory) + state-scoped fixtures
- `tests/test_models.py` — model constraints, clean(), FSM transitions
- `tests/test_services.py` — service methods, select_for_update, audit logging
- `tests/test_serializers.py` — validation rules
- `tests/test_views.py` — endpoint integration tests
- `tests/test_permissions.py` — permission class unit tests
- `tests/test_filters.py` — filter correctness
- `tests/test_rls.py` — RLS policy tests (PostgreSQL only)
- `tests/test_urls.py` — URL resolution

## Migration & Seeding Strategy

### Migration 1: `0001_initial.py`
- Create `calls_call` table (all fields, constraints, indexes)
- Create `calls_calldocument` table
- Create `calls_callproject` table (with `UniqueConstraint`)
- Create `calls_callstatelog` table (with indexes)
- Dependencies: `institutions.0001_initial`, `projects.0001_initial`, `accounts.0001_initial`

### Migration 2: `0002_rls_policies.py`
- Enable RLS on all 4 tables
- Create `tenant_isolation` + `superadmin_bypass` policies
- Pattern: conditional PostgreSQL execution (no-op on SQLite)

### Config changes
- Add `"apps.calls"` to `INSTALLED_APPS` in `config/settings.py`
- Add `path("api/", include("apps.calls.urls"))` to `config/urls.py`
- `/api/calls/` already in `TENANT_REQUIRED_PREFIXES` (tenant middleware)

### No seeding required
- No seed data for calls module (unlike institutions which has roles)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/calls/__init__.py` | Create | Package init |
| `apps/calls/apps.py` | Create | AppConfig with `name = "apps.calls"` |
| `apps/calls/models.py` | Create | Call, CallDocument, CallProject, CallStateLog + enums |
| `apps/calls/services.py` | Create | CallService, CallDocumentService, CallProjectService |
| `apps/calls/serializers.py` | Create | 6 serializers |
| `apps/calls/views.py` | Create | 4 ViewSets |
| `apps/calls/permissions.py` | Create | CanManageCall |
| `apps/calls/filters.py` | Create | CallFilter |
| `apps/calls/urls.py` | Create | Router + nested routes + FSM action paths |
| `apps/calls/admin.py` | Create | Admin registration |
| `apps/calls/migrations/__init__.py` | Create | Migrations package |
| `apps/calls/migrations/0001_initial.py` | Create | 4 tables with constraints/indexes |
| `apps/calls/migrations/0002_rls_policies.py` | Create | RLS policies for all 4 tables |
| `apps/calls/tests/__init__.py` | Create | Tests package |
| `apps/calls/tests/conftest.py` | Create | Factories + state fixtures |
| `apps/calls/tests/test_models.py` | Create | Model tests |
| `apps/calls/tests/test_services.py` | Create | Service tests |
| `apps/calls/tests/test_serializers.py` | Create | Serializer tests |
| `apps/calls/tests/test_views.py` | Create | View integration tests |
| `apps/calls/tests/test_permissions.py` | Create | Permission tests |
| `apps/calls/tests/test_filters.py` | Create | Filter tests |
| `apps/calls/tests/test_rls.py` | Create | RLS tests |
| `apps/calls/tests/test_urls.py` | Create | URL resolution tests |
| `config/settings.py` | Modify | Add `apps.calls` to `INSTALLED_APPS` |
| `config/urls.py` | Modify | Add calls URL include |

**Total**: 23 new files, 2 modified files, 0 deleted.

## Open Questions

- [ ] None — all design decisions resolved by spec and existing patterns.
