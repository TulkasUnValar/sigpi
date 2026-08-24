"""
API tests for the documents ViewSets — STRICT TDD (RED phase).

Covers the Phase 5 API Contract from spec.md:
- DocumentViewSet: list/detail CRUD (signed → 409), types, presign
  (400/403 contract), confirm (409 wrong key / 503 storage), versions
  (list descending + re-upload + signed 409), version detail + presigned
  GET, sign (404/409/503 contract + end-to-end flow), download.
- DigitalSignatureViewSet: read-only signatures per document.
- MinutesViewSet: CRUD (invalid acta 400, signed 409), audit events.

Error contract (spec.md Error Handling):
  400 ValidationError · 403 cross-institution / auditor write · 404 missing
  document/version · 409 immutable/object-key/hash/re-sign · 503 storage.

Test pattern: Django test Client + force_login + session institution_id
(matches apps/budgets/tests/test_views.py).

RED PHASE: views.py does not exist — module import fails.

Spec reference: openspec/changes/attachments/specs/documents/spec.md
"""

import hashlib
import io
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import AuditEvent, InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.calls.models import Call, CallType
from apps.documents.models import Document, DocumentType, DocumentVersion
from apps.documents.tests.conftest import (
    DigitalSignatureFactory,
    DocumentFactory,
    DocumentVersionFactory,
)
from apps.institutions.models import Institution

# ──────────────────────────────────────────────
# Storage fake — presign/exists/open interface
# ──────────────────────────────────────────────


class FakeStorage:
    """In-memory stand-in for MinIOStorage with a 'broken' switch (503)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.broken = False

    def build_object_key(self, institution_id, document_id, version, filename):
        return f"documents/{institution_id}/{document_id}/v{version}/{filename}"

    def presign_put(self, object_key, expires=None):
        if self.broken:
            raise RuntimeError("minio down")
        return f"https://minio.example/put/{object_key}"

    def presign_get(self, object_key, expires=None):
        if self.broken:
            raise RuntimeError("minio down")
        return f"https://minio.example/get/{object_key}"

    def exists(self, object_key):
        if self.broken:
            raise RuntimeError("minio down")
        return object_key in self.objects

    def open(self, object_key, mode="rb"):
        if self.broken:
            raise RuntimeError("minio down")
        return io.BytesIO(self.objects[object_key])

    def put(self, object_key, data):
        self.objects[object_key] = data


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _acta_type():
    return DocumentType.objects.get(code="acta_inicio")


def _non_acta_type():
    return DocumentType.objects.get(code="informe_final")


def _acta_document(institution, user, **kwargs):
    return DocumentFactory(
        institution=institution, doc_type=_acta_type(), created_by=user, **kwargs
    )


def _signed_document(institution, user):
    """Document whose single version carries a signature (locked flag via update)."""
    doc = _acta_document(institution, user)
    version = DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
    DigitalSignatureFactory(document_version=version, signer=user, sha256=version.sha256)
    Document.objects.filter(pk=doc.pk).update(is_signed=True)
    return doc


def _call(institution, title="Test Call"):
    return Call.objects.create(
        institution=institution,
        title=title,
        description="Desc",
        call_type=CallType.INTERNAL,
    )


def _presign_payload(**overrides):
    payload = {
        "doc_type": "acta_inicio",
        "filename": "file.pdf",
        "content_type": "application/pdf",
    }
    payload.update(overrides)
    return payload


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU005")


@pytest.fixture
def other_institution(db):
    return Institution.objects.create(name="Other University", code="OU005")


@pytest.fixture
def asistente_role(db):
    return get_role("Asistente")


@pytest.fixture
def auditor_role(db):
    return get_role("Auditor")


@pytest.fixture
def write_user(db, institution, asistente_role):
    """Asistente (level 6) — the ceiling role that may write documents."""
    user = User.objects.create_user(email="write@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=asistente_role, is_active=True
    )
    return user


@pytest.fixture
def auditor_user(db, institution, auditor_role):
    """Auditor (level 7) — read-only per SPEC §6.7 permissions table."""
    user = User.objects.create_user(email="auditor@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=auditor_role, is_active=True
    )
    return user


@pytest.fixture
def foreign_user(db, other_institution, asistente_role):
    """Asistente whose active institution differs from the main fixtures."""
    user = User.objects.create_user(email="foreign@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=other_institution, role=asistente_role, is_active=True
    )
    return user


@pytest.fixture
def fake_storage(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr("apps.documents.services.default_storage", storage)
    return storage


# ════════════════════════════════════════════════════════
# DocumentViewSet — types (RF-D08)
# ════════════════════════════════════════════════════════


class TestDocumentTypes:
    def test_types_lists_exactly_12(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        r = api_client.get(reverse("documents:document-types"))
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 12
        codes = {item["code"] for item in data}
        assert "acta_inicio" in codes and "certificacion" in codes and "otro" in codes

    def test_types_unauthenticated_denied(self, api_client):
        r = api_client.get(reverse("documents:document-types"))
        assert r.status_code == 403


# ════════════════════════════════════════════════════════
# DocumentViewSet — presign (RF-D01)
# ════════════════════════════════════════════════════════


class TestPresign:
    def test_presign_returns_upload_contract(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert set(data.keys()) == {"upload_url", "object_key", "document_id"}
        assert data["upload_url"].startswith("https://minio.example/put/")
        assert data["object_key"] == (
            f"documents/{institution.pk}/{data['document_id']}/v1/file.pdf"
        )
        doc = Document.objects.get(pk=data["document_id"])
        assert doc.institution_id == institution.pk
        assert doc.title == "file.pdf"
        assert doc.doc_type.code == "acta_inicio"

    def test_presign_unknown_doc_type_400(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(doc_type="bogus"),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_presign_path_traversal_filename_400(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(filename="../evil.pdf"),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_presign_foreign_entity_403(
        self, api_client, institution, other_institution, write_user, fake_storage
    ):
        """Entity belongs to a different institution → 403 (spec RF-D01)."""
        _login(api_client, write_user, institution)
        foreign_call = _call(other_institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(entity_type="call", entity_id=str(foreign_call.pk)),
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_presign_binds_entity_fk(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        call = _call(institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(entity_type="call", entity_id=str(call.pk)),
            content_type="application/json",
        )
        assert r.status_code == 201
        doc = Document.objects.get(pk=r.json()["document_id"])
        assert doc.entity_type == "call"
        assert doc.call_id == call.pk

    def test_presign_auditor_write_denied_403(
        self, api_client, institution, auditor_user, fake_storage
    ):
        _login(api_client, auditor_user, institution)
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_presign_unauthenticated_403(self, api_client):
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_presign_storage_unavailable_503(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        fake_storage.broken = True
        r = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        )
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"

    def test_presign_superuser_sees_all_institutions(
        self, api_client, institution, other_institution
    ):
        """Superuser bypasses tenant scoping (design: superadmin bypass)."""
        user = User.objects.create_user(email="root@test.edu", auth_source="local", password="p")
        user.is_superuser = True
        user.save()
        _login(api_client, user, institution)
        _acta_document(institution, user)
        _acta_document(other_institution, user)
        r = api_client.get(reverse("documents:document-list"))
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    def test_list_without_membership_returns_empty(
        self, api_client, institution, write_user
    ):
        """Authenticated user with session institution but no active membership → empty."""
        nomad = User.objects.create_user(email="nomad@test.edu", auth_source="local", password="p")
        _login(api_client, nomad, institution)
        _acta_document(institution, write_user)
        r = api_client.get(reverse("documents:document-list"))
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_post_list_starts_presign_flow(self, api_client, institution, write_user, fake_storage):
        """POST /documents/ is the presign flow entry (spec API Contract note)."""
        _login(api_client, write_user, institution)
        r = api_client.post(
            reverse("documents:document-list"),
            _presign_payload(),
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert set(data.keys()) == {"upload_url", "object_key", "document_id"}
        assert Document.objects.filter(pk=data["document_id"]).exists()


# ════════════════════════════════════════════════════════
# DocumentViewSet — CRUD (RF-D06 immutability)
# ════════════════════════════════════════════════════════


class TestDocumentCRUD:
    def test_list_scoped_to_institution(
        self, api_client, institution, other_institution, write_user
    ):
        _login(api_client, write_user, institution)
        _acta_document(institution, write_user)
        _acta_document(institution, write_user)
        _acta_document(other_institution, write_user)
        r = api_client.get(reverse("documents:document-list"))
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 2
        assert all(item["institution"] == str(institution.pk) for item in data)

    def test_list_unauthenticated_403(self, api_client):
        r = api_client.get(reverse("documents:document-list"))
        assert r.status_code == 403

    def test_retrieve_document(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        r = api_client.get(reverse("documents:document-detail", kwargs={"pk": doc.pk}))
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == str(doc.pk)
        assert data["doc_type"]["code"] == "acta_inicio"
        assert data["current_version"] == 1
        assert data["is_signed"] is False
        assert data["signature"] is None

    def test_retrieve_foreign_document_404(
        self, api_client, institution, other_institution, write_user
    ):
        _login(api_client, write_user, institution)
        foreign = _acta_document(other_institution, write_user)
        r = api_client.get(reverse("documents:document-detail", kwargs={"pk": foreign.pk}))
        assert r.status_code == 404

    def test_update_title_unsigned(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.patch(
            reverse("documents:document-detail", kwargs={"pk": doc.pk}),
            {"title": "Renamed.pdf"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Renamed.pdf"

    def test_update_signed_document_409(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        r = api_client.patch(
            reverse("documents:document-detail", kwargs={"pk": doc.pk}),
            {"title": "Hacked.pdf"},
            content_type="application/json",
        )
        assert r.status_code == 409
        assert r.json()["detail"] == "Signed documents are immutable"

    def test_delete_unsigned_document(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.delete(reverse("documents:document-detail", kwargs={"pk": doc.pk}))
        assert r.status_code == 204
        assert not Document.objects.filter(pk=doc.pk).exists()

    def test_delete_signed_document_409(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        r = api_client.delete(reverse("documents:document-detail", kwargs={"pk": doc.pk}))
        assert r.status_code == 409
        assert Document.objects.filter(pk=doc.pk).exists()


# ════════════════════════════════════════════════════════
# DocumentViewSet — confirm (RF-D01)
# ════════════════════════════════════════════════════════


class TestConfirm:
    def _confirm(self, api_client, doc_id, object_key, sha256, **overrides):
        payload = {
            "object_key": object_key,
            "size_bytes": 4,
            "mime_type": "application/pdf",
            "sha256": sha256,
        }
        payload.update(overrides)
        return api_client.post(
            reverse("documents:document-confirm", kwargs={"pk": doc_id}),
            payload,
            content_type="application/json",
        )

    def test_confirm_creates_version_and_audits(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        presigned = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        ).json()
        fake_storage.put(presigned["object_key"], b"data")
        r = self._confirm(api_client, presigned["document_id"], presigned["object_key"], "a" * 64)
        assert r.status_code == 201
        data = r.json()
        assert data["version"] == 1
        assert data["document"] == presigned["document_id"]
        assert data["sha256"] == "a" * 64
        assert data["size_bytes"] == 4
        event = AuditEvent.objects.get(event_type="DOCUMENT_UPLOADED")
        assert event.details["document_id"] == presigned["document_id"]
        assert event.details["version"] == 1

    def test_confirm_wrong_key_409(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc_a = _acta_document(institution, write_user)
        doc_b = _acta_document(institution, write_user)
        wrong_key = fake_storage.build_object_key(institution.pk, doc_b.pk, 1, "other.pdf")
        fake_storage.put(wrong_key, b"data")
        r = self._confirm(api_client, doc_a.pk, wrong_key, "a" * 64)
        assert r.status_code == 409
        assert r.json()["detail"] == "Object key mismatch"
        assert not doc_a.versions.exists()

    def test_confirm_signed_document_409(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        key = fake_storage.build_object_key(institution.pk, doc.pk, 2, "v2.pdf")
        fake_storage.put(key, b"data")
        r = self._confirm(api_client, doc.pk, key, "a" * 64)
        assert r.status_code == 409

    def test_confirm_object_missing_400(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        key = fake_storage.build_object_key(institution.pk, doc.pk, 1, "missing.pdf")
        r = self._confirm(api_client, doc.pk, key, "a" * 64)
        assert r.status_code == 400

    def test_confirm_storage_unavailable_503(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        key = fake_storage.build_object_key(institution.pk, doc.pk, 1, "file.pdf")
        fake_storage.broken = True
        r = self._confirm(api_client, doc.pk, key, "a" * 64)
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"


# ════════════════════════════════════════════════════════
# DocumentViewSet — versions (RF-D03)
# ════════════════════════════════════════════════════════


class TestVersions:
    def test_versions_list_descending(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        DocumentVersionFactory(document=doc, version=2, uploaded_by=write_user)
        r = api_client.get(reverse("documents:document-versions", kwargs={"pk": doc.pk}))
        assert r.status_code == 200
        data = r.json()
        assert [v["version"] for v in data] == [2, 1]
        assert data[0]["mime_type"] == "application/pdf"
        assert data[0]["object_key"].endswith("/v2/file.pdf")

    def test_versions_upload_bumps_version(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        r = api_client.post(
            reverse("documents:document-versions", kwargs={"pk": doc.pk}),
            {"filename": "v2.pdf", "content_type": "application/pdf"},
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == 2
        assert data["object_key"] == f"documents/{institution.pk}/{doc.pk}/v2/v2.pdf"
        assert data["upload_url"].startswith("https://minio.example/put/")

    def test_versions_upload_signed_document_409(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        r = api_client.post(
            reverse("documents:document-versions", kwargs={"pk": doc.pk}),
            {"filename": "v2.pdf", "content_type": "application/pdf"},
            content_type="application/json",
        )
        assert r.status_code == 409

    def test_versions_upload_storage_unavailable_503(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        fake_storage.broken = True
        r = api_client.post(
            reverse("documents:document-versions", kwargs={"pk": doc.pk}),
            {"filename": "v2.pdf", "content_type": "application/pdf"},
            content_type="application/json",
        )
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"

    def test_versions_foreign_document_404(
        self, api_client, institution, other_institution, write_user
    ):
        _login(api_client, write_user, institution)
        foreign = _acta_document(other_institution, write_user)
        r = api_client.get(reverse("documents:document-versions", kwargs={"pk": foreign.pk}))
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# DocumentViewSet — version detail + download
# ════════════════════════════════════════════════════════


class TestVersionDetailAndDownload:
    def test_version_detail_returns_download_url(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        r = api_client.get(
            reverse("documents:document-version-detail", kwargs={"pk": doc.pk, "version": 1})
        )
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == 1
        assert data["download_url"].startswith("https://minio.example/get/")
        assert data["signature"] is None

    def test_version_detail_missing_404(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.get(
            reverse("documents:document-version-detail", kwargs={"pk": doc.pk, "version": 99})
        )
        assert r.status_code == 404

    def test_version_detail_storage_unavailable_503(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        fake_storage.broken = True
        r = api_client.get(
            reverse("documents:document-version-detail", kwargs={"pk": doc.pk, "version": 1})
        )
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"

    def test_download_returns_latest_version(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        DocumentVersionFactory(document=doc, version=2, uploaded_by=write_user)
        r = api_client.get(reverse("documents:document-download", kwargs={"pk": doc.pk}))
        assert r.status_code == 200
        data = r.json()
        assert data["version"] == 2
        assert data["object_key"].endswith("/v2/file.pdf")
        assert data["download_url"].startswith("https://minio.example/get/")

    def test_download_no_versions_404(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.get(reverse("documents:document-download", kwargs={"pk": doc.pk}))
        assert r.status_code == 404

    def test_download_storage_unavailable_503(
        self, api_client, institution, write_user, fake_storage
    ):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        fake_storage.broken = True
        r = api_client.get(reverse("documents:document-download", kwargs={"pk": doc.pk}))
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"


# ════════════════════════════════════════════════════════
# DocumentViewSet — sign (RF-D04)
# ════════════════════════════════════════════════════════


class TestSign:
    def _prepare_version(self, api_client, institution, write_user, fake_storage, content):
        """presign → PUT (fake) → confirm; returns (doc_id, version)."""
        _login(api_client, write_user, institution)
        presigned = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        ).json()
        fake_storage.put(presigned["object_key"], content)
        r = api_client.post(
            reverse("documents:document-confirm", kwargs={"pk": presigned["document_id"]}),
            {
                "object_key": presigned["object_key"],
                "size_bytes": len(content),
                "mime_type": "application/pdf",
                "sha256": hashlib.sha256(content).hexdigest(),
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        return presigned["document_id"], 1

    def test_sign_flow_end_to_end(self, api_client, institution, write_user, fake_storage):
        """presign → PUT → confirm → sign → lock + DOCUMENT_SIGNED audit (RF-D04)."""
        content = b"%PDF-1.4 fake bytes for signature"
        doc_id, version = self._prepare_version(
            api_client, institution, write_user, fake_storage, content
        )
        r = api_client.post(
            reverse("documents:document-sign", kwargs={"pk": doc_id, "version": version})
        )
        assert r.status_code == 201
        data = r.json()
        assert data["sha256"] == hashlib.sha256(content).hexdigest()
        assert data["signer"] == str(write_user.pk)
        assert data["document_version"] == str(
            DocumentVersion.objects.get(document_id=doc_id, version=1).pk
        )
        assert Document.objects.get(pk=doc_id).is_signed is True
        event = AuditEvent.objects.get(event_type="DOCUMENT_SIGNED")
        assert event.details["document_id"] == doc_id
        assert event.details["version"] == 1

    def test_sign_version_not_found_404(self, api_client, institution, write_user, fake_storage):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        r = api_client.post(reverse("documents:document-sign", kwargs={"pk": doc.pk, "version": 5}))
        assert r.status_code == 404

    def test_sign_re_sign_409(self, api_client, institution, write_user, fake_storage):
        content = b"re-sign test content"
        doc_id, version = self._prepare_version(
            api_client, institution, write_user, fake_storage, content
        )
        url = reverse("documents:document-sign", kwargs={"pk": doc_id, "version": version})
        assert api_client.post(url).status_code == 201
        r = api_client.post(url)
        assert r.status_code == 409
        assert r.json()["detail"] == "Version already signed"

    def test_sign_hash_mismatch_409(self, api_client, institution, write_user, fake_storage):
        """Server-computed hash differs from confirmed hash → 409 IntegrityCheck."""
        content = b"tampered bytes"
        _login(api_client, write_user, institution)
        presigned = api_client.post(
            reverse("documents:document-presign"),
            _presign_payload(),
            content_type="application/json",
        ).json()
        fake_storage.put(presigned["object_key"], content)
        api_client.post(
            reverse("documents:document-confirm", kwargs={"pk": presigned["document_id"]}),
            {
                "object_key": presigned["object_key"],
                "size_bytes": len(content),
                "mime_type": "application/pdf",
                "sha256": "b" * 64,  # client-claimed hash that does NOT match the bytes
            },
            content_type="application/json",
        )
        r = api_client.post(
            reverse(
                "documents:document-sign",
                kwargs={"pk": presigned["document_id"], "version": 1},
            )
        )
        assert r.status_code == 409
        assert r.json()["detail"] == "Integrity check failed"
        assert Document.objects.get(pk=presigned["document_id"]).is_signed is False

    def test_sign_other_version_signed_409(self, api_client, institution, write_user, fake_storage):
        """New version of a locked document → 409 SignedDocumentImmutable."""
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=2, uploaded_by=write_user)
        r = api_client.post(reverse("documents:document-sign", kwargs={"pk": doc.pk, "version": 2}))
        assert r.status_code == 409
        assert r.json()["detail"] == "Signed documents are immutable"

    def test_sign_storage_unavailable_503(self, api_client, institution, write_user, fake_storage):
        content = b"storage down content"
        doc_id, version = self._prepare_version(
            api_client, institution, write_user, fake_storage, content
        )
        fake_storage.broken = True
        r = api_client.post(
            reverse("documents:document-sign", kwargs={"pk": doc_id, "version": version})
        )
        assert r.status_code == 503
        assert r.json()["detail"] == "Storage unavailable"

    def test_sign_auditor_denied_403(self, api_client, institution, write_user, auditor_user):
        _login(api_client, auditor_user, institution)
        doc = _acta_document(institution, write_user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        r = api_client.post(reverse("documents:document-sign", kwargs={"pk": doc.pk, "version": 1}))
        assert r.status_code == 403


# ════════════════════════════════════════════════════════
# Signed document queries (RF-D05)
# ════════════════════════════════════════════════════════


class TestSignedQueries:
    def test_filter_signed_documents_with_signature_metadata(
        self, api_client, institution, write_user
    ):
        _login(api_client, write_user, institution)
        signed = _signed_document(institution, write_user)
        _acta_document(institution, write_user)  # unsigned
        r = api_client.get(reverse("documents:document-list"), {"is_signed": "true"})
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["id"] == str(signed.pk)
        sig = data[0]["signature"]
        assert sig is not None
        assert sig["signer"] == write_user.email
        assert sig["sha256"] == "a" * 64
        assert "signed_at" in sig

    def test_filter_signed_documents_empty_when_none(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        _acta_document(institution, write_user)  # unsigned only
        r = api_client.get(reverse("documents:document-list"), {"is_signed": "true"})
        assert r.status_code == 200
        assert r.json()["results"] == []


# ════════════════════════════════════════════════════════
# DigitalSignatureViewSet — read-only per document
# ════════════════════════════════════════════════════════


class TestDigitalSignatureViewSet:
    def test_signatures_list_for_document(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        r = api_client.get(reverse("documents:document-signatures", kwargs={"pk": doc.pk}))
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["signer"] == str(write_user.pk)
        assert data[0]["sha256"] == "a" * 64

    def test_signature_retrieve(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _signed_document(institution, write_user)
        sig = doc.versions.first().signatures.first()
        r = api_client.get(
            reverse(
                "documents:document-signature-detail",
                kwargs={"pk": doc.pk, "signature_pk": sig.pk},
            )
        )
        assert r.status_code == 200
        assert r.json()["id"] == str(sig.pk)

    def test_signatures_foreign_document_scoped_out(
        self, api_client, institution, other_institution, write_user
    ):
        """A foreign document's signatures are invisible (empty, tenant scoping)."""
        _login(api_client, write_user, institution)
        foreign = _signed_document(other_institution, write_user)
        r = api_client.get(reverse("documents:document-signatures", kwargs={"pk": foreign.pk}))
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_signature_retrieve_foreign_404(
        self, api_client, institution, other_institution, write_user
    ):
        _login(api_client, write_user, institution)
        foreign = _signed_document(other_institution, write_user)
        sig = foreign.versions.first().signatures.first()
        r = api_client.get(
            reverse(
                "documents:document-signature-detail",
                kwargs={"pk": foreign.pk, "signature_pk": sig.pk},
            )
        )
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# MinutesViewSet — CRUD (RF-D07)
# ════════════════════════════════════════════════════════


class TestMinutes:
    def test_create_minutes_audits(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.post(
            reverse("documents:minutes-list"),
            {"acta_type": "inicio", "document": str(doc.pk)},
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["acta_type"] == "inicio"
        assert data["document"] == str(doc.pk)
        assert data["institution"] == str(institution.pk)
        event = AuditEvent.objects.get(event_type="MINUTES_CREATED")
        assert event.details["minutes_id"] == data["id"]
        assert event.details["acta_type"] == "inicio"

    def test_create_minutes_invalid_acta_type_400(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        r = api_client.post(
            reverse("documents:minutes-list"),
            {"acta_type": "bogus", "document": str(doc.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_create_minutes_non_acta_document_400(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)
        doc = DocumentFactory(
            institution=institution, doc_type=_non_acta_type(), created_by=write_user
        )
        r = api_client.post(
            reverse("documents:minutes-list"),
            {"acta_type": "inicio", "document": str(doc.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_create_minutes_cross_institution_document_403(
        self, api_client, institution, other_institution, write_user
    ):
        _login(api_client, write_user, institution)
        foreign = _acta_document(other_institution, write_user)
        r = api_client.post(
            reverse("documents:minutes-list"),
            {"acta_type": "inicio", "document": str(foreign.pk)},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_minutes_list_scoped(self, api_client, institution, other_institution, write_user):
        from apps.documents.tests.conftest import MinutesFactory

        _login(api_client, write_user, institution)
        MinutesFactory(institution=institution, created_by=write_user)
        MinutesFactory(institution=institution, created_by=write_user)
        MinutesFactory(institution=other_institution, created_by=write_user)
        r = api_client.get(reverse("documents:minutes-list"))
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 2
        assert all(item["institution"] == str(institution.pk) for item in data)

    def test_minutes_update_unsigned(self, api_client, institution, write_user):
        from apps.documents.tests.conftest import MinutesFactory

        _login(api_client, write_user, institution)
        minutes = MinutesFactory(institution=institution, created_by=write_user)
        r = api_client.patch(
            reverse("documents:minutes-detail", kwargs={"pk": minutes.pk}),
            {"acta_type": "cierre"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["acta_type"] == "cierre"

    def test_minutes_delete_unsigned(self, api_client, institution, write_user):
        from apps.documents.tests.conftest import Minutes, MinutesFactory

        _login(api_client, write_user, institution)
        minutes = MinutesFactory(institution=institution, created_by=write_user)
        r = api_client.delete(reverse("documents:minutes-detail", kwargs={"pk": minutes.pk}))
        assert r.status_code == 204
        assert not Minutes.objects.filter(pk=minutes.pk).exists()

    def test_minutes_superuser_sees_all_institutions(
        self, api_client, institution, other_institution
    ):
        from apps.documents.tests.conftest import MinutesFactory

        user = User.objects.create_user(email="root2@test.edu", auth_source="local", password="p")
        user.is_superuser = True
        user.save()
        _login(api_client, user, institution)
        MinutesFactory(institution=institution, created_by=user)
        MinutesFactory(institution=other_institution, created_by=user)
        r = api_client.get(reverse("documents:minutes-list"))
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    def test_minutes_update_signed_document_409(self, api_client, institution, write_user):
        """An acta becomes immutable once its backing document is signed (RF-D07)."""
        from apps.documents.tests.conftest import MinutesFactory

        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        minutes = MinutesFactory(institution=institution, document=doc, created_by=write_user)
        # Sign the backing document AFTER the minutes row exists (model guard
        # rejects creating an acta for an already-signed document).
        version = DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        DigitalSignatureFactory(document_version=version, signer=write_user, sha256=version.sha256)
        Document.objects.filter(pk=doc.pk).update(is_signed=True)
        r = api_client.patch(
            reverse("documents:minutes-detail", kwargs={"pk": minutes.pk}),
            {"acta_type": "cierre"},
            content_type="application/json",
        )
        assert r.status_code == 409

    def test_minutes_delete_signed_document_409(self, api_client, institution, write_user):
        from apps.documents.tests.conftest import Minutes, MinutesFactory

        _login(api_client, write_user, institution)
        doc = _acta_document(institution, write_user)
        minutes = MinutesFactory(institution=institution, document=doc, created_by=write_user)
        version = DocumentVersionFactory(document=doc, version=1, uploaded_by=write_user)
        DigitalSignatureFactory(document_version=version, signer=write_user, sha256=version.sha256)
        Document.objects.filter(pk=doc.pk).update(is_signed=True)
        r = api_client.delete(reverse("documents:minutes-detail", kwargs={"pk": minutes.pk}))
        assert r.status_code == 409
        assert Minutes.objects.filter(pk=minutes.pk).exists()

    def test_minutes_auditor_write_denied_403(self, api_client, institution, auditor_user):
        _login(api_client, auditor_user, institution)
        r = api_client.post(
            reverse("documents:minutes-list"),
            {"acta_type": "inicio", "document": str(uuid.uuid4())},
            content_type="application/json",
        )
        assert r.status_code == 403
