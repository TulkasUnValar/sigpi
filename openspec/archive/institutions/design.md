# Design: Institutions & Research Structure (6.1)

## Technical Approach

Expand the auth stubs (`Institution`, `ResearchCenter`) into a 6-entity hierarchy with FSM lifecycle, DRF CRUD API, and RLS tenant isolation. The approach follows the auth module's pragmatic Clean Architecture: Django models as entities, a service layer for FSM transitions, DRF ViewSets as interface adapters, and data migrations for RLS policies.

The hierarchy uses **denormalized `institution_id`** on every entity for O(1) RLS filtering (no tree traversal). Flexible parenting allows skipping levels (e.g., facultad directly under institution without sede).

## Architecture Decisions

| Decision | Choice | Alternative | Rationale |
|----------|--------|-------------|-----------|
| FSM library | `django-fsm` (add to deps) | Plain model methods | Declarative transitions, guards, and signals. Spec requires FSM. Already planned in RNF-011. |
| ViewSet style | `ModelViewSet` per entity | Function-based views (auth pattern) | 6 entities × CRUD = 36+ endpoints. ViewSets eliminate boilerplate. Auth used FBVs because it had only 7 custom endpoints. |
| URL nesting | DRF `SimpleRouter` + manual nested paths | `drf-nested-routers` package | Avoid new dependency. Nested paths are simple to wire manually with `@action` or extra `path()` entries. |
| Status field | `FSMField(default="active")` on each entity | Shared `Status` abstract model | Abstract base class adds complexity for a single field. Use `FSMField` directly; extract if >3 fields shared. |
| Parent validation | `clean()` method per model | DB-level CHECK constraint | CHECK can't validate cross-table FK consistency. `clean()` + `full_clean()` in `save()` matches auth pattern. |
| Deactivate guard | Service method queries children | DB trigger | Business logic belongs in Python layer. Triggers are opaque and harder to test. |
| RLS migration | New migration in `institutions` app | Extend `accounts/0004` | Each app owns its RLS policies. Auth migration is already applied. |
| Code uniqueness | `(institution_id, code)` per sub-entity | Global unique code | Each university defines its own code scheme. Institution.code stays globally unique. |

## Data Flow

```
Client → DRF ViewSet → Serializer.validate() → Service.transition() → Model.save()
              │                                        │
              └── TenantMiddleware (institution_id) ────┘
              │                                        │
              └── TenantRLSMiddleware (SET LOCAL) ──→ PostgreSQL RLS
```

FSM transitions flow:
```
ViewSet.dispatch("POST /activate")
  → InstitutionLifecycleService.activate(instance)
    → instance.activate()  [django-fsm transition]
    → instance.save()
    → return instance
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/institutions/models.py` | Modify | Expand Institution/ResearchCenter stubs; add Sede, Facultad, ResearchGroup, ResearchLine with FSMField |
| `backend/apps/institutions/services.py` | Create | `InstitutionLifecycleService` — transition methods with child-active guards |
| `backend/apps/institutions/serializers.py` | Create | ModelSerializers for all 6 entities; nested read serializers for parent display |
| `backend/apps/institutions/views.py` | Create | 6 ModelViewSets with institution-scoped querysets and permission classes |
| `backend/apps/institutions/urls.py` | Create | DRF SimpleRouter + nested URL patterns per spec API contract |
| `backend/apps/institutions/admin.py` | Modify | Register all 6 models with appropriate list_display and filters |
| `backend/apps/institutions/migrations/0002_expand_hierarchy.py` | Create | Add columns to stubs + create 4 new tables + indexes |
| `backend/apps/institutions/migrations/0003_rls_policies.py` | Create | RLS policies for 5 new institution-scoped tables (Institution has no institution_id) |
| `backend/apps/institutions/tests/` | Create | Test files: test_models, test_services, test_serializers, test_views, test_rls |
| `backend/config/middleware/tenant.py` | Modify | Add `/api/institutions/` to TENANT_REQUIRED_PREFIXES |
| `backend/pyproject.toml` | Modify | Add `django-fsm>=3.0` to dependencies |

## Interfaces / Contracts

### Abstract Base Mixin (code pattern, not abstract model)

```python
class InstitutionScopedModel(models.Model):
    """Pattern followed by all 5 sub-institution entities (not Institution itself)."""
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = FSMField(default="active", protected=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        constraints = [
            UniqueConstraint(fields=["institution", "code"], name="..."),
        ]
```

### Lifecycle Service

```python
class InstitutionLifecycleService:
    @staticmethod
    def deactivate(instance) -> None:
        """Guard: reject if any child entity has status='active'."""
        if _has_active_children(instance):
            raise ConflictError("Deactivate or archive children first.")
        instance.deactivate()
        instance.is_active = False
        instance.save()

    @staticmethod
    def archive(instance) -> None:
        """Guard: reject if any child entity has status='active'. Terminal."""
        if _has_active_children(instance):
            raise ConflictError("Deactivate or archive children first.")
        instance.archive()
        instance.is_active = False
        instance.save()

    @staticmethod
    def activate(instance) -> None:
        instance.activate()
        instance.is_active = True
        instance.save()
```

### Child Resolution Map

| Entity | Children query |
|--------|---------------|
| Institution | Sede, Facultad, ResearchCenter (direct FK) |
| Sede | Facultad, ResearchCenter (where sede=self) |
| Facultad | ResearchCenter (where facultad=self) |
| ResearchCenter | ResearchGroup (where center=self) |
| ResearchGroup | ResearchLine (where group=self) |
| ResearchLine | None (leaf) |

### Permission Matrix

| Action | Required Role |
|--------|---------------|
| Institution CRUD | Superadmin only |
| Sede/Facultad/Center CRUD | IsInstitutionAdmin (level ≤ 2) |
| Group/Line CRUD | IsCenterDirector (level ≤ 3) |
| Lifecycle transitions | Same as create permissions |
| Read (list/detail) | IsAuthenticated + IsSameInstitution |

### RLS Policies

New tables added to RLS (same pattern as `accounts/0004`):
- `institutions_sede`
- `institutions_facultad`
- `institutions_researchcenter` (already has RLS from auth — verify)
- `institutions_researchgroup`
- `institutions_researchline`

Institution table excluded — it has no `institution_id` column. Superadmins see all institutions.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Model `clean()` validation, FSM transitions, child-active guards | pytest + factory-boy factories per entity |
| Unit | Serializer validation (code uniqueness, parent mismatch) | pytest with serializer.is_valid() assertions |
| Integration | ViewSet CRUD + lifecycle endpoints + permission checks | pytest + DRF `APIClient` with session auth |
| Integration | RLS row filtering per institution | pytest-postgresql (skip on SQLite with `@pytest.mark.skipif`) |
| E2E | N/A | Deferred to frontend integration |

## Migration / Rollout

### Migration 0002: Expand Hierarchy

1. **AddField** to Institution: `description`, `address`, `contact_email`, `contact_phone`, `logo_url`, `status` (FSMField, default="active")
2. **AddField** to ResearchCenter: `description`, `contact_email`, `contact_phone`, `status`, `sede` (FK nullable), `facultad` (FK nullable)
3. **AlterField** on ResearchCenter: `code` → required (remove blank=True), add `UniqueConstraint(institution, code)`
4. **CreateModel**: Sede, Facultad, ResearchGroup, ResearchLine
5. **AddIndex**: `(institution_id, status)` on each sub-entity for filtered queries

### Migration 0003: RLS Policies

Same `RunPython` pattern as `accounts/0004` — new migration in `institutions` app adds RLS to 5 tables.

### Rollback

Reverse migration 0003 removes RLS. Reverse migration 0002 drops new tables and removes added columns. No data loss risk — greenfield, no production data.

## Open Questions

- [ ] `django-fsm` vs `django-fsm-3`: verify which package version supports Django 5.1 with `FSMField(default=..., protected=True)`. If `django-fsm` is unmaintained, use `django-fsm-3`.
- [ ] Institution table RLS: should Institution have its own RLS policy? Currently excluded (no `institution_id` column). Superadmin-only CRUD may be sufficient.
