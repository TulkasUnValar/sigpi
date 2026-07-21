"""
Progress Reporting module (§6.5) — Data Models.

Implements the data model defined in design.md and spec.md:
- ProgressReport: 6-state FSM, DENORMALIZED institution_id for RLS
- ProgressReview: append-only director observations (RN-P05)
- ProgressDocument: metadata-only document records (RF-043)
- ProgressStateLog: domain audit log for FSM transitions (RN-P04)

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField, transition

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class ProgressStatus(models.TextChoices):
    """FSM states for the ProgressReport lifecycle (6 states)."""

    BORRADOR = "borrador", "Borrador"
    ENVIADO = "enviado", "Enviado"
    EN_REVISION = "en_revision", "En Revisión"
    OBSERVADO = "observado", "Observado"
    APROBADO = "aprobado", "Aprobado"
    RECHAZADO = "rechazado", "Rechazado"


class ProgressDocumentType(models.TextChoices):
    """Document type choices for ProgressDocument — metadata-only (RF-043)."""

    EVIDENCE = "evidence", "Evidence"
    ANNEX = "annex", "Annex"
    REPORT = "report", "Report"
    OTHER = "other", "Other"


class ProgressReviewType(models.TextChoices):
    """Review type choices — append-only director observations (RN-P05)."""

    OBSERVATION = "observation", "Observation"
    REJECTION = "rejection", "Rejection"


# Terminal state — no outbound transitions allowed (RN-P07).
PROGRESS_TERMINAL_STATES = {ProgressStatus.APROBADO}

# ──────────────────────────────────────────────
# ProgressReport
# ──────────────────────────────────────────────


class ProgressReport(models.Model):
    """Periodic progress report with 6-state FSM lifecycle.

    Standalone model (does NOT inherit InstitutionScopedModel) because
    that base carries fields (code/name/description + 3-state FSM) that
    do not apply.  Carries DENORMALIZED institution_id for RLS.

    Field-level constraints:
      - RN-P01: 0 <= cumulative_percentage <= 100 (clean() + DB CHECK).
      - RN-P02: period_end >= period_start (clean() + DB CHECK).

    FSM transitions (9 total) defined as @transition methods below.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="progress_reports",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="progress_reports",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="created_progress_reports",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    description = models.TextField()
    cumulative_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    activities = models.TextField()
    difficulties = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    status = FSMField(default=ProgressStatus.BORRADOR, protected=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "progress_progressreport"
        verbose_name = "Progress Report"
        verbose_name_plural = "Progress Reports"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cumulative_percentage__gte=0)
                & models.Q(cumulative_percentage__lte=100),
                name="check_progress_percentage_range",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="check_progress_period_dates",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="idx_progress_inst_status",
            ),
            models.Index(
                fields=["project", "status"],
                name="idx_progress_project_status",
            ),
            models.Index(
                fields=["created_by"],
                name="idx_progress_created_by",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.title} — {self.period_start} / {self.period_end}"

    def clean(self):
        super().clean()
        errors = {}

        # RN-P01: cumulative_percentage range.
        if self.cumulative_percentage is not None:
            if self.cumulative_percentage < 0:
                errors.setdefault("cumulative_percentage", []).append(
                    "Cumulative percentage must be between 0 and 100."
                )
            elif self.cumulative_percentage > 100:
                errors.setdefault("cumulative_percentage", []).append(
                    "Cumulative percentage must be between 0 and 100."
                )

        # RN-P02: period_end >= period_start.
        if self.period_start and self.period_end:
            if self.period_end < self.period_start:
                errors.setdefault("period_end", []).append(
                    "Period end must be on or after period start."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ── FSM Transitions (9 total) ────────────────────────────────

    @transition(
        field=status,
        source=ProgressStatus.BORRADOR,
        target=ProgressStatus.ENVIADO,
    )
    def submit(self):
        """borrador → enviado."""

    @transition(
        field=status,
        source=ProgressStatus.ENVIADO,
        target=ProgressStatus.EN_REVISION,
    )
    def accept_review(self):
        """enviado → en_revision."""

    @transition(
        field=status,
        source=ProgressStatus.EN_REVISION,
        target=ProgressStatus.APROBADO,
    )
    def approve(self):
        """en_revision → aprobado (terminal)."""

    @transition(
        field=status,
        source=ProgressStatus.EN_REVISION,
        target=ProgressStatus.OBSERVADO,
    )
    def observe(self):
        """en_revision → observado."""

    @transition(
        field=status,
        source=ProgressStatus.EN_REVISION,
        target=ProgressStatus.RECHAZADO,
    )
    def reject(self):
        """en_revision → rechazado."""

    @transition(
        field=status,
        source=[
            ProgressStatus.EN_REVISION,
            ProgressStatus.OBSERVADO,
            ProgressStatus.RECHAZADO,
        ],
        target=ProgressStatus.BORRADOR,
    )
    def return_to_draft(self):
        """en_revision | observado | rechazado → borrador."""

    @transition(
        field=status,
        source=ProgressStatus.OBSERVADO,
        target=ProgressStatus.ENVIADO,
    )
    def resubmit(self):
        """observado → enviado."""


# ──────────────────────────────────────────────
# ProgressReview
# ──────────────────────────────────────────────


class ProgressReview(models.Model):
    """Append-only director observation or rejection (RN-P05).

    Created when a director triggers observe() or reject().
    reviewed_by is nullable (SET_NULL on user deletion).
    No update/delete endpoints exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progress_report = models.ForeignKey(
        ProgressReport,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_reviews",
    )
    review_text = models.TextField()
    review_type = models.CharField(
        max_length=20,
        choices=ProgressReviewType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "progress_progressreview"
        verbose_name = "Progress Review"
        verbose_name_plural = "Progress Reviews"
        ordering = ["progress_report", "-created_at"]

    def __str__(self) -> str:
        preview = self.review_text[:60]
        return preview + ("…" if len(self.review_text) > 60 else "")


# ──────────────────────────────────────────────
# ProgressDocument
# ──────────────────────────────────────────────


class ProgressDocument(models.Model):
    """Metadata-only document record for a ProgressReport (RF-043).

    Follows the ProjectDocument pattern: stores name, type,
    and external URL. No file upload in MVP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progress_report = models.ForeignKey(
        ProgressReport,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=255)
    doc_type = models.CharField(
        max_length=20,
        choices=ProgressDocumentType.choices,
    )
    external_url = models.URLField(max_length=500, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "progress_progressdocument"
        verbose_name = "Progress Document"
        verbose_name_plural = "Progress Documents"
        ordering = ["progress_report", "-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_doc_type_display()})"


# ──────────────────────────────────────────────
# ProgressStateLog
# ──────────────────────────────────────────────


class ProgressStateLog(models.Model):
    """Domain audit log for FSM transitions (RN-P04).

    Dedicated per-report log for queryable state history.
    Each transition is also mirrored to AuditEvent for
    cross-module audit consistency.

    triggered_by is nullable (SET_NULL on user deletion).
    Append-only — no update/delete endpoints exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progress_report = models.ForeignKey(
        ProgressReport,
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
        related_name="progress_state_logs",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "progress_progressstatelog"
        verbose_name = "Progress State Log"
        verbose_name_plural = "Progress State Logs"
        ordering = ["progress_report", "-created_at"]
        indexes = [
            models.Index(
                fields=["progress_report", "-created_at"],
                name="idx_progress_sl_report_time",
            ),
            models.Index(
                fields=["from_state", "to_state"],
                name="idx_progress_sl_states",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} → {self.to_state}"
