"""
Signal definitions and receivers for the project_workflow module.

`project_state_changed` is defined here so the `projects` module can
import and emit it without creating a circular dependency.

Receiver `on_project_state_change` listens for project FSM transitions
and creates/resets/cancels WorkflowInstance rows accordingly.

Provides: project, from_state, to_state, triggered_by
"""

import django.dispatch
from django.db import transaction
from django.dispatch import receiver

from apps.project_workflow.models import (
    WorkflowInstance,
    WorkflowInstanceStatus,
)
from apps.project_workflow.services import WorkflowService, WorkflowTemplateService

# NOTE: Keep this object stable — existing tests and the projects module
# hold references to it. Do NOT reassign this name.
project_state_changed = django.dispatch.Signal()


@receiver(project_state_changed)
def on_project_state_change(sender, project, from_state, to_state, triggered_by, **kwargs):
    """Create, advance, reset, or cancel WorkflowInstance based on project state.

    - enviado (from borrador) or en_revision  → create_instance
    - enviado (from observado)                → reset_instance (resubmit)
    - aprobado                                → advance/complete workflow
    - observado                               → record observe action
    - rechazado                               → reject workflow
    - cancelado / cerrado                     → cancel_instance
    """
    # Defensive: skip if project is not a real Project model instance
    # (e.g., tests that emit the signal with mock strings)
    try:
        from apps.projects.models import Project

        if not isinstance(project, Project):
            return
    except Exception:
        return

    # States that trigger workflow creation
    if to_state in ("enviado", "en_revision"):
        # Resubmit from observed -> reset existing instance
        if to_state == "enviado" and from_state == "observado":
            instance = (
                WorkflowInstance.objects.filter(
                    project_id=project.id,
                    status__in=[
                        WorkflowInstanceStatus.PENDING,
                        WorkflowInstanceStatus.OBSERVED,
                    ],
                ).first()
            )
            if instance:
                with transaction.atomic():
                    WorkflowService.reset_instance(instance, triggered_by)
            return

        # Fresh submit -> create new instance (idempotent)
        with transaction.atomic():
            template = WorkflowTemplateService.get_default_template(
                project.institution_id, center_id=getattr(project, "center_id", None)
            )
            if template:
                WorkflowService.create_instance(
                    project.id, template.id, triggered_by=triggered_by
                )
        return

    # Terminal / action states that require an existing active instance
    instance = (
        WorkflowInstance.objects.filter(
            project_id=project.id,
            status__in=[
                WorkflowInstanceStatus.PENDING,
                WorkflowInstanceStatus.OBSERVED,
            ],
        )
        .select_related("current_step", "template")
        .first()
    )

    if instance is None:
        return

    if to_state == "aprobado":
        with transaction.atomic():
            WorkflowService.advance_step(instance.id, triggered_by=triggered_by)
        return

    if to_state == "observado":
        with transaction.atomic():
            WorkflowService.observe(instance.id, user=triggered_by)
        return

    if to_state == "rechazado":
        with transaction.atomic():
            WorkflowService.reject(instance.id, user=triggered_by)
        return

    if to_state in ("cancelado", "cerrado"):
        with transaction.atomic():
            WorkflowService.cancel_instance(instance.id, user=triggered_by)
        return
