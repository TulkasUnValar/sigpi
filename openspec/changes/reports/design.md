# Design: Reports / Informes Module (§6.6)

## Technical Approach

Standalone `apps.reports` Django app following the established SIGPI patterns (UUID PKs, `clean()` + `full_clean()` in `save()`, `AuditEventEmitter` for audit, `HasRoleLevelOrHigher` for role checks). Two models (`Report`, `ReportApproval`), three service classes (`ReportRenderer`, `ReportGenerator`, `ReportApprovalService`), three API endpoints (preview, PDF, approve), and four Django templates.

The advances report (RF-053) depends on `apps.progress` which is **not on this branch** — only `__pycache__` artifacts remain. Source lives at commit `fa00816` on `feature/advances-phase-4`. This must be resolved before apply (cherry-pick or merge).

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Report model shape | Generic `Report` with `report_type` + `entity_id` (UUID) | Per-type models (ProjectReport, ResearcherReport…) | 4 types share identical lifecycle (generate → approve). Generic avoids 4 near-identical models. Entity resolved dynamically by type. |
| Approval storage | Separate `ReportApproval` model | Fields on `Report` | Separation enables re-approval history, cleaner audit, and RN-018 metadata without polluting the Report model. |
| PDF engine | WeasyPrint (HTML → PDF) | ReportLab, xhtml2pdf | Proposal mandates WeasyPrint (RF-057). Django templates → HTML → PDF gives WYSIWYG preview for free. |
| Preview strategy | Reuse `ReportRenderer.render_html()` | Separate preview template | Single source of truth — preview HTML IS the PDF input. Guarantees WYSIWYG (RF-056). |
| RN-017 guard | Query `ProgressReport.objects.filter(project=project).exclude(status='aprobado')` | Boolean flag on Project | Dynamic check is always current. A flag would need synchronization logic and could go stale. |
| Template location | `apps/reports/templates/reports/` | Project-level `templates/` dir | Follows `APP_DIRS: True` convention already in `settings/base.py`. Self-contained app. |
| Progress dependency | Cherry-pick progress source from `fa00816` | Stub progress models | Stub would be fragile and diverge. Cherry-pick preserves the real implementation. |

## Data Flow

```
User Request
     │
     ▼
┌─────────────┐    permission     ┌──────────────────┐
│  DRF View   │────── check ─────→│ HasRoleLevel /   │
│ (preview/   │                   │ IsCenterDirector  │
│  pdf/approve)│                   │ / IsSameInst.    │
└──────┬──────┘                   └──────────────────┘
       │
       ▼
┌──────────────────┐    context    ┌──────────────────┐
│ ReportRenderer   │─── build ────→│ ContextBuilder   │
│ .render_html()   │               │ (per-type logic) │
└──────┬───────────┘               └──────────────────┘
       │ html string
       ▼
┌──────────────────┐    PDF bytes  ┌──────────────────┐
│ ReportGenerator  │─── stream ───→│ FileResponse     │
│ (WeasyPrint)     │               │ application/pdf  │
└──────┬───────────┘               └──────────────────┘
       │
       ▼
┌──────────────────┐
│ AuditEventEmitter│
│ REPORT_GENERATED │
└──────────────────┘
```

**Approval flow:**

```
POST /api/reports/{type}/{id}/approve/
     │
     ▼
IsCenterDirectorForProject (RN-016)
     │
     ▼
ReportApprovalService.approve()
     │
     ├── RN-017: has_pending_progress_reports? ──YES──→ 409 Conflict
     │
     └── NO → create ReportApproval (RN-018)
              → emit REPORT_APPROVED audit
              → 200 OK
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/reports/__init__.py` | Create | Package init |
| `backend/apps/reports/apps.py` | Create | AppConfig: `apps.reports` |
| `backend/apps/reports/models.py` | Create | `Report`, `ReportApproval` models |
| `backend/apps/reports/services.py` | Create | `ReportRenderer`, `ReportGenerator`, `ReportApprovalService` |
| `backend/apps/reports/views.py` | Create | `ReportPreviewView`, `ReportPDFView`, `ReportApproveView` |
| `backend/apps/reports/urls.py` | Create | URL routing for 3 endpoints |
| `backend/apps/reports/permissions.py` | Create | `CanGenerateReport`, `CanApproveReport` |
| `backend/apps/reports/admin.py` | Create | Admin registration |
| `backend/apps/reports/templates/reports/base.html` | Create | Print CSS base template |
| `backend/apps/reports/templates/reports/project_report.html` | Create | Project report template |
| `backend/apps/reports/templates/reports/researcher_report.html` | Create | Researcher report template |
| `backend/apps/reports/templates/reports/center_report.html` | Create | Center report template |
| `backend/apps/reports/templates/reports/advances_report.html` | Create | Advances report template |
| `backend/apps/reports/tests/` | Create | Test suite (≥90% coverage) |
| `backend/apps/accounts/audit.py` | Modify | Add `REPORT_GENERATED`, `REPORT_APPROVED` to `AuditEventType` |
| `backend/config/settings/base.py` | Modify | Add `apps.reports` and `apps.progress` to `LOCAL_APPS` |
| `backend/config/urls.py` | Modify | Include `apps.reports.urls` |
| `backend/pyproject.toml` | Modify | Add `weasyprint>=62.0` dependency |
| `backend/Dockerfile` | Modify | Add GTK3/Pango/cairo system libs for WeasyPrint |

## Interfaces / Contracts

### Report Model

```python
class ReportType(models.TextChoices):
    PROJECT = "project", "Project Report"
    RESEARCHER = "researcher", "Researcher Report"
    CENTER = "center", "Center Report"
    ADVANCES = "advances", "Advances Report"

class ReportStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    APPROVED = "approved", "Approved"

class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    entity_id = models.UUIDField()  # Project, Researcher, Center, or Project (advances)
    institution = models.ForeignKey("institutions.Institution", ...)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default="generated")
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey("accounts.User", related_name="generated_reports", ...)
    created_at = models.DateTimeField(auto_now_add=True)
```

### ReportApproval Model

```python
class ReportApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    report = models.ForeignKey(Report, related_name="approvals", ...)
    approved_by = models.ForeignKey("accounts.User", ...)
    approved_at = models.DateTimeField(auto_now_add=True)
    report_version = models.PositiveIntegerField()
```

### Service Interfaces

```python
class ReportRenderer:
    def render_html(self, report_type: str, entity_id: UUID, user: User) -> str:
        """Build context dict per type, render Django template to HTML string."""

class ReportGenerator:
    def generate_pdf(self, html: str) -> bytes:
        """WeasyPrint HTML → PDF bytes."""

class ReportApprovalService:
    def approve(self, report: Report, user: User) -> ReportApproval:
        """Validate RN-017, create ReportApproval, emit audit. Raises on conflict."""

    @staticmethod
    def has_pending_progress_reports(project: Project) -> bool:
        """True if any ProgressReport for project is not in 'aprobado' status."""
```

### API Endpoints

| Method | Path | Response | Permissions |
|--------|------|----------|-------------|
| GET | `/api/reports/{type}/{id}/preview/` | `{"html": "..."}` | `HasRoleLevelOrHigher(4)` + `IsSameInstitution` |
| GET | `/api/reports/{type}/{id}/pdf/` | `FileResponse` (PDF stream) | `HasRoleLevelOrHigher(4)` + `IsSameInstitution` |
| POST | `/api/reports/{type}/{id}/approve/` | `200` / `409` | `IsCenterDirectorForProject` |

### Audit Events (added to `AuditEventType`)

```python
REPORT_GENERATED = "REPORT_GENERATED", "Report Generated"
REPORT_APPROVED = "REPORT_APPROVED", "Report Approved"
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `ReportRenderer` context building per type | Mock model queries, assert context dict shape |
| Unit | `ReportGenerator` WeasyPrint call | Mock `weasyprint.HTML`, assert `write_pdf()` called |
| Unit | `ReportApprovalService` RN-017 guard | Factory: project with pending vs approved progress reports |
| Unit | `Report` / `ReportApproval` model validation | `clean()` constraints, UUID PK, defaults |
| Integration | Preview endpoint → HTML response | `APIClient.get()`, assert `{"html": "..."}` |
| Integration | PDF endpoint → FileResponse stream | `APIClient.get()`, assert `Content-Type: application/pdf` |
| Integration | Approve endpoint → 200 / 409 / 403 | Factory: director vs non-director, pending vs clean |
| Integration | Audit events emitted | Assert `AuditEvent` created after PDF and approve |
| E2E | Full flow: generate → preview → PDF → approve | Sequential test with real WeasyPrint (smoke) |

## Migration / Rollout

1. **Pre-apply**: Cherry-pick or merge `apps.progress` source from `feature/advances-phase-4` (commit `fa00816`) into `feature/reports`. Verify `from apps.progress.models import ProgressReport` works.
2. **Migration**: Single `0001_initial` migration creating `reports_report` and `reports_reportapproval` tables.
3. **Dockerfile**: Add `libgtk-3-0 libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info` to `apt-get install`.
4. **Rollback**: Remove `apps.reports` from `INSTALLED_APPS`, drop tables, revert config changes. `ReportApproval` dropped with app.

## Open Questions

- [ ] **Progress source merge strategy**: Cherry-pick `fa00816` or full merge of `feature/advances-phase-4`? Cherry-pick is surgical but may miss migrations. Full merge is safer but brings more changes.
- [ ] **Report versioning**: Should `Report.version` auto-increment on re-generation, or only on re-approval? Current design: version increments on each `Report` creation for the same entity.
