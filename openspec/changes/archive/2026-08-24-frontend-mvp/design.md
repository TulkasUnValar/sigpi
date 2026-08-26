# Design: SIGPI Frontend MVP

## Technical Approach

Implement the six capabilities in three vertical slices: foundation/shell/dashboard, projects, then advances. Use feature-based modules under the existing Next.js 15 App Router, keeping Zustand for authentication and active-institution context and TanStack Query v5 for all server data. Consume the existing DRF API only; dashboard KPIs are composed client-side from project/progress list queries. Spanish copy is hardcoded and routes remain flat (no locale segment).

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Frontend structure | Feature-based modules plus shared UI/lib | Layer-only folders | Matches the six capabilities and keeps module ownership clear at this MVP scale. |
| Server state | TanStack Query; Zustand only for auth/session/institution | Raw fetch in components; Zustand cache | Central keys, deduplication, loading/error states, and reliable FSM invalidation prevent cross-screen cache drift. |
| UI foundation | shadcn/ui with React 19-compatible Radix and next-themes | Custom primitives; another UI kit | Existing spec mandates accessible primitives while preserving local composition and styling. |
| Navigation | Authenticated layout with desktop sidebar and mobile drawer | Top navigation; separate layouts | Supports role-filtered navigation and the required responsive workflow. |
| Forms/tables | react-hook-form + zod; server-paginated TanStack tables | Uncontrolled forms; client pagination | Gives per-step validation, typed errors, and matches DRF page/count/next/previous responses. |

## Data Flow

```text
AppProviders → feature query hooks → lib/api.ts → DRF /api/
     ↑                 │                 │
Zustand auth ─────────┘                 └─ normalized ApiError → Toaster/form
FSM mutation → invalidate resource + projects + advances + dashboard keys
```

`QueryClientProvider` wraps the authenticated layout. Query keys include the active institution; switching institution clears/invalidate all scoped queries before refetch. Dashboard uses parallel list queries and role-specific selectors, never a new backend endpoint.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/package.json` | Modify | Add TanStack Query, Radix/shadcn dependencies, next-themes, react-hook-form, zod, and MSW. |
| `frontend/app/layout.tsx`, `frontend/middleware.ts` | Modify | Add providers/Spanish metadata, protect dashboard/projects/nested advances, and preserve institution header behavior. |
| `frontend/lib/api.ts`, `frontend/lib/query-keys.ts`, `frontend/lib/errors.ts` | Modify/Create | Generic typed request methods (JSON/multipart, CSRF, credentials), key factories, and `{detail}`/field-error normalization. |
| `frontend/store/auth.ts` | Modify | Notify QueryClient on institution changes and retain auth-only state. |
| `frontend/components/ui/*`, `frontend/components/shared/*`, `frontend/components/shell/*` | Create | shadcn primitives, StatusBadge, ConfirmDialog, Timeline, EmptyState, Skeletons, Toaster, sidebar/drawer/topbar, and role guards. |
| `frontend/features/{dashboard,projects,advances}/**` | Create | Queries, mutations, schemas, tables, wizard/detail views, and reusable FSM action configuration. |
| `frontend/app/dashboard`, `frontend/app/projects`, `frontend/app/projects/[id]/advances` | Create | Route pages; advances are nested under the project. |
| `frontend/fixtures/*` | Create | Development fixtures/seeding adapter for non-empty dashboard, projects, and advances. |
| `frontend/__tests__/**/*`, `frontend/mocks/*` | Create/Modify | Jest/RTL unit and component tests plus MSW handlers/server. |

## Interfaces / Contracts

```ts
type ApiError = { message: string; status: number; fieldErrors?: Record<string, string[]> };
type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
type FsmAction<TState> = { name: string; label: string; destructive?: boolean; allowedRoles: string[]; run: (id: string, input?: TState) => Promise<unknown> };
```

`FsmActionBar` derives visible actions from `(resource, state, role)`. It renders `ConfirmDialog` only for reject/cancel/close/archive; successful mutations invalidate the resource, detail/list, dashboard, and related project keys, while failures leave cache untouched and show normalized errors. Project wizard state is local to the route, with one zod schema per step and a final review submission.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | API client, errors, key factories, role/action maps, schemas, KPI selectors | Jest with real inputs and contract assertions. |
| Component | Shell breakpoints, guards, tables, wizard validation, tabs, FSM confirmation/invalidation | React Testing Library + user-event; QueryClient test wrapper. |
| Integration | Query hooks and mutation failure/success behavior | MSW handlers for DRF envelopes and endpoint errors. |
| E2E | Optional smoke of login → project → advance flow | Playwright later; not required by current Jest gate. |

Keep Jest branch coverage at least 80% per slice; raise the existing branch threshold from 70% when the first slice lands. Add explicit RED tests for every spec scenario before implementation.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable documentation classification | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

Routing and shell boundaries are covered by middleware, role-guard, and responsive-shell tests; they do not invoke commands or subprocesses.

## Migration / Rollout

No backend/data migration. Deliver as three reviewable slices: foundation/shell/dashboard, projects, advances. Seed fixtures are development-only and rollback is removal/revert of the relevant frontend slice.

## Open Questions

- [ ] Confirm exact DRF ordering parameter names for server-side sorting before table implementation.
