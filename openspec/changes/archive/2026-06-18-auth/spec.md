# SIGPI Authentication & Authorization Specification

## Purpose

Establish the auth foundation for SIGPI: Keycloak OIDC SSO, django-allauth local fallback, multi-institution user sessions, role-based access control, and tenant isolation via PostgreSQL RLS.

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **User** | `id`, `email` (unique), `keycloak_uuid` (unique, nullable), `auth_source` (`keycloak`\|`local`), `is_active`, `is_superuser`, `last_login` | Email MUST be unique globally. Superadmin MUST be local. |
| **InstitutionMembership** | `id`, `user` (FK), `institution` (FK), `role` (FK), `centers` (M2M), `is_primary`, `joined_at` | User MUST have ≥1 membership. Only one MAY be primary per user. |
| **Role** | `id`, `name`, `keycloak_role_name`, `level` | 7 fixed roles: Superadmin, Admin, Center Director, Researcher, Co-investigator, Committee, Auditor. |
| **Permission** | `id`, `codename`, `description` | Mapped to Django permissions and Keycloak client roles. |

## Functional Requirements

### Requirement: FR-001 — Keycloak OIDC Authentication

The system MUST authenticate users via Keycloak 26 OIDC using `mozilla-django-oidc`.

#### Scenario: First-time OIDC login
- GIVEN a user with a valid Keycloak session
- WHEN they initiate SIGPI login
- THEN the system creates/updates a local User with `keycloak_uuid`, `email`, `institution`, `centers`, and `role` from claims

#### Scenario: Returning OIDC login
- GIVEN an existing local User with matching `keycloak_uuid`
- WHEN they log in via Keycloak
- THEN the system updates claims and issues a session

### Requirement: FR-002 — Local Fallback Authentication

The system MUST fall back to django-allauth local auth when Keycloak is unreachable.

#### Scenario: Keycloak unavailable
- GIVEN Keycloak returns 503 or times out
- WHEN a user submits local credentials
- THEN the system authenticates via allauth and issues a session

### Requirement: FR-003 — Email-Uniqueness & Account Linking

The system MUST enforce email uniqueness and link accounts deterministically.

#### Scenario: Automatic linking with verified email
- GIVEN a Keycloak user with a verified email matching an existing local User
- WHEN they log in via OIDC
- THEN the system links the accounts automatically

#### Scenario: Manual confirmation for unverified email
- GIVEN a Keycloak user with an unverified email matching a local User
- WHEN they log in via OIDC
- THEN the system requests manual confirmation before linking

### Requirement: FR-004 — Multi-Institution Session

The system MUST support multi-institution membership with one active institution per session.

#### Scenario: Institution switch
- GIVEN a user belongs to two institutions
- WHEN they POST `/auth/switch-institution/` with `institution_id`
- THEN the session updates `institution_id` and all querysets reload scoped to the new institution

#### Scenario: Missing active institution
- GIVEN a user with multiple memberships and no active institution in session
- WHEN they access a tenant-scoped endpoint
- THEN the system returns 400 with "Active institution required"

### Requirement: FR-005 — Role-Based Permissions

The system MUST map 7 roles to Django Groups and enforce them via custom DRF permission classes.

#### Scenario: Center Director approval access
- GIVEN a user with the Center Director role for institution A
- WHEN they attempt to approve a project in center C within institution A
- THEN `IsCenterDirector` allows the action

#### Scenario: Cross-institution access denied
- GIVEN a user with the Center Director role for institution A
- WHEN they access a project in institution B
- THEN `IsSameInstitution` returns 403

### Requirement: FR-006 — Tenant Isolation

The system MUST enforce tenant isolation via PostgreSQL RLS as defense-in-depth.

#### Scenario: RLS enforcement
- GIVEN a query on a tenant-scoped table
- WHEN executed under the application DB user
- THEN RLS policies restrict rows to the session’s `institution_id`

### Requirement: FR-007 — Auth Audit Events

The system MUST emit audit events for login, logout, role change, and permission denied.

#### Scenario: Successful login audit
- GIVEN a user logs in successfully
- WHEN the session is created
- THEN an audit event is emitted with user, timestamp, IP, auth source, and institution

### Requirement: FR-008 — Keycloak Role Reconciliation

The system MUST reconcile Keycloak roles with Django Groups via Celery.

#### Scenario: Role sync
- GIVEN a role change occurs in Keycloak
- WHEN the Celery beat task runs (every 5 minutes)
- THEN Django Group membership is updated to match Keycloak

## API Contract

| Endpoint | Method | Auth | Request Body | Response |
|---|---|---|---|---|
| `/auth/login/` | POST | None | `{provider: "keycloak"\|"local", credentials}` | `200` Session cookie + CSRF token |
| `/auth/logout/` | POST | Session | None | `204` |
| `/auth/callback/` | GET | None | OIDC authorization code | `302` Redirect to dashboard |
| `/auth/switch-institution/` | POST | Session | `{institution_id: UUID}` | `200` `{user, active_institution, role}` |
| `/auth/me/` | GET | Session | None | `200` User profile + memberships + active institution |

## Security Requirements

- All auth endpoints MUST use HTTPS in production.
- Session cookies MUST be `HttpOnly`, `Secure`, `SameSite=Lax`.
- OIDC tokens MUST be validated (signature, issuer, audience, expiration).
- RLS policies MUST apply to all tenant-scoped tables.
- Superusers bypass RLS via a separate DB role; migration user bypasses RLS.
- Failed login attempts SHOULD be rate-limited per IP.

## Error Handling

| Error | Status | Response Body |
|---|---|---|
| Invalid credentials | `401` | `{"detail": "Authentication failed."}` |
| Keycloak unreachable | `503` | `{"detail": "SSO unavailable; use local login."}` |
| Institution access denied | `403` | `{"detail": "You do not belong to this institution."}` |
| Permission denied | `403` | `{"detail": "You do not have permission for this action."}` |
| Missing active institution | `400` | `{"detail": "Active institution required."}` |
| Unverified email linking | `409` | `{"detail": "Confirm account linking manually."}` |

## Non-Functional Requirements

- Test coverage MUST be ≥80%.
- Auth response time SHOULD be <300ms for local, <800ms for OIDC round-trip.
- Role sync latency MUST be <5 minutes.
- The system MUST support graceful degradation when Keycloak is down.
