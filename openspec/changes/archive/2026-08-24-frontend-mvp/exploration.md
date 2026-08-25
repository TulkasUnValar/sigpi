# Exploration: Frontend MVP for SIGPI — Pages, Components & Core User Flows

## Current State

- **Backend (DONE)**: 9 MVP apps fully implemented — `accounts` (auth + audit events), `institutions` (Institution/Sede/Facultad/ResearchCenter/ResearchGroup/ResearchLine with lifecycle actions), `researchers` (affiliations, external profiles, attachments), `projects` (12-state FSM + 14 transition endpoints + members/documents/observations/state_history), `project_workflow` (templates, instances, actions), `progress` (advances: 6-state FSM + documents/reviews/state_history + `/projects/{id}/progress/` shortcut), `products` (11 hardcoded types + authors/attachments), `calls` (6-state FSM + documents/projects/state_history), `reports` (preview/pdf/approve for types: `project`, `researcher`, `center`, `advances`).
- **API conventions**: all under `/api/` prefix, UUID PKs, DRF `PageNumberPagination` with `PAGE_SIZE=25` (page/count/next/previous envelope), JSON errors as `{"detail": "..."}`, Django session cookie auth + `X-CSRFToken` header, institution scope propagated via `X-Institution-ID` header (set in middleware from `institution_id` cookie).
- **Frontend (scaffold only)**: Next.js 15 App Router + React 19 + TS strict + Zustand 5 + Jest/RTL. Only auth pages exist: `/login`, `/logout`, `/me`, `/switch-institution`. `store/auth.ts` (Zustand persisted: user, activeInstitution, institutions, roles, centers), `lib/api.ts` (fetch wrapper for auth endpoints with CSRF handling), `middleware.ts` (sessionid-cookie guard + X-Institution-ID header), `components/` (LoginForm, OIDCButton, ProtectedRoute, InstitutionSelector, UserProfileCard).
- **Mandated but NOT installed**: shadcn/ui (RNF-007), next-intl (RNF-005), next-themes (RNF-006). No data-fetching lib (no TanStack Query/SWR) — raw fetch only.
- **Roles** (from membership.role.name + centers): superadmin, institutional admin, center director, investigator/researcher, co-investigator, auditor.

## Module-by-Module Screen Inventory

| Module | Screens | Key Data from API |
|---|---|---|
| **Auth / Dashboard** (accounts) | `/login` (exists), `/logout` (exists), `/me` (exists), `/switch-institution` (exists), **NEW `/dashboard`** — role-aware home (pending approvals, my projects, KPIs) | `/auth/me/`, `/auth/switch-institution/` |
| **Institutions** | `/institutions` list (table + filters) · `/institutions/[id]` detail with tabs (sedes, facultades, centers) · create/edit forms for each level · nested lists: `/institutions/[id]/sedes`, `/facultades`, `/centers`, `/centers/[id]/groups`, `/groups/[id]/lines` · lifecycle action buttons (activate/deactivate/archive with confirm) | CRUD + nested CRUD + POST `activate/deactivate/archive` per entity |
| **Researchers** | `/researchers` list (filters: institution, completeness badge) · `/researchers/[id]` detail (profile completeness %, affiliations w/ set-primary, external profiles CvLAC/GrupLAC/ORCID/Scholar, attachments) · create/edit form · attachment upload | `/researchers/` + nested `affiliations`, `profiles`, `attachments`, `set_primary` |
| **Projects** | `/projects` list (state badges, filters: state/center/line/year, search) · `/projects/new` form (basic info, association center/group/line, team, docs) · `/projects/[id]` detail — tabs: overview, team, documents, observations (timeline), state history · role-conditional FSM action bar (submit/approve/observe+comment/reject/start_execution/suspend/resume/finalize/initiate_closure/close/cancel/return_to_draft) | `/projects/` + 14 FSM POSTs + nested `members`, `documents`, `observations`, `state_history` |
| **Advances (progress)** | `/projects/[id]/advances` list (per project, cumulative % indicator) · `/advances/new` form (period, description, %, activities, difficulties, next steps, attachments) · `/advances/[id]` detail (review timeline, docs, state history) · director approval actions (approve/observe/reject/return_to_draft) | `/progress/` + FSM POSTs + nested `documents`, `reviews`, `state_history`; `/projects/{id}/progress/` |
| **Products** | `/products` list (filters: type/year/center/group/project/researcher) · `/products/new` (type, authors, evidence attachments) · `/products/[id]` detail | `/products/` + nested `authors`, `attachments` |
| **Calls** | `/calls` list (filters: state/type/institution) · `/calls/new` (dates: aperture < closure < evaluation < results; internal/external) · `/calls/[id]` detail (docs, linked projects, state history) · FSM action bar (open_call/close_call/start_evaluation/publish_results/archive) | `/calls/` + 5 FSM POSTs + nested `documents`, `projects`, `state_history` |
| **Reports** | `/reports` hub (choose type: project/researcher/center/advances + pick entity) · preview view (iframe of returned HTML, RF-056) · PDF download (streamed) · approve action for final reports (RN-016/17) | `GET /reports/{type}/{id}/preview/`, `.../pdf/`, `POST .../approve/` |
| **Workflow** (project_workflow) | Minimal: `/workflows` templates list (admin-only) · workflow instance view embedded in project detail (optional for MVP) | `/workflows/templates/`, `/workflows/instances/` + `actions` |
| **Audit** (in accounts, backend-only today) | `/audit` log viewer — filters by entity/user/action (⚠️ **no endpoint exists yet**; backend records `AuditEvent` but exposes no read API) | None — needs new backend endpoint or is deferred |

## User Flow Map (Primary Personas)

**Investigator**: login → dashboard → Projects → new project (draft) → fill form (title, summary, objectives, methodology, keywords, center/group/line, dates, team, docs) → submit → director reviews → *observed* → fix from observation timeline → resubmit → approved/execution → register advances (period, %, activities, attachments) → upload products with evidence → finalize/close.

**Center Director**: login → dashboard (pending approvals queue) → review project → approve/observe(reason)/reject → review advances → approve/observe/reject → generate reports (preview → PDF) → approve final reports → monitor indicators on dashboard.

**Institutional Admin**: login → institutions structure management (sedes/facultades/centers/groups/lines + activate/deactivate/archive) → researchers registry → calls management → audit log → reports.

## Component Inventory (estimate)

- **Layout**: authenticated app shell (sidebar/nav + topbar with InstitutionSelector + user menu + theme toggle), role-based nav filtering.
- **~10 tables** (one per list screen) with server-side pagination (page/count/next/previous), sort, and filter bars.
- **~20 forms** (entity create/edit across 8 modules) with validation + error display; project form likely a wizard/tabbed form.
- **Cross-cutting**: StatusBadge (12 project states, 6 advance states, 6 call states, 6 institution lifecycle states), FSM action bar (role-conditional buttons + confirm dialogs), observation/review/history Timeline, ConfirmDialog for lifecycle/FSM actions, FileUpload (multipart to metadata-based endpoints), Tabs (detail pages), EmptyState, Skeletons, Toaster, Modal/Drawer, PDF preview modal (iframe), filter/select dropdowns (center/group/line cascading).

## Technical Considerations

1. **API client**: extend `lib/api.ts` generically (typed `get/post/patch/del` with CSRF + `credentials: include` + `X-Institution-ID` header). Standardize error handling on `{detail}` and field-error maps for form display. Multipart upload for attachments (Content-Type change per endpoint).
2. **Server state**: current Zustand store is client-only. Recommend introducing **TanStack Query** for server data (caching, invalidation after FSM transitions — e.g., approve invalidates project + dashboard queues) OR keep raw fetch + Zustand; decision needed before apply. Zustand stays for auth/session + active-institution context (derived roles/centers already exist).
3. **Routing & auth**: middleware currently guards only `/me`, `/switch-institution`, `/dashboard`. Must extend PROTECTED_PREFIXES to all new modules; add role-based route guards (director-only routes) at page level; `/reports` and `/audit` restricted by role. Next.js App Router structure per SPEC §11 (`app/[locale]/` if i18n adopted, else flat `app/{module}/`).
4. **Active-institution context**: every list/detail call must include active institution scope (header already plumbed by middleware via cookie). Switching institution must invalidate cached queries.
5. **Pagination**: all list endpoints are DRF page-based (25/page) — tables need page controls, not infinite scroll, unless API changes.
6. **Reports**: preview returns HTML for iframe injection; PDF endpoint returns binary — handle as blob download; approve is POST.
7. **i18n/themes (RNF-005/006)**: next-intl + next-themes mandated but absent; `[locale]` route segment decision impacts ALL route paths — must be decided at proposal time, not retrofitted.
8. **shadcn/ui (RNF-007)**: mandated; must be added to the scaffold (radix deps) — React 19 compatibility needs verification.

## Risks

- **Audit has no read endpoint** — a frontend audit screen requires a new backend change or must be cut from MVP.
- **Budgets & documents modules not implemented** (no `budgets` app; documents are metadata-only nested under projects/progress/calls) — budget screens and document preview/signing are OUT of MVP scope; report types `product`/`budget` don't exist server-side (only project/researcher/center/advances).
- **i18n `[locale]` decision is load-bearing** — retrofitting locale segments after pages are built is expensive; decide in proposal.
- **React 19 + shadcn/ui/radix compatibility** unverified; validate before committing to the component library.
- **No data-fetching layer yet** — hand-rolled fetch + manual cache invalidation across 20+ screens is a high-maintenance path; TanStack Query recommendation should be validated.
- **FSM action UX**: 14 project transitions with role guards need careful per-state action mapping; wrong visibility = user-facing 403s.
- **Jest coverage floor is 80% (config)** — a large frontend build with 20+ screens will need disciplined component tests to hold the floor.
- **Review budget (400 lines)**: the full frontend build will far exceed one PR — sdd-tasks must plan chained PRs by module.

## Open Questions

1. Scope: does the frontend MVP ship all 8 non-auth modules, or a priority subset (dashboard, projects, advances, researchers)?
2. i18n: Spanish-first UI with next-intl now, or defer `[locale]` and hardcode Spanish for MVP?
3. Server-state library: TanStack Query vs plain fetch + Zustand?
4. Navigation: persistent sidebar (desktop) vs top nav — pattern choice affects the shell.
5. Audit viewer: add backend endpoint (scope increase) or defer the screen?

## Recommendation

Proceed to proposal with a **module-staged frontend build** in this order: (1) app shell + dashboard + navigation, (2) projects (largest: FSM UI), (3) advances, (4) researchers, (5) products, (6) calls, (7) institutions structure admin, (8) reports hub, (9) workflow (minimal) + audit (deferred pending endpoint). Introduce TanStack Query + shadcn/ui in the first slice; resolve the `[locale]` question in the proposal before any page is built. Budgets/documents/search/Superset stay out of the frontend MVP (no backend support).

## Ready for Proposal

**Yes** — scope boundaries and sequencing are clear. The orchestrator should confirm the 5 open questions (especially i18n scope and server-state library) with the user before launching `sdd-propose`.