# Exploration: Frontend Calls Module (SIGPI §6.8)

## Current State

### Backend `apps.calls` — COMPLETE (archived, 2026-07-29; spec at `openspec/specs/calls/spec.md`)

Verified in models.py, serializers.py, views.py, urls.py, services.py, permissions.py, filters.py:

**4 entities**:
- **Call** — institution-scoped (FK + denormalized `institution_id` for RLS), 6-state FSM via django-fsm, `call_type` (internal/external) with `external_entity` conditional rules, 4 nullable dates (`submission_start/end`, `evaluation_start/end`) with ordering CHECK constraints, indexed `(institution, status)`.
- **CallDocument** — metadata-only (`name`, `doc_type`, `external_url`); no file upload in MVP.
- **CallProject** — through-model linking Project→Call with `UniqueConstraint(project)` (one call per project).
- **CallStateLog** — append-only domain audit log; mirrors to `AuditEvent`.

**FSM (5 transitions, 6 states)**: `borrador → abierta → cerrada → en_evaluacion → resultados_publicados → archivada` (terminal). `archivada` is terminal (no outbound transitions). `archive` accepts source `cerrada` OR `resultados_publicados`. All transitions use `select_for_update` + emit `AuditEvent`. Guarded by `director_centro` (role level ≤ 3).

**API surface** (under `/api/`, DRF pagination ON globally):
- `/calls/` GET (list, lightweight 5-field serializer) / POST (create)
- `/calls/{id}/` GET (full detail) / PATCH / DELETE (borrador + no projects only)
- `/calls/{id}/open_call|close_call|start_evaluation|publish_results|archive/` POST (5 FSM actions)
- `/calls/{id}/documents/` GET/POST, `/calls/{id}/documents/{did}/` PATCH/DELETE
- `/calls/{id}/projects/` GET/POST, `/calls/{id}/projects/{pid}/` DELETE
- `/calls/{id}/state_history/` GET (read-only logs)
- Filtering (`CallFilter`): `status`, `call_type`, `title`, `submission_start_after/before`, `evaluation_start_after/before`; plus `search` (title/description) and `ordering` (title/created_at/status/call_type).

**Permissions**: reads (list/retrieve/state_history) = any authenticated user (institution-scoped queryset); mutations (create/update/delete/FSM/documents/projects) = `director_centro`+ (role level ≤ 3) with institution match; superadmin/admin bypass institution check. Delete restricted to `borrador` without linked projects (service guard).

**Serializer detail**: `CallSerializer` handles both read + write (single serializer); `institution`, `status`, `id`, timestamps are read-only (institution/status injected by service). `CallListSerializer` exposes 5 fields: `id`, `title`, `status`, `call_type`, `created_at`. Business rules validated at serializer + model level.

### Frontend — researchers module is the most recent complete analog (done)

Existing feature folders: `dashboard`, `researchers`, `projects`, `institutions`, `advances`. Shared libs: `lib/api.ts` (typed fetch + CSRF + `X-Institution-ID` tenant header + `sendInstitutionId` opt-out), `lib/errors.ts` (ApiError), `lib/query-keys.ts` (institution-scoped key factories), `store/auth.ts` (Zustand: roles derived as `[membership.role.name]`, activeInstitution). Stack: TanStack Query v5 + zod + RHF + shadcn/ui + MSW + Jest ≥80%.

**Relevant patterns**:
- **FSM action bar**: `features/projects/FsmActionBar.tsx` + `features/projects/fsm.ts` — the exact pattern for calls. `FsmAction` shape is `{ name, label, destructive, allowedRoles, fromStates }`; `getProjectActions(state, roles)` filters by role + state; destructive actions open `ConfirmDialog`; `useProjectTransition()` POSTs `/api/{resource}/{id}/{action}/`. Researchers' `features/researchers/fsm.ts` reuses the same `FsmAction` type from `features/institutions/types`. **Calls maps directly to this 1:1** (5 actions, same `{id, action}` transition shape).
- **List page**: `app/researchers/page.tsx` — paginated table, `page` state, `RoleGuard`-gated create CTA, EmptyState. Backend returns `Page<T>` envelope.
- **Detail page**: `app/researchers/[id]/page.tsx` — header + `StatusBadge` + tabs (Overview + nested managers), role-gated Edit + destructive action button.
- **StatusBadge**: `components/shared/StatusBadge.tsx` — maps DRF status → Spanish label + variant. Current entries include all project/advance statuses but **NOT the calls FSM statuses** (`abierta`, `en_evaluacion`, `resultados_publicados`) — these must be added.
- **query-keys**: institution-scoped factories (`list(institutionId, filters)` + `detail(institutionId, id)` + nested). Researchers added a `researchers` factory; calls needs its own `calls` factory with nested `documents`, `projects`, `stateHistory`.
- **MSW + fixtures**: `mocks/handlers.ts` has in-memory stores seeded from `frontend/fixtures/*.ts`; `fixtures/index.ts` re-exports. Researchers handlers were added with pagination + nested stores. **Calls needs a `fixtures/calls.ts` + handlers** (list CRUD + 5 FSM + documents + projects + state_history).

### No existing frontend references to the calls API

`grep` for `/api/calls|convocatoria|Call` in `frontend/**` returned **no matches** — the calls module is **greenfield** on the frontend. No latent consumer bug exists for calls.

**IMPORTANT — the projects wizard pagination bug is ALREADY FIXED.** The researchers exploration (#348) flagged `useResearchers()` in `features/projects/queries.ts` as calling `api.get<ResearcherOption[]>` and mapping directly (crashing against the paginated real API). Current code shows this was fixed: `useResearchers()` now returns `Page<ResearcherList>` and `app/projects/new/page.tsx` maps `data.results`. So the calls change does **NOT** need to carry a projects-wizard fix — unlike the researchers change.

## What the UI Needs

Routes (mirror researchers, no locale prefix):
- `/calls` — list: paginated table (title, status badge, call_type, submission dates, created_at), `RoleGuard`-gated create CTA, filters (status/type) if in scope.
- `/calls/new` — create form (director+): title, description, call_type, external_entity (conditional on type), 4 nullable dates. Reuse EntityForm pattern from institutions/advances.
- `/calls/[id]` — detail: header + `StatusBadge` + FSM action bar (5 actions from `getCallActions`), tabs: **Overview** (fields + dates), **Documents** (metadata-only manager), **Projects** (linked projects manager), **State history** (read-only logs).
- `/calls/[id]/edit` — edit form (PATCH), gated by director+.

Feature module `features/calls/`:
- `types.ts` — `Page<T>`, `CallList`, `Call`, `CreateCallPayload`, `UpdateCallPayload`, `CallDocument`, `CallProject`, `CallStateLog`, nested payloads.
- `schemas.ts` — zod schemas: conditional `external_entity` (required if external, forbidden if internal), date ordering validation.
- `constants.ts` — `CALL_TYPES`, `CALL_DOCUMENT_TYPES`, Spanish labels.
- `fsm.ts` — `CALL_ACTIONS` (5) with `fromStates`/`allowedRoles` (`director`, `admin`, `superadmin`), `getCallActions(state, roles)`.
- `queries.ts` — `useCallsList`, `useCallDetail`, `useCallDocuments`, `useCallProjects`, `useCallStateHistory` (institution-scoped).
- `mutations.ts` — create/update/delete, `useCallTransition` (5 FSM POSTs), document create/update/delete, project link/unlink.
- `permissions.ts` — `canManageCall(roles)` (director+) helper.

Cross-cutting:
- `lib/query-keys.ts` — add `calls` factory (list/detail/documents/projects/stateHistory).
- `components/shared/StatusBadge.tsx` — add `abierta`, `en_evaluacion`, `resultados_publicados` entries (and confirm `cerrada`/`archivada` already covered — `cerrada` and `archivada` exist).
- `components/shell/Sidebar.tsx` — add "Convocatorias" nav item (all authenticated roles; label in Spanish).
- `mocks/handlers.ts` + `fixtures/calls.ts` (+ index export) — MSW fixtures/handlers.
- **Backend: NO changes.**

## Affected Areas

- `frontend/features/calls/**` — types, schemas, queries, mutations, fsm, permissions, constants, components (NEW)
- `frontend/app/calls/**` — list, new, `[id]` (detail with tabs), `[id]/edit` routes (NEW)
- `frontend/lib/query-keys.ts` — add `calls` key factory
- `frontend/components/shell/Sidebar.tsx` — "Convocatorias" nav item
- `frontend/components/shared/StatusBadge.tsx` — add calls FSM status entries
- `frontend/mocks/handlers.ts` + `frontend/fixtures/calls.ts` + `frontend/fixtures/index.ts` — MSW fixtures/handlers
- Backend: none

## Approaches

1. **Feature-module slices (3 chained PRs)** — PR1: foundation (types/schemas/constants/query-keys/StatusBadge/Sidebar) + list + create + detail overview + FSM action bar + MSW list/create/FSM; PR2: nested managers (Documents metadata-only, Projects link/unlink, State history read-only) + fixtures/handlers; PR3: filters + polish + verify. Fits 400-line budget, follows researchers/institutions precedent, calls FSM maps 1:1 to the existing projects `FsmActionBar`. — Effort: Medium. **RECOMMENDED.**
2. **Full module in one change** — ~1300+ lines, exceeds the 400-line review budget → violates delivery guard. — High.
3. **Reuse institutions EntityConfig/EntityForm generic machinery** — calls has an FSM + nested managers + distinct date/type rules; the generic form fights this shape (same conclusion as researchers). — Med/High.

## Recommendation

**Approach 1** — sliced read-first delivery with 3 chained PRs. The calls module mirrors researchers nearly exactly (institution-scoped, nested managers, FSM, read-only history), and the FSM action bar reuses the proven projects pattern verbatim. This is the lowest-risk path and fits the 400-line review budget under `stacked-to-main`.

## Risks

1. **State history + projects/documents nested managers** add surface; keep the detail page tabs lean (read-only history, metadata-only documents, project link/unlink) to stay within budget.
2. **No existing frontend consumer of calls API** → no latent bug to fix in this change (unlike researchers). Confirm the projects-wizard pagination fix is genuinely already merged before proposing (verified in working tree).
3. **FSM destructive/confirm UX** — `archive` is terminal and destructive; route it through `ConfirmDialog`. Invalid transitions return 409/403 from backend — must surface via `getErrorMessage`.
4. **Conditional type/entity + date ordering** validation must match backend rules exactly (external_entity required for external, forbidden for internal; end ≥ start) to avoid 400s.
5. **400-line review budget** → chained PRs mandatory; forecast sizes in sdd-tasks.
6. **Role gating** — calls mutations are `director_centro`+ (level ≤ 3); map to frontend roles `director`, `admin`, `superadmin` (consistent with researchers `CREATE_ROLES`). Confirm the role-name mapping (`director` vs `director_centro`) with the auth contract.

## Ready for Proposal

**Yes** — confirm with user: (1) delete action scope (backend only allows `borrador` + no projects — surface only from detail for director+); (2) state history read-only tab desired; (3) list filters (status/type) in PR3 scope vs v1. After confirmation: `sdd-propose` for change `frontend-calls`.
