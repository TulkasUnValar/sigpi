# Institutions & Research Structure Specification

## Purpose

Manage the 6-entity hierarchy — Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine — with lifecycle FSM and tenant isolation.

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **Institution** | `id` (UUID PK), `name`, `code` (unique), `description`, `address`, `contact_email`, `contact_phone`, `logo_url`, `status`, `is_active`, timestamps | `code` unique globally |
| **Sede** | `id` (UUID PK), `institution` (FK, denorm), `code`, `name`, `description`, `status`, `is_active`, timestamps | `(institution, code)` unique |
| **Facultad** | `id`, `institution` (FK, denorm), `sede` (FK, nullable), `code`, `name`, `description`, `status`, `is_active`, timestamps | `(institution, code)` unique |
| **ResearchCenter** | `id`, `institution` (FK, denorm), `sede` (FK, nullable), `facultad` (FK, nullable), `code`, `name`, `description`, `contact_email`, `contact_phone`, `status`, `is_active`, timestamps | `(institution, code)` unique |
| **ResearchGroup** | `id`, `institution` (FK, denorm), `center` (FK), `code`, `name`, `description`, `status`, `is_active`, timestamps | `(institution, code)` unique |
| **ResearchLine** | `id`, `institution` (FK, denorm), `group` (FK), `code`, `name`, `description`, `status`, `is_active`, timestamps | `(institution, code)` unique |

All entities: `status` ∈ {`active`, `deactivated`, `archived`}; `institution_id` denormalized for RLS efficiency.

## Functional Requirements

### Requirement: RF-001 — Institution Creation

The system MUST allow creating institutions.

#### Scenario: Superadmin creates institution
- GIVEN a superadmin user
- WHEN they POST `/institutions/` with name and code
- THEN an Institution is created with status `active`

### Requirement: RF-002 — Sede Creation

The system MUST allow creating sedes under an institution.

#### Scenario: Admin creates sede
- GIVEN an active institution
- WHEN they POST `/institutions/{id}/sedes/` with name and code
- THEN a Sede is created linked to that institution

### Requirement: RF-003 — Facultad Creation

The system MUST allow creating facultades under an institution, optionally under a sede.

#### Scenario: Admin creates facultad without sede
- GIVEN an active institution
- WHEN they POST `/institutions/{id}/facultades/` with name, code, and no sede
- THEN a Facultad is created linked directly to the institution

#### Scenario: Admin creates facultad with sede
- GIVEN an active institution with an active sede
- WHEN they POST `/institutions/{id}/facultades/` with sede included
- THEN the Facultad is linked to both institution and sede

### Requirement: RF-004 — ResearchCenter Creation

The system MUST allow creating research centers.

#### Scenario: Admin creates center
- GIVEN an active institution
- WHEN they POST `/institutions/{id}/centers/` with name and code
- THEN a ResearchCenter is created with status `active`

### Requirement: RF-005 — Flexible Center Parenting

The system MUST allow associating centers to institutions, sedes, or facultades.

#### Scenario: Center attached to facultad
- GIVEN an active institution with an active facultad
- WHEN they create a ResearchCenter with facultad set and sede null
- THEN the center is linked to the facultad

### Requirement: RF-006 — ResearchGroup Creation

The system MUST allow creating research groups under a center.

#### Scenario: Director creates group
- GIVEN an active ResearchCenter
- WHEN they POST `/centers/{id}/groups/` with name and code
- THEN a ResearchGroup is created linked to that center

### Requirement: RF-007 — ResearchLine Creation

The system MUST allow creating research lines under a group.

#### Scenario: Director creates line
- GIVEN an active ResearchGroup
- WHEN they POST `/groups/{id}/lines/` with name and code
- THEN a ResearchLine is created linked to that group

### Requirement: RF-008 — Lifecycle Management

The system MUST allow activating, deactivating, or archiving institutional structures.

#### Scenario: Deactivate entity
- GIVEN an active entity with no active children
- WHEN an authorized user triggers deactivate
- THEN the entity transitions to `deactivated`

#### Scenario: Block deactivate with active children
- GIVEN an active entity with active children
- WHEN an authorized user triggers deactivate
- THEN the action is rejected with 409

#### Scenario: Archive entity
- GIVEN a deactivated entity with no active children
- WHEN an authorized user triggers archive
- THEN the entity transitions to `archived` terminally

#### Scenario: Reactivate entity
- GIVEN a deactivated entity
- WHEN an authorized user triggers activate
- THEN the entity transitions back to `active`

## API Contract

| Endpoint | Method | Auth | Request Body | Response |
|---|---|---|---|---|
| `/institutions/` | GET, POST | Session | `{name, code, ...}` | List / Institution |
| `/institutions/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | Institution / 204 |
| `/institutions/{id}/sedes/` | GET, POST | Session | `{name, code}` | List / Sede |
| `/institutions/{id}/sedes/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | Sede / 204 |
| `/institutions/{id}/facultades/` | GET, POST | Session | `{name, code, sede?}` | List / Facultad |
| `/institutions/{id}/facultades/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | Facultad / 204 |
| `/institutions/{id}/centers/` | GET, POST | Session | `{name, code, sede?, facultad?}` | List / ResearchCenter |
| `/institutions/{id}/centers/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | ResearchCenter / 204 |
| `/centers/{id}/groups/` | GET, POST | Session | `{name, code}` | List / ResearchGroup |
| `/centers/{id}/groups/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | ResearchGroup / 204 |
| `/groups/{id}/lines/` | GET, POST | Session | `{name, code}` | List / ResearchLine |
| `/groups/{id}/lines/{id}/` | GET, PATCH, DELETE | Session | `{name, ...}` | ResearchLine / 204 |
| `/{entity}/{id}/activate/` | POST | Session | None | 200 `{status: active}` |
| `/{entity}/{id}/deactivate/` | POST | Session | None | 200 `{status: deactivated}` |
| `/{entity}/{id}/archive/` | POST | Session | None | 200 `{status: archived}` |

## FSM Lifecycle

| Transition | Source | Target | Guard |
|---|---|---|---|
| `activate` | `deactivated` | `active` | — |
| `deactivate` | `active` | `deactivated` | No active children |
| `archive` | `active` | `archived` | No active children |
| `archive` | `deactivated` | `archived` | No active children |

Archived is terminal; reactivation requires creating a new entity.

## Security Requirements

- RLS policies MUST filter all 6 tables by `institution_id`.
- Superadmins MAY bypass RLS.
- Institution admins MUST only access data for their institution.
- Center Directors MUST only access centers in their `InstitutionMembership.centers` M2M.

## Error Handling

| Error | Status | Response |
|---|---|---|
| Duplicate code per institution | 409 | `{"detail": "Code already exists for this institution."}` |
| Parent institution mismatch | 400 | `{"detail": "Parent belongs to a different institution."}` |
| Active children on deactivate/archive | 409 | `{"detail": "Deactivate or archive children first."}` |
| RLS institution violation | 403 | `{"detail": "Institution access denied."}` |
| Invalid status transition | 400 | `{"detail": "Invalid transition from X to Y."}` |

## Non-Functional Requirements

- Test coverage MUST be ≥80%.
- API response time SHOULD be <200ms for list, <100ms for detail.
- Model `clean()` MUST validate parent chain institution consistency before save.

## MODIFIED Capabilities

### Auth — RLS Policy Extension

RLS policies in `accounts/rls.py` MUST be extended to cover the 6 new institution-scoped tables.

### Auth — InstitutionMembership Centers M2M

`InstitutionMembership.centers` M2M MUST resolve to real `ResearchCenter` records.
