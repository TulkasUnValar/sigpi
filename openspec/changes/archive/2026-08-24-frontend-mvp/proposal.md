# Proposal: SIGPI Frontend MVP — Dashboard, Projects & Advances

## Intent

Backend MVP (9 modules) is done; frontend has only auth pages. This slice ships the core research workflow — investigators create projects, directors review them, both track advances — and establishes the shell, data-layer, and FSM UX patterns later modules will reuse.

## Scope

### In Scope
- Foundation: shadcn/ui, TanStack Query, generic typed API client (CSRF, X-Institution-ID, multipart)
- App shell: sidebar (desktop) + drawer (mobile), topbar, role-based nav + route guards
- Dashboard: role-aware home (KPIs, pending approvals, my projects)
- Projects: list (filters, pagination), create wizard, detail tabs, 14-transition FSM action bar
- Advances: per-project list + cumulative %, create, detail, director FSM actions
- Shared components: StatusBadge, ConfirmDialog, Timeline, EmptyState, Skeletons, Toaster

### Out of Scope
- Modules: researchers, products, calls, institutions, reports, workflow
- Audit viewer (no backend endpoint), i18n (`[locale]` deferred; Spanish hardcoded)
- Budgets, document files, search, Superset; any backend change

## Capabilities

> Contract with sdd-spec. All new — no existing spec-level behavior changes.

### New Capabilities
- `ui-foundation`: shadcn/ui + base primitives
- `server-state`: TanStack Query, query keys, post-FSM invalidation, error normalization
- `app-shell`: layout, nav, role guards, institution-switch invalidation
- `dashboard`: role-aware home
- `projects-ui`: list/create/detail + FSM actions + tabs
- `advances-ui`: list/create/detail + FSM actions + progress

### Modified Capabilities
- None — backend unchanged; APIs consumed as-is.

## Approach

Module-staged: slice 1 foundation + shell + dashboard, slice 2 projects, slice 3 advances. Zustand keeps auth/session; TanStack Query owns server data; FSM actions invalidate affected queries.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/lib/api.ts` | Modified | Generic get/post/patch/del, multipart |
| `frontend/middleware.ts` | Modified | Extend PROTECTED_PREFIXES |
| `frontend/app/{dashboard,projects,advances}/` | New | Routes (flat, no `[locale]`) |
| `frontend/components/` | New | shadcn/ui + domain components |
| `frontend/store/auth.ts` | Modified | Institution switch → invalidation |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| shadcn/ui × React 19 incompat | Med | Spike in slice 1 before building on it |
| FSM action visibility wrong → 403s | Med | Per-state/role action map from specs; test all transitions |
| Dashboard lacks dedicated endpoint | Med | Compose from list endpoints (see questions) |
| Jest 80% floor on 20+ screens | High | Component tests per slice; coverage per PR |
| PRs exceed 400 lines | High | sdd-tasks chains PRs by module |

## Rollback Plan

Each slice lands as its own PR — revert the slice branch, others untouched. Foundation revert: uninstall deps, git-restore `lib/api.ts`/`middleware.ts`. No backend or data changes.

## Dependencies

- Backend MVP running (`/api/`), session + CSRF auth
- TanStack Query v5; shadcn/ui (React 19-compatible Radix)
- OpenSpec context + config

## Success Criteria

- [ ] Investigator creates + submits project; director approves — end to end
- [ ] Director reviews an advance; state reflects immediately
- [ ] Institution switch refreshes scoped data
- [ ] Shell responsive (sidebar/drawer)
- [ ] Jest ≥ 80%, lint + typecheck green per slice

## Proposal question round

Questions for the user before approval:

1. Project creation: multi-step wizard or single long form? (assumes wizard)
2. FSM confirmations: ConfirmDialog for every transition, or only destructive (reject/cancel/close)?
3. Dashboard data: compose KPIs from list endpoints, or add backend aggregate endpoint (scope increase)?
4. Advances routing: nested under `/projects/[id]/advances`, or top-level `/advances`?
5. Dev seed data: fixtures needed to demo non-empty states?