# Exploration: Frontend Institutions Module (SIGPI §6.1)

## Current State

### Backend `apps.institutions` — COMPLETE (archived 2026-06-19; 245 tests, 96.5% coverage)

The real 6-entity hierarchy (verified in `backend/apps/institutions/models.py`):

```
Institution (root, no RLS)
└── Sede
    └── Facultad (optional sede; can hang directly on institution)
        └── ResearchCenter (flexible parent: institution | sede | facultad)
            └── ResearchGroup
                └── ResearchLine (leaf)
```

**Prompt corrections (verified against code, not assumed):**
- The prompt's "Ministry → ViceMinistry → Entity → Group → Institution → Headquarter" does NOT exist anywhere in the codebase. The hierarchy is the research structure from SPEC §6.1 (Institution/Sede/Facultad/ResearchCenter/ResearchGroup/ResearchLine).
- SPEC §6.2 is "Módulo de autenticación y seguridad" (auth) — the institutions module is §6.1.
- "Institution has completeness validation" does NOT exist in `apps.institutions` (the only "completeness" hit is a test name). If required, it is a NEW backend capability, out of scope for a pure frontend change.
- "Institution ↔ User affiliation" = `InstitutionMembership` in `apps/accounts/models.py` (join table User↔Institution with Role + centers M2M). Already consumed by the frontend auth store (`memberships`, `centers`).

**API surface** (all under `/api/`, mounted in `backend/config/urls.py`):
- `/institutions/` GET/POST, `/institutions/{pk}/` GET/PATCH/DELETE — superadmin writes, any authenticated user reads (no RLS on root table)
- `/institutions/{pk}/sedes/`, `/institutions/{pk}/facultades/`, `/institutions/{pk}/centers/` (+ detail) — writes require level ≤ 2 (institution admin+)
- `/centers/{pk}/groups/`, `/groups/{pk}/lines/` (+ detail) — writes require level ≤ 3 (center director+)
- Lifecycle POST actions on every entity: `/{entity}/{pk}/activate|deactivate|archive/` — 409 `"Deactivate or archive children first."` when active children block; `archived` is TERMINAL
- Serializers expose: `id`, `institution`, `institution_name`, `code`, `name`, `description`, `status`, `is_active`, `created_at`, `updated_at` (+ `sede`/`facultad`/`contact_email`/`contact_phone` where applicable). Parent FKs are read-only on write (injected from URL).

**Tenant scoping (important):** `TenantMiddleware` (`backend/config/middleware/tenant.py`) requires a session `institution_id` for `/api/institutions/`, `/api/centers/`, `/api/groups/`, `/api/lines/` for non-superusers. The frontend's `X-Institution-ID` header is NOT read by the backend — session scoping (set via `POST /auth/switch-institution/`) is the source of truth. Superusers bypass the tenant requirement.

### Frontend — MVP shipped (frontend-mvp archived; 3 PRs)

- Routes: `/dashboard`, `/projects`, `/projects/new`, `/projects/[id]`, `/projects/[id]/advances`, `/login`, `/logout`, `/me`, `/switch-institution`. **No institutions pages exist yet.**
- Feature module pattern: `features/{module}/{types,schemas,queries,mutations,fsm,FsmActionBar}.ts(x)`
- `lib/api.ts`: typed fetch wrapper (CSRF token, credentials include, `institutionId` option), `lib/errors.ts` (normalizes `{detail}`/field errors → `ApiError`), `lib/query-keys.ts` (institution-scoped key factories), `lib/query-client.ts`
- `store/auth.ts` (Zustand + persist): `user`, `activeInstitution`, `institutions`, `roles`, `centers`; `switchInstitution()` clears the whole query cache on switch
- shadcn/ui primitives: button, card, dialog, alert-dialog, dropdown-menu, input, label, select, sheet, skeleton, sonner, switch, tabs, separator, badge
- shared: StatusBadge, ConfirmDialog, EmptyState, Skeleton, Toaster; shell: AuthenticatedLayout, Sidebar (role-filtered nav), Topbar, Drawer, RoleGuard
- Testing: MSW handlers + fixtures; Jest coverage ≥80% floor; ESLint + `tsc --noEmit` green per PR
- **The projects wizard already consumes institutions endpoints**: `useCenters` → `/api/institutions/{id}/centers/`, `useGroups` → `/api/centers/{id}/groups/`, `useLines` → `/api/groups/{id}/lines/` (via `HierarchyNode` type) — so the institutions API is partially exercised by the frontend today.

## What the UI Needs (SPEC §6.1)

1. **Pages/components**: institutions list + hierarchy tree, detail views per entity level, create/edit forms for all 6 entities, lifecycle action bars, institution switcher integration (exists).
2. **Hierarchy in the UI**: a tree view (Institution → Sede → Facultad → Center → Group → Line) with expand/collapse, status badges, per-node actions. No tree component exists in deps — custom recursive component required.
3. **Reusable patterns**: feature folder structure, query key factories, MSW fixtures, FsmActionBar, ConfirmDialog, StatusBadge, dependent selects (already used in wizard), AuthenticatedLayout + RoleGuard.
4. **shadcn/ui components**: Button, Dialog, AlertDialog (archive confirm), Select (parent selection), Badge, Card, Input, Label, Tabs, DropdownMenu, Skeleton, Sheet. New: tree/collapsible primitive (custom, or extend existing with chevrons).
5. **API integration**: `features/institutions/queries.ts` + `mutations.ts` following the projects pattern; add `institutions` key factory to `query-keys.ts`; institution-scoped invalidation.
6. **MVP vs future**: MVP = tree + CRUD + lifecycle + role guards. Future = drag-and-drop re-parenting (backend has no move API today), completeness indicators (backend has none), bulk import, deep-link to a specific center from projects module.
7. **Business rules affecting frontend**: role-gated writes (superadmin > admin > director); 409 on deactivate/archive with active children; archived is terminal (no reactivate); `(institution, code)` uniqueness → duplicate code errors surface as 409 field errors; parent-FK read-only (parent chosen via URL nesting, not form).

## Affected Areas

- `frontend/app/institutions/**` — new routes: list/tree, entity detail, create/edit (NEW)
- `frontend/features/institutions/**` — types, schemas, queries, mutations, fsm, components (NEW)
- `frontend/lib/query-keys.ts` — add `institutions` key factory
- `frontend/mocks/handlers.ts` + `frontend/fixtures/*` — MSW fixtures for all 6 entities
- `frontend/components/shell/Sidebar.tsx` — add "Estructura institucional" nav item (role-gated)
- `frontend/components/ui/` — add tree/collapsible primitive if not using a dependency
- Backend: NO changes expected — API is complete for this module

## Approaches

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| 1 | **Read-first slices** (PR1: tree + institution CRUD; PR2: Sede/Facultad/Center CRUD; PR3: Group/Line CRUD + polish) | Fits 400-line review budget; each slice independently verifiable; fast value | More phases/PRs; tree component needed early | Medium |
| 2 | Full CRUD for all 6 entities in one change | One complete flow | ~1900+ lines; exceeds review budget; high risk; slow review | High |
| 3 | Generic "entity-factory" (one config-driven form/tree for all levels) | Maximally DRY | Entity-specific fields (contact_email, flexible parenting) fight the generic shape; over-abstraction hurts tests | Med/High |

## Recommendation

**Approach 1** with an internal typed entity config in `features/institutions` (shared form/tree logic parameterized per entity, but with explicit per-entity `types.ts` and queries — no over-abstraction). Reuse the projects/advances patterns verbatim:

- `fsm.ts` + `FsmActionBar` adapted for the 3 lifecycle actions (activate/deactivate/archive), destructive = deactivate + archive (archive is terminal → ConfirmDialog mandatory)
- `ConfirmDialog`, `StatusBadge`, `EmptyState`, `Skeleton` from shared
- MSW handlers + fixtures + Jest coverage ≥80% floor
- Role guards via existing `RoleGuard` + role-filtered Sidebar entry

**Suggested change name**: `frontend-institutions` (per OpenSpec convention).

## API Integration Plan

- `queryKeys.institutions`: `all`, `lists`, `list(institutionId, level)`, `details`, `detail(institutionId, entity, id)`, `tree(institutionId)`
- Queries: `useInstitutions()`, `useInstitutionDetail(id)`, `useChildren(institutionId, level)` (sedes/facultades/centers), `useGroups(centerId)`, `useLines(groupId)`, `useInstitutionTree(institutionId)` (if a tree endpoint is added — otherwise compose client-side from list queries)
- Mutations: `useCreateEntity(level)`, `useUpdateEntity(level)`, `useDeleteEntity(level)`, `useEntityTransition()` (POST `/api/{entity}/{pk}/{action}/`)
- Invalidation: on any institution-scoped mutation, invalidate `["institutions"]`; entity CRUD under an institution invalidates the parent detail + tree; lifecycle transitions invalidate the entity + tree (+ dashboard if institution-level)
- Parent FK injection: entity create forms POST to the nested URL (e.g. `/api/institutions/{pk}/sedes/`) — parent is NOT in the body
- Error handling: reuse `errors.ts` — 409 `{detail}` from lifecycle guards and duplicate codes surface via Toaster

## Component Inventory (NEW)

- `features/institutions/InstitutionTree.tsx` — recursive tree (custom; chevron expand/collapse, StatusBadge per node, per-node action menu)
- `features/institutions/EntityForm.tsx` — config-driven create/edit dialog form (react-hook-form + zod schema per level)
- `features/institutions/EntityDetail.tsx` — detail view with child list + action bar
- `features/institutions/FsmActionBar.tsx` — 3-transition action bar (activate/deactivate/archive)
- `components/ui/collapsible.tsx` (or tree.tsx) — if not already present, a small recursive disclosure primitive
- Reused: Button, Dialog/AlertDialog, Select, Badge, Card, Input, Label, Tabs, DropdownMenu, Skeleton, Sheet, ConfirmDialog, StatusBadge, EmptyState

## Risks

1. **Prompt ↔ codebase mismatch (blocking for proposal)**: hierarchy names, §6.2 vs §6.1, "completeness validation" — the proposal MUST be written against the real research hierarchy. Confirm with the user before `sdd-propose`.
2. "Completeness validation" does not exist in the backend — if the user expects it, it is a separate backend change (spec + design + backend work first).
3. **Superadmin bootstrap edge case**: creating the FIRST institution when the user has no memberships → auth store has no `activeInstitution`; the API works (superusers bypass tenant middleware) but the UI must not require an active institution for the institutions list/tree, and `InstitutionSelector` hides for ≤1 institution.
4. **No tree component in deps**: custom implementation must keep WCAG 2.1 AA (ui-foundation requirement) and Jest coverage ≥80%.
5. **Tenant scoping via session, not header**: `X-Institution-ID` is vestigial; all institution-scoped queries must rely on the auth store's `activeInstitution` (post-switch cache clear already handles refetch).
6. **FSM 409s** ("Deactivate or archive children first.") must be surfaced clearly — users need to know WHY the action was rejected.
7. **Review budget (400 lines)** → chained PRs required (delivery strategy from session preflight).

## Ready for Proposal

**Yes** — with one prerequisite: the orchestrator must confirm the hierarchy naming with the user (real model = Institution/Sede/Facultad/ResearchCenter/ResearchGroup/ResearchLine per SPEC §6.1 and the archived backend spec; the prompt's Ministry/ViceMinistry/... model does not exist). After confirmation, `sdd-propose` for change `frontend-institutions`.

## Recommended First Slice Scope

**PR 1 (slice 1)**: `features/institutions` foundation — types, schemas, queries, mutations, fsm table; `/institutions` list page with hierarchy tree (read); institution create/edit + lifecycle action bar; MSW fixtures; Sidebar nav item; coverage ≥80%.
**PR 2 (slice 2)**: Sede/Facultad/ResearchCenter CRUD (admin level) with dependent parent selects + child lists on detail.
**PR 3 (slice 3)**: ResearchGroup/ResearchLine CRUD (director level) + tree interaction polish (status filters, deep links) + full verification.
