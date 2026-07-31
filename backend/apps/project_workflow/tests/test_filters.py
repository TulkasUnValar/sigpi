"""
Filter tests for project_workflow — STRICT TDD (RED phase).

Tests define expected behavior of WorkflowInstanceFilter:
- project (UUIDFilter)
- status (ChoiceFilter)
- center (UUIDFilter via project__center_id)
- overdue (BooleanFilter method: deadline_date < now AND status=pending)

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: Tests fail because filters.py does not exist yet.
"""
import datetime
import uuid

from django.utils import timezone

from apps.project_workflow.models import (
    WorkflowInstance,
    WorkflowInstanceStatus,
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
# WorkflowInstanceFilter
# ──────────────────────────────────────────────────────────


class TestWorkflowInstanceFilterByProject:
    """Filter by project_id (UUID)."""

    def test_filter_by_project(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        project_a = uuid.uuid4()
        project_b = uuid.uuid4()

        WorkflowInstance.objects.create(project_id=project_a, institution=inst, template=template)
        WorkflowInstance.objects.create(project_id=project_b, institution=inst, template=template)

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"project": str(project_a)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project_id == project_a

    def test_filter_by_project_no_match(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(project_id=uuid.uuid4(), institution=inst, template=template)

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"project": str(uuid.uuid4())}, queryset=qs)
        assert f.qs.count() == 0


class TestWorkflowInstanceFilterByStatus:
    """Filter by status choice."""

    def test_filter_by_status_pending(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(), institution=inst, template=template, status=WorkflowInstanceStatus.PENDING
        )
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(), institution=inst, template=template, status=WorkflowInstanceStatus.COMPLETED
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"status": "pending"}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().status == WorkflowInstanceStatus.PENDING

    def test_filter_by_status_completed(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(), institution=inst, template=template, status=WorkflowInstanceStatus.PENDING
        )
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(), institution=inst, template=template, status=WorkflowInstanceStatus.COMPLETED
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"status": "completed"}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().status == WorkflowInstanceStatus.COMPLETED


class TestWorkflowInstanceFilterByCenter:
    """Filter by center via project__center_id."""

    def test_filter_by_center(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        center_a = _make_center(inst, name="A", code="A")
        center_b = _make_center(inst, name="B", code="B")
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project_a = _make_project(inst, center_a, pi)
        project_b = _make_project(inst, center_b, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")

        WorkflowInstance.objects.create(project_id=project_a.id, institution=inst, template=template)
        WorkflowInstance.objects.create(project_id=project_b.id, institution=inst, template=template)

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"center": str(center_a.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project_id == project_a.id


class TestWorkflowInstanceFilterByOverdue:
    """Filter by overdue flag (method filter)."""

    def test_filter_overdue_true(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        overdue = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() + datetime.timedelta(days=1),
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"overdue": "true"}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().id == overdue.id

    def test_filter_overdue_false(self, db):
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )
        not_overdue = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() + datetime.timedelta(days=1),
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"overdue": "false"}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().id == not_overdue.id

    def test_overdue_excludes_completed(self, db):
        """Completed instances are NOT overdue even with past deadline."""
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.COMPLETED,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"overdue": "true"}, queryset=qs)
        assert f.qs.count() == 0

    def test_overdue_excludes_null_deadline(self, db):
        """Instances with null deadline are NOT overdue."""
        from apps.project_workflow.filters import WorkflowInstanceFilter

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=None,
        )

        qs = WorkflowInstance.objects.all()
        f = WorkflowInstanceFilter(data={"overdue": "true"}, queryset=qs)
        assert f.qs.count() == 0
