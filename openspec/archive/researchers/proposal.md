# Proposal: Researchers Module (SIGPI §6.3)

## Intent

Centralize researcher profiles — academic, institutional, and external — as the third MVP module. Researchers are the primary actors who create projects, report advances, and produce research outputs. Without this module, no downstream workflow can function.

## Current State

- **Auth module** (archived): User model with Keycloak OIDC + allauth fallback, 7-role hierarchy, `InstitutionMembership` with `centers` M2M, RLS tenant isolation.
- **Institutions module** (active): 6-entity hierarchy (Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine), `InstitutionScopedModel` abstract base, FSM lifecycle, RLS policies.
- No researcher model, profile, or affiliation logic exists yet.

## Proposed State

After this change:
- `Researcher` model linked to `User` via optional FK (User can exist without Researcher).
- `ResearcherAffiliation` junction table enabling M2M between researcher and centers/groups/lines within one institution.
- `ExternalProfile` model with `provider` choices (CvLAC, ORCID, Google Scholar, LinkedIn, ResearchGate) + `url`.
- `ResearcherAttachment` metadata-only model (name, type, external URL). Real file storage deferred to `documents` module.
- Automatic profile completeness score calculated from mandatory field population.
- Full CRUD API following institutions patterns (ViewSet, permissions, RLS).

## Scope

### In Scope
- `Researcher` model with profile fields (names, document, contact, bio, academic formation)
- `ResearcherAffiliation` junction table (researcher ↔ center/group/line, M2M within one institution)
- `ExternalProfile` model with provider enum + URL
- `ResearcherAttachment` metadata-only model (name, type, external_url)
- Profile completeness auto-calculation (non-null mandatory fields / total mandatory fields)
- CRUD API: Admin+ creates researchers, researcher updates own profile, authenticated read
- RLS policies extending tenant isolation to researcher tables
- Unique constraint: `(institution, document_number)` per RN-001

### Out of Scope
- Automatic CvLAC/GrupLAC sync (SPEC §19 — TBD, low priority)
- Multi-institution researcher (MVP: one institution per researcher, documented as known limitation)
- Real file upload via MinIO (deferred to `documents` module)
- Meilisearch indexing (deferred to `search` module)
- PDF researcher reports (deferred to `reports` module)
- Researcher FSM lifecycle (no state machine needed — `is_active` boolean suffices)

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `researchers`: Researcher profile CRUD, affiliation M2M, external profiles, attachment metadata, completeness score

### Modified Capabilities
- `auth`: RLS policy extension to cover `researchers_researcher`, `researchers_researcheraffiliation`, `researchers_externalprofile`, `researchers_researcherattachment` tables

## Approach

Follow the `InstitutionScopedModel` abstract base from institutions. `Researcher` carries denormalized `institution_id` for RLS efficiency. Affiliations use a junction table (`ResearcherAffiliation`) instead of simple FKs to support researchers belonging to multiple centers/groups/lines within the same institution. `ExternalProfile` uses Django `TextChoices` for provider enum. Completeness is a computed property on the serializer — count of populated mandatory fields divided by total mandatory fields. No FSM; `is_active` mirrors `User.is_active` for soft-deactivation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/researchers/` | New | Models, serializers, views, services, tests |
| `backend/apps/accounts/rls.py` | Modified | RLS policies for 4 new researcher tables |
| `backend/config/settings/base.py` | Modified | Register `researchers` in INSTALLED_APPS |
| `frontend/app/[locale]/researchers/` | New | List, detail, create/edit researcher pages |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Affiliation M2M complexity in queries | Medium | Scoped queries via `InstitutionScopedModel`; prefetch_related for affiliations |
| Profile completeness logic drift | Low | Keep formula simple (null-check); document mandatory fields list |
| Tight coupling with future projects module | Medium | Researcher model does NOT import Project; cross-module via service layer |
| One-institution MVP limitation | Low | Document as known constraint; multi-institution requires junction pattern + RLS redesign |

## Rollback Plan

1. Drop `researchers` app from `INSTALLED_APPS` — no other module depends on it yet.
2. Reverse migration drops 4 researcher tables — no foreign keys from other modules reference them.
3. Remove RLS policies for researcher tables — auth/institutions RLS unaffected.
4. Frontend: remove `/researchers/` route — no other routes link to it in MVP.

## Dependencies

- `accounts` module (User model, RLS infrastructure, permission classes)
- `institutions` module (ResearchCenter, ResearchGroup, ResearchLine models)
- PostgreSQL 16 with RLS enabled

## Success Criteria

- [ ] Researcher CRUD works via API with correct permissions (Admin+ creates, owner updates, authenticated reads)
- [ ] ResearcherAffiliation supports M2M to centers/groups/lines within one institution
- [ ] ExternalProfile stores CvLAC, ORCID, Google Scholar, LinkedIn, ResearchGate URLs
- [ ] Attachment metadata (name, type, external_url) stored without file upload
- [ ] Profile completeness score auto-calculated and exposed in API response
- [ ] `(institution, document_number)` uniqueness enforced (RN-001)
- [ ] RLS blocks cross-institution researcher access at DB level
- [ ] Test coverage ≥80% with strict TDD
- [ ] User can exist without a linked Researcher profile

## Proposal Question Round

The following assumptions need user confirmation before specs:

1. **Mandatory fields for completeness**: We assume first_name, last_name, document_type, document_number, primary_email, and at least one affiliation. Correct?
2. **Attachment types**: We propose CV, certificate, academic degree, support letter, other. Any institution-specific types needed?
3. **Affiliation cardinality**: A researcher can have multiple affiliations but only ONE can be marked `is_primary`. Acceptable?
