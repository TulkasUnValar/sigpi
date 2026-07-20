"""
Projects — Research Project Lifecycle module (SIGPI §6.4).

Implements the data model defined in design.md and spec.md:
- Project: 12-state FSM, rich metadata, institution-scoped
- ProjectMember: team junction (co_investigator, student, seedbed, collaborator)
- ProjectDocument: metadata-only document records
- ProjectObservation: append-only observation log (RN-014)
- ProjectStateLog: domain audit log for FSM transitions (RN-012)

Design reference: openspec/changes/projects/design.md
Spec reference:   openspec/changes/projects/spec.md

GREEN PHASE: Full model implementation — tests must pass.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField, transition

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class ProjectStatus(models.TextChoices):
    """FSM states for the Project lifecycle (12 states)."""

    BORRADOR = "borrador", "Borrador"
    ENVIADO = "enviado", "Enviado"
    EN_REVISION = "en_revision", "En Revisión"
    OBSERVADO = "observado", "Observado"
    APROBADO = "aprobado", "Aprobado"
    EN_EJECUCION = "en_ejecucion", "En Ejecución"
    SUSPENDIDO = "suspendido", "Suspendido"
    FINALIZADO = "finalizado", "Finalizado"
    EN_CIERRE = "en_cierre", "En Cierre"
    CERRADO = "cerrado", "Cerrado"
    RECHAZADO = "rechazado", "Rechazado"
    CANCELADO = "cancelado", "Cancelado"


class ProjectRole(models.TextChoices):
    """Member role choices for ProjectMember."""

    CO_INVESTIGATOR = "co_investigator", "Co-Investigator"
    STUDENT = "student", "Student"
    SEEDBED = "seedbed", "Seedbed"
    COLLABORATOR = "collaborator", "Collaborator"


class ProjectDocumentType(models.TextChoices):
    """Document type choices for ProjectDocument."""

    PROPOSAL = "proposal", "Proposal"
    ANNEX = "annex", "Annex"
    CONTRACT = "contract", "Contract"
    REPORT = "report", "Report"
    OTHER = "other", "Other"


# Terminal states — no outbound transitions allowed.
TERMINAL_STATES = {
    ProjectStatus.CERRADO,
    ProjectStatus.RECHAZADO,
    ProjectStatus.CANCELADO,
}

# ──────────────────────────────────────────────
# Project
# ──────────────────────────────────────────────


class Project(models.Model):
    """Research project with 12-state FSM lifecycle.

    Standalone model (does NOT inherit InstitutionScopedModel) because
    that base carries code/name/description + 3-state FSM that do not
    apply to a project.  Carries denormalized institution_id for RLS.

    Field-level constraints:
      - RN-007: principal_investigator non-null (enforced in clean()).
      - RN-008: center non-null (enforced in clean()).
      - RN-013: dates validated in clean() + DB CHECK constraints.

    FSM transitions (15 total) defined as @transition methods below.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    center = models.ForeignKey(
        "institutions.ResearchCenter",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    group = models.ForeignKey(
        "institutions.ResearchGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    line = models.ForeignKey(
        "institutions.ResearchLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    principal_investigator = models.ForeignKey(
        "researchers.Researcher",
        on_delete=models.CASCADE,
        related_name="led_projects",
    )
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    objectives = models.TextField()
    methodology = models.TextField()
    expected_results = models.TextField()
    keywords = models.CharField(max_length=500, blank=True)
    start_date = models.DateField()
    estimated_end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    status = FSMField(default=ProjectStatus.BORRADOR, protected=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects_project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estimated_end_date__gte=models.F("start_date")),
                name="check_estimated_end_date_gte_start_date",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(actual_end_date__isnull=True)
                    | models.Q(actual_end_date__gte=models.F("start_date"))
                ),
                name="check_actual_end_date_gte_start_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="idx_project_inst_status",
            ),
            models.Index(
                fields=["center", "status"],
                name="idx_project_center_status",
            ),
            models.Index(
                fields=["principal_investigator"],
                name="idx_project_pi",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        errors = {}

        # RN-007: principal_investigator non-null.
        if not self.principal_investigator_id:
            errors.setdefault("principal_investigator", []).append(
                "Principal investigator is required."
            )

        # RN-008: center non-null.
        if not self.center_id:
            errors.setdefault("center", []).append(
                "Center is required."
            )

        # RN-013: date validation.
        if self.start_date and self.estimated_end_date:
            if self.estimated_end_date < self.start_date:
                errors.setdefault("estimated_end_date", []).append(
                    "Estimated end date must be on or after start date."
                )
        if self.start_date and self.actual_end_date:
            if self.actual_end_date < self.start_date:
                errors.setdefault("actual_end_date", []).append(
                    "Actual end date must be on or after start date."
                )

        # Hierarchy integrity: group must belong to the same center chain.
        if self.group_id and self.center_id:
            if self.group.center_id != self.center_id:
                errors.setdefault("group", []).append(
                    "Group must belong to the same center chain."
                )

        # Hierarchy integrity: line must belong to the same center chain.
        if self.line_id and self.center_id:
            if self.line.group.center_id != self.center_id:
                errors.setdefault("line", []).append(
                    "Line must belong to the same center chain."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ── FSM Transitions (15 total) ──────────────────────

    @transition(field=status, source=ProjectStatus.BORRADOR, target=ProjectStatus.ENVIADO)
    def submit(self):
        """borrador → enviado."""

    @transition(
        field=status, source=ProjectStatus.ENVIADO, target=ProjectStatus.EN_REVISION
    )
    def accept_review(self):
        """enviado → en_revision."""

    @transition(
        field=status, source=ProjectStatus.EN_REVISION, target=ProjectStatus.APROBADO
    )
    def approve(self):
        """en_revision → aprobado."""

    @transition(
        field=status, source=ProjectStatus.EN_REVISION, target=ProjectStatus.OBSERVADO
    )
    def observe(self):
        """en_revision → observado."""

    @transition(
        field=status,
        source=[ProjectStatus.EN_REVISION, ProjectStatus.OBSERVADO],
        target=ProjectStatus.BORRADOR,
    )
    def return_to_draft(self):
        """en_revision | observado → borrador."""

    @transition(
        field=status, source=ProjectStatus.EN_REVISION, target=ProjectStatus.RECHAZADO
    )
    def reject(self):
        """en_revision → rechazado (terminal)."""

    @transition(
        field=status, source=ProjectStatus.OBSERVADO, target=ProjectStatus.ENVIADO
    )
    def resubmit(self):
        """observado → enviado."""

    @transition(
        field=status, source=ProjectStatus.APROBADO, target=ProjectStatus.EN_EJECUCION
    )
    def start_execution(self):
        """aprobado → en_ejecucion."""

    @transition(
        field=status,
        source=ProjectStatus.EN_EJECUCION,
        target=ProjectStatus.SUSPENDIDO,
    )
    def suspend(self):
        """en_ejecucion → suspendido."""

    @transition(
        field=status,
        source=ProjectStatus.SUSPENDIDO,
        target=ProjectStatus.EN_EJECUCION,
    )
    def resume(self):
        """suspendido → en_ejecucion."""

    @transition(
        field=status,
        source=ProjectStatus.EN_EJECUCION,
        target=ProjectStatus.FINALIZADO,
    )
    def finalize(self):
        """en_ejecucion → finalizado."""

    @transition(
        field=status,
        source=ProjectStatus.FINALIZADO,
        target=ProjectStatus.EN_CIERRE,
    )
    def initiate_closure(self):
        """finalizado → en_cierre."""

    @transition(
        field=status, source=ProjectStatus.EN_CIERRE, target=ProjectStatus.CERRADO
    )
    def close(self):
        """en_cierre → cerrado (terminal)."""

    @transition(
        field=status,
        source=[
            ProjectStatus.BORRADOR,
            ProjectStatus.ENVIADO,
            ProjectStatus.EN_REVISION,
            ProjectStatus.OBSERVADO,
            ProjectStatus.APROBADO,
            ProjectStatus.EN_EJECUCION,
            ProjectStatus.SUSPENDIDO,
            ProjectStatus.FINALIZADO,
            ProjectStatus.EN_CIERRE,
        ],
        target=ProjectStatus.CANCELADO,
    )
    def cancel(self):
        """Any non-terminal → cancelado (terminal)."""


# ──────────────────────────────────────────────
# ProjectMember
# ──────────────────────────────────────────────


class ProjectMember(models.Model):
    """Team membership junction linking Researcher to Project.

    A researcher can only hold one role per project (unique constraint).
    Roles: co_investigator, student, seedbed, collaborator.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    researcher = models.ForeignKey(
        "researchers.Researcher",
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=30, choices=ProjectRole.choices)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects_projectmember"
        verbose_name = "Project Member"
        verbose_name_plural = "Project Members"
        ordering = ["project", "joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "researcher"],
                name="unique_project_researcher",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.researcher} — {self.get_role_display()}"


# ──────────────────────────────────────────────
# ProjectDocument
# ──────────────────────────────────────────────


class ProjectDocument(models.Model):
    """Metadata-only document record for a Project.

    Follows the ResearcherAttachment pattern: stores name, type,
    and external URL. No file upload in MVP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20, choices=ProjectDocumentType.choices)
    external_url = models.URLField(max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects_projectdocument"
        verbose_name = "Project Document"
        verbose_name_plural = "Project Documents"
        ordering = ["project", "-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_doc_type_display()})"


# ──────────────────────────────────────────────
# ProjectObservation
# ──────────────────────────────────────────────


class ProjectObservation(models.Model):
    """Append-only observation log (RN-014).

    Created when a director triggers the observe() transition.
    observed_by is nullable (SET_NULL on user deletion).
    No update/delete endpoints exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    observed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_observations",
    )
    observation_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects_projectobservation"
        verbose_name = "Project Observation"
        verbose_name_plural = "Project Observations"
        ordering = ["project", "-created_at"]

    def __str__(self) -> str:
        preview = self.observation_text[:60]
        return preview + ("…" if len(self.observation_text) > 60 else "")


# ──────────────────────────────────────────────
# ProjectStateLog
# ──────────────────────────────────────────────


class ProjectStateLog(models.Model):
    """Domain audit log for FSM transitions (RN-012).

    Dedicated per-project log for queryable state history.
    Each transition is also mirrored to AuditEvent for
    cross-module audit consistency.

    triggered_by is nullable (SET_NULL on user deletion).
    Append-only — no update/delete endpoints exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="state_logs",
    )
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    triggered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_state_logs",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects_projectstatelog"
        verbose_name = "Project State Log"
        verbose_name_plural = "Project State Logs"
        ordering = ["project", "-created_at"]
        indexes = [
            models.Index(
                fields=["project", "-created_at"],
                name="idx_statelog_project_time",
            ),
            models.Index(
                fields=["from_state", "to_state"],
                name="idx_statelog_states",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} → {self.to_state}"
