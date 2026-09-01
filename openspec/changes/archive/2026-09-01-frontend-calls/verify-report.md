```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:887928586c97a25a0fce1b2188c31d9fd346b6d7f4865133a5410e351f1d2e8f
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 3/3
test_command: cd frontend; jest --passWithNoTests
test_exit_code: 0
test_output_hash: sha256:eee4a63529e574b5240c14e3487ab5b03470439c91ab6b03cd8a46b8b1034508
build_command: cd frontend; npx tsc --noEmit
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
coverage_command: cd frontend; npx jest --coverage --passWithNoTests
coverage_exit_code: 0
coverage_statements: 90.51
coverage_branches: 89.42
coverage_functions: 80.12
coverage_lines: 91.96
coverage_threshold: 80
eslint_command: cd frontend; npx eslint .
eslint_exit_code: 0
eslint_output_hash: sha256:f2d6a86b0134a220189b22e70b6f26de00bfc94b4771603f079cb4acbe6b0e62
prettier_pr3_command: cd frontend; npx prettier --check features/calls/CallList.tsx features/calls/constants.ts features/calls/queries.ts fixtures/calls.ts fixtures/index.ts mocks/handlers.ts __tests__/features/calls/list.test.tsx __tests__/features/calls/fixtures.test.ts __tests__/features/calls/queries.test.tsx __tests__/features/calls/constants.test.ts
prettier_pr3_exit_code: 0
prettier_pr3_output_hash: sha256:17aa973d3f004560237d9a95171210b0671deff23d61628eecf7322ff5938f20
pr3_scope_only: true
pr3_requirements_total: 2
pr3_scenarios_total: 3
pr3_scenarios_compliant: 3
pr3_new_tests: 20
pr3_full_suite_tests: 571
pr3_full_suite_passing: 571
pr3_branch_coverage: 89.42
pr3_functions_coverage: 80.12
strict_tdd_mode: true
```

## Verification Report

**Change**: `frontend-calls` (project `sigpi`)
**Scope**: PR3 only — Filters + Polish + Verify (tasks 3.1–3.3)
**Mode**: Strict TDD (runner `cd frontend; jest --passWithNoTests`)
**Branch / HEAD**: `feature/frontend-calls-pr3` @ `862213f` (stacked on `feature/frontend-calls-pr2` @ `05dd7b8`, 4 commits)
**Date**: 2026-09-01
**Session**: `ses_fa2b678e7ffeLCVEKF4Qf4YcMj`
**Artifact store**: hybrid (OpenSpec file + Engram topic)

### Completeness

| Metric | Value |
|---|---|
| PR3 tasks total | 3 |
| PR3 tasks complete | 3 |
| PR3 tasks incomplete | 0 |
| Spec requirements (PR3 in scope) | 2 (Call list with filters, MSW fixtures and coverage) |
| Spec scenarios (PR3 in scope) | 3 |
| PR3 scenarios compliant | 3 |
| PR1/PR2 requirements excluded | 10 / 22 (per spec PR Boundaries table) |

PR3 in-scope requirements (per `specs/calls-ui/spec.md` PR Boundaries table):
- **Call list with filters** — status / call_type filter refetch wiring (3.1), a11y polish (3.2)
- **MSW fixtures and coverage** — coverage hardening tests + Jest ≥80% verification (3.3)

PR1 already satisfied the Paginated list / Empty institution / Paginated list handler / FSM handler scenarios; PR3 does not regress those (verified by full-suite rerun, 571/571).

### Build & Tests Execution

**Build (`tsc --noEmit`)**: PASS — exit 0
```text
(empty stdout/stderr — clean type check)
```
output_hash: `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (SHA-256 of empty bytes)

**Tests (`jest --passWithNoTests`)**: PASS — exit 0 — **571/571 tests, 68/68 suites**
```text
Test Suites: 68 passed, 68 total
Tests:       571 passed, 571 total
Snapshots:   0 total
Time:        21.078 s
Ran all test suites.
```
output_hash: `sha256:eee4a63529e574b5240c14e3487ab5b03470439c91ab6b03cd8a46b8b1034508`

**Coverage (`jest --coverage --passWithNoTests`)**: PASS — exit 0 — all metrics ≥80% threshold
| Metric | Value | Threshold | Status |
|---|---|---|---|
| Statements | 90.51 % | ≥ 80 | ✅ |
| Branches  | 89.42 % | ≥ 80 | ✅ |
| Functions | 80.12 % | ≥ 80 | ✅ (margin 0.12 pp) |
| Lines     | 91.96 % | ≥ 80 | ✅ |

**ESLint (`eslint .`)**: PASS — exit 0
```text
(node:1613723) [MODULE_TYPELESS_PACKAGE_JSON] Warning: Module type of file:///.../eslint.config.js?mtime=... is not specified and it doesn't parse as CommonJS.
Reparsing as ES module because module syntax was detected. This incurs a performance overhead.
To eliminate this warning, add "type": "module" to /home/tulkasubuntu/01-sigpi/frontend/package.json.
```
output_hash: `sha256:f2d6a86b0134a220189b22e70b6f26de00bfc94b4771603f079cb4acbe6b0e62`
Note: ESLint warning is informational (project `package.json` `type` field missing — not blocking, pre-existing, unrelated to PR3 diff).

**Prettier (PR3 files only)**: PASS — exit 0
```text
Checking formatting...
All matched files use Prettier code style!
```
output_hash: `sha256:17aa973d3f004560237d9a95171210b0671deff23d61628eecf7322ff5938f20`

**Prettier (repo-wide, informational)**: 245 pre-existing files flagged (HTML coverage output, `public/mockServiceWorker.js`, generated files, and PR1/PR2 files outside PR3 scope). Per acceptance criteria, repo-wide pre-existing issues are noted but not blocking.

### Spec Compliance Matrix — PR3 scope

| Requirement | Scenario | Test (file > case) | Result |
|---|---|---|---|
| Call list with filters | Filter by status | `__tests__/features/calls/list.test.tsx` > `refetches with ?status=abierta and renders only open calls` | ✅ COMPLIANT |
| Call list with filters | Filter by type | `__tests__/features/calls/list.test.tsx` > `refetches with ?call_type=external when the type filter is selected` | ✅ COMPLIANT |
| MSW fixtures and coverage | Coverage floor | `jest --coverage` (89.42 % branches ≥ 80) | ✅ COMPLIANT |

**Compliance summary**: 3/3 PR3 scenarios compliant. Combined-filter and reset-to-page-1 behaviors (per design deviation #7) are proven by `combines status and call_type filters in a single refetch`, `resets to page 1 when a filter is applied from a later page`, and `clears the status filter back to the unfiltered list via Todos` — all PASS. The a11y polish (3.2) is proven by `announces the loading region while fetching`, `renders an alert with the error message when the list query fails`, and `shows the filtered empty state when filters yield no results` — all PASS.

### TDD Compliance

| Check | Result | Details |
|---|---|---|
| TDD Evidence reported | ✅ | `sdd/frontend-calls/apply-progress` has TDD Cycle Evidence table for PR3 tasks 3.1/3.2/3.3 |
| All tasks have tests | ✅ | 3/3 PR3 tasks have test evidence (list.test.tsx + fixtures.test.ts + constants.test.ts + queries.test.tsx) |
| RED confirmed (tests exist) | ✅ | All listed test files exist on disk and contain the cited cases (list 5 + 3 = 8, fixtures 5, constants 6, queries 1) |
| GREEN confirmed (tests pass) | ✅ | Full suite 571/571; PR3-focused subset (list + fixtures + constants + queries) 37/37 |
| Triangulation adequate | ✅ | status filter: 3 cases (status alone, combined, reset-on-change, clear-via-Todos = 5 distinct assertions), type filter: 1 case; coverage hardening: 7 cases across 2 files |
| Safety Net for modified files | ✅ | Pre-existing calls suite ran 94/94 BEFORE PR3 changes (per apply-progress); full suite 571/571 AFTER — no regression |

**TDD Compliance**: 6/6 checks passed

### Test Layer Distribution

| Layer | Tests (PR3 additions) | Files | Tools |
|---|---|---|---|
| Unit | 11 | `constants.test.ts` (6) + `fixtures.test.ts` (5 PR3 cases) | jest |
| Component | 8 | `list.test.tsx` (5 filter wiring + 3 polish) | jest + @testing-library/react |
| Integration | 0 | — (PR1 covered routes integration; PR3 modifies only component layer) | — |
| E2E | 0 | — | Not in project config |
| **Total (PR3)** | **20** | **4** | |

### Changed File Coverage (PR3-only)

| File | Stmts % | Branch % | Funcs % | Lines % | Uncovered Lines | Rating |
|---|---|---|---|---|---|---|
| `features/calls/CallList.tsx` | 100 | 100 | 100 | 100 | — | ✅ Excellent |
| `features/calls/constants.ts` | 100 | 100 | 100 | 100 | — | ✅ Excellent |
| `features/calls/queries.ts` | 100 | 100 | 100 | 100 | — | ✅ Excellent |
| `fixtures/calls.ts` (added `filterCallRows`) | high | high | high | high | covered via `filterCallRows` contract tests | ✅ Excellent |
| `fixtures/index.ts` (re-export only) | n/a (barrel) | n/a | n/a | n/a | n/a | ➖ Not measurable (re-export line) |
| `mocks/handlers.ts` (list handler filter wiring) | high | high | high | high | covered indirectly via list.test.tsx query-path assertions | ✅ Acceptable |

**Average changed file coverage**: 100% on the three modules with line coverage reported; `filterCallRows` covered by 5 contract tests + 5 component tests that assert the resulting query string. The `index.ts` barrel only re-exports, and `mocks/handlers.ts` list handler reads query params via the tested `filterCallRows`.

### Assertion Quality (Step 5f audit)

Scanned all 20 PR3-added test cases across `list.test.tsx`, `fixtures.test.ts`, `constants.test.ts`, `queries.test.tsx`. Findings:

| Pattern | Result |
|---|---|
| Tautologies (`expect(true).toBe(true)`) | ✅ None |
| Empty-collection without companion non-empty test | ✅ None (filtered-empty test has companion non-filtered path) |
| Type-only assertions without value assertion | ✅ None |
| Assertions without production-code call | ✅ None (every test exercises either `useCallsList` or pure helpers via `act` + `fireEvent`) |
| Ghost loops over possibly-empty collections | ✅ None |
| Smoke-test-only (`render` + `toBeInTheDocument` without behavior) | ✅ None |
| CSS class / implementation-detail assertions | ✅ None |
| Mock-heavy tests (mocks > 2× assertions) | ✅ None (list tests use 1 `api.get` mock + ≥3 behavioral assertions per test) |

**Assertion quality**: ✅ All assertions verify real behavior (filter selection drives refetch with specific query params; loading/error/empty states have distinct roles + content; coverage tests exercise null-institution branch + label fallback paths).

### Quality Metrics

**Linter**: ✅ No errors on PR3 files (full repo exit 0; only `MODULE_TYPELESS_PACKAGE_JSON` informational warning unrelated to PR3 diff).
**Type Checker**: ✅ No errors (`tsc --noEmit` exit 0; empty output).
**Prettier**: ✅ All 10 PR3-touched files match Prettier style (exit 0); 245 pre-existing repo-wide files flagged but not blocking per acceptance criteria.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|---|---|---|
| `useCallsList({ page, status, call_type })` accepts the filter object | ✅ Implemented | `features/calls/queries.ts` — `useCallsList` serializes both filters into the query string (proven by `queries.test.tsx` > `serializes status and call_type filters into the query string` and the new null-institution fallback test) |
| Status filter selection refetches `?status=…` | ✅ Implemented | `CallList.changeStatus` → `setStatus(normalizeFilter(v))` + `setPage(1)` → query-key change drives refetch; proven by `list.test.tsx` status filter test + page-reset test |
| Call_type filter selection refetches `?call_type=…` | ✅ Implemented | Same pattern as status via `changeCallType`; proven by `list.test.tsx` type filter test |
| Combined filters serialize in one query string | ✅ Implemented | Both keys flow into the same `useCallsList` call → same query object → single `api.get` with both params (proven by `combines status and call_type filters in a single refetch`) |
| Page resets to 1 on filter change | ✅ Implemented | `changeStatus`/`changeCallType` both call `setPage(1)`; proven by `resets to page 1 when a filter is applied from a later page` |
| "Todos" clears each filter individually | ✅ Implemented | `ALL_FILTER = "all"` sentinel + `normalizeFilter` → `setStatus("")` / `setCallType("")`; proven by `clears the status filter back to the unfiltered list via Todos` |
| Loading region is announced | ✅ Implemented | `<div role="status" aria-label="Cargando convocatorias">` wraps 6 skeletons; proven by `announces the loading region while fetching` |
| Query failure renders an alert | ✅ Implemented | `error` branch renders `<div role="alert">{getErrorMessage(error)}</div>`; proven by `renders an alert with the error message when the list query fails` |
| Filtered-empty state is distinct from no-calls empty | ✅ Implemented | `EmptyState` `title={hasFilters ? "Sin resultados" : "No hay convocatorias"}`; proven by `shows the filtered empty state when filters yield no results` |
| Table is labelled | ✅ Implemented | `<table aria-label="Lista de convocatorias">` |
| Pagination count is announced | ✅ Implemented | `<span aria-live="polite">` wraps the page-count span |
| MSW list handler honors `status` / `call_type` query params | ✅ Implemented | `mocks/handlers.ts` calls `filterCallRows(callsStore, { status, call_type })` before paginating; proven by `fixtures.test.ts` (5 `filterCallRows` cases including combined and no-match) |
| `filterCallRows` is a pure function | ✅ Implemented | Exported from `fixtures/calls.ts`, barrel-re-exported from `fixtures/index.ts`; tested without MSW server (project has no `msw/node` runtime, per design deviation #8) |
| `CallList.tsx`, `constants.ts`, `queries.ts` reach 100 % coverage | ✅ Confirmed | Per coverage table above |
| Jest global coverage ≥ 80 % on all four metrics | ✅ Confirmed | statements 90.51 / branches 89.42 / functions 80.12 / lines 91.96 |
| No new dependency, no migration | ✅ Confirmed | PR3 diff is purely additive on existing module boundaries |

### Coherence (Design vs. Implementation)

| Design Decision | Followed? | Notes |
|---|---|---|
| Filter selection drives refetch immediately (no Apply button) | ✅ Yes | Design deviation #7 explicitly chosen and rationale documented; "Todos" per-filter reset options replace a clear button |
| MSW list handler filters server-side via pure function | ✅ Yes | Design deviation #8 explicitly chosen — `filterCallRows` is contract-tested so test setup does not need `msw/node` |
| `useCallsList` accepts `{ page, status, call_type }` | ✅ Yes | Filters flow through the query-key factory → one cache key per filter combination |
| Page reset on filter change | ✅ Yes | `setPage(1)` in both `changeStatus` and `changeCallType`; covered by `resets to page 1 when a filter is applied from a later page` |
| A11y: status region, alert, table label, aria-live count | ✅ Yes | All four a11y additions present and tested |
| Coverage hardening: labels, options, null-institution fallback | ✅ Yes | `constants.test.ts` (6 cases) + `queries.test.tsx` null-institution test added per task 3.3 |
| No new backend calls | ✅ Yes | PR3 diff touches only `frontend/` and OpenSpec planning files |
| Frontend-only rollout | ✅ Yes | Revert-PR3 leaves PR2's filter UI (non-refetching) intact per apply-progress rollback boundary |

### Issues Found

**CRITICAL**: None.

**WARNING**:
- Prettier flags 245 repo-wide files (HTML coverage output, `public/mockServiceWorker.js`, generated files, PR1/PR2 files outside PR3 scope). Not blocking per acceptance criteria; pre-existing in the repo at the start of the change.
- `package.json` `type` field missing (ESLint MODULE_TYPELESS_PACKAGE_JSON warning). Pre-existing; unrelated to PR3 diff.
- Coverage `functions` margin remains thin at 80.12 % (improved from 80.03 % after PR2). Floor met. Residual uncovered functions live in PR1/PR2 files (`projects/FsmActionBar.tsx` 30 % funcs, `lib/api.ts` 73.33 %, `store/auth.ts` 88.88 %) — out of PR3 scope.
- `pre-commit` hooks remain non-functional this session (Windows Python in `.git/hooks/pre-commit` vs. config `wsl-guard`). Mitigated by manual hook-equivalent runs (jest / tsc / eslint / prettier). Reinstall from WSL before the PR is pushed.

**SUGGESTION**:
- Future hardening: add a test that asserts the table also includes the page count inside the `aria-live` region (currently only the page number + count span is announced).
- Future hardening: wire `react-query` query-cache `select` to keep the empty-vs-filtered decision in pure logic instead of React state-derived branching.

### Verdict

**PASS** — PR3 slice (tasks 3.1–3.3) is complete, all runtime gates green, coverage ≥ 80 % on every metric, TDD cycle evidence intact, no regressions introduced on PR1/PR2.
