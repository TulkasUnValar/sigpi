# Proposal: Projects Module (SIGPI §6.4)

## Intent

Implement the research project lifecycle — the fourth MVP module and the system's core workflow. Researchers create projects, center directors review/approve/observe them, and the system tracks every state transition through a 12-state FSM. Without this module, SIGPI has no reason to exist.

## Current State

- **accounts** (archived): User, roles, RLS, audit, permissions including `IsProjectOwnerOrCoInvestigator` (references non-existent Project fields).
- **institutions** (archived): 6-entity hierarchy with FSM lifecycle, RLS policies.
- **researchers** (archived): Profiles, affiliations, external profiles, attachments — 207 tests, ~85-90% coverage.
- No project model, state machine, or team membership logic exists yet.

## Proposed State

After this change:
- `Project` model with full metadata, FSM (12 states, ~15 transitions), denormalized `institution_id` for RLS.
- `ProjectMember` junction (non-null FK to `Researcher` — students/seedbeds/collaborators are always Researcher profiles).
- `ProjectDocument` metadata-only (name, doc_type, external_url) — same pattern as `ResearcherAttachment`.
- `ProjectObservation` append-only log for center director observations (RN-014).
- `ProjectStateLog` domain audit log + mirror to `AuditEvent` (RN-012).
- `ProjectService` orchestrating all CRUD and state transitions.
- Project-specific permissions moved from `accounts` to `projects/permissions.py`.
- DRF filtering via `django-filter`, `SearchFilter`, `OrderingFilter` (RF-039).

## Scope

### In Scope
- 5 models: `Project`, `ProjectMember`, `ProjectDocument`, `ProjectObservation`, `ProjectStateLog`
- 12 FSM states with ~15 transitions via `django-fsm` (`protected=False`)
- `ProjectService`: create, update, submit, accept_review, approve, observe, return_to_draft, reject, start_execution, suspend, resume, finalize, initiate_closure, close, cancel
- Permissions: `IsProjectOwnerOrCoInvestigator` (moved from accounts), `IsCenterDirectorForProject`, `CanCreateProjectInCenter`, `IsProjectEditable` (RN-011)
- Nested routes: `/projects/{id}/members/`, `/projects/{id}/documents/`, `/projects/{id}/observations/`, `/projects/{id}/state_history/`
- State transition actions as POST endpoints on `/projects/{id}/`
- RLS policies for all 5 new tables
- `ProjectStateLog` domain log + `AuditEvent` mirror for cross-module audit
- DRF advanced filtering: `django-filter` (status, center, dates, keywords), `SearchFilter`, `OrderingFilter`
- `clean()` validation: RN-007, RN-008, RN-013 + DB `CHECK` constraints for date integrity
- Unique constraint: `(project, researcher)` on `ProjectMember`

### Out of Scope
- Meilisearch indexing (RF-040) — deferred to separate "Search Integration" change
- Actual file upload via MinIO/S3 (RF-036) — deferred to separate "Document Storage" change
- Frontend pages — deferred to frontend-specific change
- Project advances/reports (§6.5) — separate module
- Project outputs/deliverables (§6.6) — separate module
- Multi-institution projects — MVP: one institution per project

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `projects`: Project CRUD, FSM lifecycle (12 states), team membership, document metadata, observation history, state audit log, advanced filtering

### Modified Capabilities
- `auth`: RLS policy extension for 5 new project tables; move `IsProjectOwnerOrCoInvestigator` to `projects/permissions.py` and update field references

## Approach

Normalized relational model (Approach B from exploration), mirroring the `ResearcherAffiliation` pattern. `Project` carries denormalized `institution_id` for RLS. FSM via `django-fsm` with `protected=False` for admin repair. All state transitions centralized in `ProjectService` — views never call FSM directly. `ProjectStateLog` captures domain-specific transitions; each transition also emits an `AuditEvent` for global audit consistency. `ProjectMember.researcher` is always non-null (confirmed: students/seedbeds/collaborators are Researcher profiles). "Observe" creates `ProjectObservation` + transitions to `observado`; "return to draft" transitions to `borrador` without creating an observation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/projects/` | New | Models, services, views, serializers, permissions, urls, admin, tests |
| `backend/apps/accounts/permissions.py` | Modified | Remove/update `IsProjectOwnerOrCoInvestigator` (moved to projects) |
| `backend/apps/accounts/rls.py` | Modified | RLS policies for 5 new project tables |
| `backend/config/settings/base.py` | Modified | Register `projects` in `LOCAL_APPS` |
| `backend/config/urls.py` | Modified | Add `path("api/", include("apps.projects.urls"))` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FSM complexity: 12 states, ~15 transitions, multiple guards | Medium | Centralize in `ProjectService`; state-transition matrix in design; unit test every transition |
| Closed-project immutability bypass via nested endpoints | Medium | Apply `IsProjectEditable` to ALL project viewsets (members, documents), checking parent project status |
| `IsProjectOwnerOrCoInvestigator` field mismatch in `accounts` | High | Move to `projects/permissions.py` immediately; update field names (`principal_investigator`) |
| Cross-app circular imports (projects ↔ accounts) | Medium | Project permissions live in `projects/`; accounts keeps only generic role utilities |
| Date validation bypassed by bulk operations | Low | DB `CHECK` constraints + service-layer validation |

## Rollback Plan

1. Drop `projects` from `LOCAL_APPS` — no downstream module depends on it yet.
2. Reverse migration drops 5 project tables — no FKs from other modules reference them.
3. Remove RLS policies for project tables — accounts/institutions/researchers RLS unaffected.
4. Restore `IsProjectOwnerOrCoInvestigator` in `accounts/permissions.py` if it was removed.

## Dependencies

- `accounts` module (User, RLS infrastructure, AuditEvent, permission base classes)
- `institutions` module (Institution, ResearchCenter, ResearchGroup, ResearchLine)
- `researchers` module (Researcher model for PI and members)
- `django-fsm>=3.0` (already in `pyproject.toml`)
- `django-filter` (add to `pyproject.toml` if not present)
- PostgreSQL 16 with RLS enabled

## Success Criteria

- [ ] Project CRUD via API with correct permissions (researcher creates in affiliated center, owner/CI updates)
- [ ] All 12 FSM states reachable via correct transitions; invalid transitions rejected
- [ ] Center director can approve, observe (creates `ProjectObservation`), return to draft, and reject
- [ ] `ProjectStateLog` records every transition; `AuditEvent` mirror emitted
- [ ] `ProjectMember` supports co_investigator, student, seedbed, collaborator roles (all as `Researcher` FK)
- [ ] `ProjectDocument` stores metadata (name, doc_type, external_url) without file upload
- [ ] Closed/rejected/cancelled projects reject mutations (RN-011)
- [ ] RLS blocks cross-institution project access at DB level
- [ ] DRF filtering works for status, center, dates, keywords, ordering
- [ ] Test coverage ≥80% with strict TDD
