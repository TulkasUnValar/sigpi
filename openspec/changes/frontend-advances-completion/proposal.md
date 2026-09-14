# Proposal: Frontend Advances Module Completion (SIGPI §6.5)

## Intent

Advances is the only MVP module without frontend parity — products, reports, calls, researchers, institutions all ship full UIs, while advances has 3 inline pages plus a critical bug: `observe`/`reject` POST an empty body `{}`, creating ProgressReview rows with blank `review_text` (violates RF-046/047). Completing it delivers spec-mandated features (documents RF-043, review text RF-046/047) and closes the last MVP gap.

## Scope

### In Scope
- **PR1 — Functional gaps**: review_text Dialog+textarea for observe/reject (fixes blank-review bug; updates `action-bar.test.tsx`, which asserts the buggy `{}` body); DocumentsManager (metadata-only CRUD, calls pattern, RF-043); `constants.ts` (doc_type labels) + barrel `index.ts`; query-keys for documents/reviews; MSW handlers/fixtures
- **PR2 — Edit + delete parity**: `edit/[advanceId]/page.tsx` + shared `AdvanceForm` (RHF+zod, hides project select in edit — backend strips project); borrador-gated delete button; borrador-gated Editar button on detail; `useAdvanceDetail` gains `enabled: Boolean(id)`
- **PR3 — Structure + tests**: extract `AdvanceList`/`AdvanceDetail`/`AdvanceForm` from inline pages (products pattern); test parity (mutations/queries/index/query-keys/edit/documents/review); Jest ≥80%, `tsc --noEmit`

### Out of Scope
- File upload (RF-043 deferred; `external_url` only)
- StateHistoryManager extraction (inline timeline suffices)
- `permissions.ts` (roles already inline in fsm.ts)
- List filters/ordering (backend supports; no UI requirement)

## Capabilities

> Contract between proposal and specs phases.

### New Capabilities
- `advances-ui`: full frontend module — nested list/detail, create/edit/delete, FSM bar with review_text, documents manager, review timeline + state history, role/state gating (mirrors `calls-ui`/`researchers-ui`)

### Modified Capabilities
- `frontend-mvp`: `advances-ui` section superseded by the dedicated `advances-ui` spec (requirements move and expand)

## Approach

Approach A — full completion, 3 chained PRs (stacked-to-main): PR1 functional fixes → PR2 edit/delete parity → PR3 structure/tests. Backend untouched; zod mirrors serializer rules; borrador gating client-side, backend 403 as backstop.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/features/advances/**` | Modified/New | index.ts, constants.ts, DocumentsManager, AdvanceForm/List/Detail, PATCH/DELETE mutations, review_text in FSM |
| `frontend/app/projects/[id]/advances/**` | Modified/New | edit/[advanceId] page; pages consume extracted components; gated buttons |
| `frontend/lib/query-keys.ts` | Modified | advances documents/reviews factories |
| `frontend/mocks/handlers.ts`, `frontend/fixtures/advances.ts` | Modified/New | MSW PATCH/DELETE/documents/observe+reject with body |
| `frontend/features/advances/__tests__/action-bar.test.tsx` | Modified | removes assertion encoding buggy `{}` body |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing test encodes buggy behavior (`post(..., {})` on reject) | High | Fix assertion in same PR as dialog |
| New UI pattern: text-input FSM transition (ConfirmDialog lacks children slot) | Med | Dialog+textarea; test dialog open + payload |
| Exceeds 400-line review budget (~2,200 total) | High | 3 chained PRs; sizes forecast in sdd-tasks |
| Existing blank review_text rows in data | Low | Cosmetic; timeline renders "—" fallback |

## Rollback Plan

Stacked-to-main feature-branch chain: revert each PR independently. Frontend-only, no data/backend impact.

## Dependencies

None new: backend `apps.progress` API complete; TanStack Query, RHF+zod, shadcn/ui, MSW present; products form + calls DocumentsManager are target patterns.

## Success Criteria

- [ ] All §6.5 RFs met in UI: create/submit (RF-041/044), borrador-only edit/delete (RF-042), documents metadata CRUD (RF-043), observe/reject send `review_text` and render non-blank reviews (RF-046/047), state history shown (RF-048)
- [ ] Module parity with products/reports/calls: barrel, constants, dedicated components, edit page, gated delete
- [ ] Jest ≥80%, `tsc --noEmit` green; no test asserts the buggy empty-body POST
