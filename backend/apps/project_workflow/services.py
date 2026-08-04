"""
Service layer for project_workflow — business logic + approval orchestration.

WorkflowService: create_instance, advance_step, complete_workflow,
record_action, check_minimum_data, annotate_overdue, get_current_step.
WorkflowTemplateService: get_default_template, validate_step_order.

All methods are static — matches ProjectService / CallService pattern.

Design reference: openspec/changes/project_workflow/design.md
Spec reference:   openspec/changes/project_workflow/spec.md
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Case, Count, Q, Value, When
from django.utils import timezone

from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)

# ──────────────────────────────────────────────
# WorkflowService
# ──────────────────────────────────────────────


class WorkflowService:
    """Approval workflow orchestration for projects.

    Static methods — plain Python class, not a Django model.
    """

    @staticmethod
    def create_instance(project_id, template_id, triggered_by=None):
        """Create a WorkflowInstance for a project.

        Idempotent (WR-001): returns existing active instance if present.
        Pre-guard: check_minimum_data must pass.
        Sets current_step = first step, deadline_date = now + step.deadline_days.
        Creates WorkflowAction(action=create).
        """
        WorkflowService.check_minimum_data(project_id)

        # Idempotency: one active instance per project
        existing = WorkflowInstance.objects.filter(
            project_id=project_id,
            status__in=[WorkflowInstanceStatus.PENDING, WorkflowInstanceStatus.OBSERVED],
        ).first()
        if existing:
            return existing

        template = WorkflowTemplate.objects.get(pk=template_id)
        first_step = (
            WorkflowStep.objects.filter(template=template)
            .order_by("order")
            .first()
        )
        if first_step is None:
            raise ValidationError("The selected template has no steps.")

        deadline_date = timezone.now() + timezone.timedelta(days=first_step.deadline_days)

        with transaction.atomic():
            instance = WorkflowInstance.objects.create(
                project_id=project_id,
                institution=template.institution,
                template=template,
                current_step=first_step,
                status=WorkflowInstanceStatus.PENDING,
                deadline_date=deadline_date,
            )
            WorkflowAction.objects.create(
                instance=instance,
                action=WorkflowActionType.CREATE,
                acted_by=triggered_by,
            )
            return instance

    @staticmethod
    def check_minimum_data(project_id):
        """Validate that the project has all required fields (CA-005).

        Checks: title, abstract, objectives, methodology, expected_results,
        keywords, center, principal_investigator.
        Raises ValidationError if any are missing or empty.
        """
        # Lazy import to avoid circular dependency at module load time
        from apps.projects.models import Project

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise ValidationError("Project not found.")

        missing = []
        if not project.title:
            missing.append("title")
        if not project.abstract:
            missing.append("abstract")
        if not project.objectives:
            missing.append("objectives")
        if not project.methodology:
            missing.append("methodology")
        if not project.expected_results:
            missing.append("expected_results")
        if not project.keywords:
            missing.append("keywords")
        if not project.center_id:
            missing.append("center")
        if not project.principal_investigator_id:
            missing.append("principal investigator")

        if missing:
            raise ValidationError(
                f"Minimum data requirements not met: missing {', '.join(missing)}."
            )

    @staticmethod
    def advance_step(instance_id, triggered_by=None):
        """Advance a workflow instance to its next step.

        If there is a next step, move current_step forward and record an
        APPROVE action for the previous step.
        If there is no next step (single-step workflow), call complete_workflow.
        """
        with transaction.atomic():
            instance = (
                WorkflowInstance.objects.select_for_update()
                .select_related("current_step", "template")
                .get(pk=instance_id)
            )

            WorkflowService.check_minimum_data(instance.project_id)

            if instance.current_step is None:
                raise ValidationError("Instance has no current step to advance from.")

            next_step = (
                WorkflowStep.objects.filter(
                    template=instance.template,
                    order__gt=instance.current_step.order,
                )
                .order_by("order")
                .first()
            )

            if next_step is None:
                # No next step — complete the workflow
                return WorkflowService.complete_workflow(instance, triggered_by=triggered_by)

            # Record approval for the step we are leaving
            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.APPROVE,
                acted_by=triggered_by,
            )

            instance.current_step = next_step
            instance.save(update_fields=["current_step", "updated_at"])
            return instance

    @staticmethod
    def complete_workflow(instance_id_or_obj, triggered_by=None):
        """Mark a workflow instance as completed.

        Creates WorkflowAction(action=approve) and sets status=completed.
        Accepts either a WorkflowInstance object or an instance_id.
        """
        with transaction.atomic():
            if isinstance(instance_id_or_obj, WorkflowInstance):
                instance = instance_id_or_obj
            else:
                instance = (
                    WorkflowInstance.objects.select_for_update()
                    .select_related("current_step")
                    .get(pk=instance_id_or_obj)
                )

            WorkflowService.check_minimum_data(instance.project_id)

            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.APPROVE,
                acted_by=triggered_by,
            )
            instance.status = WorkflowInstanceStatus.COMPLETED
            instance.completed_at = timezone.now()
            instance.save(update_fields=["status", "completed_at", "updated_at"])
            return instance

    @staticmethod
    def record_action(instance_id, action_type, performed_by, notes=""):
        """Append-only action log for a workflow instance.

        Creates a WorkflowAction without mutating instance status.
        """
        instance = WorkflowInstance.objects.get(pk=instance_id)
        return WorkflowAction.objects.create(
            instance=instance,
            step=instance.current_step,
            action=action_type,
            acted_by=performed_by,
            observation_text=notes,
        )

    @staticmethod
    def annotate_overdue(qs):
        """Add is_overdue annotation to a WorkflowInstance queryset.

        Overdue = deadline_date < now AND status = pending.
        """
        now = timezone.now()
        return qs.annotate(
            is_overdue=Case(
                When(
                    Q(status=WorkflowInstanceStatus.PENDING)
                    & Q(deadline_date__lt=now),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    @staticmethod
    def get_current_step(instance):
        """Return the current WorkflowStep for an instance."""
        return instance.current_step

    @staticmethod
    def observe(instance_id_or_obj, user, observation_text=""):
        """Record an observation on a workflow instance.

        Creates WorkflowAction(action=observe) and sets status=observed.
        """
        with transaction.atomic():
            if isinstance(instance_id_or_obj, WorkflowInstance):
                instance = instance_id_or_obj
            else:
                instance = (
                    WorkflowInstance.objects.select_for_update()
                    .select_related("current_step")
                    .get(pk=instance_id_or_obj)
                )

            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.OBSERVE,
                acted_by=user,
                observation_text=observation_text,
            )
            instance.status = WorkflowInstanceStatus.OBSERVED
            instance.save(update_fields=["status", "updated_at"])
            return instance

    @staticmethod
    def reject(instance_id_or_obj, user, reason=""):
        """Reject a workflow instance.

        Creates WorkflowAction(action=reject) and sets status=rejected.
        """
        with transaction.atomic():
            if isinstance(instance_id_or_obj, WorkflowInstance):
                instance = instance_id_or_obj
            else:
                instance = (
                    WorkflowInstance.objects.select_for_update()
                    .select_related("current_step")
                    .get(pk=instance_id_or_obj)
                )

            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.REJECT,
                acted_by=user,
                observation_text=reason,
            )
            instance.status = WorkflowInstanceStatus.REJECTED
            instance.save(update_fields=["status", "updated_at"])
            return instance

    @staticmethod
    def reset_instance(instance_id_or_obj, user):
        """Reset a workflow instance to pending (resubmit).

        Sets status=pending, current_step=first step, deadline_date recomputed.
        Creates WorkflowAction(action=resubmit).
        """
        with transaction.atomic():
            if isinstance(instance_id_or_obj, WorkflowInstance):
                instance = instance_id_or_obj
            else:
                instance = (
                    WorkflowInstance.objects.select_for_update()
                    .select_related("template")
                    .get(pk=instance_id_or_obj)
                )

            first_step = (
                WorkflowStep.objects.filter(template=instance.template)
                .order_by("order")
                .first()
            )
            if first_step is None:
                raise ValidationError("Template has no steps.")

            deadline_date = timezone.now() + timezone.timedelta(days=first_step.deadline_days)

            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.RESUBMIT,
                acted_by=user,
            )
            instance.status = WorkflowInstanceStatus.PENDING
            instance.current_step = first_step
            instance.deadline_date = deadline_date
            instance.completed_at = None
            instance.save(
                update_fields=[
                    "status",
                    "current_step",
                    "deadline_date",
                    "completed_at",
                    "updated_at",
                ]
            )
            return instance

    @staticmethod
    def cancel_instance(instance_id_or_obj, user):
        """Cancel a workflow instance (terminal project states).

        Creates WorkflowAction(action=cancel) and sets status=cancelled.
        """
        with transaction.atomic():
            if isinstance(instance_id_or_obj, WorkflowInstance):
                instance = instance_id_or_obj
            else:
                instance = (
                    WorkflowInstance.objects.select_for_update()
                    .select_related("current_step")
                    .get(pk=instance_id_or_obj)
                )

            WorkflowAction.objects.create(
                instance=instance,
                step=instance.current_step,
                action=WorkflowActionType.CANCEL,
                acted_by=user,
            )
            instance.status = WorkflowInstanceStatus.CANCELLED
            instance.save(update_fields=["status", "updated_at"])
            return instance


# ──────────────────────────────────────────────
# WorkflowTemplateService
# ──────────────────────────────────────────────


class WorkflowTemplateService:
    """CRUD and query operations for WorkflowTemplate rows."""

    @staticmethod
    def get_default_template(institution_id, center_id=None):
        """Return the active template with the fewest steps.

        If center_id is provided, center-scoped active templates take precedence.
        """
        qs = WorkflowTemplate.objects.filter(
            institution_id=institution_id,
            is_active=True,
        )

        if center_id:
            center_qs = qs.filter(center_id=center_id)
            if center_qs.exists():
                qs = center_qs

        qs = qs.annotate(step_count=Count("steps")).order_by("step_count", "name")
        return qs.first()

    @staticmethod
    def validate_step_order(template_id):
        """Validate that steps for a template are sequentially ordered 1..N.

        Returns True if valid, False if gaps, duplicates, or empty.
        Duplicates are prevented by DB UniqueConstraint; this checks gaps.
        """
        orders = list(
            WorkflowStep.objects.filter(template_id=template_id)
            .values_list("order", flat=True)
            .order_by("order")
        )
        if not orders:
            return False
        return orders == list(range(1, len(orders) + 1))
