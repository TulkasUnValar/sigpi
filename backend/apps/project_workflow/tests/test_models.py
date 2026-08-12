"""
Model tests for project_workflow app — STRICT TDD.

Tests define the expected behavior of the 4-entity workflow module:
WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowAction.

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: All tests fail because models are empty stubs.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.project_workflow.models import (
    StepRole,
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)

# ──────────────────────────────────────────────
# Helpers (mirror projects test pattern)
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(
        name=f"Test University {code}",
        code=code,
    )


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution,
        name=name,
        code=code,
    )


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestWorkflowInstanceStatusEnum:
    """WorkflowInstanceStatus TextChoices has 5 states."""

    def test_all_five_states_defined(self):
        """All 5 status choices are present."""
        expected = {"pending", "completed", "observed", "rejected", "cancelled"}
        actual = {choice[0] for choice in WorkflowInstanceStatus.choices}
        assert actual == expected

    def test_default_is_pending(self):
        """Default status is pending."""
        assert WorkflowInstanceStatus.PENDING == "pending"


class TestWorkflowActionTypeEnum:
    """WorkflowActionType TextChoices has 6 types."""

    def test_all_six_types_defined(self):
        expected = {"create", "approve", "observe", "reject", "resubmit", "cancel"}
        actual = {choice[0] for choice in WorkflowActionType.choices}
        assert actual == expected


class TestStepRoleEnum:
    """StepRole TextChoices has at least center_director."""

    def test_center_director_defined(self):
        assert StepRole.CENTER_DIRECTOR == "center_director"


# ──────────────────────────────────────────────
# WorkflowTemplate Model Tests
# ──────────────────────────────────────────────


class TestWorkflowTemplateFields:
    """WorkflowTemplate model field behavior and constraints."""

    def test_create_template_minimal(self, db):
        """Template can be created with required fields."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(
            institution=inst,
            name="Standard Approval",
        )
        assert template.id is not None
        assert isinstance(template.id, uuid.UUID)
        assert template.institution == inst
        assert template.name == "Standard Approval"
        assert template.is_active is True
        assert template.description == ""

    def test_unique_name_per_institution(self, db):
        """UniqueConstraint (institution, name) enforced."""
        inst = _make_institution("TU")
        WorkflowTemplate.objects.create(institution=inst, name="Dup")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkflowTemplate.objects.create(institution=inst, name="Dup")

    def test_center_nullable(self, db):
        """center is optional."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(
            institution=inst,
            name="No Center",
        )
        assert template.center is None

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(
            institution=inst,
            name="T1",
        )
        assert str(template) == "T1"

    def test_timestamps_auto_set(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(
            institution=inst,
            name="T1",
        )
        assert template.created_at is not None
        assert template.updated_at is not None


# ──────────────────────────────────────────────
# WorkflowStep Model Tests
# ──────────────────────────────────────────────


class TestWorkflowStepFields:
    """WorkflowStep model field behavior and constraints."""

    def test_create_step(self, db):
        """Step can be created linked to a template."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(
            template=template,
            order=1,
            name="Director Review",
            deadline_days=10,
        )
        assert step.template == template
        assert step.order == 1
        assert step.name == "Director Review"
        assert step.role_required == StepRole.CENTER_DIRECTOR
        assert step.deadline_days == 10

    def test_unique_order_per_template(self, db):
        """UniqueConstraint (template, order) enforced."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkflowStep.objects.create(template=template, order=1, name="S2")

    def test_deadline_days_must_be_positive(self, db):
        """CHECK constraint enforces deadline_days > 0."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep(
            template=template,
            order=1,
            name="S1",
            deadline_days=0,
        )
        with pytest.raises(ValidationError):
            step.full_clean()

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(
            template=template,
            order=1,
            name="Review",
        )
        assert "Review" in str(step)


# ──────────────────────────────────────────────
# WorkflowInstance Model Tests
# ──────────────────────────────────────────────


class TestWorkflowInstanceFields:
    """WorkflowInstance model field behavior and constraints."""

    def test_create_instance(self, db):
        """Instance can be created with project_id and template."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        project_uuid = uuid.uuid4()
        instance = WorkflowInstance.objects.create(
            project_id=project_uuid,
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
        )
        assert instance.id is not None
        assert instance.project_id == project_uuid
        assert instance.institution == inst
        assert instance.template == template
        assert instance.status == "pending"
        assert instance.current_step is None
        assert instance.completed_at is None

    def test_default_status_pending(self, db):
        """Default status is pending when not provided."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        assert instance.status == "pending"

    def test_partial_unique_active_per_project(self, db):
        """Only one active (pending/observed) instance per project_id."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        project_uuid = uuid.uuid4()
        WorkflowInstance.objects.create(
            project_id=project_uuid,
            institution=inst,
            template=template,
            status="pending",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkflowInstance.objects.create(
                    project_id=project_uuid,
                    institution=inst,
                    template=template,
                    status="observed",
                )

    def test_completed_instance_does_not_block_new_active(self, db):
        """A completed instance does NOT block a new active one (different status)."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        project_uuid = uuid.uuid4()
        WorkflowInstance.objects.create(
            project_id=project_uuid,
            institution=inst,
            template=template,
            status="completed",
        )
        instance2 = WorkflowInstance.objects.create(
            project_id=project_uuid,
            institution=inst,
            template=template,
            status="pending",
        )
        assert instance2.status == "pending"

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        assert str(instance.project_id) in str(instance)

    def test_timestamps_auto_set(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        assert instance.created_at is not None
        assert instance.updated_at is not None


# ──────────────────────────────────────────────
# WorkflowAction Model Tests
# ──────────────────────────────────────────────


class TestWorkflowActionFields:
    """WorkflowAction model field behavior (append-only audit trail)."""

    def test_create_action(self, db):
        """Action records an event on an instance."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        user = _make_user("director@test.edu")
        action = WorkflowAction.objects.create(
            instance=instance,
            action=WorkflowActionType.APPROVE,
            acted_by=user,
            observation_text="Approved after review.",
        )
        assert action.instance == instance
        assert action.action == "approve"
        assert action.acted_by == user
        assert action.observation_text == "Approved after review."
        assert action.created_at is not None

    def test_step_nullable(self, db):
        """step is optional."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        action = WorkflowAction.objects.create(
            instance=instance,
            action=WorkflowActionType.CREATE,
        )
        assert action.step is None

    def test_acted_by_nullable(self, db):
        """acted_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        action = WorkflowAction.objects.create(
            instance=instance,
            action=WorkflowActionType.CREATE,
        )
        assert action.acted_by is None

    def test_metadata_nullable(self, db):
        """metadata JSONField is optional."""
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        action = WorkflowAction.objects.create(
            instance=instance,
            action=WorkflowActionType.CREATE,
            metadata={"source": "system"},
        )
        assert action.metadata == {"source": "system"}

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
        )
        action = WorkflowAction.objects.create(
            instance=instance,
            action=WorkflowActionType.CREATE,
        )
        assert "create" in str(action).lower()


# ──────────────────────────────────────────────
# Signal Tests
# ──────────────────────────────────────────────


class TestProjectStateChangedSignal:
    """project_state_changed signal is importable from project_workflow."""

    def test_signal_importable(self):
        """Signal can be imported without error."""
        import django.dispatch

        from apps.project_workflow.signals import project_state_changed

        assert project_state_changed is not None
        assert isinstance(project_state_changed, django.dispatch.Signal)

    def test_signal_accepts_expected_kwargs(self):
        """Signal can be sent with project, from_state, to_state, triggered_by."""
        from apps.project_workflow.signals import project_state_changed

        received = {}

        def receiver(sender, **kwargs):
            received.update(kwargs)

        project_state_changed.connect(receiver)
        try:
            project_state_changed.send(
                sender=None,
                project="mock_project",
                from_state="borrador",
                to_state="enviado",
                triggered_by="mock_user",
            )
            assert received.get("project") == "mock_project"
            assert received.get("from_state") == "borrador"
            assert received.get("to_state") == "enviado"
            assert received.get("triggered_by") == "mock_user"
        finally:
            project_state_changed.disconnect(receiver)


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestWorkflowTemplateFactory:
    """WorkflowTemplateFactory produces valid template instances."""

    def test_factory_creates_valid_template(self, db):
        from apps.project_workflow.tests.conftest import WorkflowTemplateFactory

        template = WorkflowTemplateFactory()
        assert template.id is not None
        assert template.name != ""
        assert template.institution is not None
        assert template.is_active is True

    def test_factory_unique_ids(self, db):
        from apps.project_workflow.tests.conftest import WorkflowTemplateFactory

        t1 = WorkflowTemplateFactory()
        t2 = WorkflowTemplateFactory()
        assert t1.id != t2.id


class TestWorkflowStepFactory:
    """WorkflowStepFactory produces valid step instances."""

    def test_factory_creates_valid_step(self, db):
        from apps.project_workflow.tests.conftest import WorkflowStepFactory

        step = WorkflowStepFactory()
        assert step.id is not None
        assert step.template is not None
        assert step.order >= 1
        assert step.deadline_days > 0


class TestWorkflowInstanceFactory:
    """WorkflowInstanceFactory produces valid instance instances."""

    def test_factory_creates_valid_instance(self, db):
        from apps.project_workflow.tests.conftest import WorkflowInstanceFactory

        instance = WorkflowInstanceFactory()
        assert instance.id is not None
        assert instance.project_id is not None
        assert instance.status == "pending"
        assert instance.institution is not None

    def test_factory_with_completed_status(self, db):
        from apps.project_workflow.tests.conftest import WorkflowInstanceFactory

        instance = WorkflowInstanceFactory(status="completed")
        assert instance.status == "completed"


class TestWorkflowActionFactory:
    """WorkflowActionFactory produces valid action instances."""

    def test_factory_creates_valid_action(self, db):
        from apps.project_workflow.tests.conftest import WorkflowActionFactory

        action = WorkflowActionFactory()
        assert action.id is not None
        assert action.instance is not None
        assert action.action == "create"
