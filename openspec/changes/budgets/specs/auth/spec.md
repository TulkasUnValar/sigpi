# Delta for Auth

## MODIFIED Requirements

### Requirement: FR-007 — Auth Audit Events

The system MUST emit audit events for login, logout, role change, and permission denied, and SHALL extend `AuditEventType` with `BUDGET_CREATED`, `BUDGET_UPDATED`, and `BUDGET_EXECUTION_ADDED` for budget audit (RN-021). The existing login/logout/role-change/permission-denied behavior is unchanged.
(Previously: only login, logout, role change, and permission denied event types.)

#### Scenario: Successful login audit

- GIVEN a user logs in successfully
- WHEN the session is created
- THEN an audit event is emitted with user, timestamp, IP, auth source, and institution

#### Scenario: Budget create audit

- GIVEN a Budget is created via the budgets module
- WHEN `AuditEventEmitter.emit` is called with `BUDGET_CREATED`
- THEN an AuditEvent is persisted with `event_type="BUDGET_CREATED"` and the acting user

#### Scenario: Budget update audit

- GIVEN a Budget is updated
- WHEN `AuditEventEmitter.emit` is called with `BUDGET_UPDATED`
- THEN an AuditEvent is persisted with `event_type="BUDGET_UPDATED"`

#### Scenario: Budget execution audit

- GIVEN a BudgetExecution is added
- WHEN `AuditEventEmitter.emit` is called with `BUDGET_EXECUTION_ADDED`
- THEN an AuditEvent is persisted with `event_type="BUDGET_EXECUTION_ADDED"` and details naming the line and amount

## Non-Functional Requirements

- The three new event types MUST be added to the `AuditEventType` TextChoices enum without altering existing values.
