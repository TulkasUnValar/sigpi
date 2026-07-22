## Exploration: SIGPI Advances/Progress Module (§6.5)

### Current State

SIGPI is a Django 5.1 + DRF multi-institutional research management system. Four MVP modules are fully implemented and archived: **accounts** (auth, roles, audit), **institutions** (6-entity hierarchy with FSM), **researchers** (profiles, affiliations, attachments), and **projects** (12-state FSM lifecycle, team, documents, observations, state logs).

The **projects** module (`backend/apps/projects/`) provides the canonical integration pattern for the advances module:

- **Models**: UUID PKs, `clean()` validation, `full_clean()` in `save()`, explicit `db_table`, denormalized `institution_id` for RLS.
- **FSM**: `django_fsm.FSMField` with `@transition` decorators, `protected=False` for admin repair.
- **Service layer**: Plain Python classes with `@staticmethod` for CRUD + FSM orchestration + business rules (e.g., `ProjectService`, `ProjectMemberService`).
- **ViewSets**: Action-specific permissions via `get_permissions()`, action-specific serializers via `get_serializer_class()`, institution-scoped queryset via `request.active_membership.institution`.
- **Nested routes**: Manual `path()` nesting under parent resource (e.g., `/projects/{id}/members/`, `/projects/{id}/documents/`).
- **Permissions**: `HasRoleLevelOrHigher` (levels 1–7), `IsCenterDirectorForProject` (center-bound object checks), `IsProjectOwnerOrCoInvestigator` (PI/member checks).
- **Audit**: Domain-specific append-only logs (`ProjectStateLog`, `ProjectObservation`) + global `AuditEvent` via `AuditEventEmitter`.
- **Tests**: Strict TDD with `pytest`, `factory_boy`, module-level `conftest.py` with state-scoped fixtures.
- **Documents**: Metadata-only pattern (`external_url`) — no file upload in MVP; MinIO/S3 deferred.

**Dependencies confirmed**:
- `django-fsm>=3.0` ✅
- No MinIO file-upload dependency ❌ (RF-043 deferred to post-MVP)
- No `meilisearch` dependency ❌ (RF-096 deferred)

### Affected Areas

- `backend/apps/projects/models.py` — `ProgressReport` FK to `Project`; `Project.cumulative_progress` denormalized field for RF-049.
- `backend/apps/projects/permissions.py` — `IsCenterDirectorForProject` reusable for progress review actions (CA-003).
- `backend/apps/accounts/audit.py` — `AuditEventEmitter` supports new `PROGRESS_STATE_CHANGE` event type.
- `backend/config/settings/base.py` — Add `"apps.progress"` to `LOCAL_APPS`.
- `backend/config/urls.py` — Add `path("api/", include("apps.progress.urls"))`.
- `backend/apps/accounts/migrations/0004_rls_policies.py` — Add `progress_progressreport` and `progress_progressreview` to `TENANT_SCOPED_TABLES`.
- **NEW APP** `backend/apps/progress/` — `models.py`, `services.py`, `views.py`, `serializers.py`, `permissions.py`, `urls.py`, `admin.py`, `filters.py`, `tests/`, `migrations/`.

### Approaches

#### 1. Standalone `progress` app with its own FSM (Approach A) — RECOMMENDED

Create `backend/apps/progress/` as a new bounded context:

- `ProgressReport`: 5-state FSM (`borrador` → `enviado` → `observado` → `aprobado` → `rechazado`), FK to `Project`, fields for period, description, percentage, activities, difficulties, next_steps.
- `ProgressReview`: append-only review log mirroring `ProjectObservation` (director observations on an advance).
- `ProgressDocument`: metadata-only document records mirroring `ProjectDocument` (RF-043).
- `ProgressStateLog`: domain audit log mirroring `ProjectStateLog` (RF-048).
- Service layer: `ProgressService` (CRUD + FSM orchestration), `ProgressReviewService`, `ProgressDocumentService`.
- ViewSets: `ProgressViewSet` (CRUD + FSM actions), nested `ProgressDocumentViewSet`, read-only `ProgressReviewViewSet` and `ProgressStateLogViewSet`.
- URLs: Top-level `/progress/` with filter by `project`; optionally nested `/projects/{id}/progress/` read-only shortcut.

- **Pros**: Clean separation per SPEC §6.5, follows existing app-per-module convention, avoids bloating `projects`, own migration stream, `context.md` and RLS stubs already anticipate `progress` tables.
- **Cons**: Cross-app FKs and permission imports require careful dependency management; queryset scoping logic duplicated.
- **Effort**: Medium

#### 2. Sub-module inside `projects` app (Approach B)

Add `ProgressReport`, `ProgressReview`, and `ProgressDocument` directly into `backend/apps/projects/models.py`, extending `ProjectService` and `ProjectViewSet` with progress actions.

- **Pros**: No new app registration, no cross-app imports, single migration stream, reuses `Project` queryset scoping and `IsProjectOwnerOrCoInvestigator` without imports.
- **Cons**: Violates single-responsibility; `projects` already has 5 models, 4 ViewSets, 15+ FSM actions, 553-line views; harder to archive independently; conflates project lifecycle with periodic reporting.
- **Effort**: Low-Medium
- **Verdict**: ❌ Rejected — projects module is already at bounded-context capacity.

#### 3. Generic `reports` app merging §6.5 + §6.6 (Approach C)

Merge progress (avances) and final reports (informes) into a single `reports` app with polymorphic `Report` base model.

- **Pros**: Unified approval/document/audit pattern.
- **Cons**: Premature abstraction; avances and informes have distinct actors, FSMs, and business rules (e.g., RN-017 blocks final reports based on pending avances). The SPEC treats them as separate modules.
- **Effort**: Medium-High
- **Verdict**: ❌ Rejected — conflates distinct domains before either is implemented.

### Recommendation

**Adopt Approach A (Standalone `progress` app).**

Rationale:
- The SPEC explicitly lists §6.5 as a separate module. The codebase `context.md` names `progress` as app #6 in MVP priority.
- The existing RLS migration (`accounts/migrations/0004_rls_policies.py`) already documents `"progress_progressreport"` as a planned tenant-scoped table.
- The projects app is mature and archived; extending it risks destabilizing a verified module.
- `ProgressReport` has a simpler but distinct 5-state FSM. Isolating it prevents state-transition confusion with Project's 12-state FSM.

### Risks

- **Cross-app permission reuse**: `IsCenterDirectorForProject` lives in `projects/permissions.py`; importing it into `progress/permissions.py` creates a soft coupling. Mitigation: Extract a generic `IsCenterDirectorForObject(center_attr="center")` into `accounts/permissions.py` (the base `IsCenterDirector` already does center checks).
- **Project cumulative percentage (RF-049)**: Aggregating approved `ProgressReport.percentage` per project is prone to double-counting if an advance is revised and resubmitted. Mitigation: Store `approved_percentage` on `ProgressReport` and update a denormalized `Project.cumulative_progress` field via `ProgressService.approve()`, recalculating from scratch each time.
- **Pending advances block final report (RN-017)**: The future reports module (§6.6) will query `ProgressReport` for pending (non-approved) items. Mitigation: Expose `Project.has_pending_progress_reports()` as a service-layer helper.
- **Document upload (RF-043)**: No MinIO/S3 infrastructure yet. MVP must use metadata-only `external_url` (`ProgressDocument` mirroring `ProjectDocument`). Full file upload deferred.
- **RLS policy drift**: New `progress` tables must be added to tenant-scoped RLS policies. Risk of forgetting. Mitigation: Include an RLS migration inside `progress/migrations/` (mirroring `projects/migrations/0002_rls_policies.py`) or update the centralized accounts migration.
- **Duplicate observation pattern**: `ProgressReview` must be append-only (no update/delete). Risk of copy-paste drift from `ProjectObservation`. Mitigation: Follow the exact proven pattern: `ReadOnlyModelViewSet`, all-fields-read-only serializer, create only via service-layer FSM side effects.

### Open Questions

1. **App naming**: The SPEC says "avances" but `context.md` and RLS stubs say `progress`. Should the Django app be `apps.progress` or `apps.advances`? Existing modules use English app names (`projects`, `researchers`). **Recommendation**: `apps.progress`.
2. **Nested vs top-level routing**: Should progress reports be `/projects/{id}/progress/` (nested) or `/progress/` (top-level with `project` filter)? The projects module uses manual nested routes. Progress is logically a child of project but queried independently (e.g., director dashboard). **Recommendation**: Hybrid — top-level `/progress/?project={id}` with a nested read-only shortcut `/projects/{id}/progress/`.
3. **Official reporting period (SPEC §19 item 5)**: Is the period fixed (quarterly, semiannual) or configurable per project/center? This affects whether `ProgressReport` needs a `period_type` field or just `period_start` / `period_end` dates.
4. **Percentage semantics**: Is `percentage` the advance's incremental contribution (e.g., 25% this quarter) or cumulative up to that point? RF-049 says "porcentaje de avance acumulado del proyecto", implying incremental advances are summed. Need confirmation.
5. **Co-investigator can register advances?**: SPEC §5 says "Coinvestigador — Registra avances o productos si tiene permiso". Should `ProgressReport` allow any `ProjectMember` to create, or only PI? This affects the permission matrix.
6. **Rechazado reversibility**: Is `Rechazado` terminal (no outbound transitions) or can it return to `Borrador`? The SPEC state list does not show a return path.
7. **Observation vs Review naming**: SPEC entity list (line 745) uses `ProgressReview` for "Revisión del avance". Should the append-only feedback model be `ProgressObservation` (mirroring projects) or `ProgressReview`? **Recommendation**: `ProgressReview` to align with domain terminology, same pattern.

### Ready for Proposal

**Yes** — with the caveat that Open Questions #1 (app naming) and #4 (percentage semantics) should be resolved before `sdd-propose` proceeds to `sdd-spec`.
