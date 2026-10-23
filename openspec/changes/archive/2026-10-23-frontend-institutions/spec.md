# Institutions UI Specification (institutions-ui)

**Status**: New capability — full spec. No prior frontend behavior for this domain; backend `institutions` spec unchanged.

## Purpose

Frontend management module for the 6-entity institutional hierarchy (Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine): tree visualization, per-level CRUD, FSM lifecycle actions, role-gated writes, and institution-scoped server state. Reuses the projects/advances patterns verbatim (fsm.ts + FsmActionBar, ConfirmDialog, StatusBadge, EmptyState, query-key factories, MSW).

## Functional Requirements (RF)

### Requirement: RF-F01 — Hierarchy tree

The system MUST render the full hierarchy as an expandable/collapsible tree with a StatusBadge per node and a per-node action menu.

#### Scenario: Full tree renders
- GIVEN institutions with nested children
- WHEN `/institutions` loads
- THEN root institutions render; expanding a node reveals children with status badges

#### Scenario: Empty state
- GIVEN zero institutions
- WHEN the list loads
- THEN EmptyState with create CTA renders; no `activeInstitution` is required

#### Scenario: Keyboard navigation
- GIVEN a focused tree node
- WHEN arrow keys / Enter / Space are pressed
- THEN focus and expand/collapse follow the WCAG 2.1 AA tree pattern (roles `tree`/`treeitem`, `aria-expanded`)

### Requirement: RF-F02 — Institution CRUD (root)

The system MUST support create, read, update, and delete of institutions; list and detail MUST load without `activeInstitution`.

#### Scenario: Superadmin creates institution
- GIVEN a superadmin on `/institutions/new`
- WHEN the RHF + zod form submits valid data
- THEN POST `/api/institutions/` succeeds and the tree refetches

#### Scenario: Bootstrap without membership
- GIVEN a superadmin with zero institution memberships
- WHEN visiting `/institutions`
- THEN the list renders; the institution selector is hidden when ≤1 institution exists

#### Scenario: Duplicate code
- GIVEN an existing institution code
- WHEN the form submits the same code
- THEN the 409 detail surfaces verbatim via Toaster and the form keeps its values

### Requirement: RF-F03 — Child entity CRUD

The system MUST support CRUD for Sede, Facultad, ResearchCenter, ResearchGroup, and ResearchLine, with the parent id taken from the URL.

#### Scenario: Admin creates sede
- GIVEN an active institution
- WHEN POSTing to `/api/institutions/{pk}/sedes/`
- THEN the Sede appears under its institution in the tree

#### Scenario: Center parented to facultad
- GIVEN a facultad
- WHEN POSTing to `/api/institutions/{pk}/centers/` with facultad selected
- THEN the center nests under the facultad

#### Scenario: Delete with children blocked
- GIVEN an entity that still has children
- WHEN DELETE is requested
- THEN the 409 guard detail surfaces and the node persists

### Requirement: RF-F04 — FSM lifecycle actions

The system MUST expose activate/deactivate/archive per node from the fsm.ts config table; destructive actions (deactivate, archive) MUST require ConfirmDialog; archived is terminal.

#### Scenario: Deactivate confirms
- GIVEN an active node
- WHEN deactivate is pressed
- THEN ConfirmDialog shows before POST to the deactivate endpoint

#### Scenario: Archived is terminal
- GIVEN an archived node
- WHEN its action bar renders
- THEN no transition actions appear

#### Scenario: 409 guard
- GIVEN a node with active children
- WHEN deactivate is attempted
- THEN the backend detail "Deactivate or archive children first." shows via Toaster

### Requirement: RF-F05 — Role-gated writes

The system MUST gate writes by role (superadmin > admin > director) via the existing RoleGuard; reads are open to authenticated users.

#### Scenario: Director denied institution write
- GIVEN a director
- WHEN visiting institution create or edit
- THEN the action is hidden or a 403 is surfaced

### Requirement: RF-F06 — Navigation

The sidebar MUST show a role-gated "Estructura institucional" item linking to `/institutions`.

#### Scenario: Nav item
- GIVEN an authenticated user with write role
- WHEN rendering the sidebar
- THEN the item appears and navigates to `/institutions`

## Non-Functional Requirements (RNF)

| ID | Requirement |
|---|---|
| RNF-01 | The tree component MUST pass WCAG 2.1 AA (keyboard navigation, ARIA roles, focus management, contrast). |
| RNF-02 | Jest coverage MUST be ≥80% per slice. |
| RNF-03 | ESLint and `tsc --noEmit` MUST be green per PR. |
| RNF-04 | All UI copy MUST be Spanish. |
| RNF-05 | Loading states MUST use the existing Skeleton/EmptyState patterns. |
| RNF-06 | All server data MUST flow through TanStack Query — no raw fetches in components. |

## User Stories

- **As a superadmin**, I create the first institution and manage the root level.
- **As an admin**, I manage sedes, facultades, and centers of my institution.
- **As a director**, I manage the groups and lines of my center.
- **As any user**, I browse the hierarchy read-only and understand each node's status at a glance.

## API Integration Contract

| API | Methods | Query key | Notes |
|---|---|---|---|
| `/api/institutions/`, `/api/institutions/{pk}/` | GET, POST, PATCH, DELETE | `institutions.list/detail` | DRF paginated; reads open to all authenticated users |
| `/api/institutions/{pk}/sedes/`, `/.../sedes/{pk}/` | GET, POST, PATCH, DELETE | `institutions.sedes` | parent from URL |
| `/api/institutions/{pk}/facultades/`, `/.../facultades/{pk}/` | GET, POST, PATCH, DELETE | `institutions.facultades` | optional sede field |
| `/api/institutions/{pk}/centers/`, `/.../centers/{pk}/` | GET, POST, PATCH, DELETE | `institutions.centers` | parent_type: institution\|sede\|facultad |
| `/api/centers/{pk}/groups/`, `/.../groups/{pk}/` | GET, POST, PATCH, DELETE | `institutions.groups` | |
| `/api/groups/{pk}/lines/`, `/.../lines/{pk}/` | GET, POST, PATCH, DELETE | `institutions.lines` | leaf |
| `/api/{entity}/{pk}/activate\|deactivate\|archive/` | POST | n/a (mutation) | invalidates `institutions.all` on success |

- Pagination: consume DRF `{count, next, previous, results}`; fetch all pages for tree rendering.
- Tenant scoping: all scoped queries keyed off the auth store `activeInstitution`; the `X-Institution-ID` header MUST NOT be sent (vestigial).
- Parent ids come from the URL; forms MUST NOT send the parent in the body.
- `status` values are consumed verbatim from API responses; badge mapping covers draft/active/inactive/archived with a fallback for unknown values; `archived` is terminal.

## State Management

- Add an `institutions` factory to `lib/query-keys.ts` mirroring the `projects` factory (all/lists/list/detail), institution-scoped.
- Mutations MUST invalidate `institutions.all` (and derived detail) on success; MUST NOT invalidate on failure.
- Institution switch MUST clear the scoped cache (existing auth-store behavior, reused).
- FSM actions derive solely from the `fsm.ts` config table (`name`, `label`, `destructive`, `allowedRoles`, `fromStates`) — no per-node branching logic.

## Testing Requirements

- MSW fixtures and handlers for all 6 entities; existing projects-wizard consumers stay green.
- Jest ≥80% per slice (RNF-02). Tree tests MUST cover keyboard navigation and `aria-expanded`; mutation tests MUST cover 409 guard, 400 validation, and network failure; RoleGuard tests MUST cover write denial.

## Error Handling

| Error | Behavior |
|---|---|
| 409 FSM guard ("Deactivate or archive children first.") | Backend `detail` verbatim via Toaster; no invalidation; node persists |
| 409 duplicate code | Backend `detail` verbatim via Toaster; form keeps values |
| 400 validation | Field errors mapped into the RHF form |
| 403 role denial | RoleGuard hides action or surfaces 403 |
| Network failure | Toaster error with retry; no partial cache writes |

## Slice Mapping

| Slice | Requirements |
|---|---|
| 1 (PR 1) | RF-F01, RF-F02, RF-F04, RF-F06; query-keys factory; MSW fixtures; RNF-01/02/03 foundation |
| 2 (PR 2) | RF-F03 for Sede/Facultad/ResearchCenter; RF-F05 |
| 3 (PR 3) | RF-F03 for ResearchGroup/ResearchLine; tree polish; RNF completion |

## Risks

| Risk | Mitigation |
|---|---|
| Status enum mismatch: task contract says draft\|active\|inactive\|archived; verified backend sends active\|deactivated\|archived | Frontend consumes `status` verbatim (fallback badge); apply MUST verify against live API |
| Tree component fails WCAG or coverage floor | Recursive disclosure primitive with keyboard nav + ARIA roles; Jest ≥80% per PR |
| Superadmin bootstrap (first institution, no memberships) | Institutions list does not require `activeInstitution`; selector hidden when ≤1 institution |
