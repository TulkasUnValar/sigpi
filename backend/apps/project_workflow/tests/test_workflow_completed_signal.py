"""
Signal tests for project_workflow app — STRICT TDD (RED phase).

Tests define expected behavior of `workflow_completed` signal emission:
- Emitted when `WorkflowService.complete_workflow()` runs with correct kwargs
- Project status is NOT automatically changed (MVP: manual transition only)

Spec reference:  openspec/changes/cross-module-integration/spec.md — FR-005
Design reference: openspec/changes/cross-module-integration/design.md — IP-5
"""

from unittest.mock import patch

from apps.project_workflow.models import (
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)

# ── Helpers ────────────────────────────────────────────


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
        start_date=overrides.get("start_date", __import__("datetime").date(2025, 1, 1)),
        estimated_end_date=overrides.get("estimated_end_date", __import__("datetime").date(2025, 12, 31)),
    )


# ──────────────────────────────────────────────
# workflow_completed signal (IP-5)
# ──────────────────────────────────────────────


class TestWorkflowCompletedSignal:
    """workflow_completed is dispatched when complete_workflow() runs."""

    def test_signal_emitted_on_complete_workflow(self, db):
        """complete_workflow() emits workflow_completed with project_id, instance_id, triggered_by."""
        from apps.project_workflow.services import WorkflowService
        from apps.project_workflow.signals import workflow_completed
        from apps.researchers.models import Researcher

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = __import__("apps.project_workflow.models", fromlist=["WorkflowInstance"]).WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        with patch.object(workflow_completed, "send") as mock_send:
            WorkflowService.complete_workflow(instance.id, triggered_by=user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["project_id"] == project.id
        assert kwargs["instance_id"] == instance.id
        assert kwargs["triggered_by"] == user

    def test_signal_emitted_when_advance_step_completes_workflow(self, db):
        """advance_step() on last step triggers complete_workflow() and emits signal."""
        from apps.project_workflow.services import WorkflowService
        from apps.project_workflow.signals import workflow_completed
        from apps.researchers.models import Researcher

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = __import__("apps.project_workflow.models", fromlist=["WorkflowInstance"]).WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        with patch.object(workflow_completed, "send") as mock_send:
            WorkflowService.advance_step(instance.id, triggered_by=user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["project_id"] == project.id
        assert kwargs["instance_id"] == instance.id

    def test_no_auto_transition_in_mvp(self, db):
        """workflow_completed does NOT change project.status automatically."""
        from apps.project_workflow.services import WorkflowService
        from apps.project_workflow.signals import workflow_completed
        from apps.researchers.models import Researcher

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi, status="aprobado")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = __import__("apps.project_workflow.models", fromlist=["WorkflowInstance"]).WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        original_status = project.status

        with patch.object(workflow_completed, "send") as mock_send:
            WorkflowService.complete_workflow(instance.id, triggered_by=user)

        mock_send.assert_called_once()
        project.refresh_from_db()
        assert project.status == original_status  # still aprobado, not auto-changed
