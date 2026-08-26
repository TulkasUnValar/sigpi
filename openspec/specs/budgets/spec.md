# Budgets Specification (SIGPI §6.9)

## Purpose

Manage project-scoped budgets: one Budget per project, budget lines (rubros), funding sources, execution records, and metadata-only attachments. Feeds approved/executed/balance indicators (IND-007/008/009) and the project report budget summary (RN-022). All entities are institution-scoped via RLS and audited per RN-021.

## Requirements

### Requirement: Budget CRUD (RF-B01)

The system MUST allow CRUD of exactly one Budget per project (`OneToOne` FK→Project). A Budget MUST be institution-scoped and SHALL carry `approved_amount` (Decimal). Creating a second Budget for the same project MUST be rejected.

#### Scenario: Create budget
- GIVEN an admin/director of Institution I and a Project P in I with no budget
- WHEN POST `/api/budgets/` with `project`, `approved_amount`, `name`
- THEN a Budget is created with `institution=I`

#### Scenario: Duplicate budget rejected
- GIVEN Project P already has a Budget
- WHEN POST `/api/budgets/` for P again
- THEN 409 `{"detail":"Project already has a budget."}`

### Requirement: Budget Line CRUD (RF-B02)

The system MUST allow CRUD of `BudgetLine` records (`FK→Budget`) with `name` (rubro) and `approved_amount` (Decimal). Lines MUST be reachable nested under their Budget.

#### Scenario: Create line
- GIVEN an existing Budget
- WHEN POST `/api/budgets/{id}/lines/` with `name`, `approved_amount`
- THEN a BudgetLine is created under that Budget

#### Scenario: List lines
- GIVEN a Budget with 3 lines
- WHEN GET `/api/budgets/{id}/lines/`
- THEN 3 line objects are returned

### Requirement: Funding Source CRUD (RF-B03)

The system MUST allow CRUD of `FundingSource` records (`FK→Project`). A project MUST support one or more sources (RN-019). Each source SHALL carry `name` and `amount`.

#### Scenario: Add second source
- GIVEN a Project with one FundingSource
- WHEN POST `/api/projects/{pid}/funding-sources/` with `name`, `amount`
- THEN a second FundingSource is created (RN-019 allows multiple)

### Requirement: Budget Execution (RF-B04)

The system MUST allow CRUD of `BudgetExecution` records (`FK→BudgetLine`) with `amount` (Decimal) and `executed_at` (Date). Sum of executions per line MUST NOT exceed the line's `approved_amount` unless authorized (RN-020). When an over-limit execution is attempted without authorization, the system SHALL emit a `budget_overrun_attempted` signal carrying `budget_line`, `attempted_amount`, `requested_by`, and `institution`, so the notifications module can alert an institution admin (RN-4).
(Previously: over-limit executions were rejected with 400 only; no overrun signal was emitted.)

#### Scenario: Execution within approved
- GIVEN a BudgetLine with `approved_amount=1000`
- WHEN POST `/api/budgets/{id}/lines/{lid}/executions/` with `amount=400`
- THEN the execution is created

#### Scenario: Over-execution without authorization rejected
- GIVEN a BudgetLine with `approved_amount=1000` and executions summing 900
- WHEN POST an execution with `amount=200` (would total 1100) with no `authorized_by`
- THEN 400 `{"detail":"Execution exceeds approved budget for this line."}`

#### Scenario: Over-execution authorized
- GIVEN a director_centro or user with the custom budget-authorization permission
- WHEN POST an over-limit execution with `authorized_by` set and `authorized_at`
- THEN the execution is created with authorization recorded

#### Scenario: Overrun attempt emits signal
- GIVEN an over-limit execution attempt rejected with 400
- WHEN the service raises the ValidationError
- THEN `budget_overrun_attempted` is emitted with the line, attempted amount, requesting user, and institution

#### Scenario: No signal on successful execution
- GIVEN an execution within the approved amount or with authorization
- WHEN the execution is created
- THEN no `budget_overrun_attempted` signal is emitted
### Requirement: Budget Attachment (RF-B05)

The system MUST store `BudgetAttachment` metadata-only records (`FK→Budget`) with `name`, `doc_type`, `external_url`. No file upload in MVP.

#### Scenario: Add metadata attachment
- GIVEN an existing Budget
- WHEN POST `/api/budgets/{id}/attachments/` with `name`, `doc_type`, `external_url`
- THEN a BudgetAttachment is created

#### Scenario: Reject missing external_url
- GIVEN an existing Budget
- WHEN POST an attachment without `external_url`
- THEN 400

### Requirement: Query by project/institution/status (RF-B06)

The system MUST filter Budgets by `project`, `institution`, and `status`. All queries MUST be institution-scoped.

#### Scenario: Filter by project
- GIVEN Budgets across multiple projects in Institution I
- WHEN GET `/api/budgets/?project={id}`
- THEN only the matching project's budget is returned

#### Scenario: Cross-institution hidden
- GIVEN a Budget in Institution Y
- WHEN a user of Institution X GETs it by id
- THEN 404 (RLS hides the object)

### Requirement: Summary endpoint (RF-B07)

The system MUST expose a summary of approved, executed, and balance totals per Budget (IND-007/008/009), consumable by the reports module (RN-022).

#### Scenario: Summary totals
- GIVEN a Budget with lines and executions
- WHEN GET `/api/budgets/{id}/summary/`
- THEN `{"approved":…, "executed":…, "balance": approved - executed}` is returned

#### Scenario: Summary without budget
- GIVEN a project report requested for a Project with no Budget
- WHEN the reports module queries the summary
- THEN an empty/absent summary is returned (RN-022 conditional)

## Data Model

| Entity | Key Fields | Constraints |
|---|---|---|
| **Budget** | `id` (UUID PK), `project` (OneToOne→Project), `institution` (FK), `institution_id` (denorm RLS), `name`, `approved_amount` (Decimal), `status`, `created_at`, `updated_at` | Unique project; Decimal(14,2) |
| **BudgetLine** | `id` (UUID PK), `budget` (FK→Budget), `name`, `approved_amount` (Decimal) | Decimal(14,2) |
| **FundingSource** | `id` (UUID PK), `project` (FK→Project), `name`, `amount` (Decimal) | One or more per project |
| **BudgetExecution** | `id` (UUID PK), `line` (FK→BudgetLine), `amount` (Decimal), `executed_at` (Date), `authorized_by` (FK→User, null), `authorized_at` (null) | RN-020: sum ≤ approved unless authorized |
| **BudgetAttachment** | `id` (UUID PK), `budget` (FK→Budget), `name`, `doc_type`, `external_url` | metadata-only |

## API Contract

| Endpoint | Method | Auth |
|---|---|---|
| `/api/budgets/` | GET, POST | Session |
| `/api/budgets/{id}/` | GET, PATCH, DELETE | Session |
| `/api/budgets/{id}/lines/` | GET, POST | Session |
| `/api/budgets/{id}/lines/{lid}/executions/` | GET, POST | Session |
| `/api/budgets/{id}/attachments/` | GET, POST | Session |
| `/api/budgets/{id}/summary/` | GET | Session |
| `/api/projects/{pid}/funding-sources/` | GET, POST | Session |

## Security & Permissions

| Action | Superadmin | Admin | Director Centro | Researcher |
|---|---|---|---|---|
| Create/update Budget, Lines, Sources, Attachments | ✓ | ✓ | ✓ | — |
| Record execution (within limit) | ✓ | ✓ | ✓ | — |
| Authorize over-execution | ✓ | ✓ | ✓ (director) | — |
| Read (institution-scoped) | ✓ (all) | ✓ (all) | ✓ (own) | ✓ (own) |

## Audit (RN-021)

- `BUDGET_CREATED` on Budget create
- `BUDGET_UPDATED` on Budget update
- `BUDGET_EXECUTION_ADDED` on each execution

## RLS

All budget tables MUST carry `tenant_isolation` and `superadmin_bypass` policies in a per-app `0002_rls_policies.py`.

## Error Handling

| Error | Status |
|---|---|
| Duplicate budget per project | 409 |
| Over-execution without authorization | 400 |
| RLS cross-institution access | 404 |

## Non-Functional Requirements

- Test coverage MUST be ≥90% on `apps.budgets` (strict TDD).
- Money fields MUST be `DecimalField(max_digits=14, decimal_places=2)`.
- RN-020 MUST be enforced in the service layer (no direct FK writes bypass).
- Every mutation MUST emit an audit event (RN-021).
