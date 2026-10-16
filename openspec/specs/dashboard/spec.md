# Dashboard Specification (SIGPI §6.12)

## Purpose

Provide institutional BI metrics via server-side aggregation endpoint. The dashboard exposes 14 indicators (IND-001 to IND-014) covering projects, budgets, researchers, products, calls, and progress reports. All computations are institution-scoped and role-gated (RF-090..RF-092).

## Data Model

The dashboard does not own data models. It aggregates from existing domain models:

| Source Model | Indicators Derived |
|---|---|
| `Project` | IND-001 (active count), IND-002 (by center), IND-003 (by status) |
| `ProgressReport` | IND-004 (pending), IND-005 (observed), IND-006 (compliance %) |
| `Budget` + `BudgetExecution` | IND-007 (approved), IND-008 (executed), IND-009 (balance) |
| `ResearchProduct` + `ProductAuthor` | IND-010 (by project, top 10), IND-011 (by researcher, top 10) |
| `Researcher` | IND-012 (profile completeness) |
| `Call` + `CallProject` | IND-013 (open calls), IND-014 (projects in external calls) |

## Functional Requirements

### Requirement: RF-Dash01 — Summary Endpoint (RF-090)

The system MUST expose a single endpoint returning all 14 indicators and chart data for the authenticated user's institution.

#### Scenario: Authenticated director requests summary
- GIVEN an authenticated user with director role (level 3) or higher
- WHEN GET `/api/dashboard/summary/`
- THEN the system returns a JSON response with `indicators` and `charts` sections scoped to `request.institution_id`

#### Scenario: Researcher scoped to own projects
- GIVEN an authenticated researcher (level 4)
- WHEN GET `/api/dashboard/summary/`
- THEN the system returns indicators scoped to projects where the researcher is a member

#### Scenario: Missing institution context
- GIVEN a request without `request.institution_id` (tenant middleware failure)
- WHEN GET `/api/dashboard/summary/`
- THEN the system returns 400 with `{"detail": "Institution context required."}`

### Requirement: RF-Dash02 — Indicator Definitions (RF-091)

The system MUST compute the following 14 indicators:

| Code | Name | Type | Definition |
|---|---|---|---|
| IND-001 | Total proyectos activos | int | `Project.objects.filter(institution_id=..., is_active=True).count()` |
| IND-002 | Proyectos por centro | list | `[{center_id, name, count}]` ordered by count desc |
| IND-003 | Proyectos por estado | list | `[{status, count}]` ordered by count desc |
| IND-004 | Avances pendientes | int | Count of `ProgressReport` with `status=en_revision` |
| IND-005 | Avances observados | int | Count of `ProgressReport` with `status=observado` |
| IND-006 | Cumplimiento de reportes | float | `(approved_progress_reports / expected_periods) * 100` |
| IND-007 | Presupuesto aprobado | str | Sum of `Budget.approved_amount` formatted as currency |
| IND-008 | Presupuesto ejecutado | str | Sum of `BudgetExecution.amount` formatted as currency |
| IND-009 | Saldo presupuestal | str | `(approved - executed)` formatted as currency |
| IND-010 | Productos por proyecto | list | Top 10 projects by product count: `[{project_id, title, count}]` |
| IND-011 | Productos por investigador | list | Top 10 researchers by product count: `[{researcher_id, name, count}]` |
| IND-012 | Perfiles completos | dict | `{total, complete, rate}` where `rate = (complete / total) * 100` |
| IND-013 | Convocatorias abiertas | int | Count of `Call` with `status=abierta` |
| IND-014 | Proyectos en convocatorias externas | int | Count of `CallProject` where `Call.external_entity` is not null |

#### Scenario: Indicator computation accuracy
- GIVEN an institution with 15 active projects, 3 pending advances, 2 observed advances
- WHEN GET `/api/dashboard/summary/`
- THEN `IND-001 = 15`, `IND-004 = 3`, `IND-005 = 2`

#### Scenario: Budget indicators
- GIVEN an institution with budgets totaling 100M approved and 40M executed
- WHEN GET `/api/dashboard/summary/`
- THEN `IND-007 = "100.000.000"`, `IND-008 = "40.000.000"`, `IND-009 = "60.000.000"`

#### Scenario: Profile completeness
- GIVEN an institution with 10 researchers, 7 with complete profiles
- WHEN GET `/api/dashboard/summary/`
- THEN `IND-012 = {total: 10, complete: 7, rate: 70.0}`

### Requirement: RF-Dash03 — Chart Data (RF-092)

The system MUST return pre-aggregated data structures for frontend charts:

#### Scenario: Chart data structure
- GIVEN a valid summary request
- WHEN the response is serialized
- THEN the `charts` section contains:
  - `projects_by_status`: `[{status, count}]`
  - `projects_by_center`: `[{center_id, name, count}]`
  - `budget`: `{approved, executed, balance}` as numeric strings
  - `progress_reports`: `{pending, observed, approved}` as integers

#### Scenario: Empty institution data
- GIVEN an institution with no projects or budgets
- WHEN GET `/api/dashboard/summary/`
- THEN all indicators return zero/empty values, not null

## API Contract

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/dashboard/summary/` | GET | Session | 14 indicators + chart data |

### Response Shape

```json
{
  "indicators": {
    "IND-001": 15,
    "IND-002": [
      {"center_id": "uuid", "name": "Centro A", "count": 8},
      {"center_id": "uuid", "name": "Centro B", "count": 7}
    ],
    "IND-003": [
      {"status": "activo", "count": 10},
      {"status": "finalizado", "count": 5}
    ],
    "IND-004": 3,
    "IND-005": 2,
    "IND-006": 85.5,
    "IND-007": "100.000.000",
    "IND-008": "40.000.000",
    "IND-009": "60.000.000",
    "IND-010": [
      {"project_id": "uuid", "title": "Proyecto X", "count": 12}
    ],
    "IND-011": [
      {"researcher_id": "uuid", "name": "Dr. Y", "count": 8}
    ],
    "IND-012": {"total": 10, "complete": 7, "rate": 70.0},
    "IND-013": 4,
    "IND-014": 6
  },
  "charts": {
    "projects_by_status": [{"status": "activo", "count": 10}],
    "projects_by_center": [{"center_id": "uuid", "name": "Centro A", "count": 8}],
    "budget": {"approved": "100000000", "executed": "40000000", "balance": "60000000"},
    "progress_reports": {"pending": 3, "observed": 2, "approved": 15}
  }
}
```

## Authorization

- `IsDashboardAuthorized` permission class enforces role-based access:
  - Superadmin (level 1): full access, no institution scoping
  - Admin (level 2): institution-scoped to `request.institution_id`
  - Director (level 3): institution/center-scoped
  - Researcher (level 4): scoped to projects where user is a member
  - Auditor (level 7): read-only access
- All roles ≥ director see full institutional metrics; researchers see only their projects

## Performance Requirements

- The summary endpoint SHOULD complete in < 500ms for institutions with ≤ 1000 projects
- All aggregations MUST use database-level queries (no Python loops over querysets)
- Use `Count`, `Sum`, `Coalesce` annotations to avoid N+1 queries
- Top-10 rankings (IND-010, IND-011) MUST use `ORDER BY ... LIMIT 10`

## Error Handling

| Error | Status | Response |
|---|---|---|
| Missing institution context | 400 | `{"detail": "Institution context required."}` |
| Unauthenticated | 401 | `{"detail": "Authentication credentials were not provided."}` |
| Insufficient permissions | 403 | `{"detail": "You do not have permission to perform this action."}` |

## Acceptance Criteria

- [ ] All 14 indicators return correct values for test fixtures
- [ ] Chart data structures match frontend expectations
- [ ] Role-based scoping works (researcher sees only own projects)
- [ ] Empty institution returns zero/empty values, not null
- [ ] Response time < 500ms for typical institution size
- [ ] Coverage on `apps.dashboard` ≥ 80%
- [ ] All RF-Dash01..RF-Dash03 scenarios pass under pytest

## Non-Functional Requirements

- The dashboard MUST NOT write data; it is read-only
- Currency formatting (IND-007..IND-009) MUST use Colombian peso format (thousands separator)
- Profile completeness (IND-012) defines "complete" as: `affiliations.exists() and external_profile.exists() and academic_formation != ""`
- Top-10 rankings (IND-010, IND-011) MUST be deterministic (secondary sort by id or name)
