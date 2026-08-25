# Delta for Reports

## MODIFIED Requirements

### Requirement: Project Report (RF-050)

The system MUST generate a PDF report containing project general data, objectives, team, budget summary, results, and progress. The budget summary section MUST be populated from the budgets module summary endpoint (RN-022) when the project has a registered budget, and SHALL be omitted/empty when it does not. The remaining sections are unchanged.
(Previously: budget summary was a placeholder; no budgets endpoint existed.)

#### Scenario: Generate project report

- GIVEN a project exists and the user has read access
- WHEN GET `/api/reports/project/{id}/pdf/`
- THEN the system streams a valid PDF with project data

#### Scenario: Report includes budget summary

- GIVEN a project with a registered Budget and executions
- WHEN the project report is generated
- THEN the budget summary section renders approved, executed, and balance from `/api/budgets/{id}/summary/`

#### Scenario: Report omits budget summary when absent

- GIVEN a project with no Budget
- WHEN the project report is generated
- THEN the budget summary section is omitted from the PDF

#### Scenario: Unauthorized project access

- GIVEN a user lacks read permission on the project
- WHEN GET `/api/reports/project/{id}/pdf/`
- THEN the system returns 403

## Non-Functional Requirements

- The summary endpoint MUST be tested before the report template is wired (contract stability).
