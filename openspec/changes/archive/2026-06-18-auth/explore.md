# Exploration: Authentication & Authorization Module for SIGPI

## Exploration: SIGPI Auth Module

### Current State
SIGPI is a greenfield project — no authentication or authorization code exists yet. The SPEC (v1.1) and OpenSpec config define the following constraints:

- **Backend**: Django 5.1 + Django REST Framework (DRF)
- **Primary Auth**: Keycloak 26 (OIDC/SAML)
- **Fallback Auth**: django-allauth
- **Multi-tenancy**: Logical separation by `institution_id` in a single PostgreSQL 16 DB, with Row-Level Security (RLS) as a safety net.
- **Role hierarchy**: Superadmin → Admin institucional → Director de centro → Investigador → Coinvestigador → Auditor → Usuario BI
- **Approval flow**: 1-level (Investigator sends → Center Director approves/rejects/observes)

The project uses Docker Compose for local/dev/staging, with strict TDD (pytest, ≥80% coverage).

### Affected Areas
- `backend/apps/accounts/` — Custom User model, Keycloak OIDC integration, allauth fallback, role/permission definitions
- `backend/apps/institutions/` — `institution_id` foreign key on User/Researcher/Project; institution-scoped querysets
- `backend/config/settings/` — `AUTHENTICATION_BACKENDS`, `REST_FRAMEWORK` auth/permission classes, Keycloak OIDC provider config
- `backend/apps/projects/` — Object-level permissions (who can edit which project based on institution/center/role)
- `backend/apps/audit/` — Every auth event (login, role change, permission denied) must be logged
- `backend/config/middleware/` — Multi-tenancy middleware to inject `institution_id` context into request/thread-local
- `backend/apps/accounts/migrations/` — Custom User model must be defined before first migration
- `frontend/app/[locale]/auth/` — Login/logout/callback pages, Keycloak JS adapter or NextAuth.js
- `docker-compose.yml` — Keycloak 26 service, PostgreSQL RLS setup

### Approaches

#### 1. Full Keycloak Centralization (Approach A)
Keycloak owns users, groups, roles, and SSO. Django acts as a pure OIDC Relying Party (RP). Roles are mapped from Keycloak realm/client roles into Django groups. Django permissions are coarse-grained (mostly `is_staff`, `is_superuser`); fine-grained access is enforced by custom permission classes that check Keycloak token claims (e.g., `institution_id`, `center_id`).

- **Pros**:
  - Single source of truth for identity and SSO across all institutions
  - SAML support "for free" via Keycloak Identity Provider federation
  - Enterprise-grade: MFA, session management, brute-force protection, audit logs out of the box
  - User onboarding/offboarding managed entirely in Keycloak
- **Cons**:
  - Complex: requires deep Keycloak realm/client configuration; role mapping must be maintained in two places (Keycloak + Django code)
  - Network dependency: if Keycloak is unreachable, authentication fails (allauth fallback helps, but creates divergence)
  - Performance: every API call that needs role info may require token introspection or local JWKS validation
  - Operational burden: Keycloak realm backups, upgrades, clustering for HA
- **Effort**: High

#### 2. Hybrid Local-Keycloak (Approach B) — **RECOMMENDED**
Keycloak handles OIDC/SAML SSO and enterprise federation. Upon first login via OIDC, Django creates/updates a local User record and copies essential claims (`institution_id`, `center_ids`, `role`) into local fields. Django manages its own `Group`/`Permission` model for application-level authorization. django-allauth provides independent local registration/login when Keycloak is unavailable. A background Celery task syncs role changes from Keycloak periodically.

- **Pros**:
  - Resilient: local auth works even if Keycloak is down; allauth fallback is natural, not a hack
  - Django permissions ecosystem works natively (`@permission_required`, DRF `IsAuthenticated`, `DjangoModelPermissions`)
  - Multi-tenancy is simpler: `institution_id` is a local DB column, filterable in querysets, enforceable via RLS
  - Performance: no remote token introspection per request; JWT signature validation is fast and stateless
  - Easier testing: can test auth flows without a running Keycloak instance (mock OIDC or use allauth)
- **Cons**:
  - Slight data duplication: user attributes exist in both Keycloak and Django (must be kept in sync)
  - Role changes in Keycloak require sync to Django (event-driven or polling)
  - More complex user model (must store Keycloak UUID + local fields)
- **Effort**: Medium

#### 3. Allauth-First with Optional Keycloak (Approach C)
Use django-allauth as the primary auth mechanism. Keycloak is wired as an additional OAuth2/OIDC provider via allauth's social account adapters. No direct Keycloak admin integration. Roles and permissions live entirely in Django.

- **Pros**:
  - Simplest to implement and test
  - No Keycloak operational complexity in early MVP
  - Allauth has mature OIDC provider support
- **Cons**:
  - Loses enterprise SAML/MFA benefits if Keycloak is treated as "just another OAuth provider"
  - Harder to enforce institution-wide SSO policies
  - Does not meet SPEC requirement (RNF-012) that Keycloak is the *primary* auth
- **Effort**: Low

### Recommendation
**Adopt Approach B (Hybrid Local-Keycloak)**.

Rationale:
- The SPEC explicitly names Keycloak as the *primary* auth and allauth as *fallback*. A hybrid model respects this hierarchy.
- Multi-tenancy by `institution_id` is much easier to enforce when the field is a native Django model attribute, queryable and indexable.
- The project is greenfield but expects national-scale rollout. Starting with a clean User model that references Keycloak UUID while keeping local permissions is the right long-term foundation.
- DRF's built-in permission classes (`DjangoObjectPermissions`) work out of the box when Django owns the permission matrix.

### Detailed Design Notes

#### Keycloak Integration Architecture
1. **Django as OIDC RP**: Use `mozilla-django-oidc` or `django-oauth-toolkit` (as client) to handle the OIDC flow. Given Keycloak 26, `mozilla-django-oidc` is simpler and battle-tested.
2. **User Model Mapping**:
   - Custom `User` model extends `AbstractUser`.
   - Fields: `keycloak_uuid` (UUID, unique, nullable for allauth-only users), `institution` (FK to Institution), `centers` (M2M to ResearchCenter), `role` (CharField with choices matching the hierarchy).
   - `username` stays as the local identifier; `email` is required and unique.
3. **Authentication Backends** (in order):
   - `mozilla_django_oidc.auth.OIDCAuthenticationBackend` (Keycloak OIDC)
   - `django.contrib.auth.backends.ModelBackend` (local/allauth fallback)
   - `allauth.account.auth_backends.AuthenticationBackend` (allauth social/local)
4. **Token Handling**:
   - Access tokens are short-lived (5–15 min). Refresh tokens handled by Keycloak.
   - DRF authentication class: custom `KeycloakOIDCAuthentication` that validates the Bearer JWT locally using Keycloak's JWKS endpoint, then maps `sub` claim to `User.keycloak_uuid`.
   - Token validation is local (cached JWKS) — no introspection round-trip per API call.
5. **Role Synchronization**:
   - On OIDC login, map Keycloak realm roles (`sigpi_superadmin`, `sigpi_investigador`, etc.) to Django `Group` membership.
   - Map Keycloak custom claims (`institution_id`, `center_ids`) to User fields.
   - Provide a Celery task (`sync_keycloak_users`) that periodically reconciles Keycloak users with Django to catch role changes made by admins.

#### django-allauth Fallback
- **When it activates**: When Keycloak is unreachable (network partition), or when an institution does not have Keycloak federation configured yet.
- **Avoiding conflicting user records**:
  - Enforce `email` uniqueness at the DB level.
  - When an OIDC user logs in, match by `email` first, then update `keycloak_uuid`. If a local allauth user with the same email exists, link the social account to the existing user (allauth's `connect` flow).
  - If a user is created via allauth first, and later an OIDC account with the same email arrives, the OIDC backend must link rather than create duplicate.
  - Use `ACCOUNT_EMAIL_REQUIRED = True` and `ACCOUNT_UNIQUE_EMAIL = True`.
- **Flagging**: Add `auth_source` field (`keycloak`, `allauth_local`, `allauth_social`) for audit and operational visibility.

#### Permission Model
1. **Django built-ins**: Use `Group` per role + `Permission` per model action (`add_project`, `change_project`, `approve_project`, etc.).
2. **Custom object-level permissions**:
   - Implement a `InstitutionObjectPermissionBackend` that checks `request.user.institution_id == obj.institution_id`.
   - For center-scoped objects, check intersection of `user.centers` with `obj.center`.
   - Use `django-guardian` or a lightweight custom backend. Recommendation: custom backend to avoid adding another dependency for what is essentially a single-field check.
3. **DRF Integration**:
   - `IsAuthenticated` globally.
   - Custom permission classes: `IsSameInstitution`, `IsCenterDirector`, `IsProjectOwnerOrCoInvestigator`, `IsAuditorReadOnly`.
   - These compose cleanly: `permission_classes = [IsAuthenticated, IsSameInstitution, IsProjectOwnerOrCoInvestigator]`.

#### Multi-tenancy Enforcement
1. **Application layer (primary)**:
   - All querysets filtered by `institution_id`. Use a custom `TenantQuerySet` mixin or manager that auto-applies `.filter(institution_id=current_institution)`.
   - `current_institution` is set in middleware by reading `request.user.institution_id`.
   - For Superadmin, bypass the filter (override in manager).
2. **PostgreSQL RLS (safety net)**:
   - Enable RLS on all tenant-scoped tables.
   - Policy: `CREATE POLICY institution_isolation ON projects USING (institution_id = current_setting('app.current_institution')::int);`
   - Middleware executes `SET app.current_institution = <user.institution_id>` at connection start.
   - This is a **defense-in-depth** measure, not the primary enforcement, because RLS can complicate migrations, admin, and Celery tasks.

#### Role Hierarchy Implementation
| Role | Django Group | Keycloak Realm Role | Permissions |
|---|---|---|---|
| Superadmin | `superadmin` | `sigpi_superadmin` | All permissions globally |
| Admin institucional | `admin_institucional` | `sigpi_admin_institucional` | CRUD on users/centers within their institution |
| Director de centro | `director_centro` | `sigpi_director_centro` | Approve/reject projects/avances within their centers |
| Investigador | `investigador` | `sigpi_investigador` | Create/edit own projects; edit projects where responsible/participant |
| Coinvestigador | `coinvestigador` | `sigpi_coinvestigador` | Edit projects where participant; limited PDF/dashboard access |
| Auditor | `auditor` | `sigpi_auditor` | Read-only audit logs; limited by institution |
| Usuario BI | `usuario_bi` | `sigpi_usuario_bi` | Read-only dashboards; no mutation |

- Use Django's `Group` membership as the runtime authority. Keycloak is the provisioning source.
- A `Role` model is NOT needed if we use Django `Group` + a mapping dict. However, storing role metadata (description, level) in a `Role` model can be useful for UI rendering.

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Keycloak downtime blocks enterprise login | High | Allauth fallback; graceful degradation message |
| Role sync lag between Keycloak and Django | Medium | Event-driven sync via Keycloak webhooks; fallback to Celery beat every 5 min |
| JWT token expiration causing UX friction | Medium | Short access token + refresh token rotation; frontend silent refresh |
| RLS policies accidentally block migrations/admin | Medium | Use separate DB user for migrations (bypass RLS); admin uses superuser check |
| Duplicate user records across IdPs | Medium | Enforce `email` uniqueness; implement deterministic user linking in OIDC backend |
| Institution isolation bypass via API parameter tampering | High | Always enforce tenant filter in queryset/manager; never trust client-provided `institution_id` for authz decisions |
| Performance degradation from per-request JWKS fetch | Medium | Cache JWKS in Redis/Django cache with TTL (e.g., 1 hour) |
| SAML complexity for institutions with ADFS/Shibboleth | Medium | Delegate to Keycloak IdP federation; Django never sees SAML directly |

### Integration with Other Modules

- **Institutions**: `User.institution` FK is mandatory for all non-superadmin users. Center-scoped roles (Director) use M2M `User.centers`.
- **Researchers**: A `Researcher` profile is separate from `User`. One `User` may have one `Researcher` profile per institution (or globally if we allow multi-institution researchers). The auth module must provide `request.user.researcher_profile` convenience.
- **Projects**: Project creation requires `User.institution_id` to match the project's target institution. The `IsProjectOwnerOrCoInvestigator` permission depends on auth module's group membership.
- **Audit**: Login, logout, failed login, role change, permission denied — all must emit events consumed by the `audit` app.
- **Documents/Signatures**: Digital signature actions require `firmar_documentos` permission, checked via auth module.

### Open Questions
1. **Keycloak deployment topology**: Will there be one shared Keycloak realm for all institutions, or one realm per institution? (Affects `institution_id` claim source and realm role naming.)
2. **SAML timeline**: Which institutions actually require SAML in the MVP? If none, SAML can be deferred.
3. **Researcher ↔ User cardinality**: Can one email/person belong to multiple institutions? If yes, `User` must be global and `Researcher` must be per-institution.
4. **allauth scope**: Should allauth support local social providers (Google, ORCID) or only username/password fallback?
5. **Superadmin origin**: Is the Superadmin always a local Django superuser, or also a Keycloak-managed role?

### Next Steps
1. **Decision needed**: Confirm Keycloak realm strategy (single shared vs. per-institution) before designing the OIDC backend.
2. **Decision needed**: Confirm whether a single user can belong to multiple institutions simultaneously.
3. Proceed to **sdd-propose** for the auth module to define the change scope and rollback plan.
4. After proposal approval, proceed to **sdd-spec** to write detailed requirements and Gherkin scenarios for:
   - OIDC login flow
   - Allauth fallback login
   - Role assignment and sync
   - Institution isolation enforcement
   - Permission denied audit events

---

**Status**: success
**Summary**: Auth module exploration complete. Recommended hybrid local-Keycloak approach with django-allauth fallback, Django-managed permissions, PostgreSQL RLS as defense-in-depth, and custom DRF permission classes for institution/center isolation.
**Artifacts**: `openspec/changes/auth/explore.md` | Engram `sdd/sigpi/auth-explore`
**Next**: sdd-propose
**Risks**: Keycloak downtime (mitigated by allauth), role sync lag, RLS migration complexity, JWT caching needed.
**Skill Resolution**: paths-injected — sdd-explore, sdd-phase-common
