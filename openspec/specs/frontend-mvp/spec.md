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

### Requirement: Server-side aggregation
The dashboard MUST fetch aggregated metrics from `/api/dashboard/summary/` endpoint (14 indicators per SPEC §6.12), role-aware. Client-side composition from list endpoints is deprecated due to pagination limits (25/page).

#### Scenario: Director dashboard
- GIVEN a center director
- WHEN rendering dashboard
- THEN server-side KPIs (IND-001 to IND-014) + charts (projects by status/center, budget execution, progress reports) appear

#### Scenario: Investigator dashboard
- GIVEN an investigator
- WHEN rendering
- THEN limited KPIs (backend scopes to own projects) appear; full approval queue hidden

#### Scenario: Role-based access
- GIVEN a user with role level 5+ (evaluador, asistente)
- WHEN accessing dashboard
- THEN access denied (403)

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

## institutions-ui

### Requirement: Hierarchy tree & nested CRUD
`/institutions` MUST render a recursive tree with 6 entity levels (Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine) using lazy-loaded child queries. Each node MUST show StatusBadge and per-level actions.

#### Scenario: Tree rendering
- GIVEN an institution with nested children
- WHEN `/institutions` loads
- THEN tree renders with expand/collapse per node and lazy child loading

#### Scenario: Nested CRUD
- GIVEN admin role (level ≤ 2)
- WHEN creating a sede under an institution
- THEN POST `/api/institutions/{id}/sedes/` succeeds and tree invalidates

### Requirement: FSM transitions & role gating
FsmActionBar MUST render activate/deactivate/archive transitions per state/role. Destructive actions (deactivate, archive) MUST require ConfirmDialog.

#### Scenario: Root creation
- GIVEN superadmin
- WHEN creating root institution
- THEN POST `/api/institutions/` succeeds

#### Scenario: Child entity permissions
- GIVEN director role (level 3)
- WHEN attempting to create sede
- THEN 403 (only admin+ allowed)

## documents-ui

### Requirement: List & detail with version history
`/documents` MUST render a paginated list with filters (doc_type, entity_type, is_signed, search). Detail MUST show version timeline with SHA256 hashes.

#### Scenario: Document list
- GIVEN 50 documents
- WHEN `/documents` loads
- THEN 25 render with pagination + filters

#### Scenario: Version history
- GIVEN document with 3 versions
- WHEN detail loads
- THEN version timeline renders with sha256, size_bytes, uploaded_by

### Requirement: Presigned URL upload flow
UploadButton MUST request presigned PUT URL, upload directly to MinIO, then POST confirm with object_key.

#### Scenario: Upload flow
- GIVEN user with write access (level ≤ 6)
- WHEN clicking UploadButton
- THEN presign → upload → confirm flow completes and list invalidates

### Requirement: Digital signature metadata
Detail MUST display signature metadata (signer, signed_at, sha256) when is_signed=true.

#### Scenario: Signed document
- GIVEN document with DigitalSignature
- WHEN detail loads
- THEN signature metadata renders

## reports-ui

### Requirement: Report hub & entity selector
`/reports` MUST render a hub with entity list queries and ReportGeneratorForm supporting 4 report types (project, researcher, center, advances).

#### Scenario: Entity selector
- GIVEN director role
- WHEN `/reports` loads
- THEN entity list queries render + type selector (4 types)

### Requirement: Preview, download & approval workflow
PreviewDialog MUST render HTML preview from backend. DownloadButton MUST trigger PDF download. ApprovalButton MUST require director + center membership.

#### Scenario: Preview generation
- GIVEN selected entity + type
- WHEN preview pressed
- THEN HTML preview renders in modal

#### Scenario: Approval
- GIVEN director with center membership
- WHEN approve pressed
- THEN POST `/api/reports/{id}/approve/` succeeds

### Requirement: Role-based access
Generate/preview/download: level ≤ 4. Approve: level ≤ 3 + center membership check.

#### Scenario: Role gating
- GIVEN researcher role (level 4)
- WHEN accessing approve action
- THEN button hidden (403)

## researchers-ui

### Requirement: List & detail with nested managers
`/researchers` MUST render paginated list with CompletenessBar (0-100%). Detail MUST show AffiliationsManager, ExternalProfilesManager, AttachmentsManager.

#### Scenario: Completeness indicator
- GIVEN researcher with 60% complete profile
- WHEN list renders
- THEN CompletenessBar shows 60%

#### Scenario: Nested managers
- GIVEN researcher detail
- WHEN loading
- THEN affiliations, external profiles, attachments managers render

### Requirement: Self-edit permission
Researcher MUST be able to edit own profile (researcher.user === currentUser.id) even without admin role.

#### Scenario: Self-edit
- GIVEN researcher viewing own profile
- WHEN edit pressed
- THEN edit form renders (self-permission)

### Requirement: Deactivate action
DeactivateResearcherButton MUST require admin+ (level ≤ 2) and show ConfirmDialog.

#### Scenario: Deactivate
- GIVEN admin role
- WHEN deactivate pressed
- THEN ConfirmDialog → POST `/api/researchers/{id}/deactivate/`

## products-ui

### Requirement: List with 9 filters
`/products` MUST render paginated list with filters: type (11 values), year, year__gte, year__lte, project, researcher, center, group, line.

#### Scenario: Filtered list
- GIVEN products with type=articulo
- WHEN type filter applied
- THEN list filters to articulo only

### Requirement: Authors & attachments managers
Detail MUST show AuthorsManager (researcher junction with order, is_principal) and AttachmentsManager (metadata-only).

#### Scenario: Author ordering
- GIVEN product with 3 authors
- WHEN AuthorsManager loads
- THEN authors render with order + is_principal flag

### Requirement: 11 product types
ProductForm MUST expose 11 types: articulo, libro, capitulo, software, prototipo, evento, consultoria, diseno_industrial, innovacion_proceso, innovacion_gestion, carta.

#### Scenario: Type selection
- GIVEN create form
- WHEN type dropdown opens
- THEN 11 types render

## calls-ui

### Requirement: List & detail with date ranges
`/calls` MUST render paginated list with status/call_type filters. Detail MUST show date ranges (submission_start/end, evaluation_start/end).

#### Scenario: Date range display
- GIVEN call with submission dates
- WHEN detail loads
- THEN date ranges render with timezone

### Requirement: FSM transitions (5 actions)
FsmActionBar MUST render 5 transitions: open_call, close_call, start_evaluation, publish_results, archive. Archive requires ConfirmDialog.

#### Scenario: FSM visibility
- GIVEN call in `abierta`
- WHEN rendering
- THEN close_call, archive render; others hidden

### Requirement: Documents, projects & state history managers
Detail MUST show DocumentsManager, ProjectsManager (CallProject junction), StateHistoryManager (timeline).

#### Scenario: Managers
- GIVEN call detail
- WHEN loading
- THEN documents, projects, state history managers render

## search-ui

### Requirement: Multi-index search
`/search` MUST render SearchBar with index selector (5 indices: projects, researchers, products, calls, advances) and debounced query input (300ms).

#### Scenario: Index selection
- GIVEN user selects "projects"
- WHEN query entered
- THEN search queries projects index only

### Requirement: Filtering & highlighting
SearchFilters MUST render filter controls (institution, center, line, status, year, type). SearchResults MUST render highlighted matches (`<mark>` tags from Meilisearch).

#### Scenario: Filter application
- GIVEN filters applied
- WHEN search executes
- THEN results filtered by selected values

#### Scenario: Highlighting
- GIVEN search returns hits
- WHEN results render
- THEN matched text wrapped in `<mark>` tags

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
