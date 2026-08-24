"""Phase 1 tests: storage configuration and presigned URL generation.

Covers PR 1 infrastructure: MinIO/S3 settings wiring (task 1.3) and the
MinIOStorage backend with presigned PUT/GET helpers (task 1.5).

Spec: openspec/changes/attachments/specs/documents/spec.md — MinIO/S3 Contract:
- Storage MUST use django-storages S3 backend against MinIO; bucket MUST be private.
- Object keys MUST follow documents/{institution_id}/{document_id}/v{version}/{filename}.
- Presigned PUT URLs MUST expire within 30 minutes; GET within 15 minutes.

The storage instance under test is resolved through Django's storage
framework (``storages["default"]``) so OPTIONS injection from STORAGES
is exercised — the same path production code uses.
"""

import pytest
from django.conf import settings
from django.core.files.storage import storages

from apps.documents.storage import MinIOStorage


@pytest.fixture
def storage():
    return storages["default"]


class TestStorageSettings:
    """STORAGES + MINIO_* wiring in config/settings/base.py."""

    def test_default_storage_backend_is_minio_storage(self):
        assert settings.STORAGES["default"]["BACKEND"] == "apps.documents.storage.MinIOStorage"

    def test_default_storage_options_follow_minio_settings(self):
        opts = settings.STORAGES["default"]["OPTIONS"]
        assert opts["endpoint_url"] == settings.MINIO_ENDPOINT
        assert opts["bucket_name"] == settings.MINIO_BUCKET_NAME
        assert opts["access_key"] == settings.MINIO_ACCESS_KEY
        assert opts["secret_key"] == settings.MINIO_SECRET_KEY

    def test_presign_expiry_settings_defaults(self):
        # Spec: PUT <= 30 min (1800 s), GET <= 15 min (900 s)
        assert settings.MINIO_PRESIGN_PUT_EXPIRY == 1800
        assert settings.MINIO_PRESIGN_GET_EXPIRY == 900

    def test_documents_app_is_installed(self):
        assert "apps.documents" in settings.INSTALLED_APPS

    def test_storages_app_is_installed(self):
        assert "storages" in settings.INSTALLED_APPS


class TestMinIOStorage:
    """MinIOStorage backend behavior."""

    def test_default_storage_resolves_to_minio_storage(self, storage):
        assert isinstance(storage, MinIOStorage)

    def test_instance_reads_minio_options(self, storage):
        assert storage.bucket_name == settings.MINIO_BUCKET_NAME
        assert storage.endpoint_url == settings.MINIO_ENDPOINT
        assert storage.querystring_expire == settings.MINIO_PRESIGN_GET_EXPIRY
        assert storage.querystring_auth is True

    def test_build_object_key_matches_spec_scheme(self, storage):
        key = storage.build_object_key(
            institution_id="0a1b2c3d-1111-4222-8333-444455556666",
            document_id="0a1b2c3d-aaaa-4bbb-8ccc-ddddeeeeffff",
            version=1,
            filename="informe_final.pdf",
        )
        assert (
            key == "documents/0a1b2c3d-1111-4222-8333-444455556666/"
            "0a1b2c3d-aaaa-4bbb-8ccc-ddddeeeeffff/v1/informe_final.pdf"
        )

    def test_build_object_key_with_version_bump(self, storage):
        key = storage.build_object_key("inst-2", "doc-9", 12, "acta.pdf")
        assert key == "documents/inst-2/doc-9/v12/acta.pdf"

    def test_presign_put_issues_url_expiring_in_30_minutes(self, storage, monkeypatch):
        captured = {}

        def fake_generate_presigned_url(**kwargs):
            captured.update(kwargs)
            return f"https://minio.example/upload?X-Amz-Expires={kwargs['ExpiresIn']}"

        monkeypatch.setattr(
            storage.connection.meta.client,
            "generate_presigned_url",
            fake_generate_presigned_url,
        )

        url = storage.presign_put("documents/inst-1/doc-1/v1/file.pdf")

        assert url == "https://minio.example/upload?X-Amz-Expires=1800"
        assert captured["ClientMethod"] == "put_object"
        assert captured["Params"] == {
            "Bucket": settings.MINIO_BUCKET_NAME,
            "Key": "documents/inst-1/doc-1/v1/file.pdf",
        }

    def test_presign_get_issues_url_expiring_in_15_minutes(self, storage, monkeypatch):
        captured = {}

        def fake_generate_presigned_url(**kwargs):
            captured.update(kwargs)
            return f"https://minio.example/download?X-Amz-Expires={kwargs['ExpiresIn']}"

        monkeypatch.setattr(
            storage.connection.meta.client,
            "generate_presigned_url",
            fake_generate_presigned_url,
        )

        url = storage.presign_get("documents/inst-1/doc-1/v1/file.pdf")

        assert url == "https://minio.example/download?X-Amz-Expires=900"
        assert captured["ClientMethod"] == "get_object"
        assert captured["Params"] == {
            "Bucket": settings.MINIO_BUCKET_NAME,
            "Key": "documents/inst-1/doc-1/v1/file.pdf",
        }

    def test_presign_put_respects_custom_expiry(self, storage, monkeypatch):
        captured = {}

        def fake_generate_presigned_url(**kwargs):
            captured.update(kwargs)
            return f"https://minio.example/upload?X-Amz-Expires={kwargs['ExpiresIn']}"

        monkeypatch.setattr(
            storage.connection.meta.client,
            "generate_presigned_url",
            fake_generate_presigned_url,
        )

        storage.presign_put("documents/inst-1/doc-1/v1/file.pdf", expires=120)

        assert captured["ExpiresIn"] == 120

    def test_presign_get_respects_custom_expiry(self, storage, monkeypatch):
        captured = {}

        def fake_generate_presigned_url(**kwargs):
            captured.update(kwargs)
            return f"https://minio.example/download?X-Amz-Expires={kwargs['ExpiresIn']}"

        monkeypatch.setattr(
            storage.connection.meta.client,
            "generate_presigned_url",
            fake_generate_presigned_url,
        )

        storage.presign_get("documents/inst-1/doc-1/v1/file.pdf", expires=60)

        assert captured["ExpiresIn"] == 60
