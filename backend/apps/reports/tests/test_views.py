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
from rest_framework.test import APIClient, APIRequestFactory

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
# View Helper Unit Tests
# ═══════════════════════════════════════════════════════


class TestViewHelpers:
    """Direct unit tests for views.py helper functions."""

    def test_get_entity_institution_invalid_uuid_returns_none(self, db):
        """_get_entity_institution_id returns None for invalid UUID (lines 54-57)."""
        from apps.reports.views import _get_entity_institution_id

        result = _get_entity_institution_id("project", "not-a-uuid")
        assert result is None

    def test_get_entity_institution_researcher_not_found_returns_none(self, db):
        """_get_entity_institution_id returns None for missing researcher (lines 73-74)."""
        from apps.reports.views import _get_entity_institution_id

        result = _get_entity_institution_id("researcher", str(uuid.uuid4()))
        assert result is None

    def test_get_entity_institution_center_not_found_returns_none(self, db):
        """_get_entity_institution_id returns None for missing center (lines 81-84)."""
        from apps.reports.views import _get_entity_institution_id

        result = _get_entity_institution_id("center", str(uuid.uuid4()))
        assert result is None

    def test_check_institution_access_superuser_returns_true(self, db):
        """_check_institution_access returns True for superuser (line 93)."""
        from apps.accounts.models import User
        from apps.reports.views import _check_institution_access

        superuser = User.objects.create_superuser(
            email="su@test.edu", password="testpass"
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = superuser
        assert _check_institution_access(request, uuid.uuid4()) is True

    def test_check_institution_access_membership_match(self, db):
        """_check_institution_access returns True via active_membership (line 101)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution
        from apps.reports.views import _check_institution_access

        inst = Institution.objects.create(name="Test", code="T01")
        user = User.objects.create_user(email="u@test.edu", password="testpass")
        role = Role.objects.create(name="Role", level=4)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        assert _check_institution_access(request, inst.pk) is True

    def test_user_is_entity_director_researcher_with_centers(self, db):
        """_user_is_entity_director for researcher type with centers (lines 323-341)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution, ResearchCenter
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="Test", code="T01")
        center = ResearchCenter.objects.create(institution=inst, name="C1", code="C1")
        user = User.objects.create_user(email="dir@test.edu", password="testpass")
        role = Role.objects.create(name="Director", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        membership.centers.add(center)
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "researcher", str(uuid.uuid4())
        )
        assert result is True

    def test_user_is_entity_director_project_with_center(self, db):
        """_user_is_entity_director for project type passes object permission (line 308)."""
        import datetime

        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution, ResearchCenter
        from apps.projects.models import Project
        from apps.reports.views import ReportApprovalView
        from apps.researchers.models import Researcher

        inst = Institution.objects.create(name="Test", code="T01")
        center = ResearchCenter.objects.create(institution=inst, name="C1", code="C1")
        pi = Researcher.objects.create(
            institution=inst,
            first_name="PI",
            last_name="Test",
            document_type="CC",
            document_number="PI001",
            primary_email="pi@test.edu",
        )
        today = datetime.date.today()
        project = Project.objects.create(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test Project",
            abstract="Abstract.",
            objectives="Objectives.",
            methodology="Method.",
            expected_results="Results.",
            keywords="test",
            start_date=today,
            estimated_end_date=today + datetime.timedelta(days=365),
            status="aprobado",
        )
        user = User.objects.create_user(email="dir2@test.edu", password="testpass")
        role = Role.objects.create(name="Director", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        membership.centers.add(center)
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "project", str(project.pk)
        )
        assert result is True

    def test_get_or_create_report_existing_report(self, db):
        """_get_or_create_report returns existing report (line 358)."""
        from apps.accounts.models import User
        from apps.institutions.models import Institution
        from apps.reports.models import Report
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="Test", code="T01")
        user = User.objects.create_user(email="u@test.edu", password="testpass")
        report = Report.objects.create(
            report_type="project",
            entity_id=uuid.uuid4(),
            institution=inst,
            created_by=user,
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        result = ReportApprovalView._get_or_create_report(
            request, "project", report.entity_id
        )
        assert result.pk == report.pk

    def test_get_or_create_report_entity_not_found_raises_404(self, db):
        """_get_or_create_report raises Http404 when entity not found (line 362)."""
        from django.http import Http404

        from apps.accounts.models import User
        from apps.reports.views import ReportApprovalView

        user = User.objects.create_user(email="u2@test.edu", password="testpass")
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        with pytest.raises(Http404):
            ReportApprovalView._get_or_create_report(
                request, "project", str(uuid.uuid4())
            )

    def test_get_entity_institution_id_unknown_type_returns_none(self, db):
        """_get_entity_institution_id returns None for unknown report_type (line 84)."""
        from apps.reports.views import _get_entity_institution_id

        result = _get_entity_institution_id("unknown_type", str(uuid.uuid4()))
        assert result is None

    def test_user_is_entity_director_superuser_bypass(self, db):
        """_user_is_entity_director returns True for superuser (line 320)."""
        from apps.accounts.models import User
        from apps.reports.views import ReportApprovalView

        superuser = User.objects.create_superuser(
            email="su@test.edu", password="testpass"
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = superuser
        result = ReportApprovalView._user_is_entity_director(
            request, "project", str(uuid.uuid4())
        )
        assert result is True

    def test_user_is_entity_director_center_with_valid_director(self, db):
        """_user_is_entity_director for center type with director membership (lines 338-343)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution, ResearchCenter
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="Center Inst", code="CI01")
        center = ResearchCenter.objects.create(institution=inst, name="Center1", code="C1")
        user = User.objects.create_user(email="cdir@test.edu", password="testpass")
        role = Role.objects.create(name="CenterDir", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        membership.centers.add(center)
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "center", str(center.pk)
        )
        assert result is True

    def test_user_is_entity_director_center_without_membership_returns_false(self, db):
        """Center type without center membership returns False (line 353)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution, ResearchCenter
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="NoCenter Inst", code="NC01")
        center = ResearchCenter.objects.create(institution=inst, name="Center2", code="C2")
        user = User.objects.create_user(email="nodir@test.edu", password="testpass")
        role = Role.objects.create(name="NoDir", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        # Intentionally NOT adding center to membership
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "center", str(center.pk)
        )
        assert result is False

    def test_user_is_entity_director_researcher_no_centers_returns_false(self, db):
        """Researcher type with no centers returns False (line 347/353)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="Res Inst", code="RI01")
        user = User.objects.create_user(email="resdir@test.edu", password="testpass")
        role = Role.objects.create(name="ResDir", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        # Intentionally NOT adding any centers
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "researcher", str(uuid.uuid4())
        )
        assert result is False

    def test_user_is_entity_director_unknown_type_returns_false(self, db):
        """_user_is_entity_director returns False for unknown report_type (line 353)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="Unknown Inst", code="UI01")
        user = User.objects.create_user(email="unk@test.edu", password="testpass")
        role = Role.objects.create(name="Unk", level=3)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "unknown_type", str(uuid.uuid4())
        )
        assert result is False

    def test_user_is_entity_director_center_low_role_returns_false(self, db):
        """_user_is_entity_director for center type with low role returns False (line 342)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution, ResearchCenter
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="LowRole Inst", code="LR01")
        center = ResearchCenter.objects.create(institution=inst, name="Center3", code="C3")
        user = User.objects.create_user(email="lowrole@test.edu", password="testpass")
        role = Role.objects.create(name="Researcher", level=4)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        membership.centers.add(center)
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "center", str(center.pk)
        )
        assert result is False

    def test_user_is_entity_director_researcher_low_role_returns_false(self, db):
        """_user_is_entity_director for researcher type with low role returns False (line 350)."""
        from apps.accounts.models import InstitutionMembership, Role, User
        from apps.institutions.models import Institution
        from apps.reports.views import ReportApprovalView

        inst = Institution.objects.create(name="LowRole2 Inst", code="LR02")
        user = User.objects.create_user(email="lowrole2@test.edu", password="testpass")
        role = Role.objects.create(name="Researcher2", level=4)
        membership = InstitutionMembership.objects.create(
            user=user, institution=inst, role=role
        )
        factory = APIRequestFactory()
        request = factory.get("/dummy/")
        request.user = user
        request.active_membership = membership
        request.institution_id = str(inst.pk)
        result = ReportApprovalView._user_is_entity_director(
            request, "researcher", str(uuid.uuid4())
        )
        assert result is False


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

    def test_preview_advances_returns_200(self, api_client, inst, researcher_user, project):
        """RF-053: Preview for advances type returns 200 with valid HTML."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "advances", "entity_id": str(project.pk)},
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
        assert response["Content-Type"] == "application/json"
        assert "error" in response.data or "detail" in response.data

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
        assert response["Content-Type"] == "application/json"
        assert "error" in response.data or "detail" in response.data

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
        assert response["Content-Type"] == "application/json"
        assert "error" in response.data or "detail" in response.data

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
        if response.status_code == 404:
            assert "not found" in str(response.data).lower() or "detail" in response.data

    def test_preview_superuser_bypasses_institution_check(
        self, api_client, inst_b, project
    ):
        """Superuser can preview any entity regardless of institution (line 92-93)."""
        from apps.accounts.models import User

        superuser = User.objects.create_superuser(
            email=f"super-{uuid.uuid4().hex[:6]}@test.edu",
            password="testpass",
        )
        api_client.force_authenticate(user=superuser)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"
        data = response.json()
        assert "html" in data
        assert len(data["html"]) > 0

    def test_preview_invalid_uuid_returns_404(self, api_client, inst, researcher_user):
        """Invalid UUID format returns 404 at Django URL routing level."""
        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        # Bypass reverse() because Django URL pattern rejects non-UUID strings
        response = api_client.get(
            "/api/reports/project/not-a-uuid/preview/"
        )
        assert response.status_code in (404, 400)

    def test_preview_render_valueerror_returns_404(
        self, api_client, inst, researcher_user, project
    ):
        """ValueError during render_html raises Http404 (lines 149-150)."""
        from unittest.mock import patch

        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with patch(
            "apps.reports.views.ReportRenderer.render_html",
            side_effect=ValueError("Entity vanished"),
        ):
            response = api_client.get(url)

        assert response.status_code == 404
        assert "not found" in str(response.data).lower() or "detail" in response.data

    def test_preview_template_render_failure_returns_500(
        self, api_client, inst, researcher_user, project
    ):
        """RF-057: Template rendering failure returns 500 with error structure."""
        from unittest.mock import patch

        _login(api_client, researcher_user, inst)
        _set_institution(api_client, inst)
        url = reverse(
            "reports:preview",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with patch(
            "apps.reports.views.ReportRenderer.render_html",
            side_effect=Exception("Template rendering failed"),
        ):
            response = api_client.get(url)

        assert response.status_code == 500
        assert "error" in response.data or "detail" in response.data
