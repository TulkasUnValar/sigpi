"""
End-to-end MinIO flow for the documents module — STRICT TDD (RED phase).

Covers the spec Acceptance Criteria: "Presign → upload → confirm → sign →
query flow works end-to-end against the MinIO compose service."

This suite requires a running MinIO service (docker compose up -d minio) and
MINIO_E2E=1. It is skipped in the default test run (no local MinIO daemon in
the dev environment — same as PRs 1-4 runtime harness gap).

Flow exercised:
  1. POST /api/documents/presign/   → upload_url + object_key
  2. PUT object bytes to MinIO      → real S3 PUT via boto3
  3. POST /api/documents/{id}/confirm/ → DocumentVersion v1 + DOCUMENT_UPLOADED
  4. POST /api/documents/{id}/versions/{v}/sign/ → signature + is_signed lock
  5. GET  /api/documents/?is_signed=true → signed document + signature metadata

Spec reference: openspec/changes/attachments/specs/documents/spec.md
"""

import hashlib
import os

import pytest
from django.core.files.storage import storages
from django.test import Client
from django.urls import reverse

from apps.accounts.models import AuditEvent, InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.documents.models import Document, DocumentType
from apps.institutions.models import Institution

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("MINIO_E2E") != "1",
        reason="MinIO e2e requires MINIO_E2E=1 and a running MinIO compose service",
    ),
]


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="E2E University", code="E2E01")


@pytest.fixture
def write_user(db, institution):
    role = get_role("Asistente")
    user = User.objects.create_user(email="e2e@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=role, is_active=True
    )
    return user


class TestMinIOEndToEnd:
    def test_presign_upload_confirm_sign_query(self, api_client, institution, write_user):
        _login(api_client, write_user, institution)

        # 1. presign
        r = api_client.post(
            reverse("documents:document-presign"),
            {
                "doc_type": "acta_inicio",
                "filename": "acta_e2e.pdf",
                "content_type": "application/pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        presigned = r.json()
        assert set(presigned.keys()) == {"upload_url", "object_key", "document_id"}

        # 2. real S3 PUT via the configured MinIO backend
        storage = storages["default"]
        content = b"%PDF-1.4 e2e acta bytes"
        storage.connection.meta.client.put_object(
            Bucket=storage.bucket_name,
            Key=presigned["object_key"],
            Body=content,
            ContentType="application/pdf",
        )

        # 3. confirm
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
        assert r.json()["version"] == 1
        assert AuditEvent.objects.filter(event_type="DOCUMENT_UPLOADED").exists()

        # 4. sign (server fetches bytes and recomputes SHA-256)
        r = api_client.post(
            reverse(
                "documents:document-sign",
                kwargs={"pk": presigned["document_id"], "version": 1},
            )
        )
        assert r.status_code == 201
        assert r.json()["sha256"] == hashlib.sha256(content).hexdigest()
        assert Document.objects.get(pk=presigned["document_id"]).is_signed is True
        assert AuditEvent.objects.filter(event_type="DOCUMENT_SIGNED").exists()

        # 5. signed-document query with signature metadata
        r = api_client.get(reverse("documents:document-list"), {"is_signed": "true"})
        assert r.status_code == 200
        matches = [item for item in r.json() if item["id"] == presigned["document_id"]]
        assert len(matches) == 1
        assert matches[0]["signature"]["sha256"] == hashlib.sha256(content).hexdigest()
        assert matches[0]["doc_type"]["code"] == DocumentType.objects.get(code="acta_inicio").code
