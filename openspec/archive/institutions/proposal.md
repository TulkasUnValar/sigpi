# Proposal: Institutions & Research Structure Module (6.1)

## Intent

The auth module created minimal `Institution` and `ResearchCenter` stubs to support `InstitutionMembership`. This change expands those stubs into the full hierarchical structure required by SPEC 6.1: Institution → Sede → Facultad → Centro → Grupo → Línea, with flexible parent resolution and lifecycle management (activate/deactivate/archive). Without this module, no other domain module (researchers, projects, advances) can reference the organizational entities they depend on.

## Scope

### In Scope
- Expand `Institution` model (add description, address, contact fields)
- Expand `ResearchCenter` model (add FK to Sede/Facultad, description, contact)
- Add `Sede` model (campus, belongs to Institution)
- Add `Facultad` model (faculty, belongs to Institution, optionally to Sede)
- Add `ResearchGroup` model (belongs to ResearchCenter)
- Add `ResearchLine` model (belongs to ResearchGroup)
- CRUD API endpoints for all 6 entities with nested hierarchical routes
- Lifecycle transitions: activate, deactivate, archive (django-fsm `FSMField`)
- PostgreSQL RLS policies on all institution-scoped tables
- DRF permissions scoped to institution + role (building on auth module)
- Admin site registration for all models
- Database migration expanding existing stubs (no data loss)

### Out of Scope
- Frontend pages and components (separate change)
- Meilisearch indexing (module 6.11)
- Researcher-to-entity associations (module 6.3)
- Project-to-entity associations (module 6.4)
- PDF reports for institutions (module 6.6)
- CvLAC/GrupLAC integration (module 6.3, deferred)
- Audit event emission beyond model-level signals (module 6.13)

## Capabilities

### New Capabilities
- `institution-structure`: Models, FK hierarchy, flexible parent resolution, field definitions, uniqueness constraints, and lifecycle FSM (active → deactivated → archived) for all 6 entities
- `institution-api`: DRF viewsets, nested serializers, URL routing, permissions, and RLS integration for institutional structure CRUD

### Modified Capabilities
- `auth`: RLS policies must cover new institution-scoped tables; `InstitutionMembership.centers` M2M gains real center records

## Approach

Expand stubs in `apps/institutions/models.py`. The hierarchy is not a strict tree — SPEC allows skipping levels (facultad can attach directly to institution, centro can attach to institution/sede/facultad). Each entity uses nullable FKs for optional parents and a required `institution_id` FK (denormalized) for RLS efficiency. Lifecycle uses `django-fsm` with three states: `active`, `deactivated`, `archived`. Deactivation is reversible; archival is terminal. Institution scoping uses the tenant middleware from auth. New migrations extend the existing `0001_initial` — no table renames, only column additions and new tables.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/institutions/models.py` | Modified | Expand Institution, ResearchCenter; add Sede, Facultad, ResearchGroup, ResearchLine |
| `backend/apps/institutions/serializers.py` | New | DRF serializers with nested reads |
| `backend/apps/institutions/views.py` | New | Viewsets with institution-scoped filtering |
| `backend/apps/institutions/urls.py` | New | Nested DRF routers |
| `backend/apps/institutions/admin.py` | Modified | Register all 6 models |
| `backend/apps/institutions/migrations/` | New | Migration 0002 expanding stubs + new tables |
| `backend/apps/accounts/rls.py` | Modified | Add RLS policies for new institution tables |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Stub expansion requires data migration for existing Institution/Center records | Low | Existing test fixtures have minimal data; migration adds columns with defaults |
| Flexible FK hierarchy allows inconsistent nesting (e.g., center without facultad but with sede from different institution) | Medium | Model-level `clean()` validates parent chain belongs to same institution |
| RLS policies on 6 new tables add migration complexity | Medium | Reuse tenant middleware pattern from auth; single policy template per table |
| Archiving an entity with active children orphans data | Medium | Prevent archive if entity has active children; deactivate children first |

## Rollback Plan

1. Reverse migration `0002` restores stub schema — new tables dropped, new columns removed from existing tables
2. Remove `institution-structure` and `institution-api` specs from `openspec/specs/`
3. Revert `accounts/rls.py` to auth-only policies
4. No production data risk — module has no users yet

## Dependencies

- Auth module (COMPLETE, ARCHIVED): provides User, Role, InstitutionMembership, tenant middleware, RLS policy pattern, and the Institution/ResearchCenter stubs being expanded
- django-fsm: already in project dependencies (RNF-011)
- PostgreSQL 16 with RLS enabled: configured in Docker Compose

## Success Criteria

- [ ] All 6 entities (Institution, Sede, Facultad, ResearchCenter, ResearchGroup, ResearchLine) have full CRUD via DRF endpoints
- [ ] Flexible FK hierarchy allows facultad without sede and centro attached directly to institution
- [ ] Model-level validation prevents parent chain institution mismatch
- [ ] Lifecycle FSM: active ↔ deactivated, active → archived (terminal)
- [ ] Archive is blocked if entity has active children
- [ ] RLS policies enforce institution isolation on all 6 tables
- [ ] Existing InstitutionMembership and auth functionality remains intact after stub expansion
- [ ] Test coverage ≥80% (strict TDD per project config)

## Proposal Question Round

The following assumptions need user review before specs:

1. **Cascade behavior**: Archiving an entity requires deactivating all children first. No silent cascade — the admin must explicitly deactivate. Is this acceptable, or should deactivation propagate automatically?

2. **Code fields**: The Institution stub has a `code` field (unique). Should all 6 entities have `code` fields? If yes, are they unique within their parent or unique globally?

3. **Archiving terminal state**: The proposal treats `archived` as terminal (no reactivation). Should archived entities be re-activatable, or is this correct?

4. **Institution denormalization**: Every entity carries a direct FK to Institution (even if a parent also points to Institution) for RLS efficiency. This creates redundancy but makes RLS policies simple. Acceptable?

5. **Description/address fields**: How rich should the Institution model be for MVP? Proposal assumes: name, code, description (optional), address (optional), contact_email (optional), contact_phone (optional), is_active, status, timestamps.