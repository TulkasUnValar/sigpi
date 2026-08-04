"""
Factory-boy factories for the project_workflow module.

Provides ergonomic test data generation for WorkflowTemplate,
WorkflowStep, WorkflowInstance, and WorkflowAction.

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md
"""
import uuid

import factory
from factory.django import DjangoModelFactory

from apps.project_workflow.models import (
    StepRole,
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)


class UserFactory(DjangoModelFactory):
    """Minimal User factory — defined here because accounts has no test conftest."""

    email = factory.Sequence(lambda n: f"user-{n}@test.edu")
    is_active = True

    class Meta:
        model = "accounts.User"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use create_user so password is hashed."""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        return user_model.objects.create_user(*args, **kwargs)


class WorkflowTemplateFactory(DjangoModelFactory):
    """Factory for WorkflowTemplate — institution-scoped."""

    institution = factory.SubFactory(
        "apps.institutions.tests.conftest.InstitutionFactory"
    )
    center = None
    name = factory.Sequence(lambda n: f"Template {n}")
    description = factory.Faker("paragraph", nb_sentences=2)
    is_active = True

    class Meta:
        model = WorkflowTemplate


class WorkflowStepFactory(DjangoModelFactory):
    """Factory for WorkflowStep — linked to a WorkflowTemplate."""

    template = factory.SubFactory(WorkflowTemplateFactory)
    order = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Step {n}")
    description = factory.Faker("sentence", nb_words=6)
    role_required = StepRole.CENTER_DIRECTOR
    deadline_days = 15

    class Meta:
        model = WorkflowStep


class WorkflowInstanceFactory(DjangoModelFactory):
    """Factory for WorkflowInstance — runtime approval process."""

    project_id = factory.LazyFunction(uuid.uuid4)
    institution = factory.SelfAttribute("template.institution")
    template = factory.SubFactory(WorkflowTemplateFactory)
    current_step = None
    status = WorkflowInstanceStatus.PENDING
    deadline_date = None
    completed_at = None

    class Meta:
        model = WorkflowInstance


class WorkflowActionFactory(DjangoModelFactory):
    """Factory for WorkflowAction — append-only audit record."""

    instance = factory.SubFactory(WorkflowInstanceFactory)
    step = None
    action = WorkflowActionType.CREATE
    acted_by = None
    observation_text = ""
    metadata = None

    class Meta:
        model = WorkflowAction
