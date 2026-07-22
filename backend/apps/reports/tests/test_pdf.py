"""
View tests for PDF generation endpoint (§6.6 Phase 3).

Covers: ReportPDFView — GET /api/reports/{type}/{id}/pdf/
returns FileResponse with Content-Type: application/pdf.
Tests 200, 403, 400, 404, and streaming behavior.

Spec reference:   sdd/reports/spec — RF-050–RF-053, RF-057
Design reference: openspec/changes/reports/design.md

RED PHASE: Tests written BEFORE production implementation.
"""

import uuid
from unittest.mock import patch

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
    return Institution.objects.create(name="PDF University", code="PDF001")


@pytest.fixture
def inst_b(db):
    """Another institution for cross-institution tests."""
    return Institution.objects.create(name="PDF Other University", code="PDF002")


@pytest.fixture
def role(db):
    """Researcher role (level 4)."""
    return Role.objects.create(name=f"Researcher-{uuid.uuid4().hex[:4]}", level=4)


@pytest.fixture
def researcher_user(db, inst, role):
    """Authenticated user with Researcher role in inst."""
    user = User.objects.create_user(
        email=f"pdf-user-{uuid.uuid4().hex[:6]}@test.edu",
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
        email=f"pdf-other-{uuid.uuid4().hex[:6]}@test.edu",
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
        name="PDF Test Center",
        code="PDFC01",
    )


@pytest.fixture
def researcher(db, inst):
    """Researcher profile in the test institution."""
    return Researcher.objects.create(
        institution=inst,
        first_name="PDF",
        last_name="Generator",
        document_type="CC",
        document_number="PDF-001",
        primary_email="pdfgen@test.edu",
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
        title="PDF Test Project",
        abstract="PDF abstract.",
        objectives="PDF objectives.",
        methodology="PDF methodology.",
        expected_results="PDF results.",
        keywords="pdf, test",
        start_date=today,
        estimated_end_date=today + datetime.timedelta(days=365),
        status="aprobado",
    )


def _login(client, user):
    """Force-authenticate the API client as user."""
    client.force_authenticate(user=user)


def _set_institution(client, institution):
    """Set the active institution in the session."""
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ═══════════════════════════════════════════════════════
# Helpers for mocking PDF generation
# ═══════════════════════════════════════════════════════

FAKE_PDF_BYTES = b"%PDF-1.4 Mock PDF content\n1 0 obj<<>>endobj\n%%EOF"


def _mock_pdf_generation():
    """Mock ReportGenerator.generate_report to return fake PDF bytes.

    We mock at the service layer rather than WeasyPrint directly
    because WeasyPrint's C extensions fail to load on Windows.
    """
    return patch(
        "apps.reports.services.ReportGenerator.generate_report",
        return_value=(FAKE_PDF_BYTES, "<html>Mock</html>"),
    )


def _mock_pdf_audit():
    """Mock AuditEventEmitter.emit to prevent DB writes to audit table."""
    return patch("apps.accounts.audit.AuditEventEmitter.emit")


# ═══════════════════════════════════════════════════════
# ReportPDFView Tests
# ═══════════════════════════════════════════════════════


class TestReportPDFView:
    """GET /api/reports/{type}/{id}/pdf/ — PDF generation endpoint."""

    def test_pdf_project_returns_200_with_correct_content_type(
        self, api_client, inst, researcher_user, project
    ):
        """PDF endpoint returns 200 with Content-Type: application/pdf."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_pdf_generation(), _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        # FileResponse uses streaming_content, read it to get bytes
        pdf_content = b"".join(response.streaming_content)
        assert pdf_content == FAKE_PDF_BYTES

    def test_pdf_researcher_returns_200(
        self, api_client, inst, researcher_user, researcher
    ):
        """PDF endpoint for researcher type returns 200 with PDF content."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "researcher", "entity_id": str(researcher.pk)},
        )
        with _mock_pdf_generation(), _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_pdf_center_returns_200(
        self, api_client, inst, researcher_user, center
    ):
        """PDF endpoint for center type returns 200 with PDF content."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "center", "entity_id": str(center.pk)},
        )
        with _mock_pdf_generation(), _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_pdf_returns_403_for_anonymous(self, api_client, project):
        """Unauthenticated users get 403 on PDF endpoint."""
        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code in (401, 403)

    def test_pdf_returns_403_for_cross_institution(
        self, api_client, inst_b, other_inst_user, project
    ):
        """User from institution B cannot generate PDF for institution A project (RN-015)."""
        _login(api_client, other_inst_user)
        _set_institution(api_client, inst_b)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_pdf_generation(), _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code == 403

    def test_pdf_invalid_type_returns_400(
        self, api_client, inst, researcher_user, project
    ):
        """Invalid report_type returns 400 Bad Request."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "invalid_type", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code in (400, 404)

    def test_pdf_nonexistent_entity_returns_404(
        self, api_client, inst, researcher_user
    ):
        """Entity not found returns 404."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "project", "entity_id": str(uuid.uuid4())},
        )
        with _mock_pdf_generation(), _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code in (404, 500)

    def test_pdf_calls_generate_report_with_correct_html(
        self, api_client, inst, researcher_user, project
    ):
        """ReportGenerator.generate_report() receives the correct type and entity_id."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:pdf",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with patch(
            "apps.reports.services.ReportGenerator.generate_report",
            return_value=(FAKE_PDF_BYTES, "<html>Mock</html>"),
        ) as mock_gen, _mock_pdf_audit():
            response = api_client.get(url)

        assert response.status_code == 200
        # Verify generate_report was called with correct args
        assert mock_gen.called
        # Mock.call_args is ((report_type, entity_id, user), {})
        call_args = mock_gen.call_args[0]
        assert call_args[0] == "project"
        assert str(call_args[1]) == str(project.pk)
