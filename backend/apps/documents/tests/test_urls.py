"""
URL routing tests for the documents module — STRICT TDD (RED phase).

Verifies the Phase 5 API Contract routes from spec.md:
  /documents/types/                                GET
  /documents/presign/                              POST
  /documents/                                      GET, POST
  /documents/{id}/                                 GET, PATCH, DELETE
  /documents/{id}/confirm/                         POST
  /documents/{id}/versions/                        GET, POST
  /documents/{id}/versions/{v}/                    GET
  /documents/{id}/versions/{v}/sign/               POST
  /documents/{id}/download/                        GET
  /documents/{id}/signatures/                      GET
  /documents/{id}/signatures/{signature_id}/       GET
  /minutes/                                        GET, POST
  /minutes/{id}/                                   GET, PATCH, DELETE

RED PHASE: apps.documents.urls is an empty mount point and
views.py does not exist — every reverse()/resolve() fails.

Spec reference: openspec/changes/attachments/specs/documents/spec.md — API Contract
"""

from django.urls import resolve, reverse

DOC_ID = "11111111-2222-3333-4444-555555555555"
SIG_ID = "99999999-8888-7777-6666-555555555555"


class TestDocumentUrls:
    """DocumentViewSet routes (router + custom actions)."""

    def test_list_url(self):
        assert reverse("documents:document-list") == "/api/documents/"

    def test_detail_url(self):
        assert reverse("documents:document-detail", kwargs={"pk": DOC_ID}) == (
            f"/api/documents/{DOC_ID}/"
        )

    def test_types_url(self):
        assert reverse("documents:document-types") == "/api/documents/types/"

    def test_presign_url(self):
        assert reverse("documents:document-presign") == "/api/documents/presign/"

    def test_confirm_url(self):
        assert reverse("documents:document-confirm", kwargs={"pk": DOC_ID}) == (
            f"/api/documents/{DOC_ID}/confirm/"
        )

    def test_versions_url(self):
        assert reverse("documents:document-versions", kwargs={"pk": DOC_ID}) == (
            f"/api/documents/{DOC_ID}/versions/"
        )

    def test_version_detail_url(self):
        assert (
            reverse("documents:document-version-detail", kwargs={"pk": DOC_ID, "version": 2})
            == f"/api/documents/{DOC_ID}/versions/2/"
        )

    def test_sign_url(self):
        assert (
            reverse("documents:document-sign", kwargs={"pk": DOC_ID, "version": 1})
            == f"/api/documents/{DOC_ID}/versions/1/sign/"
        )

    def test_download_url(self):
        assert reverse("documents:document-download", kwargs={"pk": DOC_ID}) == (
            f"/api/documents/{DOC_ID}/download/"
        )

    def test_detail_roundtrip(self):
        url = reverse("documents:document-detail", kwargs={"pk": DOC_ID})
        match = resolve(url)
        assert match.kwargs["pk"] == DOC_ID

    def test_sign_roundtrip(self):
        url = reverse("documents:document-sign", kwargs={"pk": DOC_ID, "version": 3})
        match = resolve(url)
        assert match.kwargs["pk"] == DOC_ID
        assert match.kwargs["version"] == "3"


class TestDigitalSignatureUrls:
    """DigitalSignatureViewSet routes (read-only, nested under documents)."""

    def test_signatures_list_url(self):
        assert reverse("documents:document-signatures", kwargs={"pk": DOC_ID}) == (
            f"/api/documents/{DOC_ID}/signatures/"
        )

    def test_signature_detail_url(self):
        assert (
            reverse(
                "documents:document-signature-detail", kwargs={"pk": DOC_ID, "signature_pk": SIG_ID}
            )
            == f"/api/documents/{DOC_ID}/signatures/{SIG_ID}/"
        )

    def test_signatures_roundtrip(self):
        url = reverse("documents:document-signatures", kwargs={"pk": DOC_ID})
        assert str(resolve(url).kwargs["pk"]) == DOC_ID


class TestMinutesUrls:
    """MinutesViewSet routes."""

    def test_list_url(self):
        assert reverse("documents:minutes-list") == "/api/minutes/"

    def test_detail_url(self):
        assert reverse("documents:minutes-detail", kwargs={"pk": DOC_ID}) == (
            f"/api/minutes/{DOC_ID}/"
        )

    def test_detail_roundtrip(self):
        url = reverse("documents:minutes-detail", kwargs={"pk": DOC_ID})
        assert resolve(url).kwargs["pk"] == DOC_ID


class TestConfigMount:
    """Root config/urls.py wiring — /api/documents/ and /api/minutes/."""

    def test_config_mounts_documents(self):
        match = resolve("/api/documents/")
        assert match.func.cls.__name__ == "DocumentViewSet"

    def test_config_mounts_minutes(self):
        match = resolve("/api/minutes/")
        assert match.func.cls.__name__ == "MinutesViewSet"

    def test_config_mounts_document_detail(self):
        match = resolve(f"/api/documents/{DOC_ID}/")
        assert match.func.cls.__name__ == "DocumentViewSet"
        assert match.kwargs["pk"] == DOC_ID
