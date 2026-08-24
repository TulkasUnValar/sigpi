"""
Admin tests for the documents app — STRICT TDD.

Verifies registration of the 5 models and the read-only rules for
signed documents (RF-066) and append-only version/signature admins.

Spec reference:  openspec/changes/attachments/specs/documents/spec.md
Design reference: openspec/changes/attachments/design.md

RED PHASE: Tests fail because admin.py does not exist.
"""

import pytest
from django.test import RequestFactory

from apps.documents.models import (
    DigitalSignature,
    Document,
    DocumentType,
    DocumentVersion,
    Minutes,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_signed_document(institution, user):
    """Document with one signed version — immutable per RF-066."""
    from apps.documents.tests.conftest import DocumentTypeFactory

    doc = Document.objects.create(
        institution=institution,
        doc_type=DocumentTypeFactory(),
        title="Signed Doc",
        created_by=user,
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version=1,
        object_key=f"documents/{institution.id}/{doc.id}/v1/file.pdf",
        sha256="a" * 64,
        size_bytes=2048,
        mime_type="application/pdf",
        uploaded_by=user,
    )
    DigitalSignature.objects.create(
        document_version=version,
        signer=user,
        sha256="a" * 64,
        signer_metadata={"ip": "127.0.0.1"},
    )
    return doc


def _admin_request(user=None):
    from django.contrib.auth.models import AnonymousUser

    req = RequestFactory().get("/admin/")
    req.user = user or AnonymousUser()
    return req


# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 5 models are registered in the Django admin."""

    @pytest.mark.parametrize(
        "model",
        [DocumentType, Document, DocumentVersion, DigitalSignature, Minutes],
    )
    def test_model_registered(self, model):
        """Model appears in admin.site._registry."""
        from django.contrib import admin

        assert model in admin.site._registry


# ──────────────────────────────────────────────
# Signed-Document Read-Only Tests
# ──────────────────────────────────────────────


class TestDocumentAdminReadOnly:
    """Signed documents are read-only in the admin (task 2.4)."""

    def _admin(self):
        from apps.documents.admin import DocumentAdmin

        return DocumentAdmin(Document, admin_site=None)

    def test_signed_document_all_fields_readonly(self, db):
        """get_readonly_fields returns every field for a signed document."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = _make_signed_document(inst, user)
        admin = self._admin()
        readonly = set(admin.get_readonly_fields(_admin_request(user), doc))
        assert readonly == {f.name for f in Document._meta.fields}

    def test_unsigned_document_keeps_base_readonly(self, db):
        """Unsigned documents keep only base readonly fields."""
        from apps.documents.tests.conftest import DocumentTypeFactory

        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Draft", created_by=user
        )
        admin = self._admin()
        readonly = set(admin.get_readonly_fields(_admin_request(user), doc))
        assert "title" not in readonly
        assert "is_signed" not in readonly

    def test_signed_document_delete_forbidden(self, db):
        """has_delete_permission returns False for a signed document."""
        from apps.accounts.models import User

        inst = _make_institution("TU")
        user = _make_user("admin@test.edu")
        superuser = User.objects.create_superuser(email="root@test.edu", password="x")
        doc = _make_signed_document(inst, user)
        admin = self._admin()
        assert admin.has_delete_permission(_admin_request(superuser), doc) is False

    def test_unsigned_document_delete_allowed_for_superuser(self, db):
        """has_delete_permission returns True for an unsigned document."""
        from apps.accounts.models import User
        from apps.documents.tests.conftest import DocumentTypeFactory

        inst = _make_institution("TU")
        user = _make_user()
        superuser = User.objects.create_superuser(email="root2@test.edu", password="x")
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Draft", created_by=user
        )
        admin = self._admin()
        assert admin.has_delete_permission(_admin_request(superuser), doc) is True


# ──────────────────────────────────────────────
# Append-Only Admin Tests
# ──────────────────────────────────────────────


class TestAppendOnlyAdmin:
    """Version and Signature admins are append-only."""

    def test_version_admin_blocks_add_change_delete(self):
        """DocumentVersionAdmin forbids add/change/delete."""
        from apps.documents.admin import DocumentVersionAdmin

        admin = DocumentVersionAdmin(DocumentVersion, admin_site=None)
        req = _admin_request()
        assert admin.has_add_permission(req) is False
        assert admin.has_change_permission(req) is False
        assert admin.has_delete_permission(req) is False

    def test_signature_admin_blocks_add_change_delete(self):
        """DigitalSignatureAdmin forbids add/change/delete."""
        from apps.documents.admin import DigitalSignatureAdmin

        admin = DigitalSignatureAdmin(DigitalSignature, admin_site=None)
        req = _admin_request()
        assert admin.has_add_permission(req) is False
        assert admin.has_change_permission(req) is False
        assert admin.has_delete_permission(req) is False
