# Design: Frontend Reports Module (SIGPI §6.6)

## Technical Approach

Add a client-side `features/reports` module following the completed products, projects, researchers, and calls conventions: typed API wrappers, institution-scoped TanStack Query hooks, shadcn/ui components, Sonner toasts, MSW handlers, and Jest/RTL tests. The `/reports` hub composes existing project, researcher, and center hooks; it MUST NOT introduce a reports list endpoint. Report status is a UI projection (`No generado`, `Generado`, `Aprobado`) updated from successful operations, because the backend exposes only preview, PDF, and approve actions.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| Entity sourcing | Reuse `useProjectsList`, `useResearchersList`, and `useCenters` | New report registry API | The backend has no list/status endpoint; reuse preserves institution scoping. |
| Preview | `useReportPreview` query plus sandboxed iframe `srcDoc` | `dangerouslySetInnerHTML`, external URL | `srcDoc` matches the PDF HTML while `sandbox` without `allow-same-origin` limits untrusted markup. |
| PDF download | Authenticated `fetch` → `blob` → `URL.createObjectURL` → temporary anchor | Plain `href`, opening a new tab | Session credentials and `X-Institution-ID` must be sent; a plain link can return 401. |
| Approval | `useApproveReport` mutation, rendered only for director/admin bypass | Client-only hidden button without server handling | UI gating improves safety, while the backend remains authoritative. 409 handling preserves the RN-017 message and cache. |

## Architecture

```text
frontend/features/reports/
  types.ts constants.ts permissions.ts queries.ts mutations.ts download.ts
  ReportHub.tsx ReportGeneratorForm.tsx PreviewDialog.tsx
  DownloadButton.tsx ApprovalButton.tsx index.ts
frontend/app/reports/page.tsx
```

`page.tsx` supplies `AuthenticatedLayout`; `ReportHub` owns composition and local selection. Feature components remain client components and use existing Card, Select, Dialog, Button, StatusBadge, Skeleton, EmptyState, and Sonner patterns.

## Data Flow

`queryKeys.reports` provides `all`, `preview(institutionId,type,id)`, and derived entity-list keys. Queries call `GET /api/reports/{type}/{id}/preview/` with `institutionId`; entity hooks provide selectors (`advances` deliberately maps to projects). PDF and approval are mutations/actions calling `/pdf/` and `/approve/` with the same institution scope.

```text
entity hooks → ReportHub → generator selection
                         ├→ preview query → PreviewDialog(srcDoc)
                         ├→ authenticated blob fetch → DownloadButton
                         └→ approve mutation → local status + entity invalidation
```

Successful approval invalidates the relevant project/researcher/center query roots and the derived report view. RN-017 409 does not invalidate anything. Preview and PDF do not invent or cache a report registry.

## Component Design and State

`ReportHub` selects report type/entity and renders derived lists. `ReportGeneratorForm` uses controlled local values and resets the entity when type changes. `PreviewDialog` keeps only `open`, selected target, and returned HTML locally; it renders `<iframe sandbox srcDoc={html}>`. `DownloadButton` exposes pending/disabled state during WeasyPrint generation. `ApprovalButton` checks `canApproveReport(user, roles, entity)` and is absent for non-directors. Server state uses TanStack Query; only preview-modal selection/open state is local UI state.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/features/reports/*` | Create | Types, constants, permission helpers, hooks, download utility, and components. |
| `frontend/app/reports/page.tsx` | Create | Protected hub entry point. |
| `frontend/lib/query-keys.ts` | Modify | Add institution-scoped reports factory. |
| `frontend/components/shell/Sidebar.tsx` | Modify | Add Spanish `Informes` navigation item. |
| `frontend/middleware.ts` | Modify | Add `/reports` to protected prefixes. |
| `frontend/fixtures/*`, `frontend/mocks/handlers.ts` | Modify | HTML, PDF, approval, success, and 403/404/409/500 scenarios. |

## Interfaces / Contracts

```ts
type ReportType = "project" | "researcher" | "center" | "advances";
type ReportStatus = "not_generated" | "generated" | "approved";
type ReportTarget = { type: ReportType; entityId: string; entityName: string };
```

All requests include `credentials: "include"` through the existing API client and `X-Institution-ID`. `downloadBlob(path, filename, institutionId)` owns authenticated blob cleanup. API errors use `ApiError.status`; Sonner displays 403/404/409/500 messages, with the 409 RN-017 server message shown verbatim.

## Testing Strategy

Jest + RTL + MSW: unit-test key factories, permissions, filename/download cleanup, dependent type mapping, iframe sandbox attributes, pending disabling, and 403/404/409/500 toast behavior. Component tests cover hub rendering, advances→projects, director-only approval, successful invalidation, and RN-017 no-invalidation. Maintain ≥80% coverage for `features/reports`; run ESLint and `tsc --noEmit` per PR.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable documentation | None | None |
| Git repository selection | N/A — no Git automation | None | None |
| Commit state | N/A — no commit automation | None | None |
| Push state | N/A — no push automation | None | None |
| PR commands | N/A — no PR automation | None | None |

Routing is changed only by adding a normal Next.js protected route; no shell, subprocess, VCS, executable-file, or process-integration boundary is introduced.

## Migration / Rollout

No data migration or feature flag. Deliver as chained PRs: **PR1** foundation (types, keys, queries/mutations, download utility, route, sidebar, middleware, MSW); **PR2** generator, preview dialog, and download UX; **PR3** approval gating, derived lists/status projection, error states, and final tests. Each slice is independently revertible and targets the 400-line review budget.

## Open Questions

- [ ] Confirm whether future backend responses will expose persisted report status; until then, keep status explicitly derived in the UI.
