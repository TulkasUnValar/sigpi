# Apply Progress — Frontend Advances Module Completion (PR 1: Functional Gaps)

## Scope

PR 1 of 3 (auto-chain, stacked-to-main). Implements RF-041 (review-text
dialog for observe/reject), RF-042 (metadata-only documents CRUD), and the
PR 1 slice of RF-045 (constants + barrel) and RF-047 (query-key factories,
no empty-body observe/reject assertion anywhere).

Mode: **Strict TDD** (openspec/config.yaml `strict_tdd: true`, Jest available).
Delivery: auto-chain, PR 1 slice, `Decision needed before apply: No`.

## Tasks Completed (13/13 PR 1)

All PR 1 tasks (1.1–1.13) are complete and marked `[x]` in `tasks.md`.

| Task | Summary |
|------|---------|
| 1.1 | FsmActionBar: observe/reject open a Dialog + textarea; confirm disabled on blank; no POST before confirm |
| 1.2 | mutations.ts: `AdvanceTransitionPayload` + optional `review_text` in observe/reject body |
| 1.3 | action-bar.test.tsx: RF-041 scenarios (dialog-open, blank-blocks, cancel-sends-nothing, body-includes-text) |
| 1.4 | types.ts: `AdvanceDocumentPayload` (AdvanceDocument already existed) |
| 1.5 | queries.ts: `useAdvanceDocuments` → `GET /api/progress/{id}/documents/` |
| 1.6 | mutations.ts: `useCreateAdvanceDocument` / `useUpdateAdvanceDocument` / `useDeleteAdvanceDocument`, invalidate advances root |
| 1.7 | DocumentsManager.tsx: metadata CRUD, external-link rows, ConfirmDialog delete, borrador+creator gated writes, no upload |
| 1.8 | constants.ts: status + doc_type labels/options with Spanish labels + getters |
| 1.9 | index.ts barrel: components, hooks, constants, fsm, schemas, types |
| 1.10 | query-keys.ts: `documents` + `reviews` factories under advances |
| 1.11 | mocks/handlers.ts + fixtures/advances.ts: documents GET/POST/PATCH/DELETE + body-aware observe/reject |
| 1.12 | documents-manager.test.tsx: CRUD flows, cache refresh, no-upload, gating |
| 1.13 | detail page mounts DocumentsManager (barrel import per RF-045) |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1–1.3 | `__tests__/features/advances/action-bar.test.tsx` | Component | ✅ 6/6 baseline | ✅ 4 new tests failed | ✅ 8/8 | ✅ 4 cases (observe, reject, blank, cancel) | ✅ `needsReviewText` extracted to fsm.ts; suite re-run green |
| 1.2 | (covered via action-bar tests) | Unit | ✅ 6/6 | ✅ (RED via component) | ✅ | ✅ approve `{}` vs reject `{review_text}` paths | ✅ payload interface exported |
| 1.4–1.7, 1.12 | `__tests__/features/advances/documents-manager.test.tsx` | Component | ✅ 50/50 baseline | ✅ module-not-found RED | ✅ 7/7 | ✅ 7 cases (render, no-upload, create+refresh, edit, delete, non-creator, non-borrador) | ✅ label map extracted to constants.ts |
| 1.1/fsm | `__tests__/features/advances/fsm.test.ts` | Unit | ✅ 12/12 | ✅ 2 new tests | ✅ 14/14 | ✅ 2 cases (review actions vs non-review) | ➖ None needed |
| 1.10 | existing query-keys suites | Unit | ✅ 14/14 (3 suites) | ✅ via factory usage | ✅ | ✅ documents/reviews shape | ➖ None needed (structural) |
| 1.8, 1.9 | (structural: constants + barrel) | Unit | N/A | Triangulation skipped: purely structural, single possible output; exercised via DocumentsManager render test ("Evidencia" label) and `tsc` | | | |

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `node ./frontend/node_modules/jest/bin/jest.js --config frontend/jest.config.js frontend/__tests__/features/advances` → **8 suites passed, 59 tests passed** |
| Runtime harness command/scenario and exact result | `npm run dev` (MSW) — manual dev-flow scenario; **N/A for automated runtime**: the installed msw build cannot be loaded through jest-resolve in this setup (raw `.ts` sources with `#core` imports — project-documented gotcha in `__tests__/features/researchers/fixtures.test.ts`). The MSW handler contract (URLs, bodies, review_text capture) is asserted by the component tests at the api-layer boundary. |
| Rollback boundary | `frontend/features/advances/*`, `frontend/lib/query-keys.ts`, `frontend/mocks/handlers.ts`, `frontend/fixtures/advances.ts`, `frontend/fixtures/index.ts`, `frontend/app/projects/[id]/advances/[advanceId]/page.tsx` — reverting these files restores pre-PR-1 behavior without touching other features. |

## Gate Checks

| Check | Command | Result |
|---|---|---|
| Tests (advances) | `jest ... frontend/__tests__/features/advances` | ✅ 59/59 |
| Tests (query-keys consumers) | `jest ... institutions/products/reports query-keys` | ✅ 14/14 |
| Types | `node node_modules/typescript/bin/tsc -p tsconfig.json --noEmit` | ✅ 0 errors |
| Lint | `node node_modules/eslint/bin/eslint.js . --ext .ts,.tsx` | ✅ exit 0 (pre-existing MODULE_TYPELESS warning only) |

## Deviations from Design

None — implementation matches `design.md`. Notes for reviewers:

- `AdvanceTransitionPayload` lives in `mutations.ts` (per tasks.md); design listed the same shape under Interfaces.
- Document mutations are named `useCreateAdvanceDocument` / `useUpdateAdvanceDocument` / `useDeleteAdvanceDocument` (feature-prefixed, consistent with `useAdvanceTransition` / `useCreateAdvance`).
- Document write gating is `status === "borrador" && user?.id === createdBy` (spec scenario S5); backend (`IsProgressCreatorOrProjectMember` + borrador guard) remains the backstop.
- `needsReviewText` (fsm.ts) drives the dialog trigger — approve and creator transitions keep the immediate `{}` POST.
- The FSM mock transition handler is now body-aware: observe/reject append a ProgressReview carrying the posted `review_text` (review_type `observation`/`rejection`).

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/features/advances/FsmActionBar.tsx` | Modified | Review-text Dialog+textarea for observe/reject; confirm disabled on blank; no POST before confirm |
| `frontend/features/advances/fsm.ts` | Modified | `needsReviewText()` pure function (observe/reject) |
| `frontend/features/advances/mutations.ts` | Modified | `AdvanceTransitionPayload` + optional `review_text`; document create/update/delete mutations |
| `frontend/features/advances/queries.ts` | Modified | `useAdvanceDocuments` (nested documents endpoint) |
| `frontend/features/advances/types.ts` | Modified | `AdvanceDocumentPayload` |
| `frontend/features/advances/DocumentsManager.tsx` | Created | Metadata-only document CRUD (calls pattern) |
| `frontend/features/advances/constants.ts` | Created | Status + doc_type labels/options (Spanish) + getters |
| `frontend/features/advances/index.ts` | Created | Module barrel |
| `frontend/lib/query-keys.ts` | Modified | `documents` + `reviews` factories under advances |
| `frontend/app/projects/[id]/advances/[advanceId]/page.tsx` | Modified | Mounts DocumentsManager; barrel imports |
| `frontend/mocks/handlers.ts` | Modified | Documents GET/POST/PATCH/DELETE; body-aware observe/reject |
| `frontend/fixtures/advances.ts` | Modified | `FixtureAdvanceDocument` type + `fixtureAdvanceDocuments` (derived from details) |
| `frontend/fixtures/index.ts` | Modified | Re-exports advance document fixtures |
| `frontend/__tests__/features/advances/action-bar.test.tsx` | Modified | RF-041 dialog scenarios; no `{}` observe/reject assertion |
| `frontend/__tests__/features/advances/documents-manager.test.tsx` | Created | RF-042 S5–S6 scenarios |
| `frontend/__tests__/features/advances/fsm.test.ts` | Modified | `needsReviewText` unit coverage |

## Remaining Work

- PR 2 — Edit/Delete Parity (tasks 2.1–2.11)
- PR 3 — Structure + Test Parity (tasks 3.1–3.10)

## PR Boundary

- Mode: chained PR slice (auto-chain, stacked-to-main)
- Current work unit: PR 1 — Functional Gaps (RF-041, RF-042, RF-045 slice, RF-047 slice)
- Boundary: starts at advances feature data layer, ends at detail page documents UI + mocks
- Review budget impact: ~800 changed lines (matches the ~800 PR 1 forecast); 13/34 change tasks complete
