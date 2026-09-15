# Tasks: Frontend Reports Module (SIGPI §6.6)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,300–1,600 (across 3 PRs) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 foundation → PR2 preview/download → PR3 approval/polish |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
```

**Flag**: PR1 is projected at ~700–900 changed lines (plumbing + hub UI + MSW + tests) and exceeds the 400-line budget. Repo precedent (frontend-researchers PR1) ran similar scope. At apply, either sub-slice PR1 into PR1a (plumbing + MSW) / PR1b (hub UI + tests), or accept `size:exception` for PR1. PR2 (~350–450) and PR3 (~350–450) are at/near budget.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Foundation: types/constants/schemas/permissions/keys/queries/mutations; ReportHub + generator; sidebar + middleware; MSW fixtures/handlers | PR1 | `cd frontend; jest features/reports app/reports --coverage` | `npm run dev` → `/reports`, select type/entity | Revert `features/reports/*`, `app/reports/*`, `query-keys.ts` reports factory, Sidebar item, middleware prefix |
| 2 | Preview + download: PreviewDialog sandbox iframe; download.ts blob; DownloadButton pending | PR2 | `cd frontend; jest features/reports --coverage` | `/reports` → "Vista previa", "Descargar PDF" | Revert `PreviewDialog.tsx`, `download.ts`, `DownloadButton.tsx` |
| 3 | Approval + polish: ApprovalButton director-gated; derived queue/status projection; filter polish; full verify | PR3 | `cd frontend; jest features/reports --coverage` | `/reports` approve as director; RN-017 409 | Revert `ApprovalButton.tsx`, queue/status derivation, filters |

## Phase 1: Foundation (PR1)

- [x] 1.1 Create `features/reports/types.ts` — `ReportType` (project/researcher/center/advances), `ReportStatus` (not_generated/generated/approved), `ReportTarget`, preview `{html}` shape.
- [x] 1.2 Create `features/reports/constants.ts` — Spanish labels (Informes, Vista previa, Descargar PDF, Aprobar, No generado/Generado/Aprobado) + endpoint builders for preview/pdf/approve.
- [x] 1.3 Create `features/reports/schemas.ts` — zod validation of generator selection `{type, entityId}` (advances maps to project).
- [x] 1.4 Create `features/reports/permissions.ts` — `canGenerateReport` (role ≤ 4; admin level ≤ 2 bypass), `canApproveReport` (director role ≤ 3 + center membership; superuser bypass) per RB-001.
- [x] 1.5 Add `reports` factory to `lib/query-keys.ts` — institution-scoped `all`, `preview(institutionId, type, id)`, derived entity-list keys.
- [x] 1.6 Create `features/reports/queries.ts` — `useReportPreview` calling `GET /api/reports/{type}/{id}/preview/` with `institutionId`; derive lists from `useProjectsList`/`useResearchersList`/`useCenters` (RB-003/RB-004).
- [x] 1.7 Create `features/reports/mutations.ts` — `useApproveReport` POST `/approve/`; success invalidates entity roots + derived view; 409 surfaces RN-017 verbatim, NO invalidation (RB-002).
- [x] 1.8 Create `features/reports/index.ts` barrel.
- [x] 1.9 Create `features/reports/ReportGeneratorForm.tsx` — controlled type/entity selects, reset entity on type change, advances targets projects.
- [x] 1.10 Create `features/reports/ReportHub.tsx` — type selector + per-type entity lists with status projection (No generado/Generado/Aprobado) and action slots.
- [x] 1.11 Create `app/reports/page.tsx` — `AuthenticatedLayout` + `ReportHub`; no API calls without CanGenerateReport.
- [x] 1.12 Add `{ href: "/reports", label: "Informes" }` to `components/shell/Sidebar.tsx` `NAV_ITEMS`.
- [x] 1.13 Add `/reports` to `middleware.ts` `PROTECTED_PREFIXES`.
- [x] 1.14 Create `fixtures/reports.ts`, register in `fixtures/index.ts`, extend `mocks/handlers.ts` — preview success/403/404/500, pdf, approve success/403/409 (RN-017 verbatim).
- [x] 1.15 Jest/RTL tests — key factories, permissions, advances→projects, hub render, denial (no API call), sidebar/middleware. Coverage ≥80%, ESLint + `tsc --noEmit` green.

## Phase 2: Preview + Download (PR2)

- [ ] 2.1 Create `features/reports/download.ts` — `downloadBlob(path, filename, institutionId)` authenticated fetch → blob → objectURL → anchor click → cleanup (credentials + X-Institution-ID).
- [ ] 2.2 Create `features/reports/PreviewDialog.tsx` — sandboxed `<iframe sandbox srcDoc={html}>` without `allow-same-origin`; error state on 403/404/500, no HTML render (RF-003).
- [ ] 2.3 Create `features/reports/DownloadButton.tsx` — triggers `downloadBlob`; pending/disabled during WeasyPrint generation (<5s NFR); filename `{type}_report.pdf` (RF-004).
- [ ] 2.4 Wire preview query + download into `ReportHub` entity rows.
- [ ] 2.5 Jest/RTL tests — iframe sandbox attributes, srcDoc render, preview error states, blob download + URL cleanup, pending disabling.

## Phase 3: Approval + Polish (PR3)

- [ ] 3.1 Create `features/reports/ApprovalButton.tsx` — rendered only when `canApproveReport`; success → toast + status `Aprobado` + invalidation; 409 shows RN-017 verbatim, no invalidation (RF-005).
- [ ] 3.2 Derive approval queue — hub section listing entities with status `generated` awaiting approval, from existing hooks only (RB-004).
- [ ] 3.3 Filter polish — status filter on entity lists, empty states, loading skeletons, a11y pass.
- [ ] 3.4 Jest/RTL tests — non-director hidden/no call, approve success + invalidation, 409 no-invalidation, queue derivation.
- [ ] 3.5 Full verification — coverage ≥80% branch, ESLint, `tsc --noEmit` across slices; confirm RF-001..RF-006 acceptance.

## PR Boundaries and Rollback Plan

| PR | Scope | Merge target | Rollback |
|----|-------|--------------|----------|
| PR1 | Foundation (1.1–1.15) | main | Revert PR1; hub/sidebar/middleware disappear, other modules unaffected |
| PR2 | Preview + download (2.1–2.5) | main | Revert PR2; hub lists remain, preview/download actions fall back |
| PR3 | Approval + polish (3.1–3.5) | main | Revert PR3; approve action and queue disappear, status stays derived |

Each PR is an autonomous slice with independent verification and rollback; no migration or feature flag.
