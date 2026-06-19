# Design: SIGPI Authentication & Authorization Module

## Technical Approach

Hybrid Local-Keycloak auth implementing Clean Architecture in Django. Keycloak 26 owns identity federation (OIDC); Django owns application-level authorization. A custom User model with `InstitutionMembership` join table supports multi-institution operation. PostgreSQL RLS provides defense-in-depth tenant isolation. Celery reconciles Keycloak→Django roles every 5 minutes.

Maps to proposal's Approach B: Keycloak issues OIDC tokens → `mozilla-django-oidc` validates → custom backend creates/updates local User → Django session + Groups provide runtime authz → RLS blocks cross-tenant leaks at DB level.

## Architecture Decisions

| Decision | Option A | Option B | Tradeoff | Choice |
|----------|----------|----------|----------|--------|
| OIDC library | `mozilla-django-oidc` | `django-oauth-toolkit` | mozilla: mature OIDC RP, less config; oauth-toolkit: OP not RP | **mozilla-django-oidc** — we need RP (client), not OP |
| Multi-tenancy model | Shared DB + `institution_id` FK | django-tenants schemas | Shared DB: simpler, RLS-compatible; schemas: stronger isolation but complex migrations | **Shared DB + RLS** — matches proposal, RLS adds safety |
| User-institution relation | FK on User | Join table `InstitutionMembership` | FK: single institution only; join: multi-institution with per-institution role | **InstitutionMembership join table** — spec requires multi-institution |
| Active institution storage | Session variable | DB column on User | Session: lightweight, per-browser; DB: persists across devices | **Session variable** — soft reset per spec, simpler |
| Superadmin auth source | Keycloak | Local-only | Keycloak: unified but risky if KC down; local: always available | **Local-only** — superadmin MUST survive Keycloak outages |
| Account linking | Auto if email verified | Always manual | Auto: better UX; manual: safer | **Auto if verified, manual if not** — balanced |
| Role sync mechanism | Webhook from Keycloak | Celery beat polling | Webhook: real-time but KC config complex; polling: 5-min lag but reliable | **Celery beat (5 min)** + webhook as future enhancement |
| Session backend | Django signed cookies | Redis-backed sessions | Cookies: stateless but large; Redis: server-side, revocable | **Redis-backed** — need revocation, institution switch |

## Clean Architecture Layers

```
Entities (pure business rules, framework-free):
  ├── User (email, keycloak_uuid, auth_source)
  ├── InstitutionMembership (user, institution, role, is_primary)
  ├── Role (name, level, keycloak_role_name)
  └── Permission (codename, description)

Use Cases (application-specific orchestration):
  ├── AuthenticateViaOIDC (validate token → create/update user → sync claims)
  ├── AuthenticateLocally (verify credentials → issue session)
  ├── SwitchInstitution (validate membership → update session)
  ├── SyncRoles (fetch KC users → reconcile Django groups)
  └── LinkAccounts (match email → verify → merge identities)

Interface Adapters (translate between use cases and externals):
  ├── OIDCAuthenticationBackend (mozilla-django-oidc → AuthenticateViaOIDC)
  ├── TenantMiddleware (request.institution_id from session)
  ├── DRF Permission Classes (IsSameInstitution, IsCenterDirector, etc.)
  ├── InstitutionScopedQuerySet (auto-filter by institution_id)
  └── AuditEventEmitter (login/logout/role-change → audit app)

Frameworks & Drivers (outermost layer, glue):
  ├── Django settings (AUTHENTICATION_BACKENDS, OIDC config)
  ├── Keycloak realm/client configuration
  ├── PostgreSQL RLS policies
  ├── Celery beat schedule (role_sync_task)
  └── Redis session backend
```

**Dependency rule**: Entities know nothing about Django. Use Cases define interfaces (protocols) that adapters implement. DRF views depend on use cases, never on Keycloak SDK directly.

## Data Model

### User (extends `AbstractUser`)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `UUIDField` | PK, default `uuid4` | UUID for external safety |
| `email` | `EmailField` | `unique=True`, `db_index` | Global unique, login identifier |
| `keycloak_uuid` | `UUIDField` | `unique=True, null=True, blank=True` | Set on first OIDC login |
| `auth_source` | `CharField(20)` | `choices=[('keycloak','Keycloak'),('local','Local')]` | Tracks origin |
| `is_active` | `BooleanField` | `default=True` | Soft-disable |
| `is_superuser` | `BooleanField` | `default=False` | Local-only superadmin |
| `last_login` | `DateTimeField` | auto | Updated on each login |
| `date_joined` | `DateTimeField` | auto_now_add | |

**Indexes**: `(email)` unique, `(keycloak_uuid)` unique partial WHERE NOT NULL.

### InstitutionMembership

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK |
| `user` | `FK(User)` | `related_name='memberships'` |
| `institution` | `FK(Institution)` | `related_name='memberships'` |
| `role` | `FK(Role)` | |
| `centers` | `M2M(ResearchCenter)` | `blank=True` |
| `is_primary` | `BooleanField` | `default=False` |
| `is_active` | `BooleanField` | `default=True` |
| `joined_at` | `DateTimeField` | `auto_now_add` |

**Constraints**: `UniqueConstraint(user, institution)`, `CheckConstraint` — at most one `is_primary=True` per user (enforced in `save()` + DB partial unique index).

### Role

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UUIDField` | PK |
| `name` | `CharField(50)` | `unique=True` |
| `keycloak_role_name` | `CharField(100)` | `blank=True` |
| `level` | `IntegerField` | Hierarchy rank (1=superadmin, 7=auditor) |

**Seed data**: 7 fixed roles loaded via data migration.

### Permission

Uses Django's built-in `auth.Permission` — no custom model needed. Map Keycloak client roles to Django permissions via `keycloak_role_name` on Role.

## Sequence Flows

### OIDC Login Flow

```
Browser → Django /auth/login/?provider=keycloak
  → 302 redirect to Keycloak authorize endpoint
  → User authenticates at Keycloak
  → 302 redirect to Django /auth/callback/?code=...
  → Django exchanges code for tokens at Keycloak token endpoint
  → mozilla-django-oidc validates id_token (signature, issuer, audience, exp)
  → OIDCAuthenticationBackend.create_user() or update_user():
      1. Extract claims: sub, email, email_verified, preferred_username,
         sigpi_institution_id, sigpi_center_ids, sigpi_role
      2. Lookup User by keycloak_uuid OR (email + email_verified=True)
      3. If found: update claims, sync membership
      4. If not found + email match + !verified: return 409 (manual linking)
      5. If not found + no match: create User + InstitutionMembership
      6. Sync Django Groups from role claim
  → Create Django session (Redis-backed) with institution_id
  → Emit audit event: LOGIN
  → 302 redirect to frontend dashboard
```

### Local Fallback Login

```
Browser → POST /auth/login/ {provider: "local", email, password}
  → Django checks Keycloak health (GET /health/ready, 2s timeout)
  → If KC healthy: return 503 "Use SSO" (local only when KC down)
  → If KC unreachable: authenticate via allauth ModelBackend
  → Validate credentials against local User (auth_source='local')
  → Create session, emit audit event: LOGIN
  → Return 200 + session cookie + CSRF token
```

### Institution Switch Flow

```
Browser → POST /auth/switch-institution/ {institution_id: UUID}
  → TenantMiddleware validates: user.memberships.filter(institution_id=...)
  → If membership exists and is_active:
      1. Update request.session['institution_id']
      2. Update request.session['active_role'] (from membership.role)
      3. Emit audit event: INSTITUTION_SWITCH
      4. Return 200 {user, active_institution, role, centers}
  → If no membership: return 403 "You do not belong to this institution"
```

### Role Sync Flow (Celery Beat — every 5 min)

```
Celery Beat → sync_keycloak_roles task
  → For each User with keycloak_uuid IS NOT NULL:
      1. Call Keycloak Admin API: GET /users/{uuid}/role-mappings/clients/{client_id}
      2. Map Keycloak client roles → Django Group names
      3. Diff current user.groups vs expected groups
      4. Add/remove groups as needed
      5. If role changed: emit audit event: ROLE_CHANGE
  → Rate-limited: batch of 100 users per run, cursor-based pagination
```

## Component Design

### TenantMiddleware

```python
# backend/config/middleware/tenant.py
class TenantMiddleware:
    """Injects institution_id from session into request context.
    Sets request.institution_id and request.active_membership.
    Returns 400 if endpoint requires tenant but none is active."""

    TENANT_REQUIRED_PREFIXES = ['/api/projects/', '/api/researchers/', ...]

    def __call__(self, request):
        request.institution_id = request.session.get('institution_id')
        request.active_membership = None
        if request.user.is_authenticated and request.institution_id:
            request.active_membership = (
                InstitutionMembership.objects
                .select_related('role')
                .filter(user=request.user, institution_id=request.institution_id, is_active=True)
                .first()
            )
        # Enforce tenant requirement for protected endpoints
        if self._requires_tenant(request.path) and not request.institution_id:
            return JsonResponse({"detail": "Active institution required."}, status=400)
        return self.get_response(request)
```

### Custom DRF Permission Classes

```python
# backend/apps/accounts/permissions.py
class IsSameInstitution(BasePermission):
    """User's active institution must match the object's institution."""
    def has_object_permission(self, request, view, obj):
        return request.institution_id == getattr(obj, 'institution_id', None)

class IsCenterDirector(BasePermission):
    """User must be Center Director in the object's center."""
    def has_object_permission(self, request, view, obj):
        membership = request.active_membership
        if not membership or membership.role.name != 'center_director':
            return False
        return obj.center_id in membership.centers.values_list('id', flat=True)

class IsProjectOwnerOrCoInvestigator(BasePermission):
    """User must be the project PI or an authorized co-investigator."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        return (obj.lead_researcher.user == user or
                obj.members.filter(user=user, role='co_investigator').exists())

class IsAuditorReadOnly(BasePermission):
    """Auditors get read-only access across all institutions."""
    def has_permission(self, request, view):
        membership = request.active_membership
        if membership and membership.role.name == 'auditor':
            return request.method in SAFE_METHODS
        return False
```

### TenantScopedQuerySet (Manager)

```python
# backend/apps/accounts/managers.py
class TenantScopedQuerySet(models.QuerySet):
    """Auto-filters by institution_id when request context is available."""
    def for_tenant(self, request):
        if request.institution_id and not request.user.is_superuser:
            return self.filter(institution_id=request.institution_id)
        return self
```

### Authentication Backend Chain

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'mozilla_django_oidc.auth.OIDCAuthenticationBackend',  # Primary: Keycloak OIDC
    'allauth.account.auth_backends.AuthenticationBackend',  # Fallback: local
    'django.contrib.auth.backends.ModelBackend',            # Django admin
]
```

Order matters: OIDC is tried first for OIDC callback URLs; allauth/ModelBackend handle local login endpoint.

## Keycloak Integration Design

### Realm Configuration

- **Realm**: `sigpi` (single shared realm for all institutions)
- **Client**: `sigpi-app` (confidential client, standard flow enabled)
- **Client roles**: One per SIGPI role (`sigpi_superadmin`, `sigpi_admin`, `sigpi_center_director`, `sigpi_researcher`, `sigpi_coinvestigator`, `sigpi_committee`, `sigpi_auditor`)
- **Groups**: Per-institution groups (`/institutions/{inst_id}/researchers`, etc.)
- **User attributes**: `sigpi_institution_id`, `sigpi_center_ids` (comma-separated)
- **Mappers**: Custom protocol mappers inject `sigpi_institution_id`, `sigpi_center_ids`, `sigpi_role` into the id_token and userinfo response

### Token Claims Expected

```json
{
  "sub": "kc-uuid",
  "email": "user@example.com",
  "email_verified": true,
  "preferred_username": "jdoe",
  "sigpi_institution_id": "uuid-of-institution",
  "sigpi_center_ids": ["uuid-center-1", "uuid-center-2"],
  "sigpi_role": "researcher",
  "realm_access": { "roles": ["sigpi_researcher"] }
}
```

### Sync Strategy

- **Primary**: Celery beat task `sync_keycloak_roles` runs every 5 minutes
- **Batching**: 100 users per run, paginated via Keycloak Admin API (`first` + `max`)
- **Idempotent**: Compares current Django groups vs expected, only diffs
- **Error handling**: Logs failures, retries individual users on next run
- **Future**: Keycloak webhook (Event Listener SPI) for real-time sync — not in MVP

## PostgreSQL RLS Design

### Strategy

- Application DB user: `sigpi_app` (no superuser, RLS enforced)
- Migration DB user: `sigpi_migrator` (bypasses RLS via `BYPASSRLS` attribute)
- Superadmin Django user: queries via `sigpi_app` but sets `SET LOCAL sigpi.bypass_rls = true` in a context manager
- Session variable: `sigpi.institution_id` set per-request via middleware

### RLS Policies

Applied to all tenant-scoped tables (projects, researchers, progress_reports, budgets, etc.):

```sql
-- Enable RLS on tenant-scoped table
ALTER TABLE projects_project ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their institution's rows
CREATE POLICY tenant_isolation ON projects_project
    USING (institution_id = current_setting('sigpi.institution_id')::uuid);

-- Policy: superadmin bypass (checks session variable)
CREATE POLICY superadmin_bypass ON projects_project
    USING (current_setting('sigpi.bypass_rls', true)::bool = true);
```

### Django Integration

```python
# backend/config/middleware/tenant.py (addition)
class TenantRLSMiddleware:
    """Sets PostgreSQL session variable for RLS on each request."""
    def __call__(self, request):
        if request.institution_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL sigpi.institution_id = %s",
                    [str(request.institution_id)]
                )
        if request.user.is_superuser:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL sigpi.bypass_rls = true")
        return self.get_response(request)
```

**Note**: `SET LOCAL` scopes to the current transaction. Combined with Django's `ATOMIC_REQUESTS=True` or explicit `transaction.atomic()` blocks to ensure RLS applies per-request.

### Tables with RLS

All tables with `institution_id` column: `projects_project`, `researchers_researcher`, `progress_progressreport`, `budgets_budget`, `calls_call`, `products_researchproduct`, `documents_document`, `institutions_researchcenter`, `institutions_researchgroup`, `institutions_researchline`.

**Excluded**: `accounts_user` (global), `accounts_role` (global), `auth_*` (Django internals), `institutions_institution` (global catalog).

## API Design (Expanded)

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login/` | POST | None | Initiate login (keycloak redirect or local auth) |
| `/auth/logout/` | POST | Session | Destroy session, clear cookies |
| `/auth/callback/` | GET | None | OIDC callback (handled by mozilla-django-oidc) |
| `/auth/switch-institution/` | POST | Session | Switch active institution |
| `/auth/me/` | GET | Session | Current user profile + memberships |
| `/auth/link-account/` | POST | Session | Confirm manual account linking |
| `/auth/keycloak-status/` | GET | None | Health check for Keycloak availability |

### Request/Response Details

**POST `/auth/login/`** (local):
```json
// Request
{"provider": "local", "email": "user@example.com", "password": "..."}
// Response 200
{"user": {"id": "uuid", "email": "..."}, "csrf_token": "..."}
// Response 503 (KC is up, use SSO)
{"detail": "SSO available. Use Keycloak login.", "redirect_url": "/auth/login/?provider=keycloak"}
```

**POST `/auth/switch-institution/`**:
```json
// Request
{"institution_id": "uuid"}
// Response 200
{
  "user": {"id": "uuid", "email": "..."},
  "active_institution": {"id": "uuid", "name": "..."},
  "role": {"name": "researcher", "level": 4},
  "centers": [{"id": "uuid", "name": "..."}]
}
```

**GET `/auth/me/`**:
```json
// Response 200
{
  "id": "uuid",
  "email": "user@example.com",
  "auth_source": "keycloak",
  "is_superuser": false,
  "memberships": [
    {
      "institution": {"id": "uuid", "name": "Universidad X"},
      "role": {"name": "researcher", "level": 4},
      "centers": [{"id": "uuid", "name": "Centro A"}],
      "is_primary": true
    }
  ],
  "active_institution_id": "uuid",
  "active_role": "researcher"
}
```

## Security Design

### Threat Model

| Threat | Severity | Mitigation |
|--------|----------|------------|
| OIDC token forgery | Critical | Validate signature, issuer, audience, expiration via `mozilla-django-oidc` |
| Session hijacking | High | `HttpOnly`, `Secure`, `SameSite=Lax` cookies; Redis session with short TTL |
| Cross-tenant data leak | Critical | RLS policies + app-layer `TenantScopedQuerySet` (defense-in-depth) |
| Brute-force login | Medium | Rate limiting via `django-ratelimit` on `/auth/login/` (5 attempts/min/IP) |
| Privilege escalation | High | Role hierarchy enforced by DRF permissions + Django Groups; superadmin local-only |
| Keycloak compromise | Medium | Fallback to local auth; Keycloak admin API access restricted to service account |
| CSRF attacks | Medium | Django CSRF middleware + `SameSite=Lax` cookies |
| Account takeover via linking | Medium | Manual confirmation for unverified emails; audit trail on all link events |
| SQL injection via RLS bypass | Low | Parameterized queries only; `SET LOCAL` uses prepared statements |

### Cookie Configuration

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True       # HTTPS only in production
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800         # 8 hours
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'  # Redis
SESSION_CACHE_ALIAS = 'default'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| **Unit** | OIDC backend `create_user`/`update_user` logic | Mock Keycloak token responses with `responses` library; test claim extraction, account linking, group sync |
| **Unit** | Permission classes (`IsSameInstitution`, `IsCenterDirector`) | Create fixtures with users in different institutions/roles; assert allow/deny |
| **Unit** | `TenantScopedQuerySet.for_tenant()` | Mock request with `institution_id`; verify queryset filtering |
| **Unit** | Role hierarchy enforcement | Test that level comparison blocks lower roles from higher actions |
| **Integration** | Full OIDC login flow | `pytest-django` + mocked Keycloak endpoints; verify User creation, session, audit event |
| **Integration** | Local fallback when KC is down | Mock KC health check returning 503; verify local auth proceeds |
| **Integration** | Institution switch | POST switch endpoint; verify session update, subsequent queries scoped correctly |
| **Integration** | Celery role sync task | Mock Keycloak Admin API; verify Django groups updated, audit events emitted |
| **Integration** | RLS policies | Use test DB with RLS enabled; create users in different institutions; verify cross-tenant queries return empty |
| **E2E** | Login → dashboard → switch institution | Playwright: navigate to login, authenticate (mocked KC), verify dashboard loads, switch institution, verify data reloads |
| **E2E** | Permission denied flows | Playwright: login as researcher, attempt admin action, verify 403 UI |

### Test Infrastructure

- **Keycloak mock**: `responses` library for HTTP mocking of KC endpoints; factory-boy for User/Membership fixtures
- **RLS testing**: Dedicated test DB with RLS policies applied; use `SET ROLE sigpi_app` to simulate app user
- **Fixtures**: `conftest.py` with `@pytest.fixture` for: `user_factory`, `membership_factory`, `institution_factory`, `role_factory`
- **Coverage target**: ≥80% per `openspec/config.yaml` `coverage_floor`

## Frontend Integration

### Next.js Auth Architecture

```
frontend/
├── app/[locale]/
│   ├── (auth)/
│   │   ├── login/page.tsx          # Login page (KC redirect + local form)
│   │   ├── callback/page.tsx       # OIDC callback handler (redirect to dashboard)
│   │   └── layout.tsx              # Unauthenticated layout
│   └── (dashboard)/
│       ├── layout.tsx              # Authenticated layout (checks session)
│       └── ...
├── middleware.ts                    # Next.js middleware: redirect unauthenticated to /login
├── lib/
│   ├── auth.ts                     # Auth API client (login, logout, switchInstitution, me)
│   └── session.ts                  # Session state management (Zustand or React Context)
└── components/
    └── auth/
        ├── LoginForm.tsx           # Local login form
        ├── InstitutionSwitcher.tsx # Dropdown to switch active institution
        └── AuthGuard.tsx           # Client-side auth check wrapper
```

### Session Management

- **No JWT in frontend**: Django session cookie (HttpOnly) is the session mechanism
- **Next.js middleware** (`middleware.ts`): checks for session cookie presence; redirects to `/login` if absent
- **API calls**: `fetch('/api/...')` with `credentials: 'include'` to send session cookie
- **CSRF**: Read CSRF cookie, send as `X-CSRFToken` header on POST/PUT/DELETE
- **Institution context**: Zustand store holds `activeInstitution`, `activeRole`, `centers`; updated on switch

### Key Frontend Flows

1. **Login**: User clicks "Login with SSO" → `window.location` redirects to Django `/auth/login/?provider=keycloak` → KC → callback → dashboard
2. **Local login**: User enters email/password → `POST /auth/login/` → on success, `router.push('/dashboard')`
3. **Institution switch**: User selects institution in dropdown → `POST /auth/switch-institution/` → Zustand store updates → `router.refresh()` to reload server components
4. **Session check**: On app load, `GET /auth/me/` → if 401, redirect to login; if 200, populate Zustand store

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/accounts/models.py` | Create | User, InstitutionMembership, Role models |
| `backend/apps/accounts/managers.py` | Create | TenantScopedQuerySet manager |
| `backend/apps/accounts/backends.py` | Create | Custom OIDC backend extending mozilla-django-oidc |
| `backend/apps/accounts/permissions.py` | Create | DRF permission classes |
| `backend/apps/accounts/serializers.py` | Create | User, Membership, Login serializers |
| `backend/apps/accounts/views.py` | Create | Auth API views (login, logout, switch, me) |
| `backend/apps/accounts/urls.py` | Create | Auth URL routing |
| `backend/apps/accounts/tasks.py` | Create | Celery task: sync_keycloak_roles |
| `backend/apps/accounts/admin.py` | Create | Django admin registration for User, Role |
| `backend/apps/accounts/migrations/0001_initial.py` | Create | Initial migration: User, Membership, Role |
| `backend/apps/accounts/migrations/0002_seed_roles.py` | Create | Data migration: seed 7 roles |
| `backend/apps/accounts/tests/` | Create | Test suite (unit + integration) |
| `backend/config/middleware/tenant.py` | Create | TenantMiddleware + TenantRLSMiddleware |
| `backend/config/settings/base.py` | Modify | AUTHENTICATION_BACKENDS, OIDC config, session config |
| `backend/config/settings/base.py` | Modify | MIDDLEWARE: add TenantMiddleware, TenantRLSMiddleware |
| `backend/config/celery.py` | Modify | Add beat schedule for role sync |
| `frontend/app/[locale]/(auth)/login/page.tsx` | Create | Login page |
| `frontend/app/[locale]/(auth)/callback/page.tsx` | Create | OIDC callback handler |
| `frontend/middleware.ts` | Create | Next.js auth middleware |
| `frontend/lib/auth.ts` | Create | Auth API client |
| `frontend/lib/session.ts` | Create | Session state management |
| `frontend/components/auth/LoginForm.tsx` | Create | Local login form component |
| `frontend/components/auth/InstitutionSwitcher.tsx` | Create | Institution switcher component |
| `frontend/components/auth/AuthGuard.tsx` | Create | Client-side auth guard |
| `sql/rls_policies.sql` | Create | RLS policy definitions (applied via Django migration) |
| `docker-compose.yml` | Modify | Add Keycloak 26 service with realm import |

## Migration / Rollout

### Phase 1: Foundation (no existing data)
1. Custom User model as first migration — `AUTH_USER_MODEL = 'accounts.User'`
2. Role seed migration (7 roles)
3. RLS policies via `RunSQL` in migration (after all tenant-scoped tables exist)

### Phase 2: Keycloak Setup
1. Docker Compose: Keycloak 26 with realm JSON import
2. Client configuration: `sigpi-app` with OIDC standard flow
3. Protocol mappers for SIGPI custom claims

### Phase 3: Frontend
1. Auth pages (login, callback)
2. Next.js middleware for route protection
3. Institution switcher

### Rollback Plan
1. Disable OIDC backend: remove from `AUTHENTICATION_BACKENDS` → allauth continues
2. Drop RLS policies via migration → app-layer filtering remains active
3. Custom User model is migration 0001 — no data loss on rollback (greenfield)

## Open Questions

- [ ] Keycloak realm JSON import: should we version-control the realm export in `infra/keycloak/`?
- [ ] Rate limiting library: `django-ratelimit` vs `django-axes` for brute-force protection?
- [ ] Should the `InstitutionMembership.centers` M2M use a through table for future metadata (e.g., `joined_center_at`)?
- [ ] RLS policy for cross-institution collaboration projects (projects spanning 2+ institutions)?
- [ ] Keycloak service account credentials management: env vars vs Docker secrets?
