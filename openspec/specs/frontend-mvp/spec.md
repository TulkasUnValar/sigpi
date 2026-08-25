# Delta for SIGPI Frontend MVP

All six capabilities are NEW — no existing spec-level behavior changes. Each section is a full spec (ADDED).

## ui-foundation

### Requirement: Theme & base primitives
The system MUST ship shadcn/ui (React 19-compatible Radix) with next-themes; every base component MUST be keyboard-accessible (WCAG 2.1 AA) and receive Spanish copy.

#### Scenario: Primitive renders
- GIVEN a fresh shadcn/ui install
- WHEN a Button/Input/Dialog is rendered
- THEN it is keyboard-focusable and exposes ARIA roles

#### Scenario: React 19 compatibility
- GIVEN slice-1 spike
- WHEN any shadcn component mounts
- THEN no React 19 peer-dependency error is thrown

## server-state

### Requirement: Query client & keys
The system MUST use TanStack Query v5 for server data with centralized key factories (`projects`, `advances`, `dashboard`) and a typed error normalizer mapping `{detail}` / field errors.

#### Scenario: Error normalization
- GIVEN a failed query returning `{"detail":"..."}`
- WHEN normalized
- THEN a typed error with `message` is surfaced to Toaster

### Requirement: Post-FSM invalidation
Every FSM mutation MUST invalidate its resource and all derived queries (dashboard KPIs, detail, lists).

#### Scenario: Approve invalidates derived data
- GIVEN a director approves an advance
- WHEN mutation succeeds
- THEN `advances`, `dashboard`, and `projects` keys refetch

#### Scenario: Mutation failure
- GIVEN a 400 invalid transition
- WHEN mutation rejects
- THEN cache is NOT invalidated and error is shown

## app-shell

### Requirement: Layout & navigation
The shell MUST render a persistent sidebar on desktop and a drawer on mobile, with topbar (InstitutionSelector, user menu, theme toggle). Nav MUST be role-filtered.

#### Scenario: Responsive shell
- GIVEN viewport ≥1024px
- WHEN rendering
- THEN sidebar is visible; under 1024px a drawer toggle is shown

#### Scenario: Role guard
- GIVEN a non-director visits a director-only route
- WHEN rendering
- THEN a 403/redirect is shown

### Requirement: Institution-switch invalidation
Switching institution MUST clear all scoped server cache.

#### Scenario: Switch institution
- GIVEN active institution changes in Zustand
- WHEN auth store updates
- THEN all institution-scoped queries invalidate and refetch

## dashboard

### Requirement: Role-aware home
The dashboard MUST compose KPIs and queues from existing list endpoints (`/projects/`, `/progress/`), role-aware.

#### Scenario: Director queue
- GIVEN a center director
- WHEN rendering dashboard
- THEN pending approvals queue + KPI cards appear

#### Scenario: Investigator KPIs
- GIVEN an investigator
- WHEN rendering
- THEN "my projects" and progress KPIs appear; approvals hidden

## projects-ui

### Requirement: List & detail
`/projects` MUST render a paginated (DRF 25/page) table with filters (status/center/line/year/search). Detail MUST expose tabs (overview, team, documents, observations, state history).

#### Scenario: Pagination
- GIVEN 60 projects
- WHEN page 1 loads
- THEN 25 render with page controls from `next`

#### Scenario: Detail tabs
- GIVEN a project detail
- WHEN loading
- THEN overview + state history render with StatusBadge

### Requirement: Create wizard
`/projects/new` MUST be a multi-step wizard (basic info → center/group/line → team → documents) with per-step validation and a review step before submit.

#### Scenario: Wizard submit
- GIVEN all steps valid
- WHEN submit is pressed
- THEN POST `/projects/` succeeds and redirects to detail

### Requirement: FSM action bar
The action bar MUST render per-state/role transitions; only destructive transitions (reject/cancel/close/archive) show ConfirmDialog.

#### Scenario: Action visibility
- GIVEN project in `en_revision` owned by director
- WHEN rendering
- THEN approve/observe/return_to_draft/reject show; reject opens ConfirmDialog

#### Scenario: Invalid action hidden
- GIVEN project in `cerrado`
- WHEN rendering
- THEN no transition buttons render

## advances-ui

### Requirement: Nested list & detail
`/projects/[id]/advances` MUST list advances for that project with a cumulative-progress indicator. Detail MUST show review timeline + state history.

#### Scenario: Nested list
- GIVEN a project with advances
- WHEN visiting `/projects/{id}/advances`
- THEN list + cumulative % render

### Requirement: Advance create & FSM
Create form (period, %, activities, difficulties, next steps). Director actions approve/observe/reject/return_to_draft with ConfirmDialog only for destructive (reject).

#### Scenario: Director approves
- GIVEN advance in `en_revision`
- WHEN approve pressed
- THEN POST `/progress/{id}/approve/` and dashboard/progress invalidate

#### Scenario: Reject confirms
- GIVEN advance in `en_revision`
- WHEN reject pressed
- THEN ConfirmDialog appears before POST

## Cross-cutting

### Requirement: Seed data
The system MUST provide dev fixtures producing non-empty dashboard, projects, and advances states.

#### Scenario: Fixtures present
- GIVEN dev database reset
- WHEN seeding
- THEN dashboard, projects, advances show data

### Requirement: Jest coverage
Frontend MUST hold Jest coverage ≥80% per slice; lint + typecheck green.

#### Scenario: Coverage floor
- GIVEN a slice PR
- WHEN `jest --coverage` runs
- THEN branch coverage ≥80%
