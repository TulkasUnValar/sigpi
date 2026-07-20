"""
Integration tests for projects ViewSets — STRICT TDD (RED phase).

Tests define the expected behavior of 5 ViewSets per spec:
- ProjectViewSet: CRUD + 16 FSM actions + filtering
- ProjectMemberViewSet: nested under project, CRUD
- ProjectDocumentViewSet: nested under project, CRUD
- ProjectObservationViewSet: read-only list
- ProjectStateLogViewSet: read-only list

Error cases: 400 missing PI, 400 PI not affiliated, 403 terminal mutation,
409 duplicate member, 403 wrong role.

Spec reference: openspec/changes/projects/spec.md — API Contract
Design reference: openspec/changes/projects/design.md — ViewSets & Permissions
"""

import datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)
from apps.researchers.models import Researcher, ResearcherAffiliation

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


_doc_counter = 0


def _make_researcher(institution, user=None, **kwargs):
    """Create a researcher with minimal required fields."""
    global _doc_counter
    _doc_counter += 1
    defaults = {
        "first_name": "Alice",
        "last_name": "Smith",
        "document_type": "CC",
        "document_number": f"RES-{_doc_counter:06d}",
        "primary_email": f"alice-{_doc_counter}@test.edu",
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
        "title": "Test Project",
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
        institution=institution, name="AI Lab", code="AI"
    )


@pytest.fixture
def superadmin_role(db):
    return Role.objects.get(name="Superadmin")


@pytest.fixture
def admin_role(db):
    return Role.objects.get(name="Admin Institucional")


@pytest.fixture
def director_role(db):
    return Role.objects.get(name="Director de Centro")


@pytest.fixture
def researcher_role(db):
    return Role.objects.get(name="Investigador")


@pytest.fixture
def auditor_role(db):
    return Role.objects.get(name="Auditor")


@pytest.fixture
def superadmin_user(db, institution, superadmin_role):
    user = User.objects.create_user(
        email="sa@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=superadmin_role, is_active=True
    )
    return user


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(
        email="admin@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def director_user(db, institution, center, director_role):
    user = User.objects.create_user(
        email="dir@test.edu", auth_source="local", password="p"
    )
    membership = InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    membership.centers.add(center)
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(
        email="res@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_pi(db, institution, researcher_user, center):
    """Researcher profile for the PI user, affiliated with center."""
    pi = _make_researcher(
        institution,
        user=researcher_user,
        document_number="PI000001",
        primary_email="res@test.edu",
    )
    ResearcherAffiliation.objects.create(
        researcher=pi, center=center, is_primary=True
    )
    return pi


@pytest.fixture
def researcher2_user(db, institution, researcher_role):
    """Second researcher user for co-investigator tests."""
    user = User.objects.create_user(
        email="res2@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_coi(db, institution, researcher2_user, center):
    """Second researcher for co-investigator role."""
    coi = _make_researcher(
        institution,
        user=researcher2_user,
        document_number="COI00001",
        primary_email="res2@test.edu",
    )
    ResearcherAffiliation.objects.create(
        researcher=coi, center=center, is_primary=True
    )
    return coi


@pytest.fixture
def auditor_user(db, institution, auditor_role):
    user = User.objects.create_user(
        email="aud@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=auditor_role, is_active=True
    )
    return user


@pytest.fixture
def project_borrador(db, institution, center, researcher_pi):
    """Project in borrador state owned by researcher_pi."""
    return _make_project(institution, center, researcher_pi, status="borrador")


@pytest.fixture
def project_enviado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="enviado")


@pytest.fixture
def project_en_revision(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="en_revision")


@pytest.fixture
def project_observado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="observado")


@pytest.fixture
def project_aprobado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="aprobado")


@pytest.fixture
def project_en_ejecucion(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="en_ejecucion")


@pytest.fixture
def project_suspendido(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="suspendido")


@pytest.fixture
def project_finalizado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="finalizado")


@pytest.fixture
def project_en_cierre(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="en_cierre")


@pytest.fixture
def project_cerrado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="cerrado")


@pytest.fixture
def project_cancelado(db, institution, center, researcher_pi):
    return _make_project(institution, center, researcher_pi, status="cancelado")


# ════════════════════════════════════════════════════════
# ProjectViewSet — CRUD
# ════════════════════════════════════════════════════════


class TestProjectViewSetCRUD:
    """CRUD operations on /projects/"""

    def test_list_as_researcher(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("projects:project-list"))
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) >= 1
        titles = [p["title"] for p in data["results"]]
        assert project_borrador.title in titles

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("projects:project-list"))
        assert r.status_code in (401, 403)

    def test_create_as_researcher(
        self, api_client, institution, researcher_user, center, researcher_pi
    ):
        _login(api_client, researcher_user, institution)
        today = datetime.date.today()
        r = api_client.post(
            reverse("projects:project-list"),
            {
                "center": str(center.pk),
                "principal_investigator": str(researcher_pi.pk),
                "title": "New Project",
                "abstract": "Abstract text",
                "objectives": "Objectives text",
                "methodology": "Methodology text",
                "expected_results": "Results text",
                "keywords": "kw1, kw2",
                "start_date": str(today),
                "estimated_end_date": str(today + datetime.timedelta(days=90)),
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "New Project"
        assert data["status"] == "borrador"

    def test_create_denied_for_auditor(
        self, api_client, institution, auditor_user, center, researcher_pi
    ):
        _login(api_client, auditor_user, institution)
        today = datetime.date.today()
        r = api_client.post(
            reverse("projects:project-list"),
            {
                "center": str(center.pk),
                "principal_investigator": str(researcher_pi.pk),
                "title": "Denied",
                "abstract": "x",
                "objectives": "x",
                "methodology": "x",
                "expected_results": "x",
                "start_date": str(today),
                "estimated_end_date": str(today + datetime.timedelta(days=90)),
            },
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_retrieve_as_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == project_borrador.title
        assert "members" in data
        assert "documents" in data

    def test_update_as_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.patch(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(project_borrador.pk)},
            ),
            {"title": "Updated Title"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Title"
        project_borrador.refresh_from_db()
        assert project_borrador.title == "Updated Title"

    def test_update_denied_for_auditor(
        self, api_client, institution, auditor_user, project_borrador
    ):
        _login(api_client, auditor_user, institution)
        r = api_client.patch(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(project_borrador.pk)},
            ),
            {"title": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_delete_borrador_as_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.delete(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 204
        assert not Project.objects.filter(pk=project_borrador.pk).exists()

    def test_delete_cerrado_denied(
        self, api_client, institution, researcher_user, project_cerrado
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.delete(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(project_cerrado.pk)},
            )
        )
        assert r.status_code in (403, 400)


# ════════════════════════════════════════════════════════
# ProjectViewSet — FSM Actions
# ════════════════════════════════════════════════════════


class TestProjectFSMActions:
    """16 FSM action endpoints on ProjectViewSet."""

    # ── submit (borrador → enviado) ──────────────────────

    def test_submit_as_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-submit",
                kwargs={"pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        project_borrador.refresh_from_db()
        assert project_borrador.status == "enviado"

    def test_submit_denied_for_auditor(
        self, api_client, institution, auditor_user, project_borrador
    ):
        _login(api_client, auditor_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-submit",
                kwargs={"pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code in (403, 401)

    def test_submit_from_wrong_state(
        self, api_client, institution, researcher_user, project_enviado
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-submit",
                kwargs={"pk": str(project_enviado.pk)},
            )
        )
        assert r.status_code == 400

    # ── accept_review (enviado → en_revision) ────────────

    def test_accept_review_as_director(
        self, api_client, institution, director_user, project_enviado
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-accept-review",
                kwargs={"pk": str(project_enviado.pk)},
            )
        )
        assert r.status_code == 200
        project_enviado.refresh_from_db()
        assert project_enviado.status == "en_revision"

    def test_accept_review_denied_for_pi(
        self, api_client, institution, researcher_user, project_enviado
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-accept-review",
                kwargs={"pk": str(project_enviado.pk)},
            )
        )
        assert r.status_code in (403, 401)

    # ── approve (en_revision → aprobado) ─────────────────

    def test_approve_as_director(
        self, api_client, institution, director_user, project_en_revision
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-approve",
                kwargs={"pk": str(project_en_revision.pk)},
            )
        )
        assert r.status_code == 200
        project_en_revision.refresh_from_db()
        assert project_en_revision.status == "aprobado"

    # ── observe (en_revision → observado) ────────────────

    def test_observe_as_director(
        self, api_client, institution, director_user, project_en_revision
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-observe",
                kwargs={"pk": str(project_en_revision.pk)},
            ),
            {"observation_text": "Needs more detail in methodology."},
            content_type="application/json",
        )
        assert r.status_code == 200
        project_en_revision.refresh_from_db()
        assert project_en_revision.status == "observado"
        assert ProjectObservation.objects.filter(
            project=project_en_revision,
            observation_text="Needs more detail in methodology.",
        ).exists()

    # ── return_to_draft (en_revision → borrador) ─────────

    def test_return_to_draft_as_director(
        self, api_client, institution, director_user, project_en_revision
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-return-to-draft",
                kwargs={"pk": str(project_en_revision.pk)},
            )
        )
        assert r.status_code == 200
        project_en_revision.refresh_from_db()
        assert project_en_revision.status == "borrador"

    # ── reject (en_revision → rechazado) ─────────────────

    def test_reject_as_director(
        self, api_client, institution, director_user, project_en_revision
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-reject",
                kwargs={"pk": str(project_en_revision.pk)},
            )
        )
        assert r.status_code == 200
        project_en_revision.refresh_from_db()
        assert project_en_revision.status == "rechazado"

    # ── resubmit (observado → enviado) ───────────────────

    def test_resubmit_as_pi(
        self, api_client, institution, researcher_user, project_observado
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-resubmit",
                kwargs={"pk": str(project_observado.pk)},
            )
        )
        assert r.status_code == 200
        project_observado.refresh_from_db()
        assert project_observado.status == "enviado"

    def test_resubmit_denied_for_auditor(
        self, api_client, institution, auditor_user, project_observado
    ):
        _login(api_client, auditor_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-resubmit",
                kwargs={"pk": str(project_observado.pk)},
            )
        )
        assert r.status_code in (403, 401)

    # ── start_execution (aprobado → en_ejecucion) ────────

    def test_start_execution_as_admin(
        self, api_client, institution, admin_user, project_aprobado
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-start-execution",
                kwargs={"pk": str(project_aprobado.pk)},
            )
        )
        assert r.status_code == 200
        project_aprobado.refresh_from_db()
        assert project_aprobado.status == "en_ejecucion"

    def test_start_execution_denied_for_pi(
        self, api_client, institution, researcher_user, project_aprobado
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-start-execution",
                kwargs={"pk": str(project_aprobado.pk)},
            )
        )
        assert r.status_code in (403, 401)

    # ── suspend (en_ejecucion → suspendido) ──────────────

    def test_suspend_as_director(
        self, api_client, institution, director_user, project_en_ejecucion
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-suspend",
                kwargs={"pk": str(project_en_ejecucion.pk)},
            ),
            {"reason": "Budget constraints."},
            content_type="application/json",
        )
        assert r.status_code == 200
        project_en_ejecucion.refresh_from_db()
        assert project_en_ejecucion.status == "suspendido"

    # ── resume (suspendido → en_ejecucion) ───────────────

    def test_resume_as_admin(
        self, api_client, institution, admin_user, project_suspendido
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-resume",
                kwargs={"pk": str(project_suspendido.pk)},
            )
        )
        assert r.status_code == 200
        project_suspendido.refresh_from_db()
        assert project_suspendido.status == "en_ejecucion"

    # ── finalize (en_ejecucion → finalizado) ─────────────

    def test_finalize_as_pi(
        self, api_client, institution, researcher_user, project_en_ejecucion
    ):
        _login(api_client, researcher_user, institution)
        actual_end = datetime.date.today()
        r = api_client.post(
            reverse(
                "projects:project-finalize",
                kwargs={"pk": str(project_en_ejecucion.pk)},
            ),
            {"actual_end_date": str(actual_end)},
            content_type="application/json",
        )
        assert r.status_code == 200
        project_en_ejecucion.refresh_from_db()
        assert project_en_ejecucion.status == "finalizado"
        assert project_en_ejecucion.actual_end_date == actual_end

    # ── initiate_closure (finalizado → en_cierre) ────────

    def test_initiate_closure_as_director(
        self, api_client, institution, director_user, project_finalizado
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-initiate-closure",
                kwargs={"pk": str(project_finalizado.pk)},
            )
        )
        assert r.status_code == 200
        project_finalizado.refresh_from_db()
        assert project_finalizado.status == "en_cierre"

    # ── close (en_cierre → cerrado) ─────────────────────

    def test_close_as_director(
        self, api_client, institution, director_user, project_en_cierre
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-close",
                kwargs={"pk": str(project_en_cierre.pk)},
            )
        )
        assert r.status_code == 200
        project_en_cierre.refresh_from_db()
        assert project_en_cierre.status == "cerrado"

    # ── cancel (any non-terminal → cancelado) ────────────

    def test_cancel_as_admin(
        self, api_client, institution, admin_user, project_borrador
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-cancel",
                kwargs={"pk": str(project_borrador.pk)},
            ),
            {"reason": "Budget reallocation."},
            content_type="application/json",
        )
        assert r.status_code == 200
        project_borrador.refresh_from_db()
        assert project_borrador.status == "cancelado"

    def test_cancel_denied_for_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-cancel",
                kwargs={"pk": str(project_borrador.pk)},
            ),
            {"reason": "I changed my mind."},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_cancel_from_terminal_denied(
        self, api_client, institution, admin_user, project_cerrado
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-cancel",
                kwargs={"pk": str(project_cerrado.pk)},
            ),
            content_type="application/json",
        )
        assert r.status_code == 400


# ════════════════════════════════════════════════════════
# ProjectMemberViewSet — nested under /projects/{pk}/members/
# ════════════════════════════════════════════════════════


class TestProjectMemberViewSet:
    """Nested member CRUD under /projects/{project_pk}/members/"""

    def test_list_members(
        self, api_client, institution, researcher_user, project_borrador,
        researcher_coi,
    ):
        ProjectMember.objects.create(
            project=project_borrador, researcher=researcher_coi,
            role="co_investigator",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-member-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1

    def test_add_member_as_pi(
        self, api_client, institution, researcher_user, project_borrador,
        researcher_coi,
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-member-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"researcher": str(researcher_coi.pk), "role": "co_investigator"},
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["researcher"] == str(researcher_coi.pk)
        assert data["role"] == "co_investigator"

    def test_add_member_denied_for_auditor(
        self, api_client, institution, auditor_user, project_borrador,
        researcher_coi,
    ):
        _login(api_client, auditor_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-member-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"researcher": str(researcher_coi.pk), "role": "co_investigator"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_update_member_role(
        self, api_client, institution, researcher_user, project_borrador,
        researcher_coi,
    ):
        member = ProjectMember.objects.create(
            project=project_borrador, researcher=researcher_coi, role="student"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.patch(
            reverse(
                "projects:project-member-detail",
                kwargs={
                    "project_pk": str(project_borrador.pk),
                    "pk": str(member.pk),
                },
            ),
            {"role": "collaborator"},
            content_type="application/json",
        )
        assert r.status_code == 200
        member.refresh_from_db()
        assert member.role == "collaborator"

    def test_remove_member(
        self, api_client, institution, researcher_user, project_borrador,
        researcher_coi,
    ):
        member = ProjectMember.objects.create(
            project=project_borrador, researcher=researcher_coi,
            role="collaborator",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.delete(
            reverse(
                "projects:project-member-detail",
                kwargs={
                    "project_pk": str(project_borrador.pk),
                    "pk": str(member.pk),
                },
            )
        )
        assert r.status_code == 204
        assert not ProjectMember.objects.filter(pk=member.pk).exists()

    def test_add_member_to_terminal_denied(
        self, api_client, institution, researcher_user, project_cerrado,
        researcher_coi,
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-member-list",
                kwargs={"project_pk": str(project_cerrado.pk)},
            ),
            {"researcher": str(researcher_coi.pk), "role": "co_investigator"},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_duplicate_member_rejected(
        self, api_client, institution, researcher_user, project_borrador,
        researcher_coi,
    ):
        ProjectMember.objects.create(
            project=project_borrador, researcher=researcher_coi,
            role="co_investigator",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-member-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"researcher": str(researcher_coi.pk), "role": "student"},
            content_type="application/json",
        )
        assert r.status_code == 400


# ════════════════════════════════════════════════════════
# ProjectDocumentViewSet — nested under /projects/{pk}/documents/
# ════════════════════════════════════════════════════════


class TestProjectDocumentViewSet:
    """Nested document CRUD under /projects/{project_pk}/documents/"""

    def test_list_documents(
        self, api_client, institution, researcher_user, project_borrador
    ):
        ProjectDocument.objects.create(
            project=project_borrador, name="test.pdf", doc_type="proposal",
            external_url="https://example.com/test.pdf",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-document-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1

    def test_add_document_as_pi(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-document-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {
                "name": "proposal_v2.pdf",
                "doc_type": "proposal",
                "external_url": "https://example.com/proposal.pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "proposal_v2.pdf"
        assert data["doc_type"] == "proposal"

    def test_update_document(
        self, api_client, institution, researcher_user, project_borrador
    ):
        doc = ProjectDocument.objects.create(
            project=project_borrador, name="old.pdf", doc_type="other",
            external_url="https://example.com/old.pdf",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.patch(
            reverse(
                "projects:project-document-detail",
                kwargs={
                    "project_pk": str(project_borrador.pk),
                    "pk": str(doc.pk),
                },
            ),
            {"name": "updated.pdf"},
            content_type="application/json",
        )
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.name == "updated.pdf"

    def test_remove_document(
        self, api_client, institution, researcher_user, project_borrador
    ):
        doc = ProjectDocument.objects.create(
            project=project_borrador, name="del.pdf", doc_type="other",
            external_url="https://example.com/del.pdf",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.delete(
            reverse(
                "projects:project-document-detail",
                kwargs={
                    "project_pk": str(project_borrador.pk),
                    "pk": str(doc.pk),
                },
            )
        )
        assert r.status_code == 204
        assert not ProjectDocument.objects.filter(pk=doc.pk).exists()


# ════════════════════════════════════════════════════════
# ProjectObservationViewSet — read-only list
# ════════════════════════════════════════════════════════


class TestProjectObservationViewSet:
    """Read-only observation list under /projects/{project_pk}/observations/"""

    def test_list_observations(
        self, api_client, institution, researcher_user, project_borrador
    ):
        ProjectObservation.objects.create(
            project=project_borrador, observation_text="Needs revision.",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-observation-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1

    def test_post_not_allowed(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-observation-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"observation_text": "Test"},
            content_type="application/json",
        )
        assert r.status_code in (405, 403, 401)

    def test_put_not_allowed(
        self, api_client, institution, researcher_user, project_borrador
    ):
        ProjectObservation.objects.create(
            project=project_borrador, observation_text="Test.",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.put(
            reverse(
                "projects:project-observation-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"observation_text": "Modified"},
            content_type="application/json",
        )
        # PUT on list endpoint should be 405 or 403
        assert r.status_code in (405, 403, 401)


# ════════════════════════════════════════════════════════
# ProjectStateLogViewSet — read-only list
# ════════════════════════════════════════════════════════


class TestProjectStateLogViewSet:
    """Read-only state history list under /projects/{project_pk}/state_history/"""

    def test_list_state_history(
        self, api_client, institution, researcher_user, project_borrador
    ):
        ProjectStateLog.objects.create(
            project=project_borrador, from_state="borrador", to_state="enviado",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-state-log-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            )
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1

    def test_post_not_allowed(
        self, api_client, institution, researcher_user, project_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "projects:project-state-log-list",
                kwargs={"project_pk": str(project_borrador.pk)},
            ),
            {"from_state": "borrador", "to_state": "enviado"},
            content_type="application/json",
        )
        assert r.status_code in (405, 403, 401)


# ════════════════════════════════════════════════════════
# Error Responses
# ════════════════════════════════════════════════════════


class TestProjectErrorResponses:
    """Verify error codes for business rule violations (spec §Error Handling)."""

    def test_missing_pi(
        self, api_client, institution, researcher_user, researcher_pi, center
    ):
        _login(api_client, researcher_user, institution)
        today = datetime.date.today()
        r = api_client.post(
            reverse("projects:project-list"),
            {
                "center": str(center.pk),
                "title": "No PI",
                "abstract": "x",
                "objectives": "x",
                "methodology": "x",
                "expected_results": "x",
                "start_date": str(today),
                "estimated_end_date": str(today + datetime.timedelta(days=90)),
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_pi_not_affiliated(
        self, api_client, institution, researcher_user, researcher_pi, center
    ):
        """Researcher without affiliation in the center should be rejected (RN-009)."""
        # Create a researcher NOT affiliated with the center
        unaffiliated = _make_researcher(
            institution,
            document_number="UNAFF001",
            primary_email="unaff@test.edu",
        )
        _login(api_client, researcher_user, institution)
        today = datetime.date.today()
        r = api_client.post(
            reverse("projects:project-list"),
            {
                "center": str(center.pk),
                "principal_investigator": str(unaffiliated.pk),
                "title": "Unaffiliated PI",
                "abstract": "x",
                "objectives": "x",
                "methodology": "x",
                "expected_results": "x",
                "start_date": str(today),
                "estimated_end_date": str(today + datetime.timedelta(days=90)),
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_cross_institution_access_denied(
        self, api_client, institution, researcher_user,
    ):
        """Project from another institution should be invisible/forbidden."""
        other_inst = Institution.objects.create(
            name="Other University", code="OU001"
        )
        other_center = ResearchCenter.objects.create(
            institution=other_inst, name="Other Lab", code="OL"
        )
        other_pi = _make_researcher(
            other_inst,
            document_number="CROSS01",
            primary_email="cross@test.edu",
        )
        other_project = _make_project(other_inst, other_center, other_pi)

        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "projects:project-detail",
                kwargs={"pk": str(other_project.pk)},
            )
        )
        assert r.status_code in (403, 404, 401)
