"""
ViewSet tests for project_workflow — STRICT TDD (RED phase).

Tests define expected behavior of 3 ViewSets:
- WorkflowTemplateViewSet: CRUD, admin+ only
- WorkflowInstanceViewSet: list/retrieve + @action approve/observe/reject
- WorkflowActionViewSet: create+list+retrieve, 405 on update/delete

Also tests:
- URL routing (DefaultRouter + action paths)
- Permission matrix (admin, director, pi, other)
- Filtering integration via query params
- 405 Method Not Allowed on action update/delete (WF-006)

Pattern follows apps/projects/tests/test_views.py for consistency.

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: Tests fail because views.py and urls.py do not exist yet.
"""

import datetime
import json
import uuid

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution, ResearchCenter
from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)
from apps.researchers.models import Researcher

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


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
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def center(db, institution):
    return ResearchCenter.objects.create(institution=institution, name="AI Lab", code="AI")


@pytest.fixture
def admin_role(db):
    return get_role("Admin Institucional")


@pytest.fixture
def director_role(db):
    return get_role("Director de Centro")


@pytest.fixture
def researcher_role(db):
    return get_role("Investigador")


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(email="admin@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def director_user(db, institution, center, director_role):
    user = User.objects.create_user(email="dir@test.edu", auth_source="local", password="p")
    membership = InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    membership.centers.add(center)
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(email="res@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_pi(db, institution, researcher_user, center):
    pi = Researcher.objects.create(
        user=researcher_user,
        institution=institution,
        first_name="Alice",
        last_name="Smith",
        document_type="CC",
        document_number="PI000001",
        primary_email="res@test.edu",
    )
    from apps.researchers.models import ResearcherAffiliation

    ResearcherAffiliation.objects.create(researcher=pi, center=center, is_primary=True)
    return pi


@pytest.fixture
def workflow_template(db, institution):
    return WorkflowTemplate.objects.create(institution=institution, name="Approval")


@pytest.fixture
def workflow_step(db, workflow_template):
    return WorkflowStep.objects.create(
        template=workflow_template, order=1, name="Director Review", deadline_days=7
    )


@pytest.fixture
def workflow_instance(db, institution, workflow_template, workflow_step, researcher_pi, center):
    project = _make_project(institution, center, researcher_pi)
    return WorkflowInstance.objects.create(
        project_id=project.id,
        institution=institution,
        template=workflow_template,
        current_step=workflow_step,
        status=WorkflowInstanceStatus.PENDING,
        deadline_date=timezone.now() + datetime.timedelta(days=7),
    )


# ──────────────────────────────────────────────────────────
# WorkflowTemplateViewSet
# ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWorkflowTemplateViewSet:
    """CRUD for templates — admin+ only."""

    def test_list_templates(
        self, api_client, institution, admin_user, workflow_template, workflow_step
    ):
        _login(api_client, admin_user, institution)
        response = api_client.get(reverse("project_workflow:workflowtemplate-list"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "results" in data
        assert len(data["results"]) >= 1
        assert data["results"][0]["name"] == "Approval"

    def test_create_template(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        payload = {
            "institution": str(institution.id),
            "name": "New Template",
            "steps": [
                {
                    "order": 1,
                    "name": "Step 1",
                    "role_required": "center_director",
                    "deadline_days": 10,
                },
            ],
        }
        response = api_client.post(
            reverse("project_workflow:workflowtemplate-list"),
            json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.content)
        assert data["name"] == "New Template"
        assert len(data["steps"]) == 1

    def test_retrieve_template(self, api_client, institution, admin_user, workflow_template):
        _login(api_client, admin_user, institution)
        response = api_client.get(
            reverse("project_workflow:workflowtemplate-detail", kwargs={"pk": workflow_template.id})
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["name"] == "Approval"

    def test_update_template(self, api_client, institution, admin_user, workflow_template):
        _login(api_client, admin_user, institution)
        response = api_client.patch(
            reverse(
                "project_workflow:workflowtemplate-detail", kwargs={"pk": workflow_template.id}
            ),
            json.dumps({"name": "Updated"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["name"] == "Updated"

    def test_delete_template(self, api_client, institution, admin_user, workflow_template):
        _login(api_client, admin_user, institution)
        response = api_client.delete(
            reverse("project_workflow:workflowtemplate-detail", kwargs={"pk": workflow_template.id})
        )
        assert response.status_code == 204

    def test_list_forbidden_to_researcher(
        self, api_client, institution, researcher_user, workflow_template
    ):
        _login(api_client, researcher_user, institution)
        response = api_client.get(reverse("project_workflow:workflowtemplate-list"))
        assert response.status_code == 403


# ──────────────────────────────────────────────────────────
# WorkflowInstanceViewSet
# ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWorkflowInstanceViewSet:
    """list/retrieve + approve/observe/reject actions."""

    def test_list_instances(self, api_client, institution, director_user, workflow_instance):
        _login(api_client, director_user, institution)
        response = api_client.get(reverse("project_workflow:workflowinstance-list"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "results" in data
        assert len(data["results"]) >= 1

    def test_retrieve_instance(self, api_client, institution, director_user, workflow_instance):
        _login(api_client, director_user, institution)
        response = api_client.get(
            reverse("project_workflow:workflowinstance-detail", kwargs={"pk": workflow_instance.id})
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["id"] == str(workflow_instance.id)
        assert "actions" in data

    def test_filter_by_status(
        self, api_client, institution, director_user, workflow_template, workflow_step
    ):
        _login(api_client, director_user, institution)
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=institution,
            template=workflow_template,
            current_step=workflow_step,
            status=WorkflowInstanceStatus.COMPLETED,
        )
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=institution,
            template=workflow_template,
            current_step=workflow_step,
            status=WorkflowInstanceStatus.PENDING,
        )

        response = api_client.get(
            reverse("project_workflow:workflowinstance-list") + "?status=pending"
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        for item in data["results"]:
            assert item["status"] == "pending"

    def test_filter_by_overdue(
        self, api_client, institution, director_user, workflow_template, workflow_step
    ):
        _login(api_client, director_user, institution)
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=institution,
            template=workflow_template,
            current_step=workflow_step,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )
        WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=institution,
            template=workflow_template,
            current_step=workflow_step,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() + datetime.timedelta(days=1),
        )

        response = api_client.get(
            reverse("project_workflow:workflowinstance-list") + "?overdue=true"
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        for item in data["results"]:
            assert item["is_overdue"] is True

    def test_approve_action(self, api_client, institution, director_user, workflow_instance):
        _login(api_client, director_user, institution)
        response = api_client.post(
            reverse(
                "project_workflow:workflowinstance-approve", kwargs={"pk": workflow_instance.id}
            ),
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "completed"

    def test_observe_action(self, api_client, institution, director_user, workflow_instance):
        _login(api_client, director_user, institution)
        response = api_client.post(
            reverse(
                "project_workflow:workflowinstance-observe", kwargs={"pk": workflow_instance.id}
            ),
            json.dumps({"observation_text": "Needs changes."}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "observed"

    def test_reject_action(self, api_client, institution, director_user, workflow_instance):
        _login(api_client, director_user, institution)
        response = api_client.post(
            reverse(
                "project_workflow:workflowinstance-reject", kwargs={"pk": workflow_instance.id}
            ),
            json.dumps({"reason": "Insufficient data."}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "rejected"

    def test_approve_forbidden_to_other_center_director(
        self, api_client, institution, center, director_user, workflow_instance
    ):
        other_center = ResearchCenter.objects.create(
            institution=institution, name="Other", code="O"
        )
        other_user = User.objects.create_user(
            email="other@test.edu", auth_source="local", password="p"
        )
        other_role = get_role("Director de Centro")
        other_membership = InstitutionMembership.objects.create(
            user=other_user, institution=institution, role=other_role, is_active=True
        )
        other_membership.centers.add(other_center)

        _login(api_client, other_user, institution)
        response = api_client.post(
            reverse(
                "project_workflow:workflowinstance-approve", kwargs={"pk": workflow_instance.id}
            ),
        )
        assert response.status_code == 403


# ──────────────────────────────────────────────────────────
# WorkflowActionViewSet
# ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWorkflowActionViewSet:
    """Create+list+retrieve — 405 on update/delete (WF-006)."""

    def test_list_actions(
        self, api_client, institution, director_user, workflow_instance, workflow_step
    ):
        WorkflowAction.objects.create(
            instance=workflow_instance,
            step=workflow_step,
            action=WorkflowActionType.CREATE,
            acted_by=director_user,
        )
        _login(api_client, director_user, institution)
        response = api_client.get(
            reverse(
                "project_workflow:workflowaction-list", kwargs={"instance_pk": workflow_instance.id}
            )
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) >= 1

    def test_create_action(
        self, api_client, institution, director_user, workflow_instance, workflow_step
    ):
        _login(api_client, director_user, institution)
        payload = {
            "action": "observe",
            "observation_text": "Needs revision.",
        }
        response = api_client.post(
            reverse(
                "project_workflow:workflowaction-list", kwargs={"instance_pk": workflow_instance.id}
            ),
            json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.content)
        assert data["action"] == "observe"

    def test_update_action_returns_405(
        self, api_client, institution, director_user, workflow_instance, workflow_step
    ):
        action = WorkflowAction.objects.create(
            instance=workflow_instance, step=workflow_step, action=WorkflowActionType.CREATE
        )
        _login(api_client, director_user, institution)
        response = api_client.patch(
            reverse(
                "project_workflow:workflowaction-detail",
                kwargs={"instance_pk": workflow_instance.id, "pk": action.id},
            ),
            json.dumps({"observation_text": "Changed."}),
            content_type="application/json",
        )
        assert response.status_code == 405

    def test_delete_action_returns_405(
        self, api_client, institution, director_user, workflow_instance, workflow_step
    ):
        action = WorkflowAction.objects.create(
            instance=workflow_instance, step=workflow_step, action=WorkflowActionType.CREATE
        )
        _login(api_client, director_user, institution)
        response = api_client.delete(
            reverse(
                "project_workflow:workflowaction-detail",
                kwargs={"instance_pk": workflow_instance.id, "pk": action.id},
            ),
        )
        assert response.status_code == 405
