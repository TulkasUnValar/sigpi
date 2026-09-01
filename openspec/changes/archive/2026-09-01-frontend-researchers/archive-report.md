# Archive Report: frontend-researchers

**Change**: `frontend-researchers`
**Project**: `sigpi`
**Archived**: 2026-09-01
**Delivery**: `auto-chain`, `stacked-to-main`
**Status**: Complete

## Executive Summary

The SIGPI frontend now provides institution-scoped researcher management across listing, creation, detail, editing, completeness, deactivation, affiliations, external profiles, and metadata-only attachments. The projects creation wizard now consumes the paginated researcher API correctly, and accessibility polish was applied to the researchers routes. All 29 implementation tasks are complete and the change passed final verification.

No backend files or backend behavior were changed.

## Delivered

### Capabilities

- Added the `features/researchers` data layer: types, zod schemas, permissions, lifecycle metadata, institution-scoped query keys, queries, mutations, and cache invalidation.
- Added researcher routes:
  - `/researchers` — paginated list, completeness bars, status badges, row actions, and empty state.
  - `/researchers/new` — role-gated creation with field-error handling and redirect to detail.
  - `/researchers/{id}` — overview, affiliations, external profiles, and attachments tabs.
  - `/researchers/{id}/edit` — self/admin editing and reactivation through `is_active` PATCH.
- Added deactivation through an admin-level destructive `ConfirmDialog` flow.
- Added affiliations management with dependent center → group → line selects, first-affiliation primary semantics, primary switching, deletion, and cross-institution error toasts.
- Added external-profile management for the supported providers.
- Added metadata-only attachment management using external links; no upload flow was introduced.
- Added the `Investigadores` sidebar item for authenticated roles and researcher `active`/`inactive` status mapping.
- Fixed the `/projects/new` researcher query to consume `Page<ResearcherList>`, map `results` to `{id, full_name}`, and intentionally avoid fetching page 2.
- Added loading, table, pagination, and form-error accessibility attributes and tests.
- Added MSW fixtures and handlers for researchers, affiliations, external profiles, and attachments.

### Principal Files and Areas

- `frontend/features/researchers/**`
- `frontend/app/researchers/**`
- `frontend/features/projects/queries.ts`
- `frontend/app/projects/new/page.tsx`
- `frontend/lib/query-keys.ts`
- `frontend/components/shell/Sidebar.tsx`
- `frontend/components/shared/StatusBadge.tsx`
- `frontend/fixtures/researchers.ts`
- `frontend/mocks/handlers.ts`
- `frontend/__tests__/**` researcher, project, shell, and status coverage

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `researchers` | Created | The new `researchers-ui` full specification was mechanically copied into `openspec/specs/researchers/spec.md`. |
| `projects` | Updated | The `Create wizard` requirement and its three scenarios from the `projects-ui` delta were merged into `openspec/specs/projects/spec.md`. |

The active change folder was moved to `openspec/changes/archive/2026-09-01-frontend-researchers/` and contains the proposal, exploration, delta specs, design, tasks, apply progress, verification report, and this archive report.

## Completion and Verification

- Tasks: **29/29 complete** — PR1 15/15, PR2 8/8, PR3 6/6.
- Tests: **81 suites / 579 tests passing**.
- Whole-project coverage: **92.31% statements / 87.87% branches / 81.30% functions / 93.28% lines**.
- `tsc --noEmit`: clean.
- ESLint: clean on changed files.
- Prettier: clean on changed files.
- Critical verification findings: **0**.
- Backend changes: **none**.

## PR Slices

No GitHub pull requests were created; the implementation remains on the local stacked branches.

| Slice | Branch | Base | Commits | Scope |
|---|---|---|---:|---|
| PR1 | `feature/frontend-researchers-pr1` | `main` | 4 | Foundation, routes, shell integration, base fixtures/handlers, and tests. |
| PR2 | `feature/frontend-researchers-pr2` | PR1 | 5 | Nested managers, nested data layer, fixtures/handlers, tab wiring, and tests. |
| PR3 | `feature/frontend-researchers-pr3` | PR2 | 4 | Wizard pagination fix, accessibility polish, contract tests, and documentation sync. |

Known work-unit commits include PR1 `ec9aeae`, `33d5ded`, `bcc1e1e`, `e1a090a`; PR2 `a14f29d`, `1d7ce17`, `c641f89`, `38a7174`, `5f297ce`; and PR3 `c65ca78`, `96732db`, `27ef617`, `ac6fa96`.

## Known Issues and Deviations

- PR3 frontend authored diff was **408 lines**, eight lines above the 400-line review budget. This was accepted by the configured `auto-chain` strategy; the aggregate change was intentionally split into three stacked slices.
- Per-file branch coverage is below 80% in `features/projects/queries.ts` (66.66%) and `ResearcherForm.tsx` (73.68%), while whole-project coverage is above the 80% floor. These remain informational warnings, not blockers.
- Repo-wide Prettier reports pre-existing issues in 194 files, including generated coverage output and earlier modules; all changed files for this change pass formatting.
- `msw/node` is not resolvable by Jest in this environment because of the installed MSW package's subpath/raw-TypeScript resolution. Runtime handlers and fixture contracts were covered without MSW-in-Jest.
- No browser E2E smoke test was run; route behavior was covered through the repository's established RTL and mocked API pattern.
- Native HTML selects were used for dependent/constrained affiliation fields instead of Radix Select for deterministic accessibility testing in jsdom.
- Existing affiliation rows display FK identifiers because the serializer exposes identifiers only; resolving every hierarchy name was out of scope.
- The `gentle-ai sdd-verify-validate` binary was unavailable during verification. The persisted verification report records this limitation and the passing test/type-check evidence.

## Risks and Rollback Plan

- Reverting PR1 removes the researchers foundation, routes, shell integration, base handlers, and tests; projects remain unaffected.
- Reverting PR2 removes nested managers, nested handlers, and tab wiring while retaining PR1 overview/edit behavior.
- Reverting PR3 restores the previous wizard pagination bug and removes the accessibility polish; it causes no data loss and leaves PR1/PR2 intact.
- No database migration, feature flag, or backend rollback is required.
- The main operational follow-up is to create and merge the stacked GitHub PRs after review, then retain this archived change as the audit trail.

## Traceability

Engram observations read during archive:

- `#349` — `sdd/frontend-researchers/proposal`
- `#350` — `sdd/frontend-researchers/spec`
- `#351` — `sdd/frontend-researchers/design`
- `#352` — `sdd/frontend-researchers/tasks`
- `#353` — `sdd/frontend-researchers/apply-progress`
- `#356` — `sdd/frontend-researchers/verify-report`

## Mechanical Archive Readback

The required recursive readbacks were run after filesystem operations. Both produced empty output (no differences):

```text
--- COPY DIFF (researchers-ui -> main) ---

--- MOVE DIFF (pre-move snapshot -> archive) ---
```

The empty `diff -r` results confirm byte-preserving copy and archive move operations.

## SDD Cycle Complete

The change has been planned, implemented, verified, and archived. It is ready for the PR review and merge workflow.
