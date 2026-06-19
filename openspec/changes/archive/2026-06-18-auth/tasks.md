# Tasks: Authentication & Authorization Module

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,400–2,600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Resolved — PR 1 of 5 (stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Custom User model, Role, InstitutionMembership + migrations + Docker infra | PR 1 | Foundation; ~320 lines; tests included |
| 2 | OIDC backend + local fallback + account linking | PR 2 | Depends on PR 1; ~430 lines; tests included |
| 3 | Auth API endpoints + tenant middleware + session config | PR 3 | Depends on PR 2; ~480 lines; tests included |
| 4 | DRF permissions + Celery role sync + audit events + RLS | PR 4 | Depends on PR 3; ~480 lines; tests included |
| 5 | Frontend auth pages + middleware + components | PR 5 | Depends on PR 3; ~570 lines; independent of PR 4 |

## Phase 1: Infrastructure & Data Model

- [x] 1.1 **[infra]** Add Keycloak 26 service to `docker-compose.yml` with realm import from `infra/keycloak/realm-export.json`. Add Redis service for session backend. (~40 lines)
- [x] 1.2 **[model]** Create `backend/apps/accounts/models.py` with `User(AbstractUser)` — UUID PK, `keycloak_uuid`, `auth_source`, `email` unique. Create `Role` model (name, keycloak_role_name, level). Create `InstitutionMembership` join table with `centers` M2M, `is_primary`, UniqueConstraint(user, institution). (~130 lines)
- [x] 1.3 **[migration]** Create `migrations/0001_initial.py` (User, Role, InstitutionMembership). Create `migrations/0002_seed_roles.py` data migration (7 roles). Set `AUTH_USER_MODEL = 'accounts.User'` in `backend/config/settings/base.py`. (~80 lines)
- [x] 1.4 **[test]** Write model tests: User creation, email uniqueness, membership constraints, primary membership validation, role hierarchy levels. (~100 lines)

## Phase 2: Authentication Backends

- [x] 2.1 **[backend]** Create `backend/apps/accounts/backends.py` — custom `OIDCAuthenticationBackend` extending `mozilla_django_oidc`. Implement `create_user()` / `update_user()`: extract claims (`sub`, `email`, `sigpi_institution_id`, `sigpi_center_ids`, `sigpi_role`), lookup by `keycloak_uuid` or email+verified, create/update User + InstitutionMembership, sync Django Groups. (~150 lines)
- [x] 2.2 **[backend]** Implement local fallback in `backend/apps/accounts/views.py` `login_view`: check Keycloak health (2s timeout), if unreachable authenticate via allauth `ModelBackend`, else return 503. Implement account linking logic: auto-link if email verified, return 409 if unverified. (~120 lines)
- [x] 2.3 **[config]** Configure `AUTHENTICATION_BACKENDS` (OIDC → allauth → ModelBackend), OIDC settings (`OIDC_RP_*`, `OIDC_OP_*`), session settings (Redis engine, cookie security), and rate limiting (`django-ratelimit` on login). (~80 lines)
- [x] 2.4 **[test]** Write backend tests: mock Keycloak token responses (first login, returning login, email linking verified/unverified, claim update, group sync). Test local fallback when KC is down. (~150 lines)

## Phase 3: Auth API & Tenant Middleware

- [x] 3.1 **[middleware]** Create `backend/config/middleware/tenant.py` — `TenantMiddleware` (inject `institution_id` from session, load `active_membership`, return 400 if tenant-required endpoint has no institution). `TenantRLSMiddleware` (SET LOCAL `sigpi.institution_id` per request). (~80 lines)
- [x] 3.2 **[api]** Create `backend/apps/accounts/serializers.py` — `LoginSerializer`, `UserSerializer`, `MembershipSerializer`, `InstitutionSwitchSerializer`. Create `views.py` — `login_view`, `logout_view`, `switch_institution_view`, `me_view`, `keycloak_status_view`. Create `urls.py` with `/auth/` routes. (~200 lines)
- [x] 3.3 **[config]** Register `TenantMiddleware` and `TenantRLSMiddleware` in `MIDDLEWARE` list. Configure `SESSION_ENGINE`, cookie settings, CSRF settings in `base.py`. (~40 lines)
- [x] 3.4 **[test]** Write API tests: login (OIDC redirect, local auth, 503 when KC up), logout, institution switch (valid/invalid membership), `/auth/me/` response shape, 400 when no active institution. (~150 lines)

## Phase 4: Permissions, Sync & Tenant Isolation

- [x] 4.1 **[permissions]** Create `backend/apps/accounts/permissions.py` — `IsSameInstitution`, `IsCenterDirector`, `IsProjectOwnerOrCoInvestigator`, `IsAuditorReadOnly` DRF permission classes. Create `managers.py` — `TenantScopedQuerySet.for_tenant(request)`. (~100 lines)
- [x] 4.2 **[tasks]** Create `backend/apps/accounts/tasks.py` — `sync_keycloak_roles` Celery task: paginate Keycloak Admin API (100 users/run), map client roles → Django Groups, diff and update, emit audit events on role change. Register beat schedule (5 min) in `backend/config/celery.py`. (~130 lines)
- [x] 4.3 **[audit]** Create audit event emitter: emit LOGIN, LOGOUT, INSTITUTION_SWITCH, ROLE_CHANGE, PERMISSION_DENIED events with user, timestamp, IP, auth_source, institution. Wire into views and tasks. (~60 lines)
- [x] 4.4 **[rls]** Create `sql/rls_policies.sql` — enable RLS on tenant-scoped tables, create `tenant_isolation` and `superadmin_bypass` policies. Wrap in Django `RunSQL` migration. (~90 lines)
- [x] 4.5 **[test]** Write permission tests (same institution, cross-institution 403, center director, auditor read-only). Write Celery sync test (mock KC Admin API, verify group diff). Write RLS integration test (cross-tenant query returns empty). (~200 lines)

## Phase 5: Frontend Auth Integration

- [x] 5.1 **[frontend]** Create `frontend/lib/api.ts` (API client: login, logout, switchInstitution, getMe, getCSRFToken) and `frontend/store/auth.ts` (Zustand store: user, activeInstitution, institutions, roles, centers, isAuthenticated, isLoading). (~330 lines)
- [x] 5.2 **[frontend]** Create `frontend/app/login/page.tsx` (SSO button + local form), `app/logout/page.tsx` (logout handler), `app/me/page.tsx` (profile), `app/switch-institution/page.tsx` (institution switch), `app/layout.tsx` (root layout). Create `frontend/components/LoginForm.tsx`, `OIDCButton.tsx`, `InstitutionSelector.tsx`, `UserProfileCard.tsx`, `ProtectedRoute.tsx`. (~320 lines)
- [x] 5.3 **[frontend]** Create `frontend/middleware.ts` — check session cookie, redirect to `/login` if absent on protected routes, attach institution context header. (~70 lines)
- [x] 5.4 **[test]** Write frontend tests: 9 test files, 64 tests total — LoginForm (6), InstitutionSelector (5), OIDCButton (2), ProtectedRoute (3), UserProfileCard (3), LoginPage (4), Middleware (9), api.ts (13), auth store (19). All pass. Coverage: 95.7% stmts, 78.4% branches, 95.3% funcs, 98.1% lines.
