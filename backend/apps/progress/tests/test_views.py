"""
Integration tests for progress ViewSets — STRICT TDD (RED phase).

Tests define the expected behavior of 4 ViewSets per spec:
- ProgressViewSet: CRUD + 9 FSM actions + filtering
- ProgressDocumentViewSet: nested under progress, CRUD
- ProgressReviewViewSet: read-only list
- ProgressStateLogViewSet: read-only list
- Nested shortcut: /projects/{id}/progress/

Error cases: 400, 403, 404, 405 for read-only endpoints.

Test pattern (matches projects/tests/test_views.py):
- django.test.Client (not DRF APIClient) for full middleware stack
- client.force_login() + session institution_id for tenant context
- Real DB records for InstitutionMembership, Role, etc.

Spec reference:   openspec/sdd/advances/spec.md — API Contract
Design reference: openspec/sdd/advances/design.md — ViewSets & Permissions
"""
import datetime
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)
from apps.projects.models import (
    Project,
    ProjectMember,
)
from apps.researchers.models import Researcher, ResearcherAffiliation

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _result_list(response):
    """Extract list from a potentially paginated DRF response."""
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


_doc_counter = 0


def _make_researcher(institution, user=None, **kwargs):
    """Create a researcher with minimal required fields."""
    global _doc_counter
    _doc_counter += 1
    defaults = {
        "first_name": "Test",
        "last_name": f"Researcher{_doc_counter}",
        "document_type": "CC",
        "document_number": f"RES-{_doc_counter:06d}",
        "primary_email": f"researcher{_doc_counter}@test.edu",
        "user": user,
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


def _make_project(institution, center, pi, **kwargs):
    """Create a project with minimal required fields."""
    today = datetime.date.today()
    defaults = {
        "institution": institution,
        "center": center,
        "principal_investigator": pi,
        "title": f"Test Project {uuid.uuid4().hex[:6]}",
        "abstract": "Test abstract",
        "objectives": "Test objectives",
        "methodology": "Test methodology",
        "expected_results": "Test results",
        "keywords": "test, project",
        "start_date": today,
        "estimated_end_date": today + datetime.timedelta(days=365),
        "status": "borrador",
    }
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def center(db, institution):
    return ResearchCenter.objects.create(
        institution=institution,
        name="Engineering Center",
        code="ENG001",
    )


@pytest.fixture
def director_role(db):
    return Role.objects.create(
        name=f"Director Centro {uuid.uuid4().hex[:4]}", level=3
    )


@pytest.fixture
def researcher_role(db):
    return Role.objects.create(
        name=f"Investigador {uuid.uuid4().hex[:4]}", level=4
    )


@pytest.fixture
def director_user(db, institution, center, director_role):
    """Create a user with Director role in the center."""
    user = User.objects.create_user(
        email=f"director-{uuid.uuid4().hex[:8]}@test.edu",
        password="testpass123",
    )
    researcher = _make_researcher(institution, user=user)
    ResearcherAffiliation.objects.create(
        researcher=researcher, center=center, is_primary=True
    )
    membership = InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    membership.centers.add(center)
    return user


@pytest.fixture
def researcher_user(db, institution, center, researcher_role):
    """Create a user with Researcher role."""
    user = User.objects.create_user(
        email=f"researcher-{uuid.uuid4().hex[:8]}@test.edu",
        password="testpass123",
    )
    researcher = _make_researcher(institution, user=user)
    ResearcherAffiliation.objects.create(
        researcher=researcher, center=center, is_primary=True
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def pi_user(db, institution, center, researcher_role):
    """Create a PI user with Researcher role and researcher record."""
    user = User.objects.create_user(
        email=f"pi-{uuid.uuid4().hex[:8]}@test.edu",
        password="testpass123",
    )
    researcher = _make_researcher(institution, user=user)
    ResearcherAffiliation.objects.create(
        researcher=researcher, center=center, is_primary=True
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user, researcher


@pytest.fixture
def project(db, institution, center, pi_user):
    """Create a project with a PI."""
    user, pi = pi_user
    return _make_project(institution, center, pi)


@pytest.fixture
def report_borrador(db, institution, center, project, pi_user, api_client):
    """Create a progress report in borrador state via API."""
    user, pi = pi_user
    # Make the user a project member
    ProjectMember.objects.create(
        project=project,
        researcher=pi,
        role="principal_investigator",
    )
    _login(api_client, user, institution)

    url = reverse("progressreport-list")
    data = {
        "project": str(project.pk),
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "description": "Test report",
        "cumulative_percentage": "50.00",
        "activities": "Test activities",
    }
    response = api_client.post(url, data, content_type="application/json")
    assert response.status_code == 201, response.content
    return ProgressReport.objects.get(pk=response.json()["id"])


@pytest.fixture
def report_enviado(db, report_borrador, pi_user, api_client, institution):
    """Progress report in enviado state."""
    user, pi = pi_user
    _login(api_client, user, institution)

    url = reverse("progressreport-submit", args=[report_borrador.pk])
    response = api_client.post(url)
    assert response.status_code == 200, response.content
    report_borrador.refresh_from_db()
    return report_borrador


@pytest.fixture
def report_en_revision(db, report_enviado, director_user, api_client, institution):
    """Progress report in en_revision state."""
    _login(api_client, director_user, institution)

    url = reverse("progressreport-accept-review", args=[report_enviado.pk])
    response = api_client.post(url)
    assert response.status_code == 200, response.content
    report_enviado.refresh_from_db()
    return report_enviado


@pytest.fixture
def report_observado(db, report_en_revision, director_user, api_client, institution):
    """Progress report in observado state."""
    _login(api_client, director_user, institution)

    url = reverse("progressreport-observe", args=[report_en_revision.pk])
    response = api_client.post(
        url, {"review_text": "Need more detail"}, content_type="application/json"
    )
    assert response.status_code == 200, response.content
    report_en_revision.refresh_from_db()
    return report_en_revision


@pytest.fixture
def report_rechazado(db, report_en_revision, director_user, api_client, institution):
    """Progress report in rechazado state."""
    _login(api_client, director_user, institution)

    url = reverse("progressreport-reject", args=[report_en_revision.pk])
    response = api_client.post(
        url, {"review_text": "Data wrong"}, content_type="application/json"
    )
    assert response.status_code == 200, response.content
    report_en_revision.refresh_from_db()
    return report_en_revision


# ──────────────────────────────────────────────
# ProgressViewSet — List
# ──────────────────────────────────────────────


class TestProgressViewSetList:
    """GET /progress/ — list endpoint."""

    def test_list_returns_reports(self, api_client, institution,
                                   researcher_user, report_borrador):
        """GET /progress/ returns list of progress reports."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-list")
        response = api_client.get(url)

        assert response.status_code == 200
        data = _result_list(response)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_uses_list_serializer_fields(self, api_client, institution,
                                               researcher_user, report_borrador):
        """List response has only the 7 list serializer fields."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-list")
        response = api_client.get(url)

        item = _result_list(response)[0]
        list_fields = {"id", "project", "status", "cumulative_percentage",
                       "period_start", "period_end", "created_at"}
        assert set(item.keys()) == list_fields, f"Got: {set(item.keys())}"

    def test_list_institution_scoped(self, api_client, institution,
                                      researcher_user, report_borrador):
        """Reports from another institution are not visible."""
        other_inst = Institution.objects.create(
            code="OTHER", name="Other Institution"
        )
        ResearchCenter.objects.create(
            institution=other_inst, name="Other Center", code="OC001"
        )
        other_user = User.objects.create_user(
            email=f"other-{uuid.uuid4().hex[:8]}@test.edu",
            password="testpass123",
        )
        other_role = Role.objects.create(
            name=f"Other Researcher {uuid.uuid4().hex[:4]}", level=4
        )
        _make_researcher(other_inst, user=other_user)
        InstitutionMembership.objects.create(
            user=other_user, institution=other_inst, role=other_role, is_active=True
        )

        _login(api_client, other_user, other_inst)

        url = reverse("progressreport-list")
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(_result_list(response)) == 0  # No reports in this institution

    def test_list_unauthenticated_returns_redirect(self, api_client):
        """Unauthenticated GET returns redirect to login."""
        url = reverse("progressreport-list")
        response = api_client.get(url)
        assert response.status_code in (302, 401, 403)


# ──────────────────────────────────────────────
# ProgressViewSet — CRUD
# ──────────────────────────────────────────────


class TestProgressViewSetCRUD:
    """CRUD operations (create, retrieve, update, delete)."""

    def test_create_borrador(self, api_client, institution, pi_user, project):
        """POST /progress/ creates a borrador report."""
        user, pi = pi_user
        ProjectMember.objects.create(
            project=project, researcher=pi, role="principal_investigator"
        )
        _login(api_client, user, institution)

        url = reverse("progressreport-list")
        data = {
            "project": str(project.pk),
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
            "description": "Test create via API",
            "cumulative_percentage": "50.00",
            "activities": "Test activities",
        }
        response = api_client.post(url, data, content_type="application/json")

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "borrador"
        assert body["cumulative_percentage"] == "50.00"

    def test_create_missing_required_field_returns_400(self, api_client, institution,
                                                         pi_user, project):
        """POST without activities returns 400."""
        user, pi = pi_user
        ProjectMember.objects.create(
            project=project, researcher=pi, role="principal_investigator"
        )
        _login(api_client, user, institution)

        url = reverse("progressreport-list")
        data = {
            "project": str(project.pk),
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
            "description": "Test",
            "cumulative_percentage": "50.00",
            # missing activities
        }
        response = api_client.post(url, data, content_type="application/json")
        assert response.status_code == 400

    def test_retrieve_detail(self, api_client, institution, researcher_user,
                              report_borrador):
        """GET /progress/{id}/ returns full detail with nested data."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-detail", args=[report_borrador.pk])
        response = api_client.get(url)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "borrador"
        assert "documents" in body
        assert "reviews" in body
        assert "state_logs" in body

    def test_retrieve_not_found(self, api_client, institution, researcher_user):
        """GET with non-existent UUID returns 404."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-detail",
                      args=["00000000-0000-0000-0000-000000000000"])
        response = api_client.get(url)
        assert response.status_code == 404

    def test_update_borrador(self, api_client, institution, pi_user,
                              report_borrador):
        """PATCH borrador report succeeds."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-detail", args=[report_borrador.pk])
        response = api_client.patch(
            url, {"description": "Updated desc"}, content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["description"] == "Updated desc"

    def test_update_non_borrador_rejected(self, api_client, institution,
                                            pi_user, report_enviado):
        """PATCH on enviado returns 4xx (borrador guard)."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-detail", args=[report_enviado.pk])
        response = api_client.patch(
            url, {"description": "Cannot update"}, content_type="application/json"
        )

        assert response.status_code in (400, 403)

    def test_delete_borrador(self, api_client, institution, pi_user,
                              report_borrador):
        """DELETE borrador report succeeds."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-detail", args=[report_borrador.pk])
        response = api_client.delete(url)

        assert response.status_code == 204
        assert not ProgressReport.objects.filter(pk=report_borrador.pk).exists()

    def test_delete_non_borrador_rejected(self, api_client, institution,
                                            pi_user, report_enviado):
        """DELETE on enviado returns 403."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-detail", args=[report_enviado.pk])
        response = api_client.delete(url)

        assert response.status_code == 403


# ──────────────────────────────────────────────
# ProgressViewSet — FSM Actions
# ──────────────────────────────────────────────


class TestProgressViewSetFSM:
    """9 FSM action endpoints."""

    def test_submit_borrador_to_enviado(self, api_client, institution, pi_user,
                                         report_borrador):
        """POST submit/ transitions borrador → enviado."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-submit", args=[report_borrador.pk])
        response = api_client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == "enviado"

    def test_accept_review_to_en_revision(self, api_client, institution,
                                            director_user, report_enviado):
        """POST accept_review/ transitions enviado → en_revision."""
        _login(api_client, director_user, institution)

        url = reverse("progressreport-accept-review", args=[report_enviado.pk])
        response = api_client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == "en_revision"

    def test_accept_review_non_director_403(self, api_client, institution,
                                              researcher_user, report_enviado):
        """Non-director cannot accept_review."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-accept-review", args=[report_enviado.pk])
        response = api_client.post(url)

        assert response.status_code == 403

    def test_approve_to_aprobado(self, api_client, institution, director_user,
                                  report_en_revision):
        """POST approve/ transitions en_revision → aprobado + updates project."""
        _login(api_client, director_user, institution)

        url = reverse("progressreport-approve", args=[report_en_revision.pk])
        response = api_client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == "aprobado"
        # RN-P08: project cumulative_progress updated
        report_en_revision.project.refresh_from_db()
        assert report_en_revision.project.cumulative_progress == \
            report_en_revision.cumulative_percentage

    def test_approve_non_director_403(self, api_client, institution,
                                        researcher_user, report_en_revision):
        """Non-director cannot approve."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-approve", args=[report_en_revision.pk])
        response = api_client.post(url)

        assert response.status_code == 403

    def test_observe_to_observado(self, api_client, institution, director_user,
                                   report_en_revision):
        """POST observe/ + review_text → observado + ProgressReview."""
        _login(api_client, director_user, institution)

        url = reverse("progressreport-observe", args=[report_en_revision.pk])
        response = api_client.post(
            url, {"review_text": "Need more detail"}, content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "observado"
        assert ProgressReview.objects.filter(
            progress_report=report_en_revision,
            review_type="observation",
        ).exists()

    def test_reject_to_rechazado(self, api_client, institution, director_user,
                                  report_en_revision):
        """POST reject/ + review_text → rechazado + ProgressReview."""
        _login(api_client, director_user, institution)

        url = reverse("progressreport-reject", args=[report_en_revision.pk])
        response = api_client.post(
            url, {"review_text": "Data wrong"}, content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "rechazado"
        assert ProgressReview.objects.filter(
            progress_report=report_en_revision,
            review_type="rejection",
        ).exists()

    def test_return_to_draft_en_revision(self, api_client, institution,
                                            director_user, report_en_revision):
        """POST return_to_draft/ en_revision → borrador."""
        _login(api_client, director_user, institution)

        url = reverse("progressreport-return-to-draft",
                      args=[report_en_revision.pk])
        response = api_client.post(url, content_type="application/json")

        assert response.status_code == 200
        assert response.json()["status"] == "borrador"

    def test_return_to_draft_rechazado_by_creator(self, api_client, institution,
                                                   pi_user, report_rechazado):
        """POST return_to_draft/ rechazado → borrador by creator (PI)."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-return-to-draft",
                      args=[report_rechazado.pk])
        response = api_client.post(
            url, {"reason": "Fixing data"}, content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == "borrador"

    def test_return_to_draft_rechazado_by_non_creator_403(
        self, api_client, institution, researcher_user, report_rechazado,
    ):
        """Non-creator cannot return_to_draft from rechazado."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-return-to-draft",
                      args=[report_rechazado.pk])
        response = api_client.post(url, content_type="application/json")

        assert response.status_code == 403

    def test_resubmit_observado_to_enviado(self, api_client, institution, pi_user,
                                            report_observado):
        """POST resubmit/ observado → enviado."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-resubmit", args=[report_observado.pk])
        response = api_client.post(url)

        assert response.status_code == 200
        assert response.json()["status"] == "enviado"

    def test_state_log_created_on_transition(self, api_client, institution,
                                               pi_user, report_borrador):
        """Every FSM action creates a ProgressStateLog."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-submit", args=[report_borrador.pk])
        response = api_client.post(url)

        assert response.status_code == 200
        assert ProgressStateLog.objects.filter(
            progress_report=report_borrador,
            from_state="borrador",
            to_state="enviado",
        ).exists()


# ──────────────────────────────────────────────
# ProgressViewSet — Filtering
# ──────────────────────────────────────────────


class TestProgressViewSetFiltering:
    """Filtering via query params."""

    def test_filter_by_status(self, api_client, institution, researcher_user,
                               report_borrador):
        """?status=borrador returns only borrador reports."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-list") + "?status=borrador"
        response = api_client.get(url)

        assert response.status_code == 200
        for item in _result_list(response):
            assert item["status"] == "borrador"

    def test_filter_by_project(self, api_client, institution, researcher_user,
                                report_borrador):
        """?project={id} returns only reports for that project."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-list") + \
            f"?project={report_borrador.project_id}"
        response = api_client.get(url)

        assert response.status_code == 200
        for item in _result_list(response):
            assert item["project"] == str(report_borrador.project_id)

    def test_filter_by_period_after_no_results(self, api_client, institution,
                                                  researcher_user, report_borrador):
        """?period_start_after= far future returns empty list."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-list") + "?period_start_after=2027-01-01"
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(_result_list(response)) == 0


# ──────────────────────────────────────────────
# ProgressDocumentViewSet — nested CRUD
# ──────────────────────────────────────────────


class TestProgressDocumentViewSet:
    """Nested CRUD for documents under /progress/{id}/documents/."""

    def test_list_documents(self, api_client, institution, pi_user,
                             report_borrador):
        """GET /progress/{id}/documents/ returns list."""
        user, pi = pi_user
        # Create a document first
        ProgressDocument.objects.create(
            progress_report=report_borrador,
            name="Test Doc",
            doc_type="evidence",
        )
        _login(api_client, user, institution)

        url = reverse("progressreport-documents-list",
                      args=[report_borrador.pk])
        response = api_client.get(url)

        assert response.status_code == 200
        data = _result_list(response)
        assert len(data) >= 1

    def test_create_document(self, api_client, institution, pi_user,
                              report_borrador):
        """POST /progress/{id}/documents/ creates a document."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-documents-list",
                      args=[report_borrador.pk])
        data = {
            "name": "Evidence Q1",
            "doc_type": "evidence",
            "external_url": "https://example.com/ev.pdf",
        }
        response = api_client.post(url, data, content_type="application/json")

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["name"] == "Evidence Q1"
        assert body["doc_type"] == "evidence"

    def test_create_document_on_non_borrador_rejected(self, api_client, institution,
                                                        pi_user,
                                                        report_enviado):
        """POST on enviado report returns 403."""
        user, pi = pi_user
        _login(api_client, user, institution)

        url = reverse("progressreport-documents-list",
                      args=[report_enviado.pk])
        data = {"name": "Doc", "doc_type": "evidence"}
        response = api_client.post(url, data, content_type="application/json")

        assert response.status_code == 403

    def test_update_document(self, api_client, institution, pi_user,
                              report_borrador):
        """PATCH document updates name."""
        user, pi = pi_user
        doc = ProgressDocument.objects.create(
            progress_report=report_borrador,
            name="Original",
            doc_type="evidence",
        )
        _login(api_client, user, institution)

        url = reverse("progressreport-documents-detail",
                      args=[report_borrador.pk, doc.pk])
        response = api_client.patch(
            url, {"name": "Updated"}, content_type="application/json"
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_document(self, api_client, institution, pi_user,
                              report_borrador):
        """DELETE document removes it."""
        user, pi = pi_user
        doc = ProgressDocument.objects.create(
            progress_report=report_borrador,
            name="To Delete",
            doc_type="evidence",
        )
        _login(api_client, user, institution)

        url = reverse("progressreport-documents-detail",
                      args=[report_borrador.pk, doc.pk])
        response = api_client.delete(url)

        assert response.status_code == 204
        assert not ProgressDocument.objects.filter(pk=doc.pk).exists()


# ──────────────────────────────────────────────
# ProgressReviewViewSet — read-only
# ──────────────────────────────────────────────


class TestProgressReviewViewSet:
    """Read-only review list under /progress/{id}/reviews/."""

    def test_list_reviews(self, api_client, institution, researcher_user,
                           report_borrador):
        """GET /progress/{id}/reviews/ returns review list."""
        ProgressReview.objects.create(
            progress_report=report_borrador,
            review_text="Test review",
            review_type="observation",
        )
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-reviews-list",
                      args=[report_borrador.pk])
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_post_review_rejected(self, api_client, institution, researcher_user,
                                   report_borrador):
        """POST /progress/{id}/reviews/ returns 405."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-reviews-list",
                      args=[report_borrador.pk])
        response = api_client.post(
            url, {"review_text": "Test"}, content_type="application/json"
        )

        assert response.status_code == 405

    def test_delete_review_rejected(self, api_client, institution, researcher_user,
                                     report_borrador):
        """DELETE on a review returns 405."""
        review = ProgressReview.objects.create(
            progress_report=report_borrador,
            review_text="Test",
            review_type="observation",
        )
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-reviews-detail",
                      args=[report_borrador.pk, review.pk])
        response = api_client.delete(url)

        assert response.status_code == 405


# ──────────────────────────────────────────────
# ProgressStateLogViewSet — read-only
# ──────────────────────────────────────────────


class TestProgressStateLogViewSet:
    """Read-only state log list under /progress/{id}/state_history/."""

    def test_list_state_logs(self, api_client, institution, researcher_user,
                              report_borrador):
        """GET /progress/{id}/state_history/ returns state log list."""
        ProgressStateLog.objects.create(
            progress_report=report_borrador,
            from_state="borrador",
            to_state="enviado",
        )
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-state-history-list",
                      args=[report_borrador.pk])
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_post_state_log_rejected(self, api_client, institution,
                                       researcher_user, report_borrador):
        """POST /progress/{id}/state_history/ returns 405."""
        _login(api_client, researcher_user, institution)

        url = reverse("progressreport-state-history-list",
                      args=[report_borrador.pk])
        response = api_client.post(
            url, {"from_state": "x"}, content_type="application/json"
        )

        assert response.status_code == 405


# ──────────────────────────────────────────────
# Nested routing: /projects/{id}/progress/
# ──────────────────────────────────────────────


class TestNestedProjectProgress:
    """Nested shortcut /projects/{id}/progress/."""

    def test_nested_project_progress_list(self, api_client, institution,
                                            researcher_user, report_borrador):
        """GET /projects/{id}/progress/ returns reports for project."""
        _login(api_client, researcher_user, institution)

        url = reverse("project-progress-list",
                      args=[report_borrador.project_id])
        response = api_client.get(url)

        assert response.status_code == 200
        results = _result_list(response)
        assert isinstance(results, list)

    def test_nested_project_progress_scoped(self, api_client, institution,
                                              researcher_user, report_borrador,
                                              pi_user, project):
        """Nested route returns only reports for the specified project."""
        # Create another report for a different project
        user2, pi2 = pi_user
        # pi2 is already the PI for 'project' fixture, so make another project
        other_center = ResearchCenter.objects.create(
            institution=institution, name="Other Center", code="OC002"
        )
        ResearcherAffiliation.objects.create(
            researcher=pi2, center=other_center
        )
        other_project = _make_project(institution, other_center, pi2)
        ProjectMember.objects.create(
            project=other_project, researcher=pi2, role="principal_investigator"
        )
        _login(api_client, user2, institution)
        data = {
            "project": str(other_project.pk),
            "period_start": "2026-02-01",
            "period_end": "2026-07-31",
            "description": "Other project report",
            "cumulative_percentage": "30.00",
            "activities": "Other activities",
        }
        resp = api_client.post(reverse("progressreport-list"), data,
                               content_type="application/json")
        assert resp.status_code == 201

        _login(api_client, researcher_user, institution)

        url = reverse("project-progress-list",
                      args=[report_borrador.project_id])
        response = api_client.get(url)

        assert response.status_code == 200
        for item in _result_list(response):
            assert item["project"] == str(report_borrador.project_id)
