"""
Permission tests for project_workflow — STRICT TDD (RED phase).

Tests define expected behavior of IsWorkflowStepApprover:
- Admin+ (level ≤ 2) bypasses
- Center Director (level ≤ 3) with matching center passes
- Others fail

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: Tests fail because permissions.py does not exist yet.
"""

import datetime
from unittest.mock import MagicMock

from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Helpers (matching researchers/projects permission test pattern)
# ──────────────────────────────────────────────────────────


def _make_request(
    method="GET",
    authenticated=True,
    is_superuser=False,
    institution_id=None,
    role_level=None,
    center_ids=None,
):
    """Build a mock DRF Request with the given attributes."""
    user = MagicMock()
    user.is_authenticated = authenticated
    user.is_superuser = is_superuser

    membership = None
    if role_level is not None:
        role = MagicMock()
        role.level = role_level
        membership = MagicMock()
        membership.role = role
        if center_ids:
            membership.centers.values_list.return_value = [(cid,) for cid in center_ids]
        else:
            membership.centers.values_list.return_value = []

    request = MagicMock(spec=Request)
    request.user = user
    request.method = method
    request.institution_id = institution_id
    request.active_membership = membership

    return request


def _mock_view():
    return MagicMock()


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


def _make_instance_for_project(project):
    from apps.project_workflow.models import WorkflowInstance, WorkflowStep, WorkflowTemplate

    template = WorkflowTemplate.objects.create(institution=project.institution, name="T1")
    step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
    return WorkflowInstance.objects.create(
        project_id=project.id,
        institution=project.institution,
        template=template,
        current_step=step,
    )


# ──────────────────────────────────────────────────────────
# IsWorkflowStepApprover
# ──────────────────────────────────────────────────────────


class TestIsWorkflowStepApprover:
    """Permission: Center Director of project's center OR Admin+ (level ≤ 2)."""

    def test_admin_bypasses_has_permission(self):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        perm = IsWorkflowStepApprover()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_superadmin_bypasses_has_permission(self):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        perm = IsWorkflowStepApprover()
        request = _make_request(method="POST", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_researcher_fails_has_permission(self):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        perm = IsWorkflowStepApprover()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_unauthenticated_fails_has_permission(self):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        perm = IsWorkflowStepApprover()
        request = _make_request(authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_director_of_project_center_passes(self, db):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        instance = _make_instance_for_project(project)

        perm = IsWorkflowStepApprover()
        request = _make_request(
            method="POST",
            role_level=3,
            institution_id=str(inst.id),
            center_ids=[str(center.id)],
        )
        request.active_membership.centers.values_list.return_value = [center.id]
        assert perm.has_object_permission(request, _mock_view(), instance) is True

    def test_director_of_other_center_fails(self, db):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        inst = _make_institution("TU")
        center_a = _make_center(inst, name="A", code="A")
        center_b = _make_center(inst, name="B", code="B")
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center_a, pi)
        instance = _make_instance_for_project(project)

        perm = IsWorkflowStepApprover()
        request = _make_request(
            method="POST",
            role_level=3,
            institution_id=str(inst.id),
            center_ids=[str(center_b.id)],
        )
        assert perm.has_object_permission(request, _mock_view(), instance) is False

    def test_admin_bypasses_center_check(self, db):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        instance = _make_instance_for_project(project)

        perm = IsWorkflowStepApprover()
        request = _make_request(
            method="POST",
            role_level=2,
            institution_id=str(inst.id),
            center_ids=[],
        )
        assert perm.has_object_permission(request, _mock_view(), instance) is True

    def test_no_membership_fails(self, db):
        from apps.project_workflow.permissions import IsWorkflowStepApprover

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        instance = _make_instance_for_project(project)

        perm = IsWorkflowStepApprover()
        request = _make_request(
            method="POST",
            role_level=3,
            institution_id=str(inst.id),
            center_ids=None,
        )
        assert perm.has_object_permission(request, _mock_view(), instance) is False
