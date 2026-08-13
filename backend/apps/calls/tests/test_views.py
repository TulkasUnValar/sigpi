"""
Integration tests for calls ViewSets — STRICT TDD (RED phase).

Tests define the expected behavior of 4 ViewSets per spec:
- CallViewSet: CRUD + 5 FSM actions + filtering
- CallDocumentViewSet: nested under call, CRUD
- CallProjectViewSet: nested under call, CRUD with state guard
- CallStateLogViewSet: read-only list

Error cases: 400 validation, 403 permission, 404 not found, 409 invalid transition/duplicate.

Spec reference: openspec/changes/calls/spec.md — API Contract
Design reference: openspec/changes/calls/design.md — ViewSets & Permissions
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.calls.models import Call, CallDocument, CallProject, CallStateLog
from apps.institutions.models import Institution

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def superadmin_role(db):
    return get_role("Superadmin")


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
def auditor_role(db):
    return get_role("Auditor")


@pytest.fixture
def superadmin_user(db, institution, superadmin_role):
    user = User.objects.create_user(email="sa@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=superadmin_role, is_active=True
    )
    return user


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(email="admin@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def director_user(db, institution, director_role):
    user = User.objects.create_user(email="dir@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(email="res@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def auditor_user(db, institution, auditor_role):
    user = User.objects.create_user(email="aud@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=auditor_role, is_active=True
    )
    return user


@pytest.fixture
def call_borrador(db, institution):
    return Call.objects.create(
        institution=institution,
        title="Borrador Call",
        description="Desc",
        call_type="internal",
        status="borrador",
    )


@pytest.fixture
def call_abierta(db, institution):
    return Call.objects.create(
        institution=institution,
        title="Abierta Call",
        description="Desc",
        call_type="internal",
        status="abierta",
    )


@pytest.fixture
def call_cerrada(db, institution):
    return Call.objects.create(
        institution=institution,
        title="Cerrada Call",
        description="Desc",
        call_type="internal",
        status="cerrada",
    )


@pytest.fixture
def call_en_evaluacion(db, institution):
    return Call.objects.create(
        institution=institution,
        title="Eval Call",
        description="Desc",
        call_type="internal",
        status="en_evaluacion",
    )


@pytest.fixture
def call_resultados_publicados(db, institution):
    return Call.objects.create(
        institution=institution,
        title="Results Call",
        description="Desc",
        call_type="internal",
        status="resultados_publicados",
    )


@pytest.fixture
def project_not_linked(db, institution):
    from apps.projects.tests.conftest import ProjectFactory

    return ProjectFactory(institution=institution, title="Standalone Project")


# ════════════════════════════════════════════════════════
# CallViewSet — CRUD
# ════════════════════════════════════════════════════════


class TestCallViewSetCRUD:
    """CRUD operations on /api/calls/"""

    def test_list_as_researcher(self, api_client, institution, researcher_user, call_borrador):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-list"))
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert len(data["results"]) >= 1
        titles = [c["title"] for c in data["results"]]
        assert call_borrador.title in titles

    def test_list_as_superadmin_sees_all_calls(self, api_client, institution, superadmin_user):
        """Superadmin bypasses institution scoping in get_queryset (line 119)."""
        # Ensure Django superuser flag is set (get_queryset checks is_superuser, not role)
        superadmin_user.is_superuser = True
        superadmin_user.save(update_fields=["is_superuser"])
        other_inst = Institution.objects.create(name="Other", code="OT003")
        Call.objects.create(
            institution=other_inst,
            title="Other Call",
            description="Desc",
            call_type="internal",
            status="borrador",
        )
        _login(api_client, superadmin_user, institution)
        r = api_client.get(reverse("calls:call-list"))
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1
        titles = [c["title"] for c in data["results"]]
        assert "Other Call" in titles

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("calls:call-list"))
        assert r.status_code == 403

    def test_create_as_director(self, api_client, institution, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {
                "title": "New Call",
                "description": "Description",
                "call_type": "internal",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "New Call"
        assert data["status"] == "borrador"

    def test_create_rejects_external_without_entity(self, api_client, institution, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {
                "title": "Bad Call",
                "description": "Desc",
                "call_type": "external",
            },
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "external_entity" in r.json()

    def test_create_rejects_internal_with_entity(self, api_client, institution, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {
                "title": "Bad Call",
                "description": "Desc",
                "call_type": "internal",
                "external_entity": "CONAHCYT",
            },
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "external_entity" in r.json()

    def test_create_denied_for_researcher(self, api_client, institution, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {
                "title": "Denied",
                "description": "Desc",
                "call_type": "internal",
            },
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_retrieve_as_researcher(self, api_client, institution, researcher_user, call_borrador):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-detail", kwargs={"pk": str(call_borrador.pk)}))
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == call_borrador.title

    def test_update_as_director(self, api_client, institution, director_user, call_borrador):
        _login(api_client, director_user, institution)
        r = api_client.patch(
            reverse("calls:call-detail", kwargs={"pk": str(call_borrador.pk)}),
            {"title": "Updated Title"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Title"
        call_borrador.refresh_from_db()
        assert call_borrador.title == "Updated Title"

    def test_update_denied_for_researcher(
        self, api_client, institution, researcher_user, call_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.patch(
            reverse("calls:call-detail", kwargs={"pk": str(call_borrador.pk)}),
            {"title": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_delete_borrador_as_director(
        self, api_client, institution, director_user, call_borrador
    ):
        _login(api_client, director_user, institution)
        r = api_client.delete(reverse("calls:call-detail", kwargs={"pk": str(call_borrador.pk)}))
        assert r.status_code == 204
        assert not Call.objects.filter(pk=call_borrador.pk).exists()

    def test_delete_non_borrador_denied(self, api_client, institution, director_user, call_abierta):
        _login(api_client, director_user, institution)
        r = api_client.delete(reverse("calls:call-detail", kwargs={"pk": str(call_abierta.pk)}))
        assert r.status_code == 400

    def test_retrieve_cross_institution_not_found(
        self, api_client, institution, researcher_user, call_borrador
    ):
        """RLS: cross-institution call must return 404."""
        other_inst = Institution.objects.create(name="Other", code="OT001")
        other_call = Call.objects.create(
            institution=other_inst,
            title="Other Call",
            description="Desc",
            call_type="internal",
            status="borrador",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-detail", kwargs={"pk": str(other_call.pk)}))
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# CallViewSet — FSM Actions
# ════════════════════════════════════════════════════════


class TestCallFSMActions:
    """5 FSM action endpoints on CallViewSet."""

    def test_open_call_as_director(self, api_client, institution, director_user, call_borrador):
        _login(api_client, director_user, institution)
        r = api_client.post(reverse("calls:call-open-call", kwargs={"pk": str(call_borrador.pk)}))
        assert r.status_code == 200
        call_borrador.refresh_from_db()
        assert call_borrador.status == "abierta"

    def test_open_call_denied_for_researcher(
        self, api_client, institution, researcher_user, call_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(reverse("calls:call-open-call", kwargs={"pk": str(call_borrador.pk)}))
        assert r.status_code == 403

    def test_close_call_as_director(self, api_client, institution, director_user, call_abierta):
        _login(api_client, director_user, institution)
        r = api_client.post(reverse("calls:call-close-call", kwargs={"pk": str(call_abierta.pk)}))
        assert r.status_code == 200
        call_abierta.refresh_from_db()
        assert call_abierta.status == "cerrada"

    def test_start_evaluation_as_director(
        self, api_client, institution, director_user, call_cerrada
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-start-evaluation", kwargs={"pk": str(call_cerrada.pk)})
        )
        assert r.status_code == 200
        call_cerrada.refresh_from_db()
        assert call_cerrada.status == "en_evaluacion"

    def test_publish_results_as_director(
        self, api_client, institution, director_user, call_en_evaluacion
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-publish-results",
                kwargs={"pk": str(call_en_evaluacion.pk)},
            )
        )
        assert r.status_code == 200
        call_en_evaluacion.refresh_from_db()
        assert call_en_evaluacion.status == "resultados_publicados"

    def test_archive_from_resultados_publicados_as_director(
        self, api_client, institution, director_user, call_resultados_publicados
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-archive",
                kwargs={"pk": str(call_resultados_publicados.pk)},
            )
        )
        assert r.status_code == 200
        call_resultados_publicados.refresh_from_db()
        assert call_resultados_publicados.status == "archivada"

    def test_archive_from_cerrada_as_director(
        self, api_client, institution, director_user, call_cerrada
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(reverse("calls:call-archive", kwargs={"pk": str(call_cerrada.pk)}))
        assert r.status_code == 200
        call_cerrada.refresh_from_db()
        assert call_cerrada.status == "archivada"

    def test_invalid_transition_returns_400(
        self, api_client, institution, director_user, call_borrador
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-publish-results",
                kwargs={"pk": str(call_borrador.pk)},
            )
        )
        assert r.status_code == 400

    def test_fsm_creates_state_log(self, api_client, institution, director_user, call_borrador):
        _login(api_client, director_user, institution)
        api_client.post(reverse("calls:call-open-call", kwargs={"pk": str(call_borrador.pk)}))
        assert CallStateLog.objects.filter(call=call_borrador).exists()

    def test_fsm_validation_error_handler(
        self, api_client, institution, director_user, call_borrador
    ):
        """FSM action raising ValidationError (not TransitionNotAllowed) hits _extract_error."""
        from unittest.mock import patch

        from django.core.exceptions import ValidationError

        _login(api_client, director_user, institution)
        with patch("apps.calls.views.CallService.open_call") as mock_open:
            mock_open.side_effect = ValidationError({"status": ["Custom validation error."]})
            r = api_client.post(
                reverse("calls:call-open-call", kwargs={"pk": str(call_borrador.pk)})
            )
        assert r.status_code == 400
        assert "status" in r.json()


class TestExtractError:
    """Direct unit tests for CallViewSet._extract_error (lines 206-211)."""

    def test_extract_error_with_message_dict(self):
        from django.core.exceptions import ValidationError

        from apps.calls.views import CallViewSet

        e = ValidationError({"field": ["error message"]})
        result = CallViewSet._extract_error(e)
        assert result == {"field": ["error message"]}

    def test_extract_error_with_messages_list(self):
        from django.core.exceptions import ValidationError

        from apps.calls.views import CallViewSet

        e = ValidationError(["first error", "second error"])
        result = CallViewSet._extract_error(e)
        assert result == "first error"

    def test_extract_error_with_plain_string(self):
        from django.core.exceptions import ValidationError

        from apps.calls.views import CallViewSet

        e = ValidationError("plain error")
        result = CallViewSet._extract_error(e)
        assert result == "plain error"


# ════════════════════════════════════════════════════════
# CallDocumentViewSet — nested under call
# ════════════════════════════════════════════════════════


class TestCallDocumentViewSet:
    """Nested CRUD for CallDocument under /calls/{pk}/documents/."""

    def test_list_documents_as_researcher(
        self, api_client, institution, researcher_user, call_borrador
    ):
        CallDocument.objects.create(
            call=call_borrador, name="Doc1", doc_type="convocatoria", external_url="https://a.com"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "calls:call-document-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_create_document_as_director(
        self, api_client, institution, director_user, call_borrador
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-document-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            ),
            {
                "name": "New Doc",
                "doc_type": "anexo",
                "external_url": "https://example.com/doc",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "New Doc"
        assert data["call"] == str(call_borrador.pk)

    def test_create_document_denied_for_researcher(
        self, api_client, institution, researcher_user, call_borrador
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-document-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            ),
            {
                "name": "Doc",
                "doc_type": "anexo",
                "external_url": "https://example.com/doc",
            },
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_update_document_as_director(
        self, api_client, institution, director_user, call_borrador
    ):
        doc = CallDocument.objects.create(
            call=call_borrador, name="Old", doc_type="convocatoria", external_url="https://a.com"
        )
        _login(api_client, director_user, institution)
        r = api_client.patch(
            reverse(
                "calls:call-document-detail",
                kwargs={"call_pk": str(call_borrador.pk), "pk": str(doc.pk)},
            ),
            {"name": "Updated"},
            content_type="application/json",
        )
        assert r.status_code == 200
        doc.refresh_from_db()
        assert doc.name == "Updated"

    def test_delete_document_as_director(
        self, api_client, institution, director_user, call_borrador
    ):
        doc = CallDocument.objects.create(
            call=call_borrador,
            name="ToDelete",
            doc_type="convocatoria",
            external_url="https://a.com",
        )
        _login(api_client, director_user, institution)
        r = api_client.delete(
            reverse(
                "calls:call-document-detail",
                kwargs={"call_pk": str(call_borrador.pk), "pk": str(doc.pk)},
            )
        )
        assert r.status_code == 204
        assert not CallDocument.objects.filter(pk=doc.pk).exists()


# ════════════════════════════════════════════════════════
# CallProjectViewSet — nested under call
# ════════════════════════════════════════════════════════


class TestCallProjectViewSet:
    """Nested CRUD for CallProject under /calls/{pk}/projects/."""

    def test_list_projects_as_researcher(
        self, api_client, institution, researcher_user, call_abierta, project_not_linked
    ):
        CallProject.objects.create(call=call_abierta, project=project_not_linked)
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "calls:call-project-list",
                kwargs={"call_pk": str(call_abierta.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_link_project_to_open_call_as_director(
        self, api_client, institution, director_user, call_abierta, project_not_linked
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-project-list",
                kwargs={"call_pk": str(call_abierta.pk)},
            ),
            {"project": str(project_not_linked.pk)},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert CallProject.objects.filter(call=call_abierta, project=project_not_linked).exists()

    def test_link_project_to_non_open_call_denied(
        self, api_client, institution, director_user, call_borrador, project_not_linked
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-project-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            ),
            {"project": str(project_not_linked.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_link_duplicate_project_returns_400(
        self, api_client, institution, director_user, call_abierta, project_not_linked
    ):
        CallProject.objects.create(call=call_abierta, project=project_not_linked)
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-project-list",
                kwargs={"call_pk": str(call_abierta.pk)},
            ),
            {"project": str(project_not_linked.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_unlink_project_as_director(
        self, api_client, institution, director_user, call_abierta, project_not_linked
    ):
        cp = CallProject.objects.create(call=call_abierta, project=project_not_linked)
        _login(api_client, director_user, institution)
        r = api_client.delete(
            reverse(
                "calls:call-project-detail",
                kwargs={"call_pk": str(call_abierta.pk), "pk": str(cp.pk)},
            )
        )
        assert r.status_code == 204
        assert not CallProject.objects.filter(pk=cp.pk).exists()


# ════════════════════════════════════════════════════════
# CallStateLogViewSet — read-only nested
# ════════════════════════════════════════════════════════


class TestCallStateLogViewSet:
    """Read-only list of CallStateLog under /calls/{pk}/state_history/."""

    def test_list_state_logs_as_researcher(
        self, api_client, institution, researcher_user, call_borrador
    ):
        CallStateLog.objects.create(call=call_borrador, from_state="borrador", to_state="abierta")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "calls:call-state-log-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_create_state_log_denied(self, api_client, institution, director_user, call_borrador):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-state-log-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            ),
            {"from_state": "borrador", "to_state": "abierta"},
            content_type="application/json",
        )
        assert r.status_code == 405


# ════════════════════════════════════════════════════════
# Filtering & Search
# ════════════════════════════════════════════════════════


class TestCallFiltering:
    """Filter and search on /api/calls/."""

    def test_filter_by_status(
        self, api_client, institution, researcher_user, call_borrador, call_abierta
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-list") + "?status=abierta")
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["title"] == call_abierta.title

    def test_filter_by_call_type(self, api_client, institution, researcher_user):
        Call.objects.create(
            institution=institution,
            title="External",
            description="Desc",
            call_type="external",
            external_entity="Entity",
            status="borrador",
        )
        Call.objects.create(
            institution=institution,
            title="Internal",
            description="Desc",
            call_type="internal",
            status="borrador",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-list") + "?call_type=external")
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["title"] == "External"

    def test_search_by_title(self, api_client, institution, researcher_user, call_borrador):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-list") + "?search=Borrador")
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["title"] == call_borrador.title

    def test_ordering_by_created_at(
        self, api_client, institution, researcher_user, call_borrador, call_abierta
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-list") + "?ordering=-created_at")
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) >= 2


# ════════════════════════════════════════════════════════
# Error Responses
# ════════════════════════════════════════════════════════


class TestCallErrorResponses:
    """400/403/404/409 error scenarios."""

    def test_400_date_ordering(self, api_client, institution, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {
                "title": "Bad Dates",
                "description": "Desc",
                "call_type": "internal",
                "submission_start": "2026-06-01",
                "submission_end": "2026-05-01",
            },
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "submission_end" in r.json()

    def test_400_delete_non_borrador(self, api_client, institution, director_user, call_abierta):
        _login(api_client, director_user, institution)
        r = api_client.delete(reverse("calls:call-detail", kwargs={"pk": str(call_abierta.pk)}))
        assert r.status_code == 400

    def test_404_cross_institution_detail(self, api_client, institution, researcher_user):
        other = Institution.objects.create(name="Other", code="OT002")
        other_call = Call.objects.create(
            institution=other,
            title="Other",
            description="Desc",
            call_type="internal",
            status="borrador",
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-detail", kwargs={"pk": str(other_call.pk)}))
        assert r.status_code == 404

    def test_400_invalid_fsm_transition(
        self, api_client, institution, director_user, call_borrador
    ):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-publish-results",
                kwargs={"pk": str(call_borrador.pk)},
            )
        )
        assert r.status_code == 400

    def test_400_duplicate_project_link(
        self, api_client, institution, director_user, call_abierta, project_not_linked
    ):
        CallProject.objects.create(call=call_abierta, project=project_not_linked)
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-project-list",
                kwargs={"call_pk": str(call_abierta.pk)},
            ),
            {"project": str(project_not_linked.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_400_create_document_terminal_call(self, api_client, institution, director_user):
        """Adding a document to a terminal call triggers perform_create handler."""
        call_archivada = Call.objects.create(
            institution=institution,
            title="Terminal Call",
            description="Desc",
            call_type="internal",
            status="archivada",
        )
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-document-list",
                kwargs={"call_pk": str(call_archivada.pk)},
            ),
            {
                "name": "Doc",
                "doc_type": "anexo",
                "external_url": "https://example.com/doc",
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_400_update_document_terminal_call(self, api_client, institution, director_user):
        """Updating a document under a terminal call triggers perform_update handler."""
        call_archivada = Call.objects.create(
            institution=institution,
            title="Terminal Call",
            description="Desc",
            call_type="internal",
            status="archivada",
        )
        doc = CallDocument.objects.create(
            call=call_archivada,
            name="Old",
            doc_type="convocatoria",
            external_url="https://a.com",
        )
        _login(api_client, director_user, institution)
        r = api_client.patch(
            reverse(
                "calls:call-document-detail",
                kwargs={"call_pk": str(call_archivada.pk), "pk": str(doc.pk)},
            ),
            {"name": "Updated"},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_400_delete_document_terminal_call(self, api_client, institution, director_user):
        """Deleting a document under a terminal call triggers perform_destroy handler."""
        call_archivada = Call.objects.create(
            institution=institution,
            title="Terminal Call",
            description="Desc",
            call_type="internal",
            status="archivada",
        )
        doc = CallDocument.objects.create(
            call=call_archivada,
            name="ToDelete",
            doc_type="convocatoria",
            external_url="https://a.com",
        )
        _login(api_client, director_user, institution)
        r = api_client.delete(
            reverse(
                "calls:call-document-detail",
                kwargs={"call_pk": str(call_archivada.pk), "pk": str(doc.pk)},
            )
        )
        assert r.status_code == 400

    def test_404_documents_nonexistent_call(self, api_client, institution, director_user):
        """Creating a document for a non-existent call triggers Http404 in _get_parent_call."""
        fake_pk = "00000000-0000-0000-0000-000000000000"
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-document-list", kwargs={"call_pk": fake_pk}),
            {"name": "Doc", "doc_type": "anexo", "external_url": "https://example.com/doc"},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_404_projects_nonexistent_call(
        self, api_client, institution, director_user, project_not_linked
    ):
        """Linking a project to a non-existent call triggers Http404 in _get_parent_call."""
        fake_pk = "00000000-0000-0000-0000-000000000000"
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-project-list", kwargs={"call_pk": fake_pk}),
            {"project": str(project_not_linked.pk)},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_404_state_logs_nonexistent_call(self, api_client, institution, researcher_user):
        """State logs for a non-existent call return empty queryset (200, not 404)."""
        fake_pk = "00000000-0000-0000-0000-000000000000"
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("calls:call-state-log-list", kwargs={"call_pk": fake_pk}))
        assert r.status_code == 200
        assert len(r.json()["results"]) == 0

    def test_403_cross_institution_document_update(
        self, api_client, institution, director_user, call_borrador
    ):
        """Cross-institution document access triggers check_object_permissions redirect → 403."""
        other_inst = Institution.objects.create(name="Other", code="OT002")
        other_call = Call.objects.create(
            institution=other_inst,
            title="Other Call",
            description="Desc",
            call_type="internal",
            status="borrador",
        )
        doc = CallDocument.objects.create(
            call=other_call,
            name="Doc",
            doc_type="convocatoria",
            external_url="https://a.com",
        )
        _login(api_client, director_user, institution)
        r = api_client.patch(
            reverse(
                "calls:call-document-detail",
                kwargs={"call_pk": str(other_call.pk), "pk": str(doc.pk)},
            ),
            {"name": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_400_malformed_create_call(self, api_client, institution, director_user):
        """Missing required fields trigger serializer validation → 400."""
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("calls:call-list"),
            {"description": "Missing title", "call_type": "internal"},
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "title" in r.json()

    def test_400_malformed_create_document(
        self, api_client, institution, director_user, call_borrador
    ):
        """Missing required fields in document serializer trigger validation → 400."""
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "calls:call-document-list",
                kwargs={"call_pk": str(call_borrador.pk)},
            ),
            {"doc_type": "anexo"},
            content_type="application/json",
        )
        assert r.status_code == 400
        assert "name" in r.json()
