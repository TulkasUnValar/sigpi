# Archive Report: Frontend Reports Module (SIGPI §6.6)

## Change

`frontend-reports`

## Status

**COMPLETED** — All implementation tasks across 3 PRs merged to main, 104 tests passing, coverage ≥80%, tsc + ESLint clean.

## Archive Date

2026-09-16

## Artifact Store

hybrid (OpenSpec + Engram)

## Delivery

- **Strategy**: auto-chain
- **Chain strategy**: stacked-to-main
- **PRs**: #33 (foundation + preview/download components), #34 (wire preview/download + approval flow)

## Executive Summary

The frontend reports surface was delivered as the final missing MVP frontend module. Backend `apps.reports` (preview/PDF/approve) was already archived; this change provided the complete UI layer: a protected `/reports` hub with report-type selector, dependent entity selector, sandboxed HTML preview, authenticated blob PDF download, and director-gated approval flow with verbatim RN-017 409 handling.

## Final State

| Metric | Value |
|--------|-------|
| Tasks total | 15 (PR1) + 5 (PR2) + 5 (PR3) = 25 |
| Tasks complete | 25/25 |
| Tests | 104 passed, 104 total (17 suites) |
| Coverage | 100% stmts / 95.71% branch / 98.38% funcs / 100% lines (features/reports aggregate) |
| Build | tsc --noEmit: clean |
| Linter | ESLint: clean |

## Files Delivered

### Feature module
- `frontend/features/reports/types.ts` — ReportType, ReportStatus, ReportTarget unions
- `frontend/features/reports/constants.ts` — Spanish labels, endpoint builders, filename contract
- `frontend/features/reports/schemas.ts` — zod validation for generator selection
- `frontend/features/reports/permissions.ts` — canGenerateReport, canApproveReport guards
- `frontend/features/reports/queries.ts` — useReportPreview, useReportEntityOptions (derived hooks)
- `frontend/features/reports/mutations.ts` — useApproveReport with 409 verbatim handling
- `frontend/features/reports/download.ts` — authenticated blob download utility
- `frontend/features/reports/index.ts` — barrel exports

### Components
- `frontend/features/reports/ReportHub.tsx` — type selector + entity lists with status indicators
- `frontend/features/reports/ReportGeneratorForm.tsx` — controlled type/entity selects
- `frontend/features/reports/PreviewDialog.tsx` — sandboxed iframe via srcDoc
- `frontend/features/reports/DownloadButton.tsx` — blob download trigger with pending state
- `frontend/features/reports/ApprovalButton.tsx` — director-gated approval action

### Pages & navigation
- `frontend/app/reports/page.tsx` — AuthenticatedLayout + ReportHub, role-gated
- `frontend/components/shell/Sidebar.tsx` — "Informes" nav item added
- `frontend/middleware.ts` — `/reports` added to PROTECTED_PREFIXES

### Tests (17 suites, 104 tests)
- `__tests__/features/reports/types.test.ts`
- `__tests__/features/reports/constants.test.ts`
- `__tests__/features/reports/schemas.test.ts`
- `__tests__/features/reports/permissions.test.ts`
- `__tests__/features/reports/query-keys.test.ts`
- `__tests__/features/reports/queries.test.tsx`
- `__tests__/features/reports/mutations.test.tsx`
- `__tests__/features/reports/fixtures.test.ts`
- `__tests__/features/reports/index.test.ts`
- `__tests__/features/reports/hub.test.tsx`
- `__tests__/features/reports/generator-form.test.tsx`
- `__tests__/features/reports/reports-page.test.tsx`
- `__tests__/features/reports/sidebar.test.tsx`
- `__tests__/features/reports/preview-dialog.test.tsx`
- `__tests__/features/reports/download-button.test.tsx`
- `__tests__/features/reports/approval-button.test.tsx`
- `__tests__/features/reports/download.test.ts`

## Spec Compliance

| Requirement | Scenarios | Status |
|-------------|-----------|--------|
| RF-001 (Reports hub page) | Hub renders entity lists; Permission denied | ✅ COMPLIANT |
| RF-002 (Report generator form) | Dependent entity selector; Advances targets projects | ✅ COMPLIANT |
| RF-003 (HTML preview) | Preview renders; Preview error | ✅ COMPLIANT |
| RF-004 (PDF download) | Blob download; Generation pending | ✅ COMPLIANT |
| RF-005 (Approval flow) | Director approves; Non-director denied; RN-017 409 guard | ✅ COMPLIANT |
| RF-006 (Sidebar navigation) | Nav item visible; Unauthenticated redirect | ✅ COMPLIANT |

## Business Rules Verified

| Rule | Status | Evidence |
|------|--------|----------|
| RB-001 (role gating) | ✅ | permissions.ts + page boundary tests |
| RB-002 (RN-017 409 verbatim, no invalidation) | ✅ | mutations.ts + lib/errors.ts + tests |
| RB-003 (institution scoping, X-Institution-ID) | ✅ | queries.ts, mutations.ts, download.ts |
| RB-004 (no invented endpoints) | ✅ | useReportEntityOptions derives from existing hooks |

## Risks Accepted

- No runtime E2E against live backend; all verification via RTL + MSW (matches repo pattern).
- Reports backend is archived; integration contract trusts fixture/handler shape.
- `mutations.ts` branch coverage 75% for defensive null institutionId branch (not required by 80% floor).

## Delta Merged

Frontend UI requirements (RF-001..RF-006) and business rules (RB-001..RB-004) merged into `openspec/specs/reports/spec.md`.

## Rollback

Revert PRs #33 and #34 independently: delete `features/reports/**`, `app/reports/**`, remove nav item, middleware prefix, and queryKeys factory. Zero backend/data impact.

## Artifacts Archived

- `openspec/changes/frontend-reports/` → `openspec/changes/archive/2026-09-16-frontend-reports/`

---
*Archive generated by SDD orchestrator. All tasks complete, tests green, spec delta merged.*
