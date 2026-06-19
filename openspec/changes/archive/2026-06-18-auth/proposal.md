# Proposal: SIGPI Authentication & Authorization Module

## Intent

SIGPI is a greenfield project with no auth code. This change establishes the entire authentication and authorization foundation: Keycloak 26 as primary SSO (OIDC/SAML), django-allauth as fallback, a custom User model supporting multi-institution operation, role-based permissions mapped to Django Groups, and PostgreSQL Row-Level Security as defense-in-depth for tenant isolation.

## Scope

### In Scope
- Custom Django User model with `keycloak_uuid`, `institution` FK, `centers` M2M, `role`, `auth_source`
- Keycloak 26 OIDC integration (single shared realm, `mozilla-django-oidc`)
- django-allauth fallback for local authentication when Keycloak is unavailable
- User model supporting "belongs to many institutions, operates in one" with session `institution_id`
- Role hierarchy (7 roles) mapped to Django Groups + Keycloak realm roles
- Custom DRF permission classes: `IsSameInstitution`, `IsCenterDirector`, `IsProjectOwnerOrCoInvestigator`, `IsAuditorReadOnly`
- Multi-tenancy middleware injecting `institution_id` into request context
- PostgreSQL RLS policies as safety net on tenant-scoped tables
- Audit event emission for login, logout, role change, permission denied
- Celery sync task for Keycloak→Django role reconciliation
- Frontend auth pages: login, logout, callback, institution-switch

### Out of Scope
- SAML federation configuration (Keycloak IdP federation is operational, not a code deliverable)
- Allauth social providers (Google, ORCID) — local username/password only for MVP
- Superadmin admin UI beyond Django admin
- Password policy beyond Keycloak defaults
- Account deletion flow (logical deletion only)

## Capabilities

### New Capabilities
- `keycloak-oidc-auth`: Keycloak OIDC login flow, token validation, user provisioning, role/claim mapping
- `allauth-local-auth`: Local username/password fallback auth with email-based user linking
- `user-multi-institution`: Custom User model, institution-scoped sessions, institution switching
- `role-permissions`: 7-role hierarchy, Django Group mapping, custom DRF permission classes
- `tenant-isolation`: Multi-tenancy middleware, TenantQuerySet manager, PostgreSQL RLS policies
- `auth-audit-events`: Auth event emission (login/logout/role change/permission denied) for audit module

### Modified Capabilities
None — this is the first module; no existing specs to modify.

## Approach

Hybrid Local-Keycloak (Approach B from exploration). Keycloak owns SSO/federation; Django owns application-level authorization. On first OIDC login, Django creates/updates a local User and copies claims (`institution_id`, `center_ids`, `role`). Django Groups and Permissions provide runtime authorization. A Celery beat task reconciles Keycloak role changes every 5 minutes. RLS policies enforce tenant isolation at the DB level as defense-in-depth.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/accounts/` | New | User model, OIDC backend, allauth config, role/permission definitions |
| `backend/apps/institutions/` | Modified | `institution_id` FK on User, institution-scoped querysets |
| `backend/config/settings/` | Modified | AUTHENTICATION_BACKENDS, DRF permission classes, OIDC/allauth config |
| `backend/config/middleware/` | New | Tenant middleware (injects `institution_id` into request) |
| `frontend/app/[locale]/auth/` | New | Login/logout/callback/institution-switch UI |
| `docker-compose.yml` | Modified | Keycloak 26 service, PostgreSQL RLS setup |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Keycloak downtime blocks enterprise login | High | allauth fallback; graceful degradation message |
| Role sync lag between Keycloak and Django | Medium | Event-driven webhooks + Celery beat every 5 min |
| Duplicate user records across IdPs | Medium | Enforce email uniqueness; deterministic linking in OIDC backend |
| RLS policies block migrations/admin | Medium | Separate DB user for migrations; superuser bypass |
| JWT UX friction from short access tokens | Medium | Silent refresh with refresh-token rotation in frontend |

## Rollback Plan

1. Disable Keycloak OIDC backend in `AUTHENTICATION_BACKENDS` — allauth local auth continues working
2. Remove RLS policies via migration (`DROP POLICY`); app-layer filtering remains active
3. Gateway-level redirect: route `/auth/*` to allauth-only flow if Keycloak is decommissioned
4. Custom User model is the first migration — no production data to lose on rollback

## Dependencies

- Keycloak 26 instance configured with SIGPI realm and client
- `mozilla-django-oidc` Python package
- `django-allauth` with `ACCOUNT_EMAIL_REQUIRED=True`, `ACCOUNT_UNIQUE_EMAIL=True`
- PostgreSQL 16 with RLS extension enabled
- Celery + Redis for background sync tasks

## Success Criteria

- [ ] OIDC login via Keycloak creates/updates local Django User with correct `keycloak_uuid`, `institution`, `role`
- [ ] Allauth local login works when Keycloak is unreachable
- [ ] Email uniqueness prevents duplicate users across IdPs
- [ ] 7-role hierarchy maps to Django Groups; DRF permission classes enforce access per role/institution
- [ ] RLS policies block cross-institution data access at the DB level
- [ ] Institution switching updates session `institution_id` and re-scopes all querysets
- [ ] All auth events emit audit records consumed by the `audit` app
- [ ] Test coverage ≥80% (strict TDD per project config)