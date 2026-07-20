# Exploration: Projects Module (SIGPI §6.4)

## Exploration: SIGPI Projects Module

### Current State

SIGPI is a Django 5.1 + DRF multi-institutional research management system. Three modules are fully implemented and archived: **accounts** (auth, roles, audit), **institutions** (6-entity hierarchy with FSM), and **researchers** (profiles, affiliations, external profiles, attachments). The next MVP module is **projects** (SIGPI §6.4), which manages the complete lifecycle of research projects.

Key architectural patterns already established:

- **Models**: UUID PKs, `clean()` validation, `full_clean()` in `save()`, explicit `db_table` in `Meta`, denormalized `institution_id` for RLS.
- **FSM**: `django_fsm.FSMField` with `@transition` decorators (used in `InstitutionScopedModel` and `Institution`). `protected=False` allows manual state repair by admins.
- **Service layer**: Plain Python classes with `@staticmethod` for CRUD orchestration and business rules (e.g., `ResearcherProfileService`, `ResearcherAffiliationService`).
- **ViewSets**: Action-specific permissions via `get_permissions()`, action-specific serializers via `get_serializer_class()`, queryset scoped by `request.active_membership.institution`.
- **Nested routes**: Manual `path()` nesting under parent resource (avoids `drf-nested-routers` dependency), e.g., `/researchers/{id}/affiliations/`.
- **Permissions**: `HasRoleLevelOrHigher` utility (levels 1–7), `IsSameInstitution` for tenant scoping, `IsCenterDirector` for center-bound approvals. **Crucially**, `IsProjectOwnerOrCoInvestigator` already exists in `accounts/permissions.py` and expects `obj.lead_researcher` and `obj.members.filter(user=user, role="co_investigator")`.
- **Serializers**: Separate `List`, `Detail`, and `Create` serializers; nested data is read-only (mutations go through dedicated endpoints).
- **Audit**: Generic `AuditEvent` model in `accounts/audit.py` with `event_type`, `institution_id`, `details` JSON, and `AuditEventEmitter`.
- **Tests**: Strict TDD with `pytest`, `factory_boy`, `conftest.py` fixtures.

Dependencies confirmed in `pyproject.toml`:
- `django-fsm>=3.0` ✅ (for RF-035)
- No `meilisearch` dependency yet ❌ (for RF-040)
- No file upload / MinIO dependency ❌ (for RF-036)

### Affected Areas

- `backend/apps/projects/` — **NEW APP**: models, services, views, serializers, permissions, urls, admin, tests
- `backend/apps/projects/models.py` — `Project`, `ProjectMember`, `ProjectDocument`, `ProjectObservation` (for RN-014), `ProjectStateLog` (for RN-012)
- `backend/apps/projects/services.py` — `ProjectService` (create with PI validation, state transitions), `ProjectMemberService`, `ProjectDocumentService`
- `backend/apps/projects/views.py` — `ProjectViewSet` (CRUD + custom actions: `submit`, `approve`, `observe`, `return`, `reject`, `suspend`, `finalize`, `close`, `cancel`), nested `ProjectMemberViewSet`, `ProjectDocumentViewSet`
- `backend/apps/projects/permissions.py` — `IsProjectOwnerOrCoInvestigator` (move from `accounts`?), `IsCenterDirectorForProject`, `CanCreateProjectInCenter`, `IsProjectEditable` (enforces RN-011)
- `backend/apps/projects/urls.py` — `/projects/`, `/projects/{id}/members/`, `/projects/{id}/documents/`, `/projects/{id}/observations/`, `/projects/{id}/state_history/`
- `backend/apps/projects/serializers.py` — `ProjectListSerializer`, `ProjectSerializer` (nested members/docs), `ProjectCreateSerializer`, `ProjectMemberSerializer`, `ProjectDocumentSerializer`, `ProjectObservationSerializer`
- `backend/apps/projects/admin.py` — `ProjectAdmin`, `ProjectMemberAdmin`, `ProjectDocumentAdmin`
- `backend/config/settings/base.py` — Add `"apps.projects"` to `LOCAL_APPS`
- `backend/config/urls.py` — Add `path("api/", include("apps.projects.urls"))`
- `backend/apps/accounts/permissions.py` — May need to update `IsProjectOwnerOrCoInvestigator` to match actual Project model field names (currently references `lead_researcher` and `members`)
- `backend/apps/accounts/audit.py` — May need new `AuditEventType` entries for project state changes (or project app defines its own state log)
- `backend/pyproject.toml` — Potentially add `meilisearch-python-sdk` or `django-meilisearch` for RF-040

### Approaches

#### 1. Monolithic Project Model with Inline JSON Fields (Approach A)

Put co-investigators, students, and collaborators as JSON fields on `Project`. Store observation history as a JSON array. Documents as a simple `ArrayField` of URLs.

- **Pros**: Simplest schema, few models, fast to implement.
- **Cons**: Loses referential integrity (no FK constraints on team members), cannot query "all projects for researcher X", no audit trail per observation, violates RN-014 and RN-012, hard to index in Meilisearch.
- **Effort**: Low
- **Verdict**: ❌ Rejected — breaks multiple business rules.

#### 2. Normalized Relational Model with Junction Tables (Approach B) — **RECOMMENDED**

Follow the `ResearcherAffiliation` pattern:

- `Project` table: title, abstract, objectives, methodology, expected_results, keywords, dates, state FSM, institution (denormalized), center FK, group FK (optional), line FK (optional), `principal_investigator` FK to `Researcher`.
- `ProjectMember` junction: `project` FK, `researcher` FK, `role` (choices: co_investigator, student, seedbed, collaborator), `joined_at`.
- `ProjectDocument` table: `project` FK, `name`, `type` (choices: proposal, annex, contract, report, other), `external_url` (MVP — metadata-only, no file upload).
- `ProjectObservation` table: `project` FK, `observed_by` FK (User), `observation_text`, `created_at`. Immutable append-only for RN-014.
- `ProjectStateLog` table: `project` FK, `from_state`, `to_state`, `triggered_by` FK (User), `created_at`, `reason`. Append-only for RN-012.

- **Pros**: Full referential integrity, queryable relationships, supports all SPEC requirements natively, aligns with existing codebase patterns, easy to add/remove roles later.
- **Cons**: More models to maintain, slightly more complex serializers.
- **Effort**: Medium

#### 3. Generic Polymorphic Membership (Approach C)

A single `ProjectMembership` table with `content_type`/`object_id` generic FK so a member can be a `Researcher`, `User`, or external person without a profile.

- **Pros**: Flexible for future member types (external evaluators, etc.).
- **Cons**: Overkill for MVP, loses type safety, generic relations are hard to optimize and serialize in DRF, no existing use of `django.contrib.contenttypes` in SIGPI.
- **Effort**: Medium-High
- **Verdict**: ❌ Rejected — adds complexity without MVP value.

### Recommendation

**Adopt Approach B (Normalized Relational Model with Junction Tables).**

Rationale:
- It mirrors the proven `ResearcherAffiliation` pattern already in production.
- It satisfies every SPEC requirement from §6.4 without workarounds.
- It keeps the project entity clean while delegating team, documents, observations, and audit to dedicated sub-entities — exactly how researchers handles affiliations/profiles/attachments.
- It enables efficient filtering (RF-039) and Meilisearch indexing (RF-040) because every field is a real column or FK.

### Detailed Design Notes

#### Project Model Structure

```python
class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey("institutions.Institution", ...)
    center = models.ForeignKey("institutions.ResearchCenter", ...)  # RN-008
    group = models.ForeignKey("institutions.ResearchGroup", null=True, blank=True, ...)
    line = models.ForeignKey("institutions.ResearchLine", null=True, blank=True, ...)
    principal_investigator = models.ForeignKey("researchers.Researcher", ...)  # RN-007
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    objectives = models.TextField()
    methodology = models.TextField()
    expected_results = models.TextField()
    keywords = models.CharField(max_length=500)  # comma-separated or JSON array
    start_date = models.DateField()
    estimated_end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    status = FSMField(default="borrador", protected=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**State machine (12 states, ~15 transitions):**

| Source | Target | Triggered By | Guard |
|---|---|---|---|
| borrador | enviado | researcher (submit) | PI set, center set, dates valid |
| enviado | en_revision | center director (accept) | — |
| en_revision | observado | center director (observe) | creates ProjectObservation |
| en_revision | aprobado | center director (approve) | — |
| en_revision | rechazado | center director (reject) | terminal |
| observado | enviado | researcher (resubmit) | — |
| aprobado | en_ejecucion | system / admin (start) | — |
| en_ejecucion | suspendido | center director / admin (suspend) | — |
| suspendido | en_ejecucion | center director / admin (resume) | — |
| en_ejecucion | finalizado | researcher / PI (finish) | actual_end_date set |
| finalizado | en_cierre | center director (initiate closure) | — |
| en_cierre | cerrado | center director (close) | terminal |
| *any* | cancelado | admin (cancel) | not already terminal |

**Validation in `clean()`:**
- RN-007: `principal_investigator` is non-null.
- RN-008: `center` is non-null.
- RN-013: `estimated_end_date` and `actual_end_date` must be ≥ `start_date`.
- RN-011: If `status` is `cerrado` or `rechazado` or `cancelado`, reject updates at the service layer (not in `clean()`, because FSM may need to set fields during terminal transition).

**Team Membership (`ProjectMember`):**

```python
class ProjectRole(models.TextChoices):
    CO_INVESTIGATOR = "co_investigator", "Co-Investigator"
    STUDENT = "student", "Student"
    SEEDBED = "seedbed", "Seedbed"
    COLLABORATOR = "collaborator", "Collaborator"

class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    researcher = models.ForeignKey("researchers.Researcher", on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=ProjectRole.choices)
    joined_at = models.DateTimeField(auto_now_add=True)
```

- Unique together: `(project, researcher)` — a researcher can only have one role per project.
- Permissions: `IsProjectOwnerOrCoInvestigator` checks `obj.principal_investigator.user == request.user` OR `obj.members.filter(researcher__user=request.user, role=ProjectRole.CO_INVESTIGATOR).exists()`.

**Documents (`ProjectDocument`):**

Follow the `ResearcherAttachment` pattern (metadata-only, no file upload in MVP):

```python
class ProjectDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20, choices=ProjectDocumentType.choices)
    external_url = models.URLField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

Document type choices: `proposal`, `annex`, `contract`, `report`, `other`.

**Observation History (`ProjectObservation`) — RN-014:**

```python
class ProjectObservation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="observations")
    observed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    observation_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

- Append-only: no update/delete endpoints. Created automatically when director triggers `observe()` transition.

**State Change Audit (`ProjectStateLog`) — RN-012:**

Two options:
1. **Reuse `AuditEvent`** from `accounts/audit.py` with a new `PROJECT_STATE_CHANGE` event type. Pros: single audit table, leverages existing emitter. Cons: generic `details` JSON is less queryable.
2. **Dedicated `ProjectStateLog` model**. Pros: queryable by project, from_state, to_state; natural FK to Project. Cons: another model.

**Recommendation**: Use a dedicated `ProjectStateLog` model for project-specific state transitions, but ALSO emit a generic `AuditEvent` for cross-module audit consistency. This is how `accounts` handles auth events — keep domain logs close to the domain, but mirror to the global audit stream.

```python
class ProjectStateLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="state_logs")
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    triggered_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Permission Classes Needed

1. **`IsProjectOwnerOrCoInvestigator`** — already exists in `accounts/permissions.py`. Update to reference correct field names (`principal_investigator` instead of `lead_researcher`). Keep in `accounts` or move to `projects/permissions.py`?
   - **Recommendation**: Move to `projects/permissions.py` to avoid cross-app circular imports. Re-export from `accounts` for backward compatibility if needed.

2. **`IsCenterDirectorForProject`** — extends `IsCenterDirector` but checks `obj.center_id` against the user's `membership.centers`. Reuse existing logic: `IsCenterDirector.has_object_permission(request, view, obj)` already does this.

3. **`CanCreateProjectInCenter`** — create permission. Checks:
   - User has `Researcher` role (level ≤ 4).
   - User has an affiliation with the project's target center (RN-009). Check via `ResearcherAffiliation.objects.filter(researcher__user=request.user, center=center).exists()`.

4. **`IsProjectEditable`** — object-level. Returns `False` if `obj.status` is in `["cerrado", "rechazado", "cancelado"]` and the user is not admin+ (level ≤ 2). Enforces RN-011.

#### Service Layer Design

```python
class ProjectService:
    @staticmethod
    def create(institution, center, principal_investigator, **data):
        # Validate RN-007, RN-008, RN-009
        # Validate dates (RN-013)
        # Set initial status = "borrador"

    @staticmethod
    def submit(project, user):
        # Guard: status == "borrador"
        # Guard: user is PI or admin
        # Transition: borrador → enviado
        # Log state change

    @staticmethod
    def approve(project, user):
        # Guard: status == "en_revision"
        # Guard: IsCenterDirectorForProject
        # Transition: en_revision → aprobado
        # Log state change

    # ... similar for observe, reject, suspend, resume, finalize, close, cancel
```

#### URL Routing

Follow the researchers pattern (manual nested paths):

```
/projects/                              GET, POST
/projects/{id}/                         GET, PATCH, DELETE
/projects/{id}/submit/                  POST
/projects/{id}/approve/                 POST
/projects/{id}/observe/                 POST
/projects/{id}/reject/                  POST
/projects/{id}/return/                  POST
/projects/{id}/suspend/                 POST
/projects/{id}/resume/                 POST
/projects/{id}/finalize/                POST
/projects/{id}/close/                   POST
/projects/{id}/cancel/                  POST
/projects/{id}/members/                 GET, POST
/projects/{id}/members/{member_id}/    PATCH, DELETE
/projects/{id}/documents/               GET, POST
/projects/{id}/documents/{doc_id}/    PATCH, DELETE
/projects/{id}/observations/           GET, POST
/projects/{id}/state_history/          GET
```

#### Meilisearch Integration (RF-040)

Meilisearch is **not** in `pyproject.toml`. Decision needed:
- **Option A**: Add `meilisearch-python-sdk` now and implement indexing via Django signals (`post_save`, `post_delete`) or a Celery task.
- **Option B**: Defer Meilisearch to a post-MVP change; implement basic DRF filtering (`django-filter` or queryset `.filter()`) for RF-039 now.

**Recommendation**: Implement basic filtering in the MVP (DRF `SearchFilter`, `OrderingFilter`, custom `django-filter` filters for status, center, dates). Add Meilisearch as a **separate change** after projects core is archived. This keeps the projects module bounded and testable.

#### Document Uploads (RF-036)

Researchers module uses `external_url` (metadata-only) and defers actual file storage. For projects:
- **MVP**: Same pattern — `ProjectDocument` stores `name`, `doc_type`, `external_url`.
- **Post-MVP**: Implement MinIO/S3 upload with presigned URLs. This avoids adding file upload infrastructure to the current change scope.

### Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `IsProjectOwnerOrCoInvestigator` in `accounts` references non-existent Project fields | High | Move permission to `projects/permissions.py` and update field names before any views use it |
| FSM transition logic becomes complex with 12 states and multiple guards | Medium | Centralize transitions in `ProjectService`; write unit tests for every transition; use a state-transition matrix table in `design.md` |
| Observation history append-only requirement (RN-014) bypassed via admin or raw SQL | Medium | Enforce at service layer; do not expose update/delete endpoints; add DB trigger or check constraint if needed |
| Date validation (RN-013) only in `clean()` may be skipped by bulk operations | Medium | Also validate in `ProjectService.create/update`; add DB `CHECK` constraint for start/end dates |
| Closed-project immutability (RN-011) bypassed via nested endpoint (e.g., updating a member of a closed project) | Medium | Apply `IsProjectEditable` to ALL project-related viewsets, including `ProjectMemberViewSet` and `ProjectDocumentViewSet`, checking the parent project's status |
| Principal investigator must be affiliated with the project's center (RN-009) — querying this may be N+1 | Medium | Use `select_related("principal_investigator__affiliations")` in queryset; validate in service layer, not per-request |
| Missing `meilisearch` dependency blocks RF-040 if not deferred | Low | Explicitly defer Meilisearch; document in proposal/spec that advanced search is out of scope for this change |
| Circular import risk between `projects` and `accounts` if permissions stay in `accounts` | Medium | Move project-specific permissions to `projects/permissions.py`; keep only generic roles (`IsSuperAdmin`, `HasRoleLevelOrHigher`) in `accounts` |

### Integration with Other Modules

- **accounts**: `Project` references `User` (state change triggered_by) and `Researcher` (PI). `ProjectMember` references `Researcher`. Permissions rely on `InstitutionMembership.role` and `InstitutionMembership.centers`.
- **institutions**: `Project` has FKs to `Institution`, `ResearchCenter`, `ResearchGroup`, `ResearchLine`. `clean()` must validate that group/line belong to the same center/institution chain. Denormalized `institution_id` for RLS.
- **researchers**: `Project.principal_investigator` → `Researcher`. `ProjectMember.researcher` → `Researcher`. RN-009 validation checks `ResearcherAffiliation` for center membership.
- **audit**: `ProjectStateLog` is the domain-specific log; mirror entries to `AuditEvent` via `AuditEventEmitter` for global audit consistency.

### Open Questions

1. **Meilisearch scope**: Should RF-040 (Meilisearch indexing) be included in this change or deferred to a dedicated search integration change?
2. **Document upload scope**: Should RF-036 include actual file upload (MinIO/S3 presigned URLs) or stick to metadata-only `external_url` like researchers?
3. **Generic member types**: Are students and seedbeds always `Researcher` profiles, or can they be unregistered users (name/email only)? The SPEC says "associate students, seedbeds, collaborators" — if they are not researchers, `ProjectMember` may need a nullable `researcher` FK plus `name`/`email` fallback fields.
4. **Group/line scoping**: Is `group` required if `line` is set? The institution hierarchy says line→group→center. If line is set, group and center are inferable. Should the model require explicit FKs to all three, or infer them?
5. **State transition permissions**: Who can trigger `cancel`? The SPEC says center director can approve/observe/return/reject (RF-038). It does not specify who can cancel. Should cancel be admin-only (level ≤ 2) or center-director?
6. **Observation vs. Return**: Is "return" (devolver) the same as "observe" (observar) or a different transition? The SPEC lists both RF-038 and state list includes "Observado" and "En revisión". Need to clarify if "return" means transition back to `borrador` or create an observation without state change.
7. **AuditEventType extension**: Should the `accounts` app add `PROJECT_STATE_CHANGE` to `AuditEventType`, or should the `projects` app define its own enum and keep domain events separate?

### Next Steps

1. **Decision needed**: Confirm whether students/seedbeds/collaborators are always existing `Researcher` profiles or can be external names.
2. **Decision needed**: Confirm whether RF-040 (Meilisearch) and RF-036 (file upload) are in scope or deferred.
3. **Decision needed**: Clarify "return" vs "observe" transition semantics (RF-038).
4. Proceed to **sdd-propose** for the projects module to define change scope, rollback plan, and bound in-scope vs deferred requirements.
5. After proposal approval, proceed to **sdd-spec** to write detailed requirements and Gherkin scenarios for:
   - Project creation (RF-027, RN-007, RN-008, RN-009)
   - State transitions (RF-035, RF-037, RF-038, RN-010, RN-011, RN-012)
   - Team member management (RF-032, RF-033)
   - Observation history (RN-014)
   - Document management (RF-036)
   - Filtering and search (RF-039, RF-040)

---

**Status**: success
**Summary**: Projects module exploration complete. Recommended normalized relational model with `Project`, `ProjectMember`, `ProjectDocument`, `ProjectObservation`, and `ProjectStateLog`, following the researchers module patterns. FSM managed via `django-fsm` + service layer. Defer Meilisearch and actual file upload to post-MVP changes. Move `IsProjectOwnerOrCoInvestigator` to `projects/permissions.py`.
**Artifacts**: `openspec/changes/projects/explore.md`
**Next**: sdd-propose
**Risks**: Permission class field mismatch, FSM complexity, closed-project immutability bypass via nested endpoints, N+1 on affiliation checks.
**Skill Resolution**: paths-injected — sdd-explore, sdd-phase-common
