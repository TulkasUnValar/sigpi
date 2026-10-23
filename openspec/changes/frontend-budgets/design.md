# Design: Frontend Budgets Module

## Technical Approach

Build an institution-scoped `features/budgets` module using the established patterns (researchers/projects/calls): thin Next.js App Router pages, client feature components, TanStack Query for server state, Zustand only for auth/institution context, RHF + zod for forms, and `api`/`ApiError` for transport. UI copy remains Spanish. The backend contract is consumed unchanged; RN-020 (execution ≤ approved) is enforced server-side but surfaced clearly in the UI.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Feature boundary | Keep all budget types, hooks, forms, managers, and tests under `features/budgets`; pages only compose them. | Put API logic in route pages. | Matches established pattern, keeps routes replaceable/testable. |
| Server state | One `budgets` query-key factory with institution id, filters/page, detail, and nested resources (lines, executions, sources, attachments, summary); invalidate budget root after successful mutations. | Zustand cache or optimistic updates. | TanStack Query already owns API state; server guards (RN-020) and 400s make refetch safer than optimistic state. |
| Authorization | UI helpers/`RoleGuard` use `director`, `admin`, `superadmin` for create/update; `director` for over-execution authorization; backend remains authoritative. | Hide only by HTTP failure. | Consistent affordances while preserving server security. |
| Decimal handling | Use string representation in forms (controlled inputs), parse to Decimal in API calls, format for display with `Intl.NumberFormat`. | Use number inputs directly. | Avoids floating-point precision errors; matches backend DecimalField(14,2). |
| Execution validation | Rely on backend RN-020 enforcement (400 on overrun); show executed vs approved in UI; separate authorization dialog for director+. | Client-side pre-validation. | Server is authoritative; client validation is UX enhancement, not security boundary. |
| Nested data | Dedicated query/mutation hooks and managers; lines/executions are nested under budget; sources are nested under project; attachments are metadata-only. | Embed mutable nested state in the budget form. | Mirrors DRF endpoints and prevents accidental complexity. |

## Data Flow

```text
AuthStore institutionId + roles
        ↓
Page → feature query hook → queryKeys.budgets → api (+ X-Institution-ID) → DRF
        ↓                                      ↑
  components ← query cache ← mutation success ─┘ invalidate budgets root
```

List params serialize `page`, `project`, `status`; detail queries use the budget id. Mutations cover:
- Budget: create, patch, delete
- Lines: create, patch, delete
- Executions: create (with optional authorization fields)
- Sources: create, patch, delete
- Attachments: create, patch, delete

Error callbacks pass `ApiError` to `getErrorMessage`/Toaster; validation errors map to RHF fields; RN-020 violations show executed vs approved clearly.

## File Layout

```text
frontend/features/budgets/
  index.ts types.ts constants.ts schemas.ts permissions.ts
  queries.ts mutations.ts
  BudgetList.tsx BudgetForm.tsx BudgetDetail.tsx
  BudgetLinesManager.tsx FundingSourcesManager.tsx
  BudgetExecutionsManager.tsx AttachmentsManager.tsx
  BudgetSummary.tsx
frontend/app/budgets/
  page.tsx
  new/page.tsx
  [id]/page.tsx
  [id]/edit/page.tsx
  [id]/lines/[lid]/page.tsx
  [id]/lines/[lid]/executions/page.tsx
frontend/fixtures/budgets.ts
frontend/__tests__/features/budgets/
  schemas.test.ts permissions.test.ts queries.test.ts mutations.test.ts
  list.test.tsx detail.test.tsx managers.test.tsx routes.test.tsx
```

Modify `frontend/lib/query-keys.ts`, `components/shell/Sidebar.tsx`, `mocks/handlers.ts`, and the fixture index. `budgets` types mirror `Budget`, `BudgetLine`, `FundingSource`, `BudgetExecution`, `BudgetAttachment`, and `Page<T>`; form payloads omit read-only institution/timestamps.

## Component Breakdown

- `/budgets` — paginated table of budgets with project name, approved_amount, status, executed/balance summary; RoleGuard-gated create CTA (admin/director)
- `/budgets/new` — form to create budget linked to project (select project, enter name, approved_amount)
- `/budgets/[id]` — detail with tabs: Overview (summary indicators), Lines (rubros), Funding Sources, Executions, Attachments; edit/delete controls (admin/director)
- `/budgets/[id]/edit` — patch form for approved_amount, name
- `/budgets/[id]/lines/[lid]` — line detail with executions list
- `/budgets/[id]/lines/[lid]/executions` — record execution form with amount, executed_at; if amount > (approved - executed), show authorization dialog requiring director confirmation

**Managers**:
- `BudgetLinesManager` — CRUD rubros with approved_amount; show sum vs budget approved_amount
- `FundingSourcesManager` — CRUD sources (name, amount); show total vs budget approved_amount
- `BudgetExecutionsManager` — list executions per line; show executed sum vs approved; authorization dialog for over-execution
- `AttachmentsManager` — metadata-only CRUD (name, doc_type, external_url)
- `BudgetSummary` — display approved/executed/balance indicators (IND-007/008/009)

Reuse researchers' list/detail/page/query/mutation/error patterns, calls' manager patterns, projects' pagination conventions, and existing shell, dialog, tabs, skeleton, and toaster components. Add Spanish labels for budget statuses, doc types.

## PR Slice Boundaries

| PR | Autonomous deliverable |
|---|---|
| PR1 foundation | Types/schemas/constants/permissions, query keys, Sidebar, budget CRUD (list/create/detail/edit), summary indicators, base MSW handlers/tests. |
| PR2 nested managers | Lines, funding sources, attachments managers; nested routes; fixtures/handlers/tests; child branch targets PR1. |
| PR3 execution + verify | Executions manager with RN-020 validation, authorization dialog, polish, coverage hardening, `jest --coverage`, `tsc --noEmit`; child branch targets PR2. |

Each slice has independent route behavior, tests, and rollback by reverting its stacked commit. Forecast remains high against the 400-line budget; `auto-chain`/`stacked-to-main` is required.

## Testing Strategy

Unit-test schemas (Decimal validation, date ordering), permissions, key shapes, and mutation invalidation. Component/route tests cover scenarios with RTL and mocked `api`/MSW fixtures, including:
- RN-020 enforcement (400 on overrun without authorization)
- Authorization flow (director confirms over-execution)
- 403 role denial
- Decimal precision (string → Decimal → display)
- Empty states, confirmations, redirects

Run Jest coverage (branch ≥80%), ESLint, and `tsc --noEmit`; no E2E is required by project config.

## Threat Matrix

| Boundary | Applicability | Safe/failure behavior and RED test |
|---|---|---|
| Application routing | Applicable — six new App Router routes. | Safe: authenticated routes render correct feature; failure: protected access follows existing auth boundary. RED tests assert each route path and auth handling. |
| Decimal precision | Applicable — money fields. | Safe: string representation in forms, parsed to Decimal in API; failure: floating-point errors. RED tests assert Decimal validation and formatting. |
| RN-020 enforcement | Applicable — execution ≤ approved. | Safe: backend 400; failure: client allows overrun. RED tests assert 400 handling and UI feedback. |

## Migration / Rollout

No migration required. Frontend-only rollout; revert stacked slices independently.

## Open Questions

- [ ] Confirm the auth store's role payload always includes `director_centro` as `director` (or add that alias in `permissions.ts`).
- [ ] Verify backend Decimal serialization format (string vs number) to ensure frontend parsing matches.
