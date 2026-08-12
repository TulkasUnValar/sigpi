# Design: Research Products (SIGPI §6.7)

## Technical Approach

Add a standalone `backend/apps/products/` Django app with three models (`ResearchProduct`, `ProductAuthor`, `ProductAttachment`). Follow the `projects`/`progress` ViewSet pattern: `ModelViewSet` for CRUD, nested `ModelViewSet` for authors/attachments, `django-filter` for filtering, institution scoping via `request.active_membership`, UUID PKs, and denormalized `institution_id`. No FSM.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|---|---|---|---|
| Attachment storage | Metadata-only `external_url` vs MinIO/S3 upload | Upload adds infra complexity; MVP precedent is metadata-only (ProjectDocument/ProgressDocument) | Metadata-only `external_url` |
| Author validation | Model `clean()` vs DB constraints vs serializer | `clean()` catches duplicates/principal rules with readable errors; DB unique constraint catches race conditions | Both: `clean()` + `UniqueConstraint(product, researcher)` |
| Type extensibility | Hardcoded `TextChoices` vs dynamic model | 11 types are stable per spec §6.7; dynamic model adds admin/UI overhead | Hardcoded `TextChoices` (code change for new types) |
| Year validation | `MinValueValidator`/`MaxValueValidator` vs `clean()` | Validators run on forms/DRF automatically; `clean()` gives unified error format | `clean()` with `1900 <= year <= current_year+1` |
| Nested routing | Manual nested `path()` vs `drf-nested-routers` | Manual avoids dependency; matches existing `projects/urls.py` pattern | Manual nested paths under `/products/{id}/authors/` and `/attachments/` |

## Data Flow

```
POST /api/products/
  → ResearchProductViewSet.perform_create
    → inject institution from active_membership
    → validate project FK belongs to same institution (404 if foreign)
    → save() → full_clean() → type & year validation
  → Return ResearchProductSerializer

POST /api/products/{id}/authors/
  → ProductAuthorViewSet.perform_create
    → parent product from URL kwargs
    → validate exactly one principal per product (clean())
    → reject duplicate researcher (UniqueConstraint + clean())
  → Return ProductAuthorSerializer

GET /api/products/?type=artículo&year__gte=2024
  → ResearchProductViewSet.list
    → institution-scoped queryset
    → django-filter (year exact/range, type, project, researcher, center, group, line)
  → Return paginated list
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/products/__init__.py` | Create | App package |
| `backend/apps/products/models.py` | Create | `ResearchProduct`, `ProductAuthor`, `ProductAttachment` |
| `backend/apps/products/serializers.py` | Create | List/Create/Detail serializers + nested child serializers |
| `backend/apps/products/views.py` | Create | `ResearchProductViewSet`, `ProductAuthorViewSet`, `ProductAttachmentViewSet` |
| `backend/apps/products/filters.py` | Create | `ResearchProductFilter` with center/group/line/researcher/project/year/type |
| `backend/apps/products/urls.py` | Create | `/api/products/` + nested authors/attachments |
| `backend/apps/products/admin.py` | Create | Minimal admin registration |
| `backend/apps/products/tests/conftest.py` | Create | `ProductFactory`, `ProductAuthorFactory`, `ProductAttachmentFactory` |
| `backend/apps/products/tests/test_models.py` | Create | Model validation, constraints, relationships |
| `backend/apps/products/tests/test_views.py` | Create | CRUD, filtering, institution scoping, nested endpoints |
| `backend/config/settings/base.py` | Modify | Add `"apps.products"` to `LOCAL_APPS` |
| `backend/config/urls.py` | Modify | `include("apps.products.urls")` under `/api/` |
| `backend/apps/accounts/migrations/0004_rls_policies.py` | Modify | Add product tables to `TENANT_SCOPED_TABLES` |

## Interfaces / Contracts

### ResearchProductFilter
```python
class ResearchProductFilter(FilterSet):
    type = ChoiceFilter(choices=ProductType.choices)
    year = NumberFilter(field_name="publication_year")
    year__gte = NumberFilter(field_name="publication_year", lookup_expr="gte")
    year__lte = NumberFilter(field_name="publication_year", lookup_expr="lte")
    project = UUIDFilter(field_name="project_id")
    center = UUIDFilter(field_name="project__center_id")
    group = UUIDFilter(field_name="project__group_id")
    line = UUIDFilter(field_name="project__line_id")
    researcher = UUIDFilter(field_name="authors__researcher_id")
```

### URL Contract
- `/api/products/` — CRUD
- `/api/products/{id}/` — Retrieve/Update/Delete
- `/api/products/{id}/authors/` — List/Create
- `/api/products/{id}/authors/{pk}/` — Retrieve/Update/Delete
- `/api/products/{id}/attachments/` — List/Create
- `/api/products/{id}/attachments/{pk}/` — Retrieve/Update/Delete

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit (models) | `clean()` validation, `UniqueConstraint`, `__str__`, enum values | pytest model tests with factories, `db` fixture |
| Unit (filters) | Filter by center, group, line, researcher, project, year exact/range, type | Create diverse fixtures, assert filtered queryset counts |
| Integration (views) | Institution scoping, nested authors/attachments, 400/404 edge cases | APIClient with authenticated user + active_membership middleware |
| Regression | Duplicate researcher rejection, missing principal, invalid type/year | Boundary values + negative cases |

## Migration / Rollout

No data migration required (greenfield app). Rollback: remove app from `INSTALLED_APPS` and `urls.py`, delete `backend/apps/products/` directory, remove RLS entries from migration and fake-reverse if tables were created.

## Open Questions

- None
