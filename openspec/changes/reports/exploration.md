## Exploration: SIGPI Reports/Informes Module (§6.6)

### Current State

- **Backend apps installed**: `accounts`, `institutions`, `researchers`, `projects`. `progress` exists only as an app shell with migrations/tests and no runtime models/services yet. `products`, `budgets`, and `calls` apps do not exist.
- **Audit system**: `apps.accounts.audit.AuditEvent` + `AuditEventEmitter` already used by `projects`. Event-type choices are auth-only, but `projects` emits arbitrary strings (e.g. `PROJECT_STATE_CHANGE`) without model validation, so reports can follow the same pattern.
- **PDF/storage stack**: `WeasyPrint` and `MinIO` are named in the architecture but **not present** in the current codebase:
  - `pyproject.toml` has no `weasyprint`, `boto3`, `minio`, or `django-storages` dependencies.
  - `docker-compose.yml` has no MinIO service.
  - No S3/storage settings or document upload infrastructure exists; document models use metadata-only `external_url`.
- **Permissions**: role-level hierarchy (`HasRoleLevelOrHigher`) and center-scoped checks (`IsCenterDirectorForProject`) already exist and can be reused.
- **Templates**: Django `TEMPLATES` uses `APP_DIRS = True` with no extra `DIRS`; report templates can live inside a new app.

### Affected Areas

- `backend/pyproject.toml` — add `weasyprint` dependency; optionally `boto3`/`minio` if storage is added now.
- `backend/Dockerfile` — WeasyPrint requires GTK/Pango/cairo system libraries.
- `backend/docker-compose.yml` — add MinIO service only if PDF caching is in scope.
- `backend/config/settings/base.py` — register `apps.reports` in `INSTALLED_APPS`; configure static files for print CSS.
- `backend/config/urls.py` — include `apps.reports.urls` under `/api/`.
- `backend/apps/accounts/audit.py` — add `REPORT_GENERATED` / `REPORT_APPROVED` event types (or accept arbitrary strings).
- `backend/apps/projects/` — data source for project reports.
- `backend/apps/researchers/` — data source for researcher reports.
- `backend/apps/institutions/` — data source for center reports.
- **New** `backend/apps/reports/` — models, services, templates, views, permissions, tests.

### Approaches

1. **Standalone `apps.reports` module** — all report logic, templates, and endpoints in one new app.
   - **Pros**: matches the `openspec/context.md` app list; centralizes WeasyPrint wiring, templates, audit, and permissions; easy to add new report types; keeps existing apps clean.
   - **Cons**: some report types depend on modules not yet built, so the first slice must be scoped; slightly more files than embedding per app.
   - **Effort**: Medium.

2. **Service layer within existing apps** — each app owns its own reports (e.g., project reports in `apps.projects`).
   - **Pros**: report logic lives next to its data; works for simple entity reports.
   - **Cons**: duplicates PDF/audit/storage wiring; cross-entity/center reports have no natural owner; permission and audit patterns become scattered and harder to keep consistent.
   - **Effort**: Medium-High.

### Recommendation

Use a **standalone `apps.reports` module**. It aligns with the existing modular architecture, centralizes the PDF/audit/permission machinery, and can be delivered incrementally. The first implementation slice should cover only the reports that are buildable today; complex reports should be added as their upstream modules land.

### Report Types Complexity

| Report | Complexity | Blockers |
|--------|------------|----------|
| Project (RF-050) | Simple | None — data is in `apps.projects`. |
| Researcher (RF-051) | Simple | None — data is in `apps.researchers`. |
| Center (RF-052) | Simple | None — data is in `apps.institutions`. |
| Advances (RF-053) | Complex | `apps.progress` has no runtime models. |
| Products (RF-054) | Complex | `apps.products` does not exist. |
| Budget (RF-055) | Complex | `apps.budgets` does not exist. |
| Calls (not listed in §6.6 but implied by objective) | Complex | `apps.calls` does not exist. |

### WeasyPrint Integration

- Use **Django templates** (not Jinja2 or raw HTML strings) so templates are auto-discovered via `APP_DIRS`, support `{% trans %}`, static CSS, and are testable by rendering to string.
- Layout:
  - `apps/reports/templates/reports/base.html` — print-oriented base template with `@media print` CSS.
  - `apps/reports/templates/reports/project_report.html`, `researcher_report.html`, `center_report.html`.
- Service design: a `ReportRenderer` class that builds the context dict and renders a template to HTML; a `ReportGenerator` that calls `weasyprint.HTML(string=html).write_pdf()`.
- Both the **preview** endpoint and the **PDF** endpoint should use the same renderer/context to avoid drift.

### Storage Strategy

- **Generate on-demand and stream directly to the client** (`FileResponse`/`HttpResponse` with `Content-Type: application/pdf`). Do not require MinIO for this change.
- Optionally persist a `GeneratedReport` metadata row (entity, report type, version, generated_by, generated_at, file_hash) for audit/versioning without storing the binary.
- **Defer MinIO caching** until the `documents` module adds S3 infrastructure. When that lands, swap the file backend behind a small storage adapter.

### Permission Model

- Reuse existing helpers: `HasRoleLevelOrHigher`, `IsCenterDirectorForProject`, `IsSameInstitution`.
- Proposal:
  - **Generate project report**: PI/co-investigator of the project, center director of the project's center, or institution admin+ (level ≤ 2).
  - **Generate researcher report**: the researcher themselves, or admin+.
  - **Generate center report**: center director for that center, or admin+.
  - **Approve final report**: center director for the project's center (RN-016); must also reject if the project has pending advances (RN-017) — currently unenforceable because `progress` is missing.

### Preview Mechanism (RF-056)

- Add `GET /api/reports/{type}/{id}/preview/` returning either:
  - `200 OK` with `text/html` rendered preview, or
  - JSON `{"html": "..."}` if the frontend prefers to inject it into an iframe.
- The preview must reuse the same template and context as PDF generation, guaranteeing WYSIWYG.

### Audit Integration (RF-058)

- Emit through `AuditEventEmitter`:
  - `REPORT_GENERATED` when a PDF is produced.
  - `REPORT_APPROVED` when a final report is approved.
- Details payload: `report_type`, `entity_id`, `format`, `version`, `center_id`, `institution_id`.
- Add the new event types to `AuditEventType` choices for consistency.

### Estimated Scope

- **New files**: ~12–15 backend files (`models.py`, `services.py`, `views.py`, `permissions.py`, `urls.py`, `serializers.py`, templates, tests, `apps.py`).
- **Changed files**: `pyproject.toml`, `Dockerfile`, `config/settings/base.py`, `config/urls.py`, possibly `apps/accounts/audit.py`.
- **Estimated lines**: 800–1,200 production lines + 600–900 test lines.
- **Review budget**: exceeds the 400-line limit; split into chained PRs:
  1. Bootstrap `apps.reports` + project/researcher/center reports + preview + audit.
  2. Director approval flow + final-report guard (blocked until `progress` exists).
  3. Advances/products/budgets/calls reports as upstream modules land.

### Risks

- **Missing upstream modules**: `progress`, `products`, `budgets`, `calls` are not implemented, so half of the §6.6 report types cannot be built now.
- **No MinIO/S3 infra**: adding PDF storage expands the change into infrastructure work that is out of scope for this module.
- **WeasyPrint system dependencies**: must update the Dockerfile/base image to include GTK/Pango/cairo; otherwise PDF generation fails at runtime.
- **AuditEventType mismatch**: choices currently only cover auth events; either extend choices or rely on no-validation creation.
- **Final-report approval rule (RN-017)**: pending-advances check cannot be enforced without `ProgressReport` data.
- **Report CSS/templates**: institutional PDF formats are undefined; templates may require multiple design iterations.
- **Permission edge cases**: researcher report ownership and center aggregation need careful object-level checks not fully covered by existing permission classes.

### Ready for Proposal

**Yes**, with an explicit scope reduction. The proposal should implement only the three simple, single-entity reports (project, researcher, center), the preview endpoint, audit emission, and the permission scaffolding. It should defer MinIO storage, final-report approval, and the complex aggregated reports until the dependent modules and infrastructure exist.
