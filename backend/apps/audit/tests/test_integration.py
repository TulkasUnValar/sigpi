"""
Audit integration tests — STRICT TDD (RED phase).

End-to-end coverage of the audit & traceability stack (SIGPI §6.13):

- Project CREATE / UPDATE / DELETE captured via the signal layer.
- Document DOWNLOAD captured via the view layer (RF-106 / RF-D09).
- Storage-failure download emits NO event (503 path).
- Audit log API returns the correct events when filtered by project_id
  (RA-3) and by user_id (RA-4).

These tests exercise the real capture path end to end:
  model save/delete → signals → AuditEventEmitter → accounts_auditevent,
  and presigned-GET issuance → view emitter → accounts_auditevent,
  then the read-only AuditLogViewSet to query the persisted rows.

Spec reference: openspec/changes/audit/specs/audit/spec.md (RA-1..RA-8)
Design reference: openspec/changes/audit/design.md — Data Flow and Signals
"""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.audit import AuditEvent, AuditEventType
from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.audit.context import audit_context, reset_audit_context
from apps.documents.models import DocumentType
from apps.documents.tests.conftest import DocumentFactory, DocumentVersionFactory
from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ──────────────────────────────────────────────
# Storage fake — presign_get interface
# ──────────────────────────────────────────────


class FakeStorage:
    """In-memory stand-in for MinIOStorage with a 'broken' switch (503)."""

    def __init__(self):
        self.broken = False

    def presign_get(self, object_key, expires=None):
        if self.broken:
            raise RuntimeError("minio down")
        return f"https://minio.example/get/{object_key}"


@pytest.fixture
def fake_storage(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr("apps.documents.services.default_storage", storage)
    return storage


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_context():
    """Ensure the request-scoped audit context never leaks between tests."""
    reset_audit_context()
    yield
    reset_audit_context()


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Integración", code="UINT1")


@pytest.fixture
def center(db, institution) -> ResearchCenter:
    return ResearchCenter.objects.create(institution=institution, name="CI Lab", code="CI")


@pytest.fixture
def user(db, institution) -> User:
    user = User.objects.create_user(
        email="actor@integ.test", auth_source="local", password="pass"
    )
    # Writable role so the user may request a document download via the API.
    InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=get_role("Asistente"),
        is_active=True,
    )
    return user


@pytest.fixture
def researcher(db, institution) -> Researcher:
    return Researcher.objects.create(
        institution=institution,
        first_name="Ana",
        last_name="Lopez",
        document_type="CC",
        document_number=f"DN-{uuid.uuid4().hex[:8]}",
        primary_email=f"ana.{uuid.uuid4().hex[:4]}@integ.edu",
    )


@pytest.fixture
def auditor(db, institution) -> User:
    user = User.objects.create_user(email="auditor@integ.test", auth_source="local", password="pass")
    InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=get_role("Auditor"),
        is_active=True,
    )
    return user


def _make_project(institution, center, researcher, **overrides):
    defaults = {
        "institution": institution,
        "center": center,
        "principal_investigator": researcher,
        "title": "Proyecto de Auditoría",
        "abstract": "Un abstract",
        "objectives": "Objetivos",
        "methodology": "Metodología",
        "expected_results": "Resultados",
        "keywords": "auditoria",
        "start_date": date(2026, 1, 1),
        "estimated_end_date": date(2026, 12, 31),
    }
    defaults.update(overrides)
    return Project.objects.create(**defaults)


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _audit_url():
    return reverse("audit:audit-list")


# ──────────────────────────────────────────────
# Project CRUD end-to-end (signal capture)
# ──────────────────────────────────────────────


class TestProjectCrudCapture:
    def test_create_project_emits_create_event(
        self, db, institution, center, researcher, user
    ):
        with audit_context(user=user, institution_id=institution.id, ip_address="10.0.0.5"):
            project = _make_project(institution, center, researcher)

        event = AuditEvent.objects.get(
            event_type=AuditEventType.CREATE, entity_type="project", entity_id=project.pk
        )
        assert event.user == user
        assert event.institution_id == institution.id
        assert event.project_id == project.pk
        assert event.action == "CREATE"

    def test_update_project_emits_update_with_old_new(
        self, db, institution, center, researcher, user
    ):
        with audit_context(user=user, institution_id=institution.id):
            project = _make_project(institution, center, researcher)
        AuditEvent.objects.all().delete()

        with audit_context(user=user, institution_id=institution.id):
            project.title = "Título Actualizado"
            project.save()

        event = AuditEvent.objects.get(event_type=AuditEventType.UPDATE, entity_type="project")
        assert event.entity_id == project.pk
        assert event.old_values.get("title") == "Proyecto de Auditoría"
        assert event.new_values.get("title") == "Título Actualizado"

    def test_delete_project_emits_delete_event(
        self, db, institution, center, researcher, user
    ):
        with audit_context(user=user, institution_id=institution.id):
            project = _make_project(institution, center, researcher)
        project_id = project.pk
        AuditEvent.objects.all().delete()

        with audit_context(user=user, institution_id=institution.id):
            project.delete()

        event = AuditEvent.objects.get(event_type=AuditEventType.DELETE, entity_type="project")
        assert event.entity_id == project_id
        assert event.old_values.get("title") == "Proyecto de Auditoría"


# ──────────────────────────────────────────────
# Document download end-to-end (view emitter, RF-106)
# ──────────────────────────────────────────────


class TestDocumentDownloadCapture:
    def test_download_emits_download_event(
        self, db, api_client, institution, user, fake_storage
    ):
        _login(api_client, user, institution)
        doc_type = DocumentType.objects.get(code="informe_final")
        doc = DocumentFactory(institution=institution, doc_type=doc_type, created_by=user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=user)

        response = api_client.get(reverse("documents:document-download", kwargs={"pk": doc.pk}))

        assert response.status_code == 200
        event = AuditEvent.objects.get(
            event_type=AuditEventType.DOCUMENT_DOWNLOADED, entity_type="document"
        )
        assert event.entity_id == doc.pk
        assert event.action == "DOWNLOAD"
        assert event.project_id == doc.project_id
        assert event.user == user
        assert event.institution_id == institution.id
        assert event.details.get("document_id") == str(doc.pk)
        assert event.details.get("version") == 1

    def test_version_detail_emits_download_event(
        self, db, api_client, institution, user, fake_storage
    ):
        _login(api_client, user, institution)
        doc_type = DocumentType.objects.get(code="informe_final")
        doc = DocumentFactory(institution=institution, doc_type=doc_type, created_by=user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=user)

        response = api_client.get(
            reverse("documents:document-version-detail", kwargs={"pk": doc.pk, "version": 1})
        )

        assert response.status_code == 200
        event = AuditEvent.objects.get(
            event_type=AuditEventType.DOCUMENT_DOWNLOADED, entity_type="document"
        )
        assert event.entity_id == doc.pk
        assert event.details.get("version") == 1

    def test_download_storage_failure_emits_no_event(
        self, db, api_client, institution, user, fake_storage
    ):
        _login(api_client, user, institution)
        doc_type = DocumentType.objects.get(code="informe_final")
        doc = DocumentFactory(institution=institution, doc_type=doc_type, created_by=user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
        fake_storage.broken = True

        response = api_client.get(reverse("documents:document-download", kwargs={"pk": doc.pk}))

        assert response.status_code == 503
        assert (
            AuditEvent.objects.filter(
                event_type=AuditEventType.DOCUMENT_DOWNLOADED, entity_type="document"
            ).count()
            == 0
        )


# ──────────────────────────────────────────────
# Audit log query end-to-end (read API, RA-3 / RA-4)
# ──────────────────────────────────────────────


class TestAuditLogQuery:
    def test_query_by_project_id_returns_correct_events(
        self, db, api_client, institution, center, researcher, user, auditor
    ):
        with audit_context(user=user, institution_id=institution.id):
            project_a = _make_project(institution, center, researcher, title="Proyecto A")
        with audit_context(user=user, institution_id=institution.id):
            _make_project(institution, center, researcher, title="Proyecto B")

        _login(api_client, auditor, institution)
        response = api_client.get(_audit_url(), {"project_id": str(project_a.pk)})

        assert response.status_code == 200
        assert response.data["count"] == 1
        result = response.data["results"][0]
        assert str(result["project_id"]) == str(project_a.pk)
        assert result["entity_type"] == "project"
        assert result["event_type"] == "CREATE"

    def test_query_by_user_id_returns_correct_events(
        self, db, api_client, institution, center, researcher, user, auditor
    ):
        with audit_context(user=user, institution_id=institution.id):
            _make_project(institution, center, researcher)
        other = User.objects.create_user(email="other@integ.test", auth_source="local", password="pass")
        with audit_context(user=other, institution_id=institution.id):
            _make_project(institution, center, researcher)

        _login(api_client, auditor, institution)
        response = api_client.get(_audit_url(), {"user_id": str(user.pk)})

        assert response.status_code == 200
        assert response.data["count"] >= 1
        for result in response.data["results"]:
            assert result["user"]["id"] == str(user.pk)

    def test_query_by_user_id_isolates_from_other_actor(
        self, db, api_client, institution, center, researcher, user, auditor
    ):
        with audit_context(user=user, institution_id=institution.id):
            _make_project(institution, center, researcher)
        other = User.objects.create_user(email="other@integ.test", auth_source="local", password="pass")
        with audit_context(user=other, institution_id=institution.id):
            _make_project(institution, center, researcher)

        _login(api_client, auditor, institution)
        response = api_client.get(_audit_url(), {"user_id": str(other.pk)})

        assert response.status_code == 200
        assert response.data["count"] >= 1
        for result in response.data["results"]:
            assert result["user"]["id"] == str(other.pk)
