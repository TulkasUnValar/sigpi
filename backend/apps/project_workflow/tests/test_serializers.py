"""
Serializer tests for project_workflow — STRICT TDD (RED phase).

Tests define expected behavior of 6 serializers:
- WorkflowTemplateListSerializer
- WorkflowTemplateSerializer (nested steps read/write)
- WorkflowStepSerializer
- WorkflowInstanceSerializer (nested actions, is_overdue)
- WorkflowInstanceListSerializer
- WorkflowActionSerializer (create-only, RO fields)

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: Tests fail because serializers.py does not exist yet.
"""
import datetime
import uuid

from django.utils import timezone

from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution
    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter
    return ResearchCenter.objects.create(institution=institution, name=name, code=code)


def _make_user(email="test@example.com"):
    from apps.accounts.models import User
    return User.objects.create_user(email=email)


def _make_project(institution, center, pi, **overrides):
    from apps.projects.models import Project
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title=overrides.get("title", "Valid Title"),
        abstract=overrides.get("abstract", "Valid abstract."),
        objectives=overrides.get("objectives", "Valid objectives."),
        methodology=overrides.get("methodology", "Valid methodology."),
        expected_results=overrides.get("expected_results", "Valid expected results."),
        keywords=overrides.get("keywords", "ai, research"),
        start_date=overrides.get("start_date", datetime.date(2025, 1, 1)),
        estimated_end_date=overrides.get("estimated_end_date", datetime.date(2025, 12, 31)),
    )


# ──────────────────────────────────────────────────────────
# WorkflowTemplateListSerializer
# ──────────────────────────────────────────────────────────


class TestWorkflowTemplateListSerializer:
    """Lightweight list: id, name, center, is_active, step_count."""

    def test_serializes_list_fields(self, db):
        from apps.project_workflow.serializers import WorkflowTemplateListSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        serializer = WorkflowTemplateListSerializer(template)
        data = serializer.data

        assert "id" in data
        assert data["name"] == "T1"
        assert data["is_active"] is True
        assert "step_count" in data
        assert data["step_count"] == 1

    def test_step_count_zero(self, db):
        from apps.project_workflow.serializers import WorkflowTemplateListSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")

        serializer = WorkflowTemplateListSerializer(template)
        assert serializer.data["step_count"] == 0


# ──────────────────────────────────────────────────────────
# WorkflowStepSerializer
# ──────────────────────────────────────────────────────────


class TestWorkflowStepSerializer:
    """id, order, name, role_required, deadline_days."""

    def test_serializes_step_fields(self, db):
        from apps.project_workflow.serializers import WorkflowStepSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        serializer = WorkflowStepSerializer(step)
        data = serializer.data

        assert data["order"] == 1
        assert data["name"] == "S1"
        assert data["role_required"] == "center_director"
        assert data["deadline_days"] == 7


# ──────────────────────────────────────────────────────────
# WorkflowTemplateSerializer (full detail + nested steps)
# ──────────────────────────────────────────────────────────


class TestWorkflowTemplateSerializer:
    """Full detail with nested steps (read-only)."""

    def test_serializes_nested_steps(self, db):
        from apps.project_workflow.serializers import WorkflowTemplateSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        serializer = WorkflowTemplateSerializer(template)
        data = serializer.data

        assert data["name"] == "T1"
        assert "steps" in data
        assert len(data["steps"]) == 1
        assert data["steps"][0]["name"] == "S1"

    def test_deserializes_nested_steps_on_create(self, db):
        from apps.project_workflow.serializers import WorkflowTemplateSerializer

        inst = _make_institution("TU")
        payload = {
            "institution": str(inst.id),
            "name": "New Template",
            "steps": [
                {"order": 1, "name": "Step 1", "role_required": "center_director", "deadline_days": 10},
            ],
        }

        serializer = WorkflowTemplateSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        template = serializer.save()

        assert template.name == "New Template"
        assert template.steps.count() == 1
        assert template.steps.first().name == "Step 1"

    def test_deserializes_nested_steps_on_update(self, db):
        from apps.project_workflow.serializers import WorkflowTemplateSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="Old", deadline_days=7)

        payload = {
            "name": "Updated",
            "steps": [
                {"order": 1, "name": "New Step", "role_required": "center_director", "deadline_days": 14},
            ],
        }

        serializer = WorkflowTemplateSerializer(template, data=payload, partial=True)
        assert serializer.is_valid(), serializer.errors
        template = serializer.save()

        assert template.name == "Updated"
        assert template.steps.count() == 1
        assert template.steps.first().name == "New Step"


# ──────────────────────────────────────────────────────────
# WorkflowInstanceListSerializer
# ──────────────────────────────────────────────────────────


class TestWorkflowInstanceListSerializer:
    """Lightweight list: id, project, status, deadline_date, is_overdue, current_step."""

    def test_serializes_list_fields(self, db):
        from apps.project_workflow.serializers import WorkflowInstanceListSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() + datetime.timedelta(days=1),
        )

        serializer = WorkflowInstanceListSerializer(instance)
        data = serializer.data

        assert "id" in data
        assert "project" in data
        assert data["status"] == "pending"
        assert "deadline_date" in data
        assert "is_overdue" in data
        assert data["is_overdue"] is False
        assert "current_step" in data

    def test_is_overdue_true(self, db):
        from apps.project_workflow.serializers import WorkflowInstanceListSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )

        serializer = WorkflowInstanceListSerializer(instance)
        assert serializer.data["is_overdue"] is True

    def test_is_overdue_false_for_completed(self, db):
        from apps.project_workflow.serializers import WorkflowInstanceListSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.COMPLETED,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )

        serializer = WorkflowInstanceListSerializer(instance)
        assert serializer.data["is_overdue"] is False


# ──────────────────────────────────────────────────────────
# WorkflowInstanceSerializer (full detail)
# ──────────────────────────────────────────────────────────


class TestWorkflowInstanceSerializer:
    """Full detail with nested actions and is_overdue."""

    def test_serializes_nested_actions(self, db):
        from apps.project_workflow.serializers import WorkflowInstanceSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )
        user = _make_user("dir@test.edu")
        WorkflowAction.objects.create(instance=instance, step=step, action=WorkflowActionType.CREATE, acted_by=user)

        serializer = WorkflowInstanceSerializer(instance)
        data = serializer.data

        assert "actions" in data
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action"] == "create"
        assert "is_overdue" in data

    def test_actions_read_only(self, db):
        from apps.project_workflow.serializers import WorkflowInstanceSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
        )

        payload = {
            "project_id": str(uuid.uuid4()),
            "status": "completed",
            "actions": [{"action": "approve"}],
        }
        serializer = WorkflowInstanceSerializer(instance, data=payload, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.actions.count() == 0  # actions are read-only


# ──────────────────────────────────────────────────────────
# WorkflowActionSerializer
# ──────────────────────────────────────────────────────────


class TestWorkflowActionSerializer:
    """Create-only, instance/step/acted_by read-only."""

    def test_serializes_action_fields(self, db):
        from apps.project_workflow.serializers import WorkflowActionSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
        )
        user = _make_user("dir@test.edu")
        action = WorkflowAction.objects.create(
            instance=instance, step=step, action=WorkflowActionType.APPROVE, acted_by=user,
            observation_text="Looks good.",
        )

        serializer = WorkflowActionSerializer(action)
        data = serializer.data

        assert data["action"] == "approve"
        assert data["observation_text"] == "Looks good."
        assert "instance" in data
        assert "step" in data
        assert "acted_by" in data

    def test_instance_read_only_on_create(self, db):
        from apps.project_workflow.serializers import WorkflowActionSerializer

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
        )

        payload = {
            "action": "observe",
            "observation_text": "Needs work.",
            "instance": str(uuid.uuid4()),  # should be ignored
        }
        serializer = WorkflowActionSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        assert "instance" not in serializer.validated_data

    def test_step_read_only_on_create(self, db):
        from apps.project_workflow.serializers import WorkflowActionSerializer

        payload = {
            "action": "observe",
            "observation_text": "Needs work.",
            "step": str(uuid.uuid4()),  # should be ignored
        }
        serializer = WorkflowActionSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        assert "step" not in serializer.validated_data
