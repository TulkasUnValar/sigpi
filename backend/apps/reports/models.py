"""
Reports / Informes module (§6.6) — Data Models.

Implements the data model defined in design.md and spec.md:
- Report: generic report (type + entity_id) with institution scoping
- ReportApproval: separate approval model with metadata (RN-018)

Spec reference:   sdd/reports/spec — RF-050–RF-058, RN-015–RN-018
Design reference: openspec/changes/reports/design.md
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class ReportType(models.TextChoices):
    """Report target types (4 types — RF-050 to RF-053)."""

    PROJECT = "project", "Project Report"
    RESEARCHER = "researcher", "Researcher Report"
    CENTER = "center", "Center Report"
    ADVANCES = "advances", "Advances Report"


class ReportStatus(models.TextChoices):
    """Report lifecycle states (4 states)."""

    DRAFT = "draft", "Draft"
    GENERATED = "generated", "Generated"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


# ──────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────


class Report(models.Model):
    """Generic report record — report_type + entity_id resolves to any entity.

    Standalone model (does NOT inherit InstitutionScopedModel) because
    that base carries fields (code/name/description + 3-state FSM) that
    do not apply. Carries DENORMALIZED institution_id for RLS.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
    )
    entity_id = models.UUIDField()
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.GENERATED,
    )
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="generated_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_report"
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="check_report_version_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "report_type", "status"],
                name="idx_reports_inst_type_status",
            ),
            models.Index(
                fields=["entity_id", "report_type"],
                name="idx_reports_entity_type",
            ),
            models.Index(
                fields=["created_by"],
                name="idx_reports_created_by",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} — {self.entity_id}"

    def clean(self):
        super().clean()
        errors: dict[str, list[str]] = {}

        # Guard: entity_id is required (non-null).
        if self.entity_id is None or self.entity_id == "":
            errors.setdefault("entity_id", []).append("Entity ID is required for a report.")

        # Guard: version must be >= 1 (DB CHECK also enforces this).
        if self.version is not None and self.version < 1:
            errors.setdefault("version", []).append("Report version must be at least 1.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# ReportApproval
# ──────────────────────────────────────────────


class ReportApproval(models.Model):
    """Approval record for a Report — separate model for re-approval history (RN-018).

    approved_by is nullable (SET_NULL on user deletion).
    report_version captures the Report.version at time of approval.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_approvals",
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    report_version = models.PositiveIntegerField()

    class Meta:
        db_table = "reports_reportapproval"
        verbose_name = "Report Approval"
        verbose_name_plural = "Report Approvals"
        ordering = ["report", "-approved_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(report_version__gte=1),
                name="check_approval_version_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["report", "-approved_at"],
                name="idx_approval_report_time",
            ),
            models.Index(
                fields=["approved_by"],
                name="idx_approval_approved_by",
            ),
        ]

    def __str__(self) -> str:
        report_type = self.report.get_report_type_display() if self.report else "Report"
        return f"{report_type} approved by {self.approved_by or 'unknown'}"
