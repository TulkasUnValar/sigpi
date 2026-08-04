"""
Project Workflow — Approval Flow module (SIGPI §6.5).

Thin approval-workflow layer sitting on top of the projects module.
Integration is signal-based: `ProjectService._log_transition()` emits a
`project_state_changed` Django signal; a receiver in this app creates/resets/cancels
`WorkflowInstance` rows. Zero schema changes to the Project model.

Models:
- WorkflowTemplate: reusable approval template per institution/center
- WorkflowStep: ordered step inside a template
- WorkflowInstance: runtime approval process for a project
- WorkflowAction: append-only audit record of every step action

Design reference: openspec/changes/project_workflow/design.md
Spec reference:   openspec/changes/project_workflow/spec.md
"""
import uuid

from django.db import models

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class WorkflowInstanceStatus(models.TextChoices):
    """Runtime status of a workflow instance."""

    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    OBSERVED = "observed", "Observed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class WorkflowActionType(models.TextChoices):
    """Types of actions recorded in the audit trail."""

    CREATE = "create", "Create"
    APPROVE = "approve", "Approve"
    OBSERVE = "observe", "Observe"
    REJECT = "reject", "Reject"
    RESUBMIT = "resubmit", "Resubmit"
    CANCEL = "cancel", "Cancel"


class StepRole(models.TextChoices):
    """Role required to act on a workflow step."""

    CENTER_DIRECTOR = "center_director", "Center Director"


# ──────────────────────────────────────────────
# WorkflowTemplate
# ──────────────────────────────────────────────


class WorkflowTemplate(models.Model):
    """Reusable approval template scoped to an institution.

    Each template defines an ordered set of WorkflowStep rows.
    A center-scoped template takes precedence over an institution-only
    template when matching projects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="workflow_templates",
    )
    center = models.ForeignKey(
        "institutions.ResearchCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_templates",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_workflow_workflowtemplate"
        verbose_name = "Workflow Template"
        verbose_name_plural = "Workflow Templates"
        ordering = ["institution", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="unique_template_name_per_institution",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "is_active"],
                name="idx_wftmpl_inst_active",
            ),
        ]

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────
# WorkflowStep
# ──────────────────────────────────────────────


class WorkflowStep(models.Model):
    """A single ordered step inside a WorkflowTemplate.

    Steps define who must act (`role_required`) and within how many
    days (`deadline_days`).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    order = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    role_required = models.CharField(
        max_length=30,
        choices=StepRole.choices,
        default=StepRole.CENTER_DIRECTOR,
    )
    deadline_days = models.PositiveIntegerField(default=15)

    class Meta:
        db_table = "project_workflow_workflowstep"
        verbose_name = "Workflow Step"
        verbose_name_plural = "Workflow Steps"
        ordering = ["template", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "order"],
                name="unique_step_order_per_template",
            ),
            models.CheckConstraint(
                condition=models.Q(deadline_days__gt=0),
                name="check_step_deadline_days_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.template.name})"


# ──────────────────────────────────────────────
# WorkflowInstance
# ──────────────────────────────────────────────


class WorkflowInstance(models.Model):
    """Runtime approval process for a single project.

    Created automatically when a Project is submitted (signal-driven).
    Stores a denormalized `institution_id` for RLS and a `project_id`
    reference (UUID only in Phase 1 to avoid circular dependency).

    Constraints:
      - WR-001: exactly one active instance per project.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.UUIDField(editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    current_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_instances",
    )
    status = models.CharField(
        max_length=20,
        choices=WorkflowInstanceStatus.choices,
        default=WorkflowInstanceStatus.PENDING,
    )
    deadline_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_workflow_workflowinstance"
        verbose_name = "Workflow Instance"
        verbose_name_plural = "Workflow Instances"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project_id"],
                condition=models.Q(status__in=["pending", "observed"]),
                name="unique_active_instance_per_project",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="idx_instance_inst_status",
            ),
            models.Index(
                fields=["project_id", "status"],
                name="idx_instance_project_status",
            ),
            models.Index(
                fields=["deadline_date"],
                name="idx_instance_deadline",
            ),
        ]

    def __str__(self) -> str:
        return f"Workflow for project {self.project_id} ({self.status})"


# ──────────────────────────────────────────────
# WorkflowAction
# ──────────────────────────────────────────────


class WorkflowAction(models.Model):
    """Append-only audit record of every action taken on a workflow instance.

    WR-002: no update/delete permitted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions",
    )
    action = models.CharField(
        max_length=20,
        choices=WorkflowActionType.choices,
    )
    acted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_actions",
    )
    observation_text = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_workflow_workflowaction"
        verbose_name = "Workflow Action"
        verbose_name_plural = "Workflow Actions"
        ordering = ["instance", "-created_at"]
        indexes = [
            models.Index(
                fields=["instance", "-created_at"],
                name="idx_action_instance_time",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.instance_id}"
