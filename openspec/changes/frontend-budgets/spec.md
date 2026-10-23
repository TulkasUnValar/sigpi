# Budgets UI Specification (budgets-ui)

**Status**: New capability — full spec. Backend `budgets` spec unchanged.

## Purpose

Frontend management module for project budgets with 5 entities: Budget (one per project), BudgetLine (rubros), FundingSource (fuentes de financiación), BudgetExecution (ejecución presupuestal), and BudgetAttachment (metadata-only). Provides CRUD operations, RN-020 enforcement (execution ≤ approved), director authorization for over-execution, and summary indicators (IND-007/008/009). Reuses established patterns from calls/researchers/projects.

## Functional Requirements (RF)

### Requirement: RF-B01 — Budget CRUD

The system MUST support create, read, update, and delete of budgets; one budget per project (OneToOne); list and detail MUST load without errors.

#### Scenario: Admin creates budget
- GIVEN an admin/director on `/budgets/new`
- WHEN the RHF + zod form submits valid data (project, name, approved_amount)
- THEN POST `/api/budgets/` succeeds and the budget list refetches

#### Scenario: Duplicate budget rejected
- GIVEN a project already has a budget
- WHEN the form submits for the same project
- THEN 409 `{"detail":"Project already has a budget."}` surfaces via Toaster

#### Scenario: Researcher read-only
- GIVEN a researcher on `/budgets`
- WHEN viewing the list
- THEN create CTA is hidden; detail is read-only

### Requirement: RF-B02 — Budget Line CRUD

The system MUST support CRUD of `BudgetLine` records (rubros) with `name` and `approved_amount`; lines MUST be reachable nested under their budget.

#### Scenario: Create line
- GIVEN an existing budget
- WHEN POSTing to `/api/budgets/{id}/lines/` with `name`, `approved_amount`
- THEN the line appears in the lines manager

#### Scenario: Line sum validation
- GIVEN a budget with `approved_amount=10000`
- WHEN lines sum to 12000
- THEN UI shows warning (sum exceeds budget approved_amount)

#### Scenario: Delete line with executions
- GIVEN a line with executions
- WHEN DELETE is requested
- THEN 409 guard detail surfaces (cannot delete line with executions)

### Requirement: RF-B03 — Funding Source CRUD

The system MUST support CRUD of `FundingSource` records linked to project; a project MUST support one or more sources (RN-019).

#### Scenario: Add second source
- GIVEN a project with one funding source
- WHEN POSTing with `name`, `amount`
- THEN the second source is created (RN-019 allows multiple)

#### Scenario: Source sum validation
- GIVEN a budget with `approved_amount=10000`
- WHEN funding sources sum to 8000
- THEN UI shows "Fuentes cubren 80% del presupuesto"

### Requirement: RF-B04 — Budget Execution

The system MUST support CRUD of `BudgetExecution` records with `amount` and `executed_at`; sum of executions per line MUST NOT exceed the line's `approved_amount` unless authorized (RN-020).

#### Scenario: Execution within approved
- GIVEN a budget line with `approved_amount=1000`
- WHEN POSTing execution with `amount=400`
- THEN the execution is created

#### Scenario: Over-execution without authorization rejected
- GIVEN a line with `approved_amount=1000` and executions summing 900
- WHEN POSTing execution with `amount=200` (would total 1100) with no `authorized_by`
- THEN 400 `{"detail":"Execution exceeds approved budget for this line."}` surfaces via Toaster

#### Scenario: Over-execution authorized
- GIVEN a director_centro
- WHEN POSTing over-limit execution with `authorized_by` set and `authorized_at`
- THEN the execution is created with authorization recorded

#### Scenario: Authorization dialog
- GIVEN an execution attempt exceeds approved amount
- WHEN the user submits
- THEN a ConfirmDialog appears requiring director confirmation

### Requirement: RF-B05 — Budget Attachment

The system MUST store `BudgetAttachment` metadata-only records with `name`, `doc_type`, `external_url`. No file upload in MVP.

#### Scenario: Add metadata attachment
- GIVEN an existing budget
- WHEN POSTing with `name`, `doc_type`, `external_url`
- THEN the attachment is created

#### Scenario: Reject missing external_url
- GIVEN an existing budget
- WHEN POSTing attachment without `external_url`
- THEN 400 validation error surfaces

### Requirement: RF-B06 — Query by project/institution/status

The system MUST filter budgets by `project`, `institution`, and `status`. All queries MUST be institution-scoped.

#### Scenario: Filter by project
- GIVEN budgets across multiple projects
- WHEN GET `/api/budgets/?project={id}`
- THEN only the matching project's budget is returned

#### Scenario: Cross-institution hidden
- GIVEN a budget in Institution Y
- WHEN a user of Institution X GETs it by id
- THEN 404 (RLS hides the object)

### Requirement: RF-B07 — Summary endpoint

The system MUST expose a summary of approved, executed, and balance totals per budget (IND-007/008/009), consumable by the reports module (RN-022).

#### Scenario: Summary totals
- GIVEN a budget with lines and executions
- WHEN GET `/api/budgets/{id}/summary/`
- THEN `{"approved":…, "executed":…, "balance": approved - executed}` is displayed

#### Scenario: Summary without budget
- GIVEN a project with no budget
- WHEN the summary is requested
- THEN an empty/absent summary is shown (RN-022 conditional)

## Non-Functional Requirements (RNF)

| ID | Requirement |
|---|---|
| RNF-01 | Jest coverage MUST be ≥80% per slice. |
| RNF-02 | ESLint and `tsc --noEmit` MUST be green per PR. |
| RNF-03 | All UI copy MUST be Spanish. |
| RNF-04 | Loading states MUST use existing Skeleton/EmptyState patterns. |
| RNF-05 | All server data MUST flow through TanStack Query — no raw fetches in components. |
| RNF-06 | Decimal fields MUST use string representation in forms, parsed to Decimal in API calls. |
| RNF-07 | Money display MUST use `Intl.NumberFormat` with proper locale (es-CO). |

## User Stories

- **As an admin**, I create the first budget for a project and manage lines/sources.
- **As a director**, I authorize over-executions when necessary and review summary indicators.
- **As a researcher**, I view budget status and execution progress (read-only).
- **As any user**, I browse budgets by project and understand the financial status at a glance.

## API Integration Contract

| API | Methods | Query key | Notes |
|---|---|---|---|
| `/api/budgets/`, `/api/budgets/{pk}/` | GET, POST, PATCH, DELETE | `budgets.list/detail` | DRF paginated; reads open to authenticated users |
| `/api/budgets/{pk}/lines/`, `/.../lines/{pk}/` | GET, POST, PATCH, DELETE | `budgets.lines` | nested under budget |
| `/api/budgets/{pk}/lines/{pk}/executions/` | GET, POST | `budgets.executions` | RN-020 enforced |
| `/api/projects/{pk}/funding-sources/`, `/.../funding-sources/{pk}/` | GET, POST, PATCH, DELETE | `budgets.sources` | linked to project, not budget |
| `/api/budgets/{pk}/attachments/`, `/.../attachments/{pk}/` | GET, POST, PATCH, DELETE | `budgets.attachments` | metadata-only |
| `/api/budgets/{pk}/summary/` | GET | `budgets.summary` | IND-007/008/009 |

- Pagination: consume DRF `{count, next, previous, results}`.
- Tenant scoping: all scoped queries keyed off the auth store `activeInstitution`; `X-Institution-ID` header sent.
- Decimal fields: backend sends strings (e.g., `"1000.00"`), frontend parses to number for display, sends back as string.
- RN-020: backend enforces; frontend surfaces 400 clearly with executed vs approved context.

## State Management

- Add a `budgets` factory to `lib/query-keys.ts` mirroring the calls/projects pattern (all/lists/list/detail/lines/executions/sources/attachments/summary).
- Mutations MUST invalidate `budgets.all` (and derived detail) on success; MUST NOT invalidate on failure.
- Budget switch MUST clear the scoped cache (existing auth-store behavior, reused).

## Testing Requirements

- MSW fixtures and handlers for all 5 entities; existing projects-wizard consumers stay green.
- Jest ≥80% per slice (RNF-01). Managers tests MUST cover RN-020 enforcement, authorization dialog, 400 validation, and network failure; RoleGuard tests MUST cover read-only denial for researcher.
- Decimal precision tests: string → Decimal → display formatting.

## Error Handling

| Error | Behavior |
|---|---|
| 400 RN-020 ("Execution exceeds approved budget") | Backend `detail` verbatim via Toaster; show executed vs approved; no invalidation |
| 409 duplicate budget | Backend `detail` verbatim via Toaster; form keeps values |
| 409 delete line with executions | Backend `detail` verbatim via Toaster; line persists |
| 400 validation (missing external_url) | Field errors mapped into the RHF form |
| 403 role denial | RoleGuard hides action or surfaces 403 |
| Network failure | Toaster error with retry; no partial cache writes |

## Slice Mapping

| Slice | Requirements |
|---|---|
| 1 (PR 1) | RF-B01, RF-B06, RF-B07; query-keys factory; MSW fixtures; RNF-01/02/03 foundation |
| 2 (PR 2) | RF-B02, RF-B03, RF-B05; nested managers and routes |
| 3 (PR 3) | RF-B04 (execution + authorization); polish; RNF completion |

## Risks

| Risk | Mitigation |
|---|---|
| Decimal precision errors | Use string representation in forms; parse to Decimal in API; format with Intl.NumberFormat |
| RN-020 validation UX | Surface 400 clearly; show executed vs approved in UI; authorization dialog for director |
| Nested route complexity (lines/executions) | Clear route structure; reuse patterns from calls managers |
| Over-execution authorization complexity | Separate dialog; require director role; record authorized_by/authorized_at |
