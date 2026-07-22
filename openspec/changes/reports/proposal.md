# Proposal: Reports / Informes Module (§6.6)

## Intent

No report generation capability exists in SIGPI. This change delivers on-demand PDF reports with preview, director approval, and audit for projects, researchers, centers, and advances.

## Scope

### In Scope
- **Project report** (RF-050): general data, objectives, team, budget summary, results, progress
- **Researcher report** (RF-051): profile, projects, production summary
- **Center report** (RF-052): center data, project list, aggregate stats
- **Advances report** (RF-053): activities, percentage, documents, reviews
- **Preview** (RF-056): JSON `{"html": "..."}` reusing PDF template
- **WeasyPrint** (RF-057): Django templates → HTML → PDF streaming
- **Audit** (RF-058): `REPORT_GENERATED` / `REPORT_APPROVED` events
- **Approval flow** (RN-016/017/018): center director approves; pending-advances guard; metadata persisted (date, approver, version)
- **Permissions** (RN-015): reuse `HasRoleLevelOrHigher`, `IsCenterDirectorForProject`
- Clean minimal default template

### Out of Scope
- Products (RF-054), Budget (RF-055), Calls reports — upstream modules missing
- MinIO/S3 caching, institutional branding, digital signatures (§6.7)

## Capabilities

### New Capabilities
- `reports`: PDF generation, preview, approval flow, audit for 4 report types

### Modified Capabilities
- `auth`: extend `AuditEventType` with `REPORT_GENERATED`, `REPORT_APPROVED`

## Approach

Standalone `apps.reports` Django app:

- **ReportRenderer**: builds context + renders Django template to HTML
- **ReportGenerator**: `weasyprint.HTML(string=html).write_pdf()` → `FileResponse` stream
- **Preview**: `GET /api/reports/{type}/{id}/preview/` → `{"html": "..."}`
- **PDF**: `GET /api/reports/{type}/{id}/pdf/` → on-demand streaming
- **Approval**: `POST /api/reports/{type}/{id}/approve/` — validates RN-017 via `has_pending_progress_reports`, persists `ReportApproval`
- **Templates**: `base.html` (print CSS) + per-type templates
- **Audit**: emit via `AuditEventEmitter`

## Affected Areas

| Area | Impact |
|------|--------|
| `backend/apps/reports/` | New — models, services, views, permissions, templates, tests |
| `backend/pyproject.toml` | Modified — add `weasyprint` |
| `backend/Dockerfile` | Modified — GTK/Pango/cairo libs |
| `backend/config/settings/base.py` | Modified — register app |
| `backend/config/urls.py` | Modified — include `reports.urls` |
| `backend/apps/accounts/audit.py` | Modified — add event types |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WeasyPrint system deps in Docker | Med | Dockerfile + CI smoke test |
| Progress source not on branch | Med | Verify importable before apply |
| Template iteration | Low | Minimal default; defer branding |

## Rollback Plan

Remove `apps.reports` from `INSTALLED_APPS`, delete app directory, revert config changes. `ReportApproval` dropped with app.

## Dependencies

- `apps.progress` (archived — must be on current branch)
- WeasyPrint system libs (GTK3, Pango, cairo)

## Success Criteria

- [ ] 4 report types generate valid PDF
- [ ] Preview JSON HTML matches PDF (WYSIWYG)
- [ ] Approval blocks on pending advances (RN-017)
- [ ] Approval metadata persisted: date, approver, version (RN-018)
- [ ] Audit events for generation and approval
- [ ] Permissions enforce RN-015
- [ ] ≥90% coverage on `apps.reports`
