# calls-ui Specification (SIGPI §6.8 — Frontend)

## Purpose

Frontend management UI for the archived `apps.calls` backend (4 entities, 6-state FSM): list with filters, create, 4-tab detail, edit, 5 FSM transitions, gated delete, and nested managers (Documents, Projects, State history). Reads are institution-scoped and open to all authenticated roles; writes are gated to `director`+ (`director_centro`, level ≤ 3). No backend changes.

## Requirements

### Requirement: Call list with filters

`/calls` MUST render the paginated list from `GET /api/calls/` (`Page<CallList>`, 25/page) with title, StatusBadge, call_type, submission dates, and created_at. The list MUST support `status` and `call_type` filters (`CallFilter`) and a `RoleGuard`-gated create CTA.

#### Scenario: Paginated list renders

- GIVEN the active institution has calls
- WHEN `/calls` loads
- THEN rows render with pagination controls, status badges, and call_type labels

#### Scenario: Filter by status

- GIVEN calls in `borrador` and `abierta`
- WHEN a user selects `abierta` and applies the filter
- THEN the list refetches `?status=abierta` and shows only abierta calls

#### Scenario: Filter by type

- GIVEN internal and external calls
- WHEN a user selects `external` and applies the filter
- THEN the list refetches `?call_type=external` and shows only external calls

#### Scenario: Empty institution

- GIVEN the institution has no calls
- WHEN `/calls` loads
- THEN an empty state with a create action renders

### Requirement: Create call

`/calls/new` MUST POST `/api/calls/` (director+). Writable fields match `CallSerializer`: `title`, `description`, `call_type`, conditional `external_entity`, and four nullable dates. zod MUST mirror backend rules — `external_entity` required for external, forbidden for internal; when present, end dates MUST be on or after start dates. Success MUST redirect to the new detail page.

#### Scenario: Create internal call succeeds

- GIVEN a director submits a valid internal call
- WHEN create is pressed
- THEN POST succeeds with `external_entity` omitted and the app redirects to `/calls/{id}`

#### Scenario: External call without entity

- GIVEN an external call form with empty `external_entity`
- WHEN create is submitted
- THEN the form surfaces a required-field error and no redirect occurs

#### Scenario: Internal call with entity

- GIVEN an internal call form with a non-empty `external_entity`
- WHEN create is submitted
- THEN the form surfaces a field error and no redirect occurs

#### Scenario: Date ordering violation

- GIVEN `submission_end` before `submission_start`
- WHEN create is submitted
- THEN the form surfaces an ordering error and no redirect occurs

### Requirement: Detail with tabs

`/calls/{id}` MUST render a header with StatusBadge, an FSM action bar, and tabs Overview, Documents, Projects, State history. Overview MUST show description, call_type, external_entity, and the four submission/evaluation dates.

#### Scenario: Detail loads

- GIVEN a call id
- WHEN the detail route loads
- THEN the four tabs render with Overview data

### Requirement: Edit call

`/calls/{id}/edit` MUST PATCH `/api/calls/{id}/` (director+) with the same zod rules as create. Status and institution MUST be read-only.

#### Scenario: Edit saves

- GIVEN a director with update permission
- WHEN the form is saved
- THEN PATCH succeeds and detail reflects the changes

### Requirement: FSM transitions

The detail action bar MUST expose the 5 transitions via `getCallActions(state, roles)` from the projects `FsmActionBar` pattern, each POSTing `/api/calls/{id}/{action}/`: `open_call`, `close_call`, `start_evaluation`, `publish_results`, and `archive`. `archive` is terminal and destructive and MUST open a ConfirmDialog. Invalid transitions (409) and non-director actions (403) MUST surface via `getErrorMessage`.

#### Scenario: Open call

- GIVEN a call in `borrador` and a director
- WHEN `open_call` is pressed
- THEN POST succeeds and the status badge becomes `abierta`

#### Scenario: Action filtered by state and role

- GIVEN a call in `cerrada` viewed by a researcher
- WHEN the action bar renders
- THEN only director-eligible, `cerrada`-valid actions appear

#### Scenario: Archive confirms and is terminal

- GIVEN a call in `resultados_publicados` and a director
- WHEN `archive` is pressed
- THEN ConfirmDialog opens, POST succeeds, and the status becomes `archivada` with no further actions

#### Scenario: Invalid transition surfaces

- GIVEN a call in `borrador`
- WHEN a director requests `publish_results`
- THEN the 409 detail surfaces via Toaster and status is unchanged

### Requirement: Gated delete

The system MUST expose a `delete` action (director+) surfaced from detail, gated to calls in `borrador` with zero linked CallProjects, behind a ConfirmDialog (destructive). It MUST DELETE `/api/calls/{id}/` and redirect to `/calls` on success.

#### Scenario: Delete confirms

- GIVEN a call in `borrador` with no linked projects and a director
- WHEN delete is pressed
- THEN ConfirmDialog appears, DELETE succeeds, and the app redirects to `/calls`

#### Scenario: Delete hidden when ineligible

- GIVEN a call in `abierta` or a non-director user
- WHEN the detail actions render
- THEN no delete action is available

### Requirement: Documents manager

The Documents tab MUST manage metadata-only records `{name, doc_type (convocatoria|anexo|reglamento|resultado|otro), external_url}` with no file upload, via `GET/POST /api/calls/{id}/documents/` and `PATCH/DELETE /api/calls/{id}/documents/{did}/`.

#### Scenario: Document metadata only

- GIVEN the Documents tab
- WHEN a document is added
- THEN only name/doc_type/external_url are captured and rendered as an external link

#### Scenario: Document deleted

- GIVEN an existing CallDocument
- WHEN delete is pressed
- THEN DELETE succeeds and the list refreshes

### Requirement: Projects manager

The Projects tab MUST list linked projects and support link/unlink via `GET/POST /api/calls/{id}/projects/` and `DELETE /api/calls/{id}/projects/{pid}/`. Linking MUST only be offered when the call is in `abierta`; a duplicate-association 409 MUST surface.

#### Scenario: Link project

- GIVEN a call in `abierta` and an unlinked project
- WHEN link is submitted
- THEN POST succeeds and the linked list refreshes

#### Scenario: Link hidden when not open

- GIVEN a call not in `abierta`
- WHEN the Projects tab renders
- THEN no link action is available

#### Scenario: Duplicate association surfaces

- GIVEN a project already linked to another call
- WHEN link is submitted
- THEN the 409 detail surfaces via Toaster

### Requirement: State history manager

The State history tab MUST render read-only logs from `GET /api/calls/{id}/state_history/` with no mutations.

#### Scenario: History renders

- GIVEN a call with state logs
- WHEN the State history tab loads
- THEN logs render read-only with no action controls

### Requirement: Institution-scoped server state

The system MUST add a `calls` query-key factory (institution-scoped list/detail + nested documents/projects/stateHistory) and MUST invalidate all call-scoped queries after any call, document, or project mutation.

#### Scenario: Mutation invalidates

- GIVEN a call mutation succeeds
- WHEN invalidation runs
- THEN list, detail, and nested keys refetch

### Requirement: Shell integration

The sidebar MUST show "Convocatorias" for every authenticated role, and StatusBadge MUST render calls FSM statuses `abierta`, `en_evaluacion`, and `resultados_publicados` (existing `borrador`, `cerrada`, `archivada` entries confirmed).

#### Scenario: Nav item

- GIVEN any authenticated user
- WHEN the shell renders
- THEN "Convocatorias" appears in the sidebar

#### Scenario: FSM badge

- GIVEN a call with status `en_evaluacion`
- WHEN a badge renders
- THEN a distinct `en_evaluacion` label shows

### Requirement: MSW fixtures and coverage

The system MUST ship MSW fixtures/handlers for calls (list, create, 5 FSM, documents, projects, state_history) and MUST hold Jest coverage ≥80% with `tsc --noEmit` green.

#### Scenario: Paginated list handler

- GIVEN an MSW calls handler
- WHEN `GET /api/calls/` is requested
- THEN a `Page<CallList>` envelope returns

#### Scenario: FSM handler

- GIVEN an MSW transition handler
- WHEN `POST /api/calls/{id}/open_call/` is requested
- THEN the call status updates to `abierta`

#### Scenario: Coverage floor

- GIVEN a PR slice
- WHEN `jest --coverage` runs
- THEN branch coverage ≥80%

## Acceptance Criteria

- Users can list (with status/type filters), create, view (4 tabs), edit, and drive calls through the 5 FSM transitions with correct role gating; `archive` and delete confirm via ConfirmDialog.
- Documents are metadata-only; project link conflicts (409) surface; state history is read-only; delete hidden unless `borrador` + no linked projects.
- Sidebar shows "Convocatorias" for all authenticated roles; Jest ≥80%; `tsc --noEmit` green; no backend changes.

## PR Boundaries

| PR | Slice | Spec scope |
|----|-------|-----------|
| PR1 — foundation | types/schemas/constants/query-keys/StatusBadge/Sidebar; list + filters; create; detail Overview; FSM action bar; MSW list/create/FSM | List, Create, Detail, Edit, FSM, Server state, Shell, MSW/coverage (base) |
| PR2 — nested managers + FSM | Documents, Projects, State history tabs; delete gate; fixtures/handlers | Documents, Projects, State history, Delete, MSW/coverage (fixtures) |
| PR3 — filters + polish + verify | status/type filter wiring; polish; Jest ≥80%, `tsc --noEmit` verification | List (filters), Coverage |
