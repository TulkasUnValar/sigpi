"""
Budgets — Presupuesto module (SIGPI §6.9).

Implements the data model defined in design.md and spec.md:
- Budget: project OneToOne, institution-scoped, 4-state lifecycle
- BudgetLine: line item (rubro) under a Budget
- FundingSource: project funding source (multiple allowed, RN-019)
- BudgetExecution: line-level execution record with optional authorization
- BudgetAttachment: metadata-only attachment record (no file upload in MVP)

Design reference: openspec/changes/budgets/design.md
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md

Money fields use DecimalField(max_digits=14, decimal_places=2) with a
non-negative DB CHECK constraint. Parents cascade; the authorization
user (BudgetExecution.authorized_by) uses SET_NULL.
"""

import uuid

from django.db import models

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class BudgetStatus(models.TextChoices):
    """Lifecycle states for a Budget (explicit data, no FSM)."""

    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    EXECUTED = "executed", "Executed"
    CLOSED = "closed", "Closed"


# ──────────────────────────────────────────────
# Budget
# ──────────────────────────────────────────────


class Budget(models.Model):
    """Project budget with a 4-state lifecycle.

    One Budget per project (OneToOne). Institution-scoped; carries
    a denormalized institution_id for RLS on the parent table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="budget",
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    name = models.CharField(max_length=255)
    approved_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=BudgetStatus.choices, default=BudgetStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budgets_budget"
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(approved_amount__gte=0),
                name="check_budget_amount_non_negative",
            ),
            models.UniqueConstraint(
                fields=["project"],
                name="unique_budget_per_project",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="idx_budget_inst_status",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────
# BudgetLine
# ──────────────────────────────────────────────


class BudgetLine(models.Model):
    """Line item (rubro) under a Budget."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    name = models.CharField(max_length=255)
    approved_amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budgets_budgetline"
        verbose_name = "Budget Line"
        verbose_name_plural = "Budget Lines"
        ordering = ["budget", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(approved_amount__gte=0),
                name="check_budgetline_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["budget"],
                name="idx_budgetline_budget",
            ),
            models.Index(
                fields=["budget", "name"],
                name="idx_budgetline_budget_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────
# FundingSource
# ──────────────────────────────────────────────


class FundingSource(models.Model):
    """Funding source for a Project (multiple allowed, RN-019)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="funding_sources",
    )
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budgets_fundingsource"
        verbose_name = "Funding Source"
        verbose_name_plural = "Funding Sources"
        ordering = ["project", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="check_fundingsource_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project"],
                name="idx_fundingsource_project",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────
# BudgetExecution
# ──────────────────────────────────────────────


class BudgetExecution(models.Model):
    """Line-level execution record.

    RN-020 (sum ≤ line approved unless authorized) is enforced in the
    service layer (Phase 2). The authorization fields are nullable and
    recorded only for authorized over-execution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    line = models.ForeignKey(
        BudgetLine,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    executed_at = models.DateField()
    authorized_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_executions_authorized",
    )
    authorized_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "budgets_budgetexecution"
        verbose_name = "Budget Execution"
        verbose_name_plural = "Budget Executions"
        ordering = ["line", "-executed_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="check_budgetexecution_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["line", "executed_at"],
                name="idx_budgetexec_line_exec",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.amount} on {self.executed_at}"


# ──────────────────────────────────────────────
# BudgetAttachment
# ──────────────────────────────────────────────


class BudgetAttachment(models.Model):
    """Metadata-only attachment record for a Budget (RF-B05).

    Stores name, doc_type, and a required external_url. No file
    upload in the MVP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=50)
    external_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "budgets_budgetattachment"
        verbose_name = "Budget Attachment"
        verbose_name_plural = "Budget Attachments"
        ordering = ["budget", "-created_at"]
        indexes = [
            models.Index(
                fields=["budget"],
                name="idx_budgetattachment_budget",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.doc_type})"
