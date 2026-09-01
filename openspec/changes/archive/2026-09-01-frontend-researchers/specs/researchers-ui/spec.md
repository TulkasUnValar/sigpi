# researchers-ui Specification (SIGPI §6.3 — Frontend)

## Purpose

Frontend management UI for the archived `apps.researchers` backend: list, create, detail with nested managers, edit, completeness, and deactivation. Reads are institution-scoped and open to all authenticated roles; writes are role-gated. No backend changes.

## Requirements

### Requirement: Researcher list

`/researchers` MUST render the paginated list from `GET /api/researchers/` (`Page<ResearcherList>`, 25/page) with a completeness bar, active/inactive StatusBadge, and row actions per researcher.

#### Scenario: Paginated list renders

- GIVEN the active institution has researchers
- WHEN `/researchers` loads
- THEN rows render with pagination controls, completeness bars, and status badges

#### Scenario: Empty institution

- GIVEN the institution has no researchers
- WHEN `/researchers` loads
- THEN an empty state with a create action renders

### Requirement: Create researcher

`/researchers/new` MUST POST `/api/researchers/` (director+, level ≤ 3); writable fields match `ResearcherCreateSerializer`. Success MUST redirect to the new detail page.

#### Scenario: Create succeeds

- GIVEN a director submits a valid form
- WHEN create is pressed
- THEN POST succeeds and the app redirects to `/researchers/{id}`

#### Scenario: Duplicate document

- GIVEN a researcher with the same `(institution, document_number)` exists
- WHEN create is submitted
- THEN the field error surfaces in the form and no redirect occurs

### Requirement: Detail with tabs

`/researchers/{id}` MUST render tabs Overview, Affiliations, External profiles, Attachments; Overview MUST show profile fields, the `is_active` badge, and the completeness bar.

#### Scenario: Detail loads

- GIVEN a researcher id
- WHEN the detail route loads
- THEN the four tabs render with Overview data

### Requirement: Edit and reactivation

`/researchers/{id}/edit` MUST PATCH `/api/researchers/{id}/` (self or admin+, gated on detail `user` when linked) and MUST include an `is_active` toggle enabling reactivation (no reactivate endpoint exists).

#### Scenario: Edit saves

- GIVEN a user with update permission
- WHEN the form is saved
- THEN PATCH succeeds and detail reflects the changes

#### Scenario: Reactivate via toggle

- GIVEN an inactive researcher the user may edit
- WHEN `is_active` is set true and saved
- THEN PATCH `{is_active: true}` succeeds and the status badge turns active

### Requirement: Completeness display

The system MUST display `completeness_score` (0–100) on list and detail with distinct visual states for complete vs incomplete profiles.

#### Scenario: Bar reflects score

- GIVEN a researcher with `completeness_score` 40
- WHEN list or detail renders
- THEN a 0–100 indicator shows 40 in an incomplete state

### Requirement: Deactivate

The system MUST expose one `deactivate` action (admin+, level ≤ 2) that POSTs `/api/researchers/{id}/deactivate/` behind a ConfirmDialog (destructive) and MUST invalidate researcher queries on success.

#### Scenario: Deactivate confirms

- GIVEN an admin views an active researcher
- WHEN deactivate is pressed
- THEN ConfirmDialog appears, then POST succeeds and the state shows inactive

#### Scenario: Role gate

- GIVEN a non-admin user
- WHEN researcher actions render
- THEN no deactivate action is available

### Requirement: Affiliations manager

The Affiliations tab MUST list and inline-create affiliations (dependent selects center → group → line, at least one FK, POST `/api/researchers/{id}/affiliations/`) and delete them. Exactly one affiliation MUST be primary: the first created is auto-primary; `set_primary` POSTs `/api/researchers/{id}/affiliations/{aff_id}/set_primary/`; the primary toggle MUST be disabled when already primary.

#### Scenario: First affiliation primary

- GIVEN a researcher with no affiliations
- WHEN one affiliation is created
- THEN it stores with `is_primary=True`

#### Scenario: Set primary

- GIVEN a researcher with two affiliations
- WHEN `set_primary` runs on the second
- THEN the second becomes primary and the first is demoted

#### Scenario: Cross-institution target

- GIVEN an affiliation target outside the researcher's institution
- WHEN create is submitted
- THEN the 400 detail surfaces via Toaster

### Requirement: External profiles and attachments managers

The External profiles tab MUST manage `{provider, url}` (provider ∈ cvlac, orcid, google_scholar, linkedin, researchgate); the Attachments tab MUST manage metadata only — `{name, type (cv|certificate|photo|other), external_url}` — with no file upload. Both MUST use their nested POST/DELETE endpoints.

#### Scenario: Profile created

- GIVEN a valid provider and url
- WHEN the profile form is submitted
- THEN POST `/api/researchers/{id}/profiles/` succeeds and the list refreshes

#### Scenario: Attachment metadata only

- GIVEN the attachments tab
- WHEN an attachment is added
- THEN only name/type/external_url are captured and rendered as an external link

### Requirement: Institution-scoped server state

The system MUST add a `researchers` query-key factory (institution-scoped list/detail + nested keys) and MUST invalidate all researcher-scoped queries after any researcher mutation.

#### Scenario: Mutation invalidates

- GIVEN a researcher mutation succeeds
- WHEN invalidation runs
- THEN list, detail, and nested keys refetch

### Requirement: Shell integration

The sidebar MUST show "Investigadores" for every authenticated role, and StatusBadge MUST render researcher `active`/`inactive` states.

#### Scenario: Nav item

- GIVEN any authenticated user
- WHEN the shell renders
- THEN "Investigadores" appears in the sidebar

#### Scenario: Inactive badge

- GIVEN a researcher with `is_active` false
- WHEN a badge renders
- THEN a distinct inactive label shows

### Requirement: MSW fixtures and coverage

The system MUST ship MSW fixtures/handlers for all four researcher entities and MUST hold Jest coverage ≥80% with `tsc --noEmit` green.

#### Scenario: Paginated list handler

- GIVEN an MSW researcher handler
- WHEN `GET /api/researchers/` is requested
- THEN a `Page<ResearcherList>` envelope returns

#### Scenario: Coverage floor

- GIVEN a PR slice
- WHEN `jest --coverage` runs
- THEN branch coverage ≥80%

## Acceptance Criteria

- Users can list, create, view (tabs), and edit researchers; the completeness bar reflects the API score; deactivation works via ConfirmDialog.
- Affiliations support dependent selects and exactly-one-primary; cross-institution errors surface.
- The projects wizard loads researcher options against the real paginated API; Jest ≥80%; `tsc --noEmit` green; sidebar nav role-gated.

## PR Boundaries

| PR | Slice | Spec scope |
|----|-------|-----------|
| PR1 — foundation | types/schemas/queries/mutations/fsm; list; create; detail Overview; edit; completeness; deactivate; shell (Sidebar + StatusBadge); MSW base | List, Create, Detail, Edit, Completeness, Deactivate, Server state, Shell, MSW/coverage |
| PR2 — nested managers | Affiliations, External profiles, Attachments tabs + MSW fixtures/handlers | Affiliations manager; External profiles & attachments managers |
| PR3 — wizard fix + polish | `useResearchers()` pagination fix in projects wizard; polish; verification | projects-ui delta (Create wizard) |
