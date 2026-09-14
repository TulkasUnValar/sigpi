# Tasks: Frontend Advances Module Completion

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,150 (PR1 ~800, PR2 ~800, PR3 ~550) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Review-text dialog + documents CRUD (RF-041/042) | PR 1 | `npx jest __tests__/features/advances` | `npm run dev` (MSW) | advances feature files, mocks, query-keys |
| 2 | Shared form, edit route, gated edit/delete (RF-043/044) | PR 2 | `npx jest __tests__/features/advances` | `npm run dev` | edit page, AdvanceForm, update/delete mutations |
| 3 | Component extraction + test parity (RF-045/046/047) | PR 3 | `npx jest --coverage` + `npx tsc --noEmit` | `npm run dev` | extracted components, route rewiring, new tests |

## PR 1 — Functional Gaps (~800 lines)

- [x] 1.1 FsmActionBar.tsx: observe/reject Dialog+textarea; confirm disabled on blank; no POST before confirm (RF-041) ~140
- [x] 1.2 mutations.ts: `AdvanceTransitionPayload` + optional `review_text` in observe/reject mutations (RF-041) ~40
- [x] 1.3 action-bar.test.tsx: remove `{}` body assertion; dialog-open, blank-blocks, cancel-sends-nothing, body-includes-text (RF-041 S1–S4) ~150
- [x] 1.4 types.ts: `AdvanceDocumentPayload` + `AdvanceDocument` (RF-042) ~30
- [x] 1.5 queries.ts: `useAdvanceDocuments` reading nested documents endpoint (RF-042) ~40
- [x] 1.6 mutations.ts: document create/update/delete, invalidate advances root (RF-042) ~80
- [x] 1.7 DocumentsManager.tsx: metadata CRUD, external-link rows, ConfirmDialog delete, gated writes, no upload (RF-042 S5–S6) ~200
- [x] 1.8 constants.ts: status + doc_type labels/options, Spanish labels (RF-045) ~60
- [x] 1.9 index.ts barrel: components, hooks, constants exports (RF-045) ~30
- [x] 1.10 query-keys.ts: `documents` + `reviews` factories under advances (RF-047) ~20
- [x] 1.11 mocks/handlers.ts + fixtures/advances.ts: documents GET/POST/PATCH/DELETE; body-aware observe/reject (RF-041/042) ~80
- [x] 1.12 documents-manager.test.tsx: CRUD flows, cache refresh, no-upload assertion (RF-042 S5–S6) ~150
- [x] 1.13 detail page: mount DocumentsManager (RF-042) ~30

Deps: 1.1→1.2→1.3; 1.4→1.5/1.6→1.7→1.12/1.13; 1.11 after 1.6; 1.9 after 1.7+1.8

## PR 2 — Edit/Delete Parity (~800 lines)

- [ ] 2.1 schemas.ts: `advanceEditSchema` reusing create rules, strips project (RF-043) ~30
- [ ] 2.2 types.ts: `AdvanceWritableFields` + `AdvanceEditPayload` (RF-043) ~20
- [ ] 2.3 mutations.ts: `useUpdateAdvance` PATCHing writable fields (RF-043) ~70
- [ ] 2.4 mutations.ts: `useDeleteAdvance` + redirect on success (RF-044) ~50
- [ ] 2.5 queries.ts: `useAdvanceDetail` gains `enabled: Boolean(id)` (RF-043) ~15
- [ ] 2.6 AdvanceForm.tsx: RHF+zod shared create/edit; project select only in create; toasts/redirects (RF-043/046) ~250
- [ ] 2.7 edit/[advanceId]/page.tsx: seed from detail query, render AdvanceForm (RF-043) ~40
- [ ] 2.8 detail page: borrador-gated `Editar`/`Eliminar`; delete needs creator + ConfirmDialog (RF-043/044) ~90
- [ ] 2.9 mocks/handlers.ts: PATCH + DELETE handlers, body/status assertions (RF-043/044) ~50
- [ ] 2.10 edit-page.test.tsx: seed, PATCH body without project, redirect, hidden outside borrador (RF-043 S1–S2) ~180
- [ ] 2.11 mutations.test.tsx: update PATCH payload, delete success + creator gating (RF-043/044) ~120

Deps: 2.1→2.2→2.3/2.4; 2.6 after 2.1; 2.7 after 2.5+2.6; 2.8 after 2.3+2.4; 2.9 after 2.3+2.4; 2.10 after 2.7; 2.11 after 2.3+2.4

## PR 3 — Structure + Test Parity (~550 lines)

- [ ] 3.1 permissions.ts: `canEditAdvance`/`canDeleteAdvance` (borrador, creator) + permissions.test.ts (RF-043/044) ~80
- [ ] 3.2 AdvanceList.tsx: extract list + progress average from inline page (RF-046) ~120
- [ ] 3.3 AdvanceDetail.tsx: extract summary, FSM, documents, review timeline, state history (RF-046) ~140
- [ ] 3.4 routes: list/detail/new/edit consume extracted components, unchanged behavior (RF-046) ~60
- [ ] 3.5 queries.test.tsx: documents/detail/enabled query coverage (RF-047) ~90
- [ ] 3.6 index.test.ts: barrel exports + Spanish doc_type labels (RF-045) ~40
- [ ] 3.7 query-keys.test.ts: documents/reviews factory shape (RF-047) ~40
- [ ] 3.8 list-page.test.tsx → AdvanceList test (RF-046) ~60
- [ ] 3.9 detail-page.test.tsx → AdvanceDetail test (RF-046) ~60
- [ ] 3.10 Gate: `jest --coverage` ≥80% + `tsc --noEmit` green; no empty-body observe/reject assertion anywhere (RF-047) ~20

Deps: 3.4 after 3.2+3.3; 3.5 after PR1/PR2 queries; 3.6 after 1.9; 3.7 after 1.10; 3.8/3.9 after 3.2/3.3
