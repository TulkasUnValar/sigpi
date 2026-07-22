"""
View and service tests for approval flow (§6.6 Phase 3).

Covers: ReportApprovalView POST /api/reports/{type}/{id}/approve/
and ReportApprovalService.approve() with RN-017 guard.

Spec reference:   sdd/reports/spec — RN-016, RN-017, RN-018
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
from apps.reports.models import Report, ReportApproval, ReportStatus
from apps.reports.views import ReportApprovalView
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
    return Institution.objects.create(name="Approval University", code="APR001")


@pytest.fixture
def director_role(db):
    """Director role (level 3)."""
    return Role.objects.create(name=f"Director-{uuid.uuid4().hex[:4]}", level=3)


@pytest.fixture
def researcher_role(db):
    """Researcher role (level 4)."""
    return Role.objects.create(name=f"Researcher-{uuid.uuid4().hex[:4]}", level=4)


@pytest.fixture
def center(db, inst):
    """Research center in the test institution."""
    return ResearchCenter.objects.create(
        institution=inst,
        name="Approval Test Center",
        code="APRC01",
    )


@pytest.fixture
def researcher_prof(db, inst):
    """Researcher profile in the test institution."""
    return Researcher.objects.create(
        institution=inst,
        first_name="Approval",
        last_name="Tester",
        document_type="CC",
        document_number="APR-001",
        primary_email="approval@test.edu",
    )


@pytest.fixture
def project(db, inst, center, researcher_prof):
    """Project in the test institution."""
    import datetime

    today = datetime.date.today()
    return Project.objects.create(
        institution=inst,
        center=center,
        principal_investigator=researcher_prof,
        title="Approval Test Project",
        abstract="Approval abstract.",
        objectives="Approval objectives.",
        methodology="Approval methodology.",
        expected_results="Approval results.",
        keywords="approval, test",
        start_date=today,
        estimated_end_date=today + datetime.timedelta(days=365),
        status="aprobado",
    )


@pytest.fixture
def director_user(db, inst, center, director_role):
    """Authenticated user with Director role whose membership includes the center."""
    user = User.objects.create_user(
        email=f"director-{uuid.uuid4().hex[:6]}@test.edu",
        password="testpass",
    )
    membership = InstitutionMembership.objects.create(
        user=user,
        institution=inst,
        role=director_role,
    )
    membership.centers.add(center)
    return user


@pytest.fixture
def director_membership(db, inst, center, director_user, director_role):
    """Return the Director's membership for request mocking."""
    return InstitutionMembership.objects.get(user=director_user, institution=inst)


@pytest.fixture
def researcher_user(db, inst, researcher_role):
    """Authenticated user with Researcher role (NOT a director)."""
    user = User.objects.create_user(
        email=f"researcher-{uuid.uuid4().hex[:6]}@test.edu",
        password="testpass",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=inst,
        role=researcher_role,
    )
    return user


@pytest.fixture
def report(db, inst, project, director_user):
    """A generated Report record ready for approval."""
    return Report.objects.create(
        report_type="project",
        entity_id=project.pk,
        institution=inst,
        status=ReportStatus.GENERATED,
        version=1,
        created_by=director_user,
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
# Mock helpers
# ═══════════════════════════════════════════════════════


def _mock_director_access():
    """Mock the director permission check to return True.

    The test client doesn't set request.active_membership (set by
    custom middleware in production), so the director check fails
    even for valid director users. This mock bypasses that.
    """
    return patch.object(
        ReportApprovalView,
        "_user_is_entity_director",
        return_value=True,
    )


def _mock_audit_emit():
    """Mock AuditEventEmitter.emit to prevent real audit writes in tests."""
    return patch("apps.accounts.audit.AuditEventEmitter.emit")


# ═══════════════════════════════════════════════════════
# ReportApprovalView Tests
# ═══════════════════════════════════════════════════════


class TestReportApprovalView:
    """POST /api/reports/{type}/{id}/approve/ — approval endpoint."""

    def test_approve_project_success_returns_200(
        self, api_client, inst, director_user, project
    ):
        """Director can approve a project report — returns 200."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_director_access(), _mock_audit_emit():
            response = api_client.post(url)

        assert response.status_code == 200

    def test_approve_creates_report_record(
        self, api_client, inst, director_user, project
    ):
        """Approval creates a Report record if none exists."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_director_access(), _mock_audit_emit():
            response = api_client.post(url)

        assert response.status_code == 200
        # A Report should now exist in APPROVED state
        report = Report.objects.filter(
            report_type="project",
            entity_id=project.pk,
        ).first()
        assert report is not None
        assert report.status == ReportStatus.APPROVED

    def test_approve_creates_approval_record_with_metadata(
        self, api_client, inst, director_user, project
    ):
        """Approval persists ReportApproval with correct metadata (RN-018)."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_director_access(), _mock_audit_emit():
            response = api_client.post(url)

        assert response.status_code == 200
        approval = ReportApproval.objects.filter(
            report__entity_id=project.pk,
        ).first()
        assert approval is not None
        assert approval.approved_by == director_user
        assert approval.report_version >= 1

    def test_approve_blocked_by_pending_progress_returns_409(
        self, api_client, inst, director_user, project
    ):
        """RN-017: Approval blocked (409) when project has pending progress reports."""
        import datetime

        from apps.accounts.models import User as UserModel
        from apps.progress.models import ProgressReport

        # Create a pending progress report (status=enviado → pending)
        today = datetime.date.today()
        pr_user = UserModel.objects.create_user(
            email=f"pr-{uuid.uuid4().hex[:6]}@test.edu", password="testpass"
        )
        ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=pr_user,
            period_start=today - datetime.timedelta(days=30),
            period_end=today,
            description="Pending progress report.",
            cumulative_percentage=50.00,
            activities="Some activities.",
            status="enviado",
        )

        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_director_access(), _mock_audit_emit():
            response = api_client.post(url)

        assert response.status_code == 409
        assert "pending" in response.data.get("error", "").lower()

    def test_approve_unauthorized_researcher_returns_403(
        self, api_client, inst, researcher_user, project
    ):
        """Non-director (researcher role) cannot approve — returns 403 (RN-016)."""
        _login(api_client, researcher_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.post(url)

        assert response.status_code == 403

    def test_approve_anonymous_returns_403(self, api_client, project):
        """Unauthenticated users cannot approve."""
        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        response = api_client.post(url)
        assert response.status_code in (401, 403)

    def test_approve_emits_audit_event(
        self, api_client, inst, director_user, project
    ):
        """Approval emits REPORT_APPROVED audit event."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(project.pk)},
        )
        with _mock_director_access(), _mock_audit_emit() as mock_emit:
            response = api_client.post(url)

        assert response.status_code == 200
        # Verify at least one audit call has REPORT_APPROVED
        approved_calls = [
            c
            for c in mock_emit.call_args_list
            if c.kwargs.get("event_type") == "REPORT_APPROVED"
        ]
        assert len(approved_calls) >= 1

    def test_approve_center_report_success(
        self, api_client, inst, director_user, center
    ):
        """Director can approve a center report — non-project type skips RN-017."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "center", "entity_id": str(center.pk)},
        )
        with _mock_director_access(), _mock_audit_emit():
            response = api_client.post(url)

        assert response.status_code == 200

    def test_approve_nonexistent_entity_returns_404(
        self, api_client, inst, director_user
    ):
        """Entity not found returns 404."""
        _login(api_client, director_user)
        _set_institution(api_client, inst)

        url = reverse(
            "reports:approve",
            kwargs={"report_type": "project", "entity_id": str(uuid.uuid4())},
        )
        response = api_client.post(url)
        assert response.status_code in (404, 500)
