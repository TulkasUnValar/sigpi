# Proposal: Calls / Convocatorias (§6.8)

## Intent

Manage funding calls (internal/external) with 6-state FSM, document metadata, and constrained project association. Covers RF-067 to RF-072.

## Scope

### In Scope
- `Call` with django-fsm: `borrador → abierta → cerrada → en_evaluacion → resultados_publicados → archivada`
- Internal/external types; external uses `external_entity` (free-text)
- `CallDocument` metadata-only (name, doc_type, external_url)
- `CallProject` through-model; `UniqueConstraint(project)` — one call per project
- `CallService` for FSM; `director_centro` role guard
- DRF `ModelViewSet` + nested routes (documents, projects)
- `django-filter`: state, type, entity, dates, institution
- RLS via `institution_id` (already in migration)

### Out of Scope
File upload, evaluation workflows, notifications, budget tracking, frontend, Meilisearch.

## Capabilities

### New
- `calls`: CRUD, FSM lifecycle, document metadata, project association, filtering

### Modified
- `projects`: Reverse relation via `CallProject`; no schema change to `Project` model

## Approach

| Component | Implementation |
|-----------|---------------|
| FSM | `django-fsm`; `CallService` guards |
| Permissions | `director_centro` for transitions; RBAC for CRUD |
| Project link | `UniqueConstraint(project)` |
| Documents | Metadata-only, mirrors `ProductAttachment` |
| Dates | All 4 nullable; ordering validated when present |
| API | `/calls/`, nested `/documents/`, `/projects/` |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/calls/` | New | Models, services, serializers, viewsets, filters, tests |
| `config/urls.py` | Modified | Register `/api/calls/` router |
| `config/settings.py` | Modified | Add `calls` to `INSTALLED_APPS` |
| RLS migration | Modified | `calls_call` already listed as planned |

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| FSM race condition | Low | `select_for_update` in service |
| Re-association blocked after cancel | Med | Allow when source is `archivada` |
| External entity duplication | Med | Defer normalization post-MVP |

## Rollback

Reverse migration drops all 3 tables. Remove from `INSTALLED_APPS`/router. Leaf module — no downstream dependencies.

## Dependencies

`django-fsm`, `django-filter`, `accounts`, `institutions`, `researchers`, `projects`

## Success Criteria

- [ ] All 6 FSM states reachable with correct role guards
- [ ] `UniqueConstraint(project)` prevents dual-call association
- [ ] Internal calls reject `external_entity`; external calls require it
- [ ] Date validation works with all-null, partial, and full sets
- [ ] Filtering correct for all supported dimensions
- [ ] Coverage ≥80%, strict TDD
- [ ] RLS restricts `calls_call` by `institution_id`

## Proposal Question Round

**Resolved**: One call per project; all dates optional; `director_centro` guards transitions.

**Open for specs phase**:
1. Does `en_evaluacion` involve a formal evaluation committee or scoring?
2. Does `resultados_publicados` require a results document upload?
3. Can projects be linked at any call state, or only when `abierta`?
4. What conditions allow `archivada`? Auto vs. manual `cerrada`?
