# Tasks: Reports / Informes Module (§6.6)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,150 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Renderer+Preview) → PR 3 (PDF+Approval) → PR 4 (Integration) |
| Delivery strategy | ask-always |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models, migrations, config, WeasyPrint setup, permissions, model tests | PR 1 → `feature/reports` | ~255 lines; base for all subsequent work |
| 2 | ReportRenderer, 4 templates, preview endpoint, renderer + preview tests | PR 2 → PR 1 branch | ~420 lines; templates are HTML-heavy but low review complexity |
| 3 | ReportGenerator, PDF endpoint, ReportApprovalService, approve endpoint, audit wiring, tests | PR 3 → PR 2 branch | ~360 lines; core business logic |
| 4 | E2E smoke test, coverage gaps, admin polish, full suite run | PR 4 → PR 3 branch | ~130 lines; verification + cleanup |

## Phase 1: Foundation (~255 lines)

- [x] 1.1 Create `backend/apps/reports/__init__.py` (empty package init)
- [x] 1.2 Create `backend/apps/reports/apps.py` — `ReportsConfig` with `name = "apps.reports"`
- [x] 1.3 Create `backend/apps/reports/models.py` — `ReportType`, `ReportStatus` choices; `Report` model (UUID PK, report_type, entity_id, institution FK, status, version, created_by FK, created_at); `ReportApproval` model (UUID PK, report FK, approved_by FK, approved_at, report_version); `clean()` + `full_clean()` in `save()`
- [x] 1.4 Run `makemigrations reports` to generate `0001_initial.py`
- [x] 1.5 Create `backend/apps/reports/permissions.py` — `CanGenerateReport` (HasRoleLevelOrHigher(4) + IsSameInstitution composite); `CanApproveReport` (IsCenterDirector composite)
- [ ] 1.6 Create `backend/apps/reports/admin.py` — register `Report` and `ReportApproval` with basic `ModelAdmin`
- [x] 1.7 Add `REPORT_GENERATED` and `REPORT_APPROVED` to `AuditEventType` in `backend/apps/accounts/audit.py`
- [x] 1.8 Add `"apps.reports"` to `LOCAL_APPS` in `backend/config/settings/base.py`
- [ ] 1.9 Add `weasyprint>=62.0` to dependencies in `backend/pyproject.toml`
- [ ] 1.10 Add WeasyPrint system libs to `backend/Dockerfile` (`libgtk-3-0 libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`)
- [x] 1.11 Create `backend/apps/reports/tests/__init__.py` and `tests/conftest.py` with `ReportFactory` and `ReportApprovalFactory`
- [x] 1.12 **RED**: Write `tests/test_models.py` — test UUID PK defaults, `ReportType`/`ReportStatus` choices, `clean()` validation, `ReportApproval.report_version` matches `Report.version`
- [x] 1.13 **GREEN**: Fix model issues to pass all `test_models.py` tests

## Phase 2: Renderer + Templates + Preview (~420 lines)

- [x] 2.1 Create `backend/apps/reports/services.py` — `ReportRenderer` class with `render_html(report_type, entity_id, user) -> str`; per-type context builders: `_project_context()`, `_researcher_context()`, `_center_context()`, `_advances_context()`; template selection by type
- [x] 2.2 Create `backend/apps/reports/templates/reports/base.html` — print-optimized CSS base template (page size, margins, fonts, table styles)
- [x] 2.3 Create `backend/apps/reports/templates/reports/project_report.html` — extends base.html; sections: general data, objectives, team, budget summary, results, progress (RF-050)
- [x] 2.4 Create `backend/apps/reports/templates/reports/researcher_report.html` — extends base.html; sections: profile, projects, production summary (RF-051)
- [x] 2.5 Create `backend/apps/reports/templates/reports/center_report.html` — extends base.html; sections: center data, project list, aggregate statistics (RF-052)
- [x] 2.6 Create `backend/apps/reports/templates/reports/advances_report.html` — extends base.html; sections: activities, completion %, documents, reviews (RF-053)
- [x] 2.7 Add `ReportPreviewView` to `backend/apps/reports/views.py` — GET returns `{"html": "..."}` using `ReportRenderer.render_html()`; applies `CanGenerateReport` permission
- [x] 2.8 Create `backend/apps/reports/urls.py` with preview route: `reports/{type}/{id}/preview/`
- [x] 2.9 Add `path("api/", include("apps.reports.urls"))` to `backend/config/urls.py`
- [x] 2.10 **RED**: Write `tests/test_services.py` — test `ReportRenderer.render_html()` returns valid HTML for each report type; mock model queries, assert context dict shape
- [x] 2.11 **RED**: Write `tests/test_views.py` (preview section) — test GET preview returns 200 with `{"html": "..."}`, test 403 for unauthorized user, test 403 for cross-institution access (RN-015)
- [x] 2.12 **GREEN**: Fix renderer and view issues to pass all tests

## Phase 3: PDF + Approval + Audit (~360 lines)

- [ ] 3.1 Add `ReportGenerator` class to `services.py` — `generate_pdf(html) -> bytes` using `weasyprint.HTML(string=html).write_pdf()`
- [ ] 3.2 Add `ReportPDFView` to `views.py` — GET streams `FileResponse` with `Content-Type: application/pdf`; calls `ReportRenderer` then `ReportGenerator`; emits `REPORT_GENERATED` audit event (RF-058)
- [ ] 3.3 Add `ReportApprovalService` to `services.py` — `approve(report, user) -> ReportApproval`; `has_pending_progress_reports(project) -> bool` queries `ProgressReport.objects.filter(project=project).exclude(status='aprobado')` (RN-017); creates `ReportApproval` with metadata (RN-018); emits `REPORT_APPROVED` audit event
- [ ] 3.4 Add `ReportApproveView` to `views.py` — POST returns 200 on success, 409 if pending progress reports (RN-017), 403 if not director (RN-016); applies `CanApproveReport` permission
- [ ] 3.5 Add pdf and approve routes to `urls.py`: `reports/{type}/{id}/pdf/` and `reports/{type}/{id}/approve/`
- [ ] 3.6 **RED**: Write `tests/test_services.py` (generator section) — mock `weasyprint.HTML`, assert `write_pdf()` called with correct HTML; test `ReportApprovalService.approve()` creates approval; test `has_pending_progress_reports()` returns True/False correctly
- [ ] 3.7 **RED**: Write `tests/test_views.py` (pdf + approve sections) — test PDF endpoint returns `FileResponse` with correct content-type; test approve returns 200/409/403; test audit events emitted after PDF and approve
- [ ] 3.8 **GREEN**: Fix service and view issues to pass all tests
- [ ] 3.9 **RED**: Write `tests/test_audit.py` — verify `REPORT_GENERATED` audit event created after PDF generation with correct user, report_type, entity_id, timestamp; verify `REPORT_APPROVED` audit event created after approval
- [ ] 3.10 **GREEN**: Fix audit wiring to pass `test_audit.py`

## Phase 4: Integration + Verification (~130 lines)

- [ ] 4.1 Write E2E smoke test in `tests/test_e2e.py` — full flow: generate preview → generate PDF → approve; uses real WeasyPrint (not mocked); asserts PDF is valid (non-empty bytes, starts with `%PDF`)
- [ ] 4.2 Polish `admin.py` — add list_display, list_filter, search_fields for `Report` and `ReportApproval`
- [ ] 4.3 Run `pytest --cov=apps.reports` and fix coverage gaps to reach ≥90%
- [ ] 4.4 Verify all spec scenarios pass: RF-050–RF-058, RN-015–RN-018 (cross-reference with spec.md)
- [ ] 4.5 Run full test suite (`pytest`) to confirm no regressions in other apps
