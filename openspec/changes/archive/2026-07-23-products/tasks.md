# Tasks: Research Products (SIGPI §6.7)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900–1100 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation: models, migrations, RLS, settings wiring | PR 1 | base = feature/products-tracker |
| 2 | Core API: serializers, views, filters, URLs | PR 2 | base = PR 1 branch |
| 3 | Tests & admin: model tests, view tests, filter tests, admin | PR 3 | base = PR 2 branch |

## Phase 1: Foundation

- [x] 1.1 Create `backend/apps/products/__init__.py` and `apps.py`
- [x] 1.2 Create `backend/apps/products/models.py` with `ResearchProduct`, `ProductAuthor`, `ProductAttachment`
- [x] 1.3 Run `makemigrations products`; verify 3 tables in migration
- [x] 1.4 Add `"apps.products"` to `LOCAL_APPS` in `backend/config/settings/base.py`
- [x] 1.5 Include product tables in `TENANT_SCOPED_TABLES` in `backend/apps/accounts/migrations/0004_rls_policies.py`
- [x] 1.6 Create `backend/apps/products/admin.py` with minimal registrations

## Phase 2: Core Implementation

- [x] 2.1 Create `backend/apps/products/serializers.py`: `ResearchProductSerializer`, `ProductAuthorSerializer`, `ProductAttachmentSerializer`
- [x] 2.2 Create `backend/apps/products/filters.py`: `ResearchProductFilter` with center, group, line, researcher, project, year exact/range, type
- [x] 2.3 Create `backend/apps/products/views.py`: `ResearchProductViewSet`, `ProductAuthorViewSet`, `ProductAttachmentViewSet` with institution scoping
- [x] 2.4 Create `backend/apps/products/urls.py`: `/api/products/` + nested `authors/` and `attachments/`
- [x] 2.5 Include `apps.products.urls` under `/api/` in `backend/config/urls.py`

## Phase 3: Integration

- [x] 3.1 Verify `migrate` runs cleanly; check RLS applies to product tables
- [x] 3.2 Verify `GET/POST /api/products/` responds 200/201 with institution scope
- [x] 3.3 Verify nested `authors/` and `attachments/` endpoints resolve correctly

## Phase 4: Testing

- [x] 4.1 RED: Write `test_models.py` — type validation, year bounds, duplicate author rejection, missing principal (RF-081, RF-082)
- [x] 4.2 GREEN: Make model tests pass
- [x] 4.3 RED: Write `test_views.py` — create product linked to project, reject foreign project, reject invalid type/year, filter by year__gte & type, empty foreign institution (RF-080, RF-084)
- [x] 4.4 GREEN: Make view tests pass
- [x] 4.5 RED: Write filter tests — center, group, line, researcher, project, year exact/range, type (RF-084)
- [x] 4.6 GREEN: Make filter tests pass
- [x] 4.7 REFACTOR: Extract shared fixtures to `conftest.py` (`ProductFactory`, `ProductAuthorFactory`, `ProductAttachmentFactory`)

## Phase 5: Coverage & Polish (Work Unit 3)

- [x] 5.1 Create `backend/apps/products/tests/conftest.py` with factory-boy factories
- [x] 5.2 Create `backend/apps/products/tests/test_admin.py` — admin registration, list_display, search_fields, list_filter, raw_id_fields
- [x] 5.3 Add edge-case tests: PUT updates, DELETE, anonymous nested access, cross-institution isolation, filter empty results, year upper bound via API
- [x] 5.4 Refactor test files for DRY and ruff compliance
- [x] 5.5 Verify `ruff check apps/products/` passes cleanly
- [x] 5.6 Run full suite: 84 tests passing, 0 failures
