# Archive Report: frontend-calls

**Project**: `sigpi`
**Change**: `frontend-calls`
**Archived**: 2026-09-01
**Status**: Complete
**Artifact store**: hybrid
**Delivery**: `auto-chain`, `stacked-to-main`

## Executive Summary

The SIGPI frontend now provides institution-scoped call management for authenticated users: filtered listing, create/edit, four-tab detail, lifecycle transitions, gated deletion, nested document/project/history managers, shell integration, and tested fixtures. All 19 implementation tasks are complete, verification passed, and the change folder was mechanically moved to the archive.

No backend files, migrations, or API contracts were changed.

## Delivered

### Capabilities

- Paginated `/calls` list with status and call-type filters, page reset, clear controls, loading/error/empty states, and role-gated create CTA.
- `/calls/new` creation and `/calls/[id]/edit` shared form with conditional `external_entity` and date-order validation.
- `/calls/[id]` detail with Overview, Documents, Projects, and State history tabs.
- Five role/state-filtered FSM transitions: `open_call`, `close_call`, `start_evaluation`, `publish_results`, and `archive`; archive is confirmed and terminal.
- Delete gate restricted to `borrador` calls with zero linked projects, with confirmation and redirect.
- Metadata-only document CRUD, `abierta`-only project linking/unlinking with duplicate 409 handling, and read-only state history.
- Institution-scoped TanStack Query keys and call-root invalidation after call, document, and project mutations.
- Sidebar `Convocatorias` navigation and all call FSM status labels in `StatusBadge`.
- MSW fixtures and handlers for calls, transitions, documents, projects, state history, and filter behavior.

### Routes

- `frontend/app/calls/page.tsx`
- `frontend/app/calls/new/page.tsx`
- `frontend/app/calls/[id]/page.tsx`
- `frontend/app/calls/[id]/edit/page.tsx`

### Principal files and areas

- New module: `frontend/features/calls/**`
- Tests: `frontend/__tests__/features/calls/**`
- Shared query state: `frontend/lib/query-keys.ts`
- Shell/status integration: `frontend/components/shell/Sidebar.tsx`, `frontend/components/shared/StatusBadge.tsx`
- Fixtures and handlers: `frontend/fixtures/calls.ts`, `frontend/fixtures/index.ts`, `frontend/mocks/handlers.ts`
- Source-of-truth spec: `openspec/specs/calls/spec.md`

## Completion Status

| Slice | Tasks | Status |
|---|---:|---|
| PR1 — foundation | 11/11 | Complete |
| PR2 — nested managers and delete gate | 5/5 | Complete |
| PR3 — filters, polish, and verification | 3/3 | Complete |
| **Total** | **19/19** | **Complete** |

The persisted `tasks.md` contains no unchecked implementation tasks. The design question regarding `director_centro` was resolved with an explicit alias in `permissions.ts`.

## Tests and Quality Gates

- Jest: **571/571 tests passing across 68/68 suites**.
- Coverage: **90.51% statements, 89.42% branches, 80.12% functions, 91.96% lines**; every metric meets the 80% floor.
- TypeScript: `tsc --noEmit` passed with exit code 0.
- ESLint: passed with exit code 0; only the pre-existing `MODULE_TYPELESS_PACKAGE_JSON` informational warning remains.
- Prettier: passed for all changed files.
- Strict TDD evidence is recorded for all slices; no E2E was required by project configuration.

## PR Slices and Commits

| Slice | Branch | Relationship | Commits |
|---|---|---|---:|
| PR1 | `feature/frontend-calls-pr1` | 14 commits off `main` | 14 |
| PR2 | `feature/frontend-calls-pr2` | 5 commits stacked on PR1 | 5 |
| PR3 | `feature/frontend-calls-pr3` | 4 commits stacked on PR2 | 4 |

The branches remain unsubmitted: **no GitHub PRs were created during apply**. PR1 and PR2 exceed the 400-line review budget forecast, while PR3 is the smaller final slice; the stacked chain is the recorded mitigation. The current PR3 tip is `862213f`; PR2 tip is `05dd7b8`. PR1's recorded tip is `3db5f19`.

## Known Issues and Deviations

- List rows do not show submission dates because the backend `CallListSerializer` does not expose them; the implementation follows the available backend contract.
- Filter selection applies immediately rather than using a separate Apply button; `Todos` clears each filter.
- Delete is implemented as `DeleteCallButton.tsx` rather than inline in `CallDetail.tsx` for isolation and testability.
- `ProjectsManager` owns its candidate-project query instead of importing the projects feature.
- The test setup does not provide an `msw/node` runtime; filter behavior is contract-tested through the pure `filterCallRows` helper and mocked API paths.
- Pre-commit hooks were non-functional in the WSL/Windows environment; manual Jest, TypeScript, ESLint, and Prettier equivalents passed. Hooks should be repaired before pushing PRs.
- Repository-wide Prettier reports pre-existing generated/out-of-scope files; changed files are clean.
- Function coverage is close to the floor at 80.12%; residual uncovered functions are in out-of-scope shared files.
- No PRs have been created yet; archive closes the SDD change, not the external review/delivery process.

## Risks and Rollback Plan

### Risks

- The 0.12 percentage-point function-coverage margin may regress if shared frontend code changes before merge.
- Backend remains authoritative for role checks, state transitions, and 403/409 responses; frontend affordances alone are not a security boundary.
- Stacked branches must be rebased or retargeted so child PRs contain only their intended slice.
- Pre-commit hook repair remains an operational prerequisite before publishing branches.

### Rollback

This is a frontend-only change with no migration or backend impact. Revert stacked merges in reverse order: PR3, then PR2, then PR1. Reverting PR3 leaves the PR2 filter UI without the final refetch/polish behavior; reverting all three restores the pre-change frontend.

## Traceability

Engram observations read during archive:

- Proposal: `#364` — `sdd/frontend-calls/proposal`
- Spec: `#365` — `sdd/frontend-calls/spec`
- Design: `#366` — `sdd/frontend-calls/design`
- Tasks: `#367` — `sdd/frontend-calls/tasks`
- Apply progress: `#368` — `sdd/frontend-calls/apply-progress`
- Verify report: `#369` — `sdd/frontend-calls/verify-report`

The native review receipt gate was structurally absent from the launch status; no review artifacts were discovered or required. The verification report is an intermediate PR3 snapshot, and the final-state facts supplied at archive time govern the totals above.

## Mechanical Archive Evidence

The pre-move recursive snapshot was compared with the archived folder using `diff -r` after the move.

```text

```

The command produced no output, indicating byte-identical archived contents before adding this report.

## SDD Cycle

The `frontend-calls` change is fully planned, implemented, verified, and archived. The synced source-of-truth frontend requirements are in `openspec/specs/calls/spec.md`. The next operational step is creating and reviewing the stacked PRs.
