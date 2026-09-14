# Delta Spec: Advances Frontend Module Completion (advances-ui)

Delta for the `advances-ui` capability. Supersedes and expands the `advances-ui` section of `openspec/specs/frontend-mvp/spec.md` (proposal — Modified Capabilities). Backend untouched; all requirements are frontend behavior.

## Section 1: Requirements

| Code | Requirement |
|------|-------------|
| RF-041 | The FSM action bar MUST collect `review_text` through a dialog with a textarea for the `observe` and `reject` transitions and MUST include it in the POST body. The dialog MUST block confirmation while `review_text` is blank, and no POST MAY fire before confirmation. |
| RF-042 | The advance detail MUST include a DocumentsManager providing metadata-only CRUD (`name`, `doc_type`, `external_url`) via the nested documents endpoints, following the calls pattern. No file upload widget SHALL be rendered. |
| RF-043 | `/projects/[id]/advances/[advanceId]/edit` MUST render a shared AdvanceForm seeded from the detail query, PATCHing only writable fields with `project` omitted, using the same zod rules as create. Edit access MUST be gated to advances in `borrador`. |
| RF-044 | The advance detail MUST expose a delete button gated to `borrador` + creator, behind a destructive ConfirmDialog, issuing `DELETE /progress/{id}/` and redirecting to the list on success. |
| RF-045 | The module MUST export a barrel `index.ts` and `constants.ts` (status and `doc_type` labels/options) mirroring the calls module; pages and tests SHALL import from the barrel. |
| RF-046 | The module MUST extract dedicated `AdvanceList`, `AdvanceDetail`, and `AdvanceForm` components from the inline pages (products pattern) and the routes MUST consume them with unchanged behavior. |
| RF-047 | The module MUST reach test parity — mutations, queries, query-keys (documents/reviews), barrel, edit, documents — with Jest coverage ≥80% and `tsc --noEmit` green. No test MAY assert an empty-body (`{}`) observe/reject POST. |

## Section 2: Scenarios

### PR1 — Functional gaps (RF-041, RF-042, part of RF-045)

#### Scenario: Observe collects review text

- GIVEN an advance in `en_revision` and a director
- WHEN `Observar` is pressed
- THEN a dialog with a textarea opens and `POST /progress/{id}/observe/` is NOT called until confirmed
- AND after confirm the request body includes `review_text` and the review renders non-blank

#### Scenario: Reject sends non-blank review text (bug fix)

- GIVEN an advance in `en_revision` and a director
- WHEN `Rechazar` is pressed, text entered, and the dialog confirmed
- THEN `POST /progress/{id}/reject/` fires with body `{ review_text }` — never `{}`
- AND the created ProgressReview renders with the entered text

#### Scenario: Blank text blocks confirmation

- GIVEN the observe/reject dialog open with an empty textarea
- WHEN the confirm action is attempted
- THEN confirmation is disabled and no POST fires

#### Scenario: Cancel sends nothing

- GIVEN the observe/reject dialog open
- WHEN cancel is pressed
- THEN no POST fires and the dialog closes

#### Scenario: Document CRUD

- GIVEN an advance in `borrador` viewed by its creator
- WHEN a document is added with `name`, `doc_type`, `external_url`
- THEN `POST /progress/{id}/documents/` succeeds and the list refreshes; editing PATCHes `documents/{did}/`; deleting confirms via ConfirmDialog then DELETEs

#### Scenario: Metadata only, no upload

- GIVEN the documents section renders
- WHEN a document row is shown
- THEN only name/doc_type/external_url appear as an external link and no file-upload control exists

### PR2 — Edit + delete parity (RF-043, RF-044)

#### Scenario: Edit borrador advance

- GIVEN a borrador advance and its creator on `/projects/[id]/advances/[advanceId]/edit`
- WHEN the form is saved
- THEN `PATCH /progress/{id}/` sends writable fields without `project` and the app redirects to the detail

#### Scenario: Edit hidden outside borrador

- GIVEN an advance not in `borrador` or a non-creator viewer
- WHEN the detail actions render
- THEN no `Editar` button renders (backend 403 remains the backstop)

#### Scenario: Delete borrador advance

- GIVEN a borrador advance and its creator
- WHEN `Eliminar` is pressed
- THEN a destructive ConfirmDialog appears, `DELETE /progress/{id}/` succeeds, and the app redirects to the list

#### Scenario: Delete hidden when ineligible

- GIVEN a non-borrador advance or a non-creator user
- WHEN the detail actions render
- THEN no delete button is available

### PR3 — Structure + tests (RF-045, RF-046, RF-047)

#### Scenario: Barrel and constants export

- GIVEN the module is imported
- WHEN `index.ts` is resolved
- THEN components, hooks, and constants export; `doc_type` values resolve to Spanish labels

#### Scenario: Extracted components keep behavior

- GIVEN the list, detail, and new/edit routes
- WHEN they render through `AdvanceList`, `AdvanceDetail`, and `AdvanceForm`
- THEN existing behaviors (list %, FSM bar, review timeline, state history, create) are unchanged

#### Scenario: Test parity gates the PR

- GIVEN PR3 CI runs
- WHEN `jest --coverage` and `tsc --noEmit` execute
- THEN coverage ≥80%, types pass, and no test asserts `post(..., {})` for observe/reject

## Section 3: API Contract

Backend endpoints already available (`apps.progress`, `/api` prefix) — no backend changes.

| Endpoint | Method | Frontend use |
|----------|--------|--------------|
| `/progress/{id}/` | PATCH | Edit borrador advance (RF-043); 403 backstop otherwise |
| `/progress/{id}/` | DELETE | Delete borrador advance, creator-only (RF-044) |
| `/progress/{id}/observe/` | POST | Body MUST include `review_text` (RF-041); backend defaults to `""` → blank rows |
| `/progress/{id}/reject/` | POST | Body MUST include `review_text` (RF-041); same blank-row risk |
| `/progress/{id}/documents/` | GET, POST | DocumentsManager list/create `{name, doc_type, external_url}` (RF-042) |
| `/progress/{id}/documents/{did}/` | PATCH, DELETE | DocumentsManager edit/delete (RF-042) |
| `/projects/{id}/progress/` | GET | List (unchanged) |

## Section 4: UI/UX Notes

- **Edit/delete gating**: `Editar` and `Eliminar` render only for `borrador` advances; delete additionally requires creator. Client-side gating with the backend 403 as backstop.
- **Observe/reject dialog**: textarea-based dialog (ConfirmDialog has no children slot — reuse the Dialog+textarea pattern from DocumentsManager); confirm disabled on blank input; `reject` keeps destructive styling.
- **DocumentsManager**: metadata-only (`external_url`, `name`, `doc_type`); rows render as external links; mutations refresh the documents list via advances-root invalidation.
- **Legacy data**: pre-existing blank `review_text` rows render a `—` fallback in the review timeline (cosmetic, non-blocking).
