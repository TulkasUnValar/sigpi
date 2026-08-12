# Proposal: SIGPI Advances/Progress Module (§6.5)

## Intent

Enable periodic progress reporting for research projects. Investigators register advances documenting activities, difficulties, and cumulative completion percentage. Center directors review, approve, observe, or reject advances. The system maintains full revision history and calculates official project progress.

This addresses RF-041 through RF-049: structured periodic reporting with director oversight and cumulative progress tracking.

## Scope

### In Scope
- **ProgressReport model**: 5-state FSM (borrador → enviado → observado → aprobado → rechazado), FK to Project, fields for period, description, cumulative percentage, activities, difficulties, next_steps
- **ProgressReview model**: Append-only director observations on advances (mirrors ProjectObservation pattern)
- **ProgressDocument model**: Metadata-only document records (mirrors ProjectDocument pattern, MinIO deferred)
- **ProgressStateLog model**: Domain audit log for FSM transitions (mirrors ProjectStateLog pattern)
- **Service layer**: ProgressService (CRUD + FSM orchestration), ProgressReviewService, ProgressDocumentService
- **ViewSets**: ProgressViewSet (CRUD + FSM actions), nested ProgressDocumentViewSet, read-only ProgressReviewViewSet and ProgressStateLogViewSet
- **Permissions**: Reuse IsCenterDirectorForProject from projects/permissions.py; add IsProgressCreatorOrProjectMember
- **Cumulative progress calculation**: Denormalized Project.cumulative_progress field updated on approval
- **Rejected state reversibility**: rechazado → borrador transition (NOT terminal)
- **Creator tracking**: created_by FK to User; any ProjectMember with permissions can create advances

### Out of Scope
- File upload infrastructure (MinIO/S3) — RF-043 deferred to post-MVP; metadata-only external_url pattern
- Meilisearch integration (RF-096) — deferred
- Final reports module (§6.6) — separate bounded context
- PDF generation (RF-053) — belongs to reports module
- Configurable reporting periods — MVP uses flexible period_start/period_end dates

## Capabilities

> This section is the CONTRACT between proposal and specs phases.
> The sdd-spec agent reads this to know exactly which spec files to create or update.

### New Capabilities
- `progress-reporting`: Periodic progress reporting with 5-state FSM lifecycle, director review workflow, cumulative progress tracking, and full audit trail

### Modified Capabilities
- `projects`: Add denormalized `cumulative_progress` field to Project model; add helper method `has_pending_progress_reports()` for future reports module integration (RN-017)

## Approach

**Standalone `apps.progress` bounded context** (Approach A from exploration).

Rationale:
- SPEC §6.5 explicitly defines advances as a separate module
- Projects module is mature and archived; extending it risks destabilizing a verified module
- ProgressReport has a simpler but distinct 5-state FSM; isolation prevents state-transition confusion with Project's 12-state FSM
- Existing RLS migration already documents `progress_progressreport` as a planned tenant-scoped table

**Technical patterns** (mirroring projects module):
- UUID PKs, `clean()` validation, `full_clean()` in `save()`, explicit `db_table`
- `django_fsm.FSMField` with `@transition` decorators, `protected=False` for admin repair
- Service layer: Plain Python classes with `@staticmethod` for CRUD + FSM orchestration
- ViewSets: Action-specific permissions via `get_permissions()`, action-specific serializers via `get_serializer_class()`
- Institution-scoped queryset via `request.active_membership.institution`
- Append-only audit logs (ProgressReview, ProgressStateLog) with ReadOnlyModelViewSet
- Domain-specific audit + global AuditEvent via AuditEventEmitter

**Percentage semantics** (resolved):
- Each ProgressReport declares the **cumulative total percentage** the project has reached at that point (not incremental contribution)
- System takes the latest approved cumulative percentage as the project's official progress
- `ProgressService.approve()` updates denormalized `Project.cumulative_progress` field
- Recalculate from scratch on each approval to avoid double-counting if advances are revised

**FSM transitions** (7 total):
1. `submit()`: borrador → enviado
2. `accept_review()`: enviado → en_revision (implicit state for director workflow)
3. `approve()`: en_revision → aprobado + update Project.cumulative_progress
4. `observe()`: en_revision → observado + create ProgressReview
5. `return_to_draft()`: en_revision | observado | rechazado → borrador
6. `reject()`: en_revision → rechazado
7. `resubmit()`: observado → enviado

**Rejected state reversibility** (resolved):
- `rechazado` is NOT terminal; can transition to `borrador` via `return_to_draft()`
- Allows investigators to correct and resubmit rejected advances

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/progress/` | New | Entire new Django app: models, services, views, serializers, permissions, urls, admin, filters, tests, migrations |
| `backend/apps/projects/models.py` | Modified | Add `cumulative_progress` DecimalField(max_digits=5, decimal_places=2, default=0) to Project model |
| `backend/apps/projects/services.py` | Modified | Add `ProjectService.has_pending_progress_reports(project)` helper for future reports module |
| `backend/config/settings/base.py` | Modified | Add `"apps.progress"` to `LOCAL_APPS` |
| `backend/config/urls.py` | Modified | Add `path("api/", include("apps.progress.urls"))` |
| `backend/apps/accounts/audit.py` | Modified | Add `PROGRESS_STATE_CHANGE` event type to AuditEventEmitter |
| `backend/apps/accounts/migrations/0004_rls_policies.py` | Modified | Add `progress_progressreport`, `progress_progressreview`, `progress_progressdocument`, `progress_progressstatelog` to `TENANT_SCOPED_TABLES` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cross-app permission coupling: Importing `IsCenterDirectorForProject` from projects creates soft dependency | Med | Extract generic `IsCenterDirectorForObject(center_attr="center")` into accounts/permissions.py, or accept the coupling as projects is stable |
| Cumulative percentage double-counting: If an advance is revised and resubmitted, naive aggregation overcounts | High | Store `percentage` on ProgressReport; on approval, recalculate Project.cumulative_progress from latest approved advance per project (not sum) |
| RLS policy drift: Forgetting to add new progress tables to tenant-scoped RLS policies | Med | Include RLS migration inside progress/migrations/ mirroring projects/migrations/0002_rls_policies.py |
| Duplicate observation pattern drift: ProgressReview copy-paste from ProjectObservation may diverge | Low | Follow exact proven pattern: ReadOnlyModelViewSet, all-fields-read-only serializer, create only via service-layer FSM side effects |
| Pending advances block final report (RN-017): Future reports module needs to query for non-approved advances | Low | Expose `Project.has_pending_progress_reports()` service-layer helper now; reports module consumes it later |
| Document upload deferred: Users expect file upload for RF-043 but MinIO not wired | High | Clear UX messaging: "Document metadata only — file upload coming soon"; external_url field accepts placeholder or future S3 URL |

## Rollback Plan

1. **Database**: Drop `progress_*` tables via reverse migration (`python manage.py migrate progress zero`)
2. **Code**: Remove `backend/apps/progress/` directory
3. **Settings**: Remove `"apps.progress"` from `LOCAL_APPS` in `backend/config/settings/base.py`
4. **URLs**: Remove `path("api/", include("apps.progress.urls"))` from `backend/config/urls.py`
5. **Projects model**: Reverse migration to remove `Project.cumulative_progress` field
6. **Audit**: Remove `PROGRESS_STATE_CHANGE` event type from `backend/apps/accounts/audit.py`
7. **RLS**: Remove progress tables from `TENANT_SCOPED_TABLES` in accounts migration

All changes are isolated to the new `progress` app + minimal integration points in projects/accounts. No data loss risk for existing modules.

## Dependencies

- `django-fsm>=3.0` ✅ (already installed)
- `django-filter` ✅ (already installed)
- No MinIO/S3 dependency (metadata-only pattern)
- No Meilisearch dependency (deferred)

## Success Criteria

- [ ] Investigators can create, edit, and submit progress reports for their projects (RF-041, RF-042, RF-044)
- [ ] Progress reports include period, description, cumulative percentage, activities, difficulties, next_steps (RF-042)
- [ ] Center directors can approve, observe, or reject advances (RF-045, RF-046, RF-047)
- [ ] Rejected advances can be corrected and resubmitted (rechazado → borrador transition)
- [ ] Full revision history is preserved and queryable (RF-048)
- [ ] System calculates and displays cumulative project progress from latest approved advance (RF-049)
- [ ] Any ProjectMember with permissions can create advances; created_by tracks the author
- [ ] Append-only audit logs (ProgressReview, ProgressStateLog) with no update/delete endpoints
- [ ] Institution-scoped queryset filtering via RLS policies
- [ ] All FSM transitions logged to ProgressStateLog + global AuditEvent
- [ ] Metadata-only document records (ProgressDocument) with external_url field (RF-043 partial)
- [ ] Test coverage ≥90% with pytest + factory_boy following projects module patterns
- [ ] Zero breaking changes to existing projects, researchers, institutions, or accounts modules
