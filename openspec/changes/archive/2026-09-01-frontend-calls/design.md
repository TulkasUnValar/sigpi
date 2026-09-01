# Design: Frontend Calls Module

## Technical Approach

Build an institution-scoped `features/calls` module using the completed researchers/projects conventions: thin Next.js App Router pages, client feature components, TanStack Query for server state, Zustand only for auth/institution context, RHF + zod for forms, and `api`/`ApiError` for transport. UI copy remains Spanish. The backend contract is consumed unchanged; its six-state lifecycle is represented by a local action table.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Feature boundary | Keep all call types, hooks, FSM, permissions, forms, managers, and tests under `features/calls`; pages only compose them. | Put API logic in route pages. | Matches researchers and keeps routes replaceable/testable. |
| Server state | One `calls` query-key factory with institution id, filters/page, detail, and nested resources; invalidate the call root after successful mutations. | Zustand cache or optimistic updates. | TanStack Query already owns API state; server guards and 409s make refetch safer than optimistic state. |
| Authorization | UI helpers/`RoleGuard` use `director`, `admin`, `superadmin` (backend `CanManageCall`, level ≤3); backend remains authoritative. | Hide only by HTTP failure. | Consistent affordances while preserving server security. |
| Lifecycle UX | `getCallActions(state, roles)` drives a reusable `FsmActionBar`; only `archive` and delete confirm. | Duplicate transition buttons in the page. | Reuses projects behavior and makes terminal/destructive actions explicit. |
| Nested data | Dedicated query/mutation hooks and managers; documents are URL metadata only, projects use association ids, history is read-only. | Embed mutable nested state in the call form. | Mirrors DRF endpoints and prevents accidental file-upload scope. |

## Data Flow

```text
AuthStore institutionId + roles
        ↓
Page → feature query hook → queryKeys.calls → api (+ X-Institution-ID) → DRF
        ↓                                      ↑
  components ← query cache ← mutation success ─┘ invalidate calls root
```

List params serialize `page`, `status`, and `call_type`; detail queries use the call id. Mutations cover create, patch, delete, five transitions, document create/patch/delete, and project link/unlink. Error callbacks pass `ApiError` to `getErrorMessage`/Toaster; validation errors map to RHF fields.

## File Layout

```text
frontend/features/calls/
  index.ts types.ts constants.ts schemas.ts permissions.ts fsm.ts
  queries.ts mutations.ts CallList.tsx CallForm.tsx CallDetail.tsx
  FsmActionBar.tsx DocumentsManager.tsx ProjectsManager.tsx StateHistoryManager.tsx
frontend/app/calls/
  page.tsx new/page.tsx [id]/page.tsx [id]/edit/page.tsx
frontend/fixtures/calls.ts
frontend/__tests__/features/calls/{fsm,schemas,queries,mutations,list,detail,managers,routes}.test.*
```

Modify `frontend/lib/query-keys.ts`, `components/shared/StatusBadge.tsx`, `components/shell/Sidebar.tsx`, `mocks/handlers.ts`, and the fixture index. `calls` types mirror `CallList`, `Call`, `CallDocument`, `CallProject`, `CallStateLog`, and `Page<T>`; form payloads omit read-only institution/status/timestamps.

## Component Breakdown

`/calls` renders title, filter controls, paginated table, empty state, and director-gated create CTA. `/calls/new` and `/calls/[id]/edit` share `CallForm`; zod enforces external-entity conditionality and both date orderings. Detail composes header/status, edit/delete controls, `FsmActionBar`, and Overview/Documents/Projects/State history tabs. Managers use shadcn cards/dialogs and confirm destructive deletes. Project linking is rendered only in `abierta`; delete only in `borrador` with zero linked projects.

Reuse researchers’ list/detail/page/query/mutation/error patterns, projects’ `FsmActionBar` and pagination conventions, institutions’ shared status/config/form primitives, and existing shell, dialog, tabs, skeleton, and toaster components. Add Spanish labels for all six call statuses, call types, and document types.

## PR Slice Boundaries

| PR | Autonomous deliverable |
|---|---|
| PR1 foundation | Types/schemas/constants/FSM/permissions, query keys, badge/sidebar, list and create, detail Overview, edit, action bar, base MSW handlers/tests. |
| PR2 nested managers + FSM | Documents, Projects, State history, delete gate, complete nested fixtures/handlers/tests; child branch targets PR1. |
| PR3 filters + polish + verify | Final status/type filter wiring, loading/error/accessibility polish, coverage hardening, `jest --coverage`, `tsc --noEmit`; child branch targets PR2. |

Each slice has independent route behavior, tests, and rollback by reverting its stacked commit. Forecast remains high against the 400-line budget; `auto-chain`/`stacked-to-main` is therefore required.

## Testing Strategy

Unit-test schemas, permissions, FSM action filtering, key shapes, and mutation invalidation. Component/route tests cover the 23 scenarios with RTL and mocked `api`/MSW fixtures, including 403/409, confirmations, redirects, empty states, and read-only history. Run Jest coverage (branch ≥80%), ESLint, and `tsc --noEmit`; no E2E is required by project config.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable documentation classification. | No test. |
| Git repository selection | N/A — no Git command integration. | No test. |
| Commit state | N/A — no commit automation. | No test. |
| Push state | N/A — no push automation. | No test. |
| PR commands | N/A — PR slicing is planning metadata only. | No test. |
| Application routing | Applicable — four new App Router routes. | Safe: authenticated routes render correct feature; failure: protected access follows existing auth boundary. RED tests assert each route path and auth handling. |

## Migration / Rollout

No migration required. Frontend-only rollout; revert stacked slices independently.

## Open Questions

- [ ] Confirm the auth store’s role payload always includes `director_centro` as `director` (or add that alias in `permissions.ts`).
