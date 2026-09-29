# Apply Progress — frontend-reports (PR1: Foundation)

**Status**: PR1 complete (15/15, tasks 1.1–1.15).
**Mode**: Strict TDD (runner `cd frontend; jest --passWithNoTests --coverage`).
**Delivery**: auto-chain, stacked-to-main. PR1 slice targets `main`.
**Date**: 2026-09-02

---

## Executive Summary (PR1)

Implemented the PR1 foundation slice of the reports module per the
`frontend-reports` spec (RF-001..RF-006, RB-001..RB-004) and design:
institution-scoped data layer (`types`, `constants` with the 4 report codes
→ Spanish labels + endpoint builders, `schemas` with zod validation of the
generator selection and advances→project mapping, `permissions` with RB-001
role gating, `query-keys` reports factory, `queries` with `useReportPreview`
and `useReportEntityOptions` deriving options from the existing
projects/researchers/centers hooks, `mutations` with `useApproveReport`),
the `ReportHub` + `ReportGeneratorForm` components, the protected
`/reports` route (`app/reports/page.tsx` role-gates the hub so a user
without `CanGenerateReport` gets a 403 alert with zero API calls), shell
integration (Sidebar `Informes` item + middleware `/reports` prefix), the
authenticated `lib/download.ts` blob-download utility, MSW fixtures +
handlers (preview success/403/404/500, pdf bytes, approve
success/403/409-RN-017 verbatim), and full Jest/RTL coverage.

All gates green: 122 suites / 935 tests (full suite, up from the 108/844
baseline), `features/reports` coverage 100% stmts / 95.71% branch / 98.38%
funcs / 100% lines (floor 80%), `tsc --noEmit` clean, ESLint clean.

One supporting change outside the feature folder: `lib/errors.ts`
`normalizeError` now also reads the backend's `{error: "..."}` key (the
reports endpoints return `error`, not `detail`). This is required for the
RN-017 approval message to surface verbatim (RB-002 / RF-005 scenario).

### TDD Cycle Evidence (PR1)

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `__tests__/features/reports/types.test.ts` | Structural | N/A (new) | ✅ Written (type-only, tsc-validated) | ✅ tsc clean + 4/4 | ➖ Single (purely structural) | ➖ None needed |
| 1.2 | `__tests__/features/reports/constants.test.ts` | Unit | N/A (new) | ✅ Written (module missing) | ✅ 10/10 | ✅ 5 cases | ➖ None needed |
| 1.3 | `__tests__/features/reports/schemas.test.ts` | Unit | N/A (new) | ✅ Written (module missing) | ✅ 8/8 | ✅ 3 cases | ➖ None needed |
| 1.4 | `__tests__/features/reports/permissions.test.ts` | Unit | N/A (new) | ✅ Written (module missing) | ✅ 10/10 | ✅ 4 cases | ✅ widened centers type (`name?`) |
| 1.5 | `__tests__/features/reports/query-keys.test.ts` | Unit | ✅ 108/844 baseline | ✅ Written (factory missing) | ✅ 5/5 | ✅ 3 cases | ➖ None needed |
| 1.6 | `__tests__/features/reports/queries.test.tsx` | Unit (RTL hook) | N/A (new) | ✅ Written (module missing) | ✅ 8/8 | ✅ 4 cases | ➖ None needed |
| 1.7 | `__tests__/features/reports/mutations.test.tsx` | Unit (RTL hook) | N/A (new) | ✅ Written (module missing) | ✅ 3/3 | ✅ 3 cases | ➖ None needed |
| 1.8 | `hub.test.tsx` + `reports-page.test.tsx` + `index.test.ts` | Component | N/A (new) | ✅ Written (modules missing) | ✅ 9/9 + 2/2 + 5/5 | ✅ 5 cases | ✅ Radix Select `key={type}` remount for entity reset |
| 1.9 | `__tests__/features/reports/generator-form.test.tsx` | Component | N/A (new) | ✅ Written (module missing) | ✅ 8/8 | ✅ 5 cases | ✅ wait-for-enabled test fix |
| 1.10 | `__tests__/features/reports/sidebar.test.tsx` | Component | ✅ 108/844 baseline | ✅ Written (item missing) | ✅ 6/6 | ✅ 5 roles | ➖ None needed |
| 1.11 | `__tests__/middleware.test.ts` (extended) | Unit | ✅ 108/844 baseline | ✅ Written (prefix missing) | ✅ 2/2 new | ✅ 2 cases | ➖ None needed |
| 1.12 | `__tests__/features/reports/fixtures.test.ts` | Unit | N/A (new) | ✅ Written (fixtures missing) | ✅ 5/5 | ✅ 5 cases | ➖ None needed |
| 1.13 | `fixtures.test.ts` contract + tsc (handlers) | Mixed | N/A (new) | ✅ Written (fixtures RED first) | ✅ tsc clean | ✅ 3 endpoint guards | ✅ moved `VALID_REPORT_TYPES` out of the handlers array (tsc TS1137 fix) |
| 1.14 | `__tests__/lib/download.test.ts` | Unit | N/A (new) | ✅ Written (module missing) | ✅ 4/4 | ✅ 4 cases | ✅ URL stubs via `as unknown` casts (tsc fix) |
| 1.15 | Full suite + `__tests__/lib/errors.test.ts` (`error` key) | Mixed | ✅ 108/844 baseline | ✅ Written (error-key cases RED) | ✅ 935/935 | ✅ full | ✅ coverage raised to 100% lines / 95.71% branch |

### Test Summary (PR1)

- **Total tests written**: 91 new across 15 test files (13 reports suites + `lib/download.test.ts` + extended `lib/errors.test.ts` + extended `middleware.test.ts`); focused slice = 16 suites / 119 tests.
- **Full suite**: 122 suites / 935 tests passing (baseline was 108/844).
- **Layers used**: Unit (constants/schemas/permissions/query-keys/fixtures/download/errors/middleware), Component (hub/generator-form/page/sidebar/barrel), Structural (types).
- **Approval tests**: 0 — no refactoring of existing behavior (baseline suite stayed green throughout).
- **Pure functions created**: `roleLevel`, `isAdminPlus`, `isDirector`, `canGenerateReport`, `canApproveReport`, `getReportTypeLabel`, `getReportStatusLabel`, `buildPreviewUrl`, `buildPdfUrl`, `buildApproveUrl`, `buildPdfFilename`, `resolveSelectorKind`, `parseReportSelection`, `downloadBlob`.

### Work Unit Evidence (PR1)

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `jest __tests__/features/reports __tests__/lib/download.test.ts __tests__/lib/errors.test.ts __tests__/middleware.test.ts` → 16 suites, 119 tests passed (exit 0) |
| Runtime harness command/scenario and exact result | `jest --passWithNoTests --coverage` (full) → 122 suites / 935 passed (exit 0); `features/reports` 100 stmts / 95.71 branch / 98.38 funcs / 100 lines; global threshold ≥80% satisfied; `tsc --noEmit` clean; ESLint clean. `npm run dev` → `/reports` not executed in this env (components exercised via RTL with the mocked api layer, matching the repo pattern) |
| Rollback boundary | Revert the PR1 slice: `frontend/features/reports/*`, `frontend/app/reports/page.tsx`, the reports factory + `ReportType` import in `lib/query-keys.ts`, `lib/download.ts`, the `error`-key branch in `lib/errors.ts` (+ its tests), the Sidebar `Informes` item, the middleware `/reports` prefix, the three report status mappings in `components/shared/StatusBadge.tsx`, `fixtures/reports.ts` + `fixtures/index.ts` registration, the reports MSW handlers, and the reports tests. All other modules unaffected |

---

## Files Changed (PR1)

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/features/reports/types.ts` | Created | `ReportType`, `ReportStatus`, `ReportSelectorKind`, `ReportTarget`, `ReportPreview`, `ReportApprovalResponse`, `Page<T>` |
| `frontend/features/reports/constants.ts` | Created | `REPORT_TYPES` (4 codes → Spanish labels), `REPORT_TYPE_OPTIONS`, `REPORT_STATUS_LABELS`, label helpers, preview/pdf/approve endpoint builders, `buildPdfFilename` |
| `frontend/features/reports/schemas.ts` | Created | `reportSelectionSchema` ({type, entityId}), `ReportSelection`, `resolveSelectorKind` (advances → project), `parseReportSelection` |
| `frontend/features/reports/permissions.ts` | Created | `roleLevel`, `isAdminPlus`, `isDirector`, `canGenerateReport` (RB-001), `canApproveReport` (RB-001/RN-016) |
| `frontend/features/reports/queries.ts` | Created | `useActiveInstitutionId`, `useReportPreview` (GET .../preview/), `useReportEntityOptions` (projects/researchers/centers hooks, RB-004) |
| `frontend/features/reports/mutations.ts` | Created | `useApproveReport` (POST .../approve/; success invalidates entity roots + reports; 409/errors never invalidate — RB-002) |
| `frontend/features/reports/ReportGeneratorForm.tsx` | Created | Controlled type/entity selects; entity options from `useReportEntityOptions`; `key={type}` remount resets the entity select on type change |
| `frontend/features/reports/ReportHub.tsx` | Created | Type selector + derived entity lists with `StatusBadge` status projection ("No generado"), loading/empty states |
| `frontend/features/reports/index.ts` | Created | Module barrel |
| `frontend/app/reports/page.tsx` | Created | `AuthenticatedLayout` + role gate (`canGenerateReport`) → `ReportHub` or 403 alert; no API calls when denied |
| `frontend/lib/query-keys.ts` | Modified | Added `reports` factory: `all`, `preview`, `pdf`, `derived` (institution-scoped) |
| `frontend/lib/errors.ts` | Modified | `normalizeError` also reads the `{error: "..."}` key (reports backend); not treated as a field error |
| `frontend/lib/download.ts` | Created | `downloadBlob(path, filename, institutionId)` — authenticated fetch → blob → objectURL → anchor click → cleanup (RF-004) |
| `frontend/components/shell/Sidebar.tsx` | Modified | Added `{ href: "/reports", label: "Informes", icon: FileText }` to `NAV_ITEMS` (RF-006) |
| `frontend/middleware.ts` | Modified | Added `/reports` to `PROTECTED_PREFIXES` (RF-006) |
| `frontend/components/shared/StatusBadge.tsx` | Modified | Added `not_generated`/`generated`/`approved` Spanish status mappings |
| `frontend/fixtures/reports.ts` | Created | `RN_017_MESSAGE`, `fixtureReportPreviewHtml`, `fixtureReportPdfBytes`, approve success/403/409 payloads |
| `frontend/fixtures/index.ts` | Modified | Registered the reports fixtures |
| `frontend/mocks/handlers.ts` | Modified | Reports handlers: preview (200/403/404/500), pdf (bytes + filename), approve (200/403/404/409 RN-017 verbatim for project p1) |
| `frontend/__tests__/features/reports/*` (13 files) | Created | types, constants, schemas, permissions, query-keys, queries, mutations, hub, generator-form, reports-page, sidebar, fixtures, index barrel |
| `frontend/__tests__/lib/download.test.ts` | Created | Blob download, header scoping, ApiError verbatim, no-click-on-failure |
| `frontend/__tests__/lib/errors.test.ts` | Modified | `error`-key cases (RN-017 verbatim, not a field error, detail precedence) |
| `frontend/__tests__/middleware.test.ts` | Modified | `/reports` redirect without session + allow with session |
| `openspec/changes/frontend-reports/tasks.md` | Modified | Tasks 1.1–1.15 marked `[x]` |

## Deviations from Design

1. **`lib/download.ts` location**: the mission task list (slice 1) places the
   authenticated blob utility at `frontend/lib/download.ts`; the design
   architecture tree lists it under `features/reports/download.ts` (PR2 task
   2.1). Followed the orchestrator's task list — `lib/download.ts`. PR2
   should re-export or reference `lib/download.ts` rather than creating a
   duplicate.
2. **`lib/errors.ts` `error`-key support (additive)**: the reports backend
   returns `{"error": "..."}` (not `detail`) for 403/409/500 responses. To
   satisfy "409 RN-017 message shown verbatim" (RB-002, RF-005), extended
   `normalizeError` to read the `error` key. Backwards compatible; covered by
   new tests.
3. **`StatusBadge` shared mapping**: added the three report statuses to
   `components/shared/StatusBadge.tsx` STATUS_META (design lists StatusBadge
   among the reused components). `getReportStatusLabel` in the module
   constants remains the module-local contract.
4. **Hub action slots**: the hub renders entity lists with status indicators
   but no action buttons in PR1 — the design defers preview/download
   (PR2) and approval (PR3) wiring. The list structure is ready for those
   slices.

## Issues Found

- **Flaky timeout (pre-existing)**: `__tests__/features/advances/create-page.test.tsx`
  exceeded the 5s timeout once under full-suite parallel load; passes in
  isolation (4/4) and passed in the final full run. Pre-existing test, not
  touched.
- **Radix Select controlled reset**: passing `value={undefined}` after a
  selection flips the Select to uncontrolled and keeps the stale internal
  value; fixed by remounting the entity Select with `key={type}`.
- **msW handlers const placement**: declared `VALID_REPORT_TYPES` inside the
  handlers array literal (invalid TS); moved to module scope.
- **jsdom lacks the blob URL API**: `URL.createObjectURL/revokeObjectURL` are
  stubbed in `__tests__/lib/download.test.ts` (typed via `as unknown`).

## Remaining Tasks

- [ ] 2.1 `features/reports/download.ts` — re-export/wire `lib/download.ts` `downloadBlob` (PR2)
- [ ] 2.2 `PreviewDialog.tsx` — sandboxed `<iframe sandbox srcDoc>` + error states (PR2)
- [ ] 2.3 `DownloadButton.tsx` — pending/disabled during generation (PR2)
- [ ] 2.4 Wire preview query + download into `ReportHub` entity rows (PR2)
- [ ] 2.5 PR2 Jest/RTL tests (PR2)
- [ ] 3.1–3.5 Approval + polish (PR3)

## Workload / PR Boundary

- Mode: chained PR slice 1 of 3 (auto-chain, stacked-to-main); PR1 targets `main`
- Current work unit: PR1 — Foundation (tasks 1.1–1.15)
- Boundary: types/constants/schemas/permissions → query-keys/queries/mutations → hub + generator + page → sidebar + middleware → fixtures + MSW → download + errors → tests
- Estimated review budget impact: PR1 is projected at ~700–900 changed
  lines (exceeds the 400-line budget — flagged in the tasks artifact; repo
  precedent: frontend-researchers PR1 ran similar scope). PR2/PR3 remain
  at/near budget.

## Status

15/15 tasks complete. Ready for PR2 (preview + download) or sdd-verify.
