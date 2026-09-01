# Exploration: Frontend Researchers Module (SIGPI §6.3)

## Current State

### Backend `apps.researchers` — COMPLETE (archived; 207 tests)

Verified in `backend/apps/researchers/models.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`, `permissions.py`:

**4 entities:**

```
Institution (scope)
└── Researcher (institution-scoped, optional OneToOne User, unique (institution, document_number))
    ├── ResearcherAffiliation (junction → center/group/line, ≥1 FK, exactly one is_primary)
    ├── ExternalProfile (provider: cvlac|orcid|google_scholar|linkedin|researchgate + url)
    └── ResearcherAttachment (metadata-only: name, type: cv|certificate|photo|other, external_url)
```

- **Researcher has NO FSM** — just `is_active` boolean + a single `deactivate` action. No `activate`/`archive` endpoints exist.
- **No file uploads** — attachments are metadata-only (`name`, `type`, `external_url`). File storage is deferred to the `documents` module.
- **Completeness score** (0–100, computed, not stored): 6 criteria — 5 mandatory fields (first_name, last_name, document_type, document_number, primary_email) + at least one ExternalProfile. Returned by `ResearcherListSerializer` (list) and `ResearcherSerializer` (detail).
- `primary_email` is the actual model field (the archived spec.md says `email` — the model wins).

**API surface** (all under `/api/`, mounted in `backend/config/urls.py`):

| Endpoint | Methods | Write permission |
|---|---|---|
| `/researchers/` | GET (list, lightweight), POST | create: director+ (level ≤ 3) |
| `/researchers/{id}/` | GET (full + nested), PATCH, DELETE | update: self or admin+ (≤ 2); delete: superadmin (≤ 1) |
| `/researchers/{id}/deactivate/` | POST | admin+ (≤ 2) |
| `/researchers/{id}/affiliations/` | GET, POST | researcher+ (≤ 4, self or admin) |
| `/researchers/{id}/affiliations/{aff_id}/` | PATCH, DELETE | researcher+ (self or admin) |
| `/researchers/{id}/affiliations/{aff_id}/set_primary/` | POST | researcher+ (self or admin) |
| `/researchers/{id}/profiles/` | GET, POST | researcher+ (self or admin) |
| `/researchers/{id}/profiles/{prof_id}/` | PATCH, DELETE | researcher+ (self or admin) |
| `/researchers/{id}/attachments/` | GET, POST | researcher+ (self or admin) |
| `/researchers/{id}/attachments/{att_id}/` | PATCH, DELETE | researcher+ (self or admin) |

- Reads: any authenticated user in the institution (list/retrieve).
- **DRF pagination is ON globally** (`PageNumberPagination`, 25/page) — `/researchers/` returns a `{count, next, previous, results}` envelope.
- Institution scoping: `TenantMiddleware` session-scoped (frontend `X-Institution-ID` header is vestigial); superusers bypass.

**Business rules that surface in the UI (from services/tests):**
- First affiliation is auto-set `is_primary=True`; exactly one primary per researcher.
- Affiliation FKs must belong to the researcher's institution (400 on violation).
- Duplicate `(institution, document_number)` → 400/409 field error on create/update.
- Deactivation does not cascade to affiliations (they render inactive via researcher.is_active).
- No "reactivate" endpoint — reactivation must go through `PATCH /researchers/{id}/` with `{is_active: true}` (allowed for self or admin+).
- No "my profile" endpoint (`/researchers/me/`) — the frontend finds the current user's researcher via the `user` FK on the detail serializer.

### Frontend — MVP + institutions shipped

- Feature module pattern: `features/{module}/{types,schemas,queries,mutations,fsm,FsmActionBar}.ts(x)`, App Router routes under `app/`.
- `lib/api.ts` typed fetch (CSRF, credentials, `institutionId`), `lib/errors.ts` (`ApiError` + field errors), `lib/query-keys.ts` institution-scoped key factories, `lib/query-client.ts`.
- `store/auth.ts` (Zustand): `roles` (string[]), `activeInstitution`, `centers`.
- TanStack Query v5; zod + react-hook-form for forms; MSW (`mocks/handlers.ts`) + fixtures (`fixtures/*.ts`); Jest + RTL coverage ≥80%; ESLint + `tsc --noEmit`.
- shadcn/ui: button, badge, card, dialog, alert-dialog, dropdown-menu, input, label, select, sheet, skeleton, sonner, switch, tabs, separator.
- shared: StatusBadge, ConfirmDialog, EmptyState, Skeleton, Toaster; shell: AuthenticatedLayout, Sidebar (role-filtered), Topbar, Drawer, RoleGuard.
- `features/institutions` (most complete): config-driven `EntityForm` (RHF + zod + `fieldOptions` for dependent selects), `EntityDetail`, `FsmActionBar`, `InstitutionTree`, per-entity configs.
- `features/projects`: wizard with dependent selects (centers→groups→lines), detail tabs, FSM action bar.
- `features/advances`: nested entity under projects — the closest pattern for affiliations/profiles/attachments (nested list under parent route, create page, FSM).
- Routes use NO `[locale]` prefix today (the researchers proposal's `app/[locale]/researchers/` path is outdated — current app has no `[locale]` segment).

**Latent bug found (must be fixed by this change):** `features/projects/queries.ts` `useResearchers()` calls `api.get<ResearcherOption[]>("/api/researchers/")` and the wizard does `researchers.map(...)` directly — but the backend returns a paginated `Page<ResearcherList>`. Against the real API this crashes; tests pass only because they mock the `api` module and no MSW researchers handler exists. The researchers module must fix this consumption point (consume `Page<ResearcherList>` or use `fetchAllPages`).

## What the UI Needs (SIGPI §6.3)

1. **Pages/routes**: list (`/researchers`), create (`/researchers/new`), detail with tabs (`/researchers/[id]`), edit (`/researchers/[id]/edit`).
2. **Detail tabs**: Overview (profile fields + completeness + is_active), Affiliations, External profiles, Attachments — each a read list + inline create + delete (following the advances nested pattern).
3. **Affiliation manager**: dependent selects center → group → line (at least one required), `is_primary` toggle + `set_primary` action, "first affiliation auto-primary" UX note.
4. **Completeness display**: 0–100 indicator (no shadcn progress primitive exists — small custom bar or add `progress.tsx`).
5. **Deactivate action**: single FSM-style action, admin+ (≤ 2), destructive → ConfirmDialog. No other transitions (no activate/archive).
6. **is_active badge**: `StatusBadge` needs `active`/`inactive` entries (currently only hierarchy + project statuses).
7. **Sidebar**: add "Investigadores" nav item (all authenticated roles — reads are open; writes gated by RoleGuard).

## Affected Areas

- `frontend/app/researchers/**` — new routes: list, new, [id] detail (tabs), [id]/edit (NEW)
- `frontend/features/researchers/**` — types, schemas, queries, mutations, fsm (deactivate only), components (NEW)
- `frontend/lib/query-keys.ts` — add `researchers` key factory (list/detail + nested affiliations/profiles/attachments)
- `frontend/features/projects/queries.ts` + `app/projects/new/page.tsx` — fix `useResearchers()` pagination mismatch
- `frontend/mocks/handlers.ts` + `frontend/fixtures/researchers.ts` — MSW fixtures/handlers for all 4 entities
- `frontend/components/shell/Sidebar.tsx` — add "Investigadores" nav item
- `frontend/components/shared/StatusBadge.tsx` — add active/inactive status metadata
- Backend: NO changes — API is complete for this module

## Approaches

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| 1 | **Feature-module slices** (PR1: foundation — types/schemas/queries/mutations/fsm + list + create + detail overview + deactivate + Sidebar + StatusBadge; PR2: nested managers — affiliations/profiles/attachments tabs + fixtures/handlers; PR3: projects wizard pagination fix + polish + verification) | Fits 400-line review budget; each slice independently verifiable; follows institutions precedent (3 PRs); no over-abstraction | More PRs/phases; nested managers deferred to PR2 | Medium |
| 2 | Full module in one change | One complete flow | ~1400+ lines; far exceeds review budget; high risk; slow review | High |
| 3 | Reuse the institutions `EntityConfig`/`EntityForm` generic machinery | Maximally DRY | Researchers have NO FSM (config assumes lifecycle), different shape (nested managers, completeness, is_active badge); forces config extensions that fight the generic form | Med/High |

## Recommendation

**Approach 1** — a dedicated `features/researchers` module following the institutions/projects/advances patterns verbatim:

- `fsm.ts` + `FsmActionBar` adapted to a single transition (`deactivate`, destructive, admin+). Reactivation is a plain PATCH (`is_active: true`) surfaced as an edit-form checkbox, not an FSM action.
- Nested managers (affiliations/profiles/attachments) as detail tabs reusing the advances pattern (nested queries + inline forms + delete); `set_primary` as a dropdown action or button with toast.
- Dependent selects (center → group → line) for the affiliation form — copy the wizard's `useCenters`/`useGroups`/`useLines` pattern (they already hit `/api/institutions/{id}/centers/` etc.).
- Completeness score as a small progress bar on list + detail.
- Fix `useResearchers()` in the projects feature to consume the paginated envelope (`Page<ResearcherList>` → map to `{id, full_name}` options), with a matching MSW handler.
- MSW fixtures + handlers, Jest ≥80%, ESLint + typecheck green per PR.

**Suggested change name**: `frontend-researchers` (per OpenSpec convention).

## API Integration Plan

- `queryKeys.researchers`: `all`, `lists`, `list(institutionId, filters)`, `details`, `detail(institutionId, id)`, nested `affiliations/profiles/attachments` under the detail key.
- Queries: `useResearchersList(params)`, `useResearcherDetail(id)`, `useResearcherAffiliations(id)`, `useResearcherExternalProfiles(id)`, `useResearcherAttachments(id)`, `useResearcherOptions()` (shared with the projects wizard).
- Mutations: `useCreateResearcher`, `useUpdateResearcher`, `useDeleteResearcher` (superadmin-only UI), `useDeactivateResearcher`, `useCreateAffiliation`, `useSetPrimaryAffiliation`, `useDeleteAffiliation`, `useCreateExternalProfile`, `useDeleteExternalProfile`, `useCreateAttachment`, `useDeleteAttachment`.
- Invalidation: any researcher-scoped mutation invalidates `["researchers"]` (+ projects when the projects-wizard options derive from it).
- Parent FK injection: child create forms POST to the nested URL (`/api/researchers/{id}/affiliations/` etc.) — researcher is NOT in the body.
- Error handling: reuse `errors.ts` — 400 field errors map into forms (EntityForm pattern), 400/409 `{detail}` (duplicate document, cross-institution affiliation) surface via Toaster.

## Risks

1. **Projects wizard pagination mismatch is a pre-existing latent bug** — the researchers module MUST fix `useResearchers()` or the researcher select in the project wizard breaks against the real API. Scope it explicitly (PR3) and coordinate with the projects tests.
2. **No reactivate endpoint** — if the user expects a lifecycle action bar like institutions (activate/deactivate/archive), the researchers module only has `deactivate`. Reactivation is a PATCH; the proposal should confirm this UX (plain edit, not FSM).
3. **No "my profile" endpoint** — self-edit detection relies on comparing `researcher.user` (detail serializer) to the current user id; the list serializer does NOT expose `user`, so the list page cannot mark "my profile" without a detail fetch or a small backend addition (avoid backend changes — backend is archived).
4. **Attachment metadata vs. file upload** — users may expect real file upload; the backend stores only name/type/external_url. The UI must present external URLs, not uploads. Confirm with the user before proposal.
5. **Affiliation edge cases** — first affiliation auto-primary, exactly-one-primary invariant, cross-institution 400s: the affiliation manager must surface these clearly (toasts + disabled primary toggle when already primary).
6. **Review budget (400 lines)** → chained PRs required (delivery strategy from session preflight).

## Ready for Proposal

**Yes** — with three user confirmations for `sdd-propose`:
1. Attachments are metadata-only (name/type/external_url), NOT file uploads — acceptable?
2. No `activate` action exists; reactivation is via the edit form (is_active toggle), and self-edit is detected via `researcher.user === current user` (no `/researchers/me/` endpoint) — acceptable?
3. The change includes the small fix to the projects wizard's `useResearchers()` pagination bug (touches `features/projects`) — in scope?

After confirmation, `sdd-propose` for change `frontend-researchers`.
