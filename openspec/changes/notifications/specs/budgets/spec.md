# Delta for Budgets Capability (Notifications Change)

Adds the `budget_overrun_attempted` signal emission required by the notifications module (RN-4, HU-005).

## MODIFIED Requirements

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