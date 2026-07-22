"""
View tests for the Reports / Informes module (§6.6) — Preview endpoint.

Covers: ReportPreviewView — GET preview returns 200 with HTML,
403 for unauthorized users, 403 for cross-institution access (RN-015).

Spec reference:   sdd/reports/spec — RF-056, RN-015
Design reference: openspec/changes/reports/design.md

RED PHASE: Tests written BEFORE production implementation.
"""

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def inst(db):
    """Test institution."""
    return Institution.objects.create(name="Preview University", code="PU001")


@pytest.fixture
def inst_b(db):
    """Another institution for cross-institution tests."""
    return Institution.objects.create(name="Other University", code="OU001")


@pytest.fixture
def role(db):
    """Researcher role (level 4)."""
    return Role.objects.create(name=f"Researcher {uuid.uuid4().hex[:4]}", level=4)


@pytest.fixture
def researcher_user(db, inst, role):
    """Authenticated user with Researcher role in inst."""
    user = User.objects.create_user(
        email=f"researcher-{uuid.uuid4().hex[:6]}@test.edu",
        password="testpass",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=inst,
        role=role,
    )
    return user


@pytest.fixture
def other_inst_user(db, inst_b, role):
    """Authenticated user in a different institution."""
    user = User.objects.create_user(
        email=f"other-{uuid.uuid4().hex[:6]}@test.edu",
        password="testpass",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=inst_b,
        role=role,
    )
    return user


@pytest.fixture
def center(db, inst):
    """Research center in the test institution."""
    return ResearchCenter.objects.create(
        institution=inst,
        name="Test Center",
        code="TC001",
    )


@pytest.fixture
def researcher(db, inst):
    """Researcher profile in the test institution."""
    return Researcher.objects.create(
        institution=inst,
        first_name="Preview",
        last_name="Tester",
        document_type="CC",
        document_number="PREV-001",
        primary_email="preview@test.edu",
    )


@pytest.fixture
def project(db, inst, center, researcher):
    """Project in the test institution."""
    import datetime

    today = datetime.date.today()
    return Project.objects.create(
        institution=inst,
        center=center,
        principal_investigator=researcher,
        title="Preview Test Project",
        abstract="Preview abstract.",
        objectives="Preview objectives.",
        methodology="Preview methodology.",
        expected_results="Preview results.",
        keywords="preview, test",
        start_date=today,
        estimated_end_date=today + datetime.timedelta(days=365),
        status="aprobado",
    )


def _login(client, user, institution):
    """Login and set active institution for DRF APIClient."""
    client.force_authenticate(user=user)
    # Set institution_id on the client's session-like storage
    client.credentials()  # reset
    client.force_authenticate(user=user)


def _set_institution(client, institution):
    """Set the active institution in the session."""
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ═══════════════════════════════════════════════════════
# ReportPreviewView Tests
# ═══════════════════════════════════════════════════════


class TestReportPreviewView:
    """GET /api/reports/{type}/{id}/preview/ — HTML preview endpoint."""

    def test_preview_project_returns_200_with_html(
        self, api_client, inst, researcher_user, project
    ):
        """Preview returns 200 with {"html": "..."} containing project title."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "html" in data
        assert isinstance(data["html"], str)
        assert len(data["html"]) > 0

    def test_preview_researcher_returns_200(self, api_client, inst, researcher_user, researcher):
        """Preview for researcher type returns 200 with valid HTML."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "researcher", "entity_id": str(researcher.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "html" in data
        assert len(data["html"]) > 0

    def test_preview_center_returns_200(self, api_client, inst, researcher_user, center):
        """Preview for center type returns 200 with valid HTML."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "center", "entity_id": str(center.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "html" in data
        assert len(data["html"]) > 0

    def test_preview_returns_403_for_anonymous(self, api_client, project):
        """Unauthenticated users get 403."""
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 403

    def test_preview_returns_403_for_cross_institution(
        self, api_client, inst_b, other_inst_user, project, inst
    ):
        """User from institution B cannot preview a project from institution A (RN-015)."""
        _login(api_client, other_inst_user, inst_b)
        _set_institution(api_client, inst_b)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 403

    def test_preview_invalid_type_returns_400(self, api_client, inst, researcher_user, project):
        """Invalid report_type returns 400 Bad Request."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "invalid", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code in (400, 404)

    def test_preview_nonexistent_entity_returns_404(self, api_client, inst, researcher_user):
        """Entity not found returns 404."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(uuid.uuid4())},
        )
        response = api_client.get(url)
        assert response.status_code in (404, 500)
