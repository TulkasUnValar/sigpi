# Design: Frontend Advances Module Completion

## Technical Approach

Complete the existing project-scoped advances feature without backend changes. Preserve its TanStack Query, shadcn/ui, Sonner, and client-component conventions, while moving page-local UI into feature components. Deliver the work as the proposal's three stacked PRs: functional gaps, edit/delete parity, then extraction and test parity.

## Architecture Decisions

| Decision | Choice | Alternatives / rationale |
|---|---|---|
| Shared form | `AdvanceForm` uses RHF with `zodResolver`; create includes `project`, edit hides it and sends writable fields only. | Retaining the hand-rolled create form would duplicate validation and make edit behavior diverge. `advanceEditSchema` reuses create rules and strips/omits project. |
| Documents | Copy calls `DocumentsManager` exactly: local dialog state, metadata fields, external-link rows, ConfirmDialog deletion, role/state-gated writes. | File upload is explicitly out of scope; a separate manager or upload abstraction adds no value. |
| Detail/list boundaries | `AdvanceList` owns progress average and rows; `AdvanceDetail` owns summary, FSM, documents, review timeline, and state history. Routes remain thin layout/parameter adapters. | Keeping inline pages prevents reuse by the edit route and blocks component-level test parity. |
| Review transitions | `observe` and `reject` use `Dialog` + textarea; confirmation is disabled for trimmed-empty text. Mutation accepts optional `review_text` and sends it only when supplied. | `ConfirmDialog` has no children slot and cannot collect input. |

## Data Flow

```text
Route params → query hook → AdvanceList/AdvanceDetail
                              ↓
                       feature mutations → api → invalidate advances/dashboard/projects
                              ↓
                  detail refreshes documents/reviews/state history
```

`useAdvanceDetail` is enabled only when an id exists. `useAdvanceDocuments` reads the nested documents endpoint and document mutations invalidate the advances root (and the detail/document key when available). Existing nested detail data remains the source for reviews and state logs; review/state-history key factories are added for endpoint/test parity.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/features/advances/AdvanceForm.tsx` | Create | RHF/zod shared create/edit form; project select only in create; server errors/toasts and redirects. |
| `frontend/features/advances/{AdvanceList,AdvanceDetail,DocumentsManager}.tsx` | Create | Extract list/detail; metadata-only document CRUD copied from calls pattern. |
| `frontend/features/advances/{constants,index}.ts` | Create | Status and document-type labels/options plus public exports. |
| `frontend/features/advances/{types,schemas,queries,mutations}.ts` | Modify | Edit/document payloads, edit schema, document query, update/delete/document mutations, enabled detail query. |
| `frontend/features/advances/FsmActionBar.tsx` | Modify | Input dialogs and review-text payloads for observe/reject. |
| `frontend/lib/query-keys.ts` | Modify | `documents` and `reviews` factories under advances. |
| `frontend/app/projects/[id]/advances/**` | Modify/Create | Thin list/new/detail wrappers, new `[advanceId]/edit/page.tsx`, gated edit/delete controls. |
| `frontend/mocks/handlers.ts`, `frontend/fixtures/advances.ts` | Modify | PATCH/DELETE/document endpoints and transition body-aware fixtures. |
| `frontend/__tests__/features/advances/**` | Modify/Create | Action-bar update; mutations, queries, index, query-keys, edit page, DocumentsManager, and schema coverage. |

## Interfaces / Contracts

```ts
type AdvanceWritableFields = Omit<CreateAdvancePayload, "project">;
type AdvanceEditPayload = AdvanceWritableFields;
type AdvanceDocumentPayload = { name: string; doc_type: string; external_url: string };
type AdvanceTransitionPayload = { id: string; action: string; review_text?: string };
```

`PATCH /api/progress/{id}/` receives `AdvanceEditPayload`; document CRUD uses `/api/progress/{id}/documents/` and `/documents/{documentId}/`; observe/reject receive `{ review_text }`. Edit and delete controls render only for `borrador`; delete additionally compares the authenticated user to `created_by`. Backend 403 responses remain the authorization backstop.

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | Schemas, payloads, query-key shape, barrel exports | Jest direct tests; assert project omission and Spanish document labels. |
| Component | Dialog validation/body, document CRUD, edit form, permissions, extracted list/detail rendering | RTL with mocked API, QueryClient, auth store; no empty-body observe/reject assertion. |
| Integration | MSW PATCH/DELETE/documents and review transition fixtures | Request-body assertions and cache refresh behavior. |
| Gate | Coverage and types | `jest --coverage` ≥80%; `tsc --noEmit`. |

## Threat Matrix

| Boundary | Applicability | Response / RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable documentation classification. | None. |
| Git repository selection | N/A — no Git automation. | None. |
| Commit state | N/A — no commit automation. | None. |
| Push state | N/A — no push automation. | None. |
| PR commands | N/A — no PR command execution. | None. |

## Migration / Rollout

No migration required. Roll out through the three stacked frontend PRs; each slice is independently revertible and backend-compatible.

## Open Questions

None.
