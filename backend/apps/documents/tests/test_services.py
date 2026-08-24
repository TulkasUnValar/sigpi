"""
Service tests for the documents module — STRICT TDD (RED phase).

Covers the Phase 4 service layer contracts from spec.md:
- DocumentService: presign key issue, confirm key-match → 409, version bump,
  entity institution check, DOCUMENT_UPLOADED audit.
- SignatureService: GET→SHA-256→sign→lock; 409 hash mismatch / re-sign /
  signed-bump; DOCUMENT_SIGNED audit.
- MinutesService: acta validation, project/institution consistency,
  MINUTES_CREATED audit.

Spec reference:  openspec/changes/attachments/specs/documents/spec.md
Design reference: openspec/changes/attachments/design.md

RED PHASE: services.py does not exist yet — all tests fail on import.
"""

import hashlib
import io
import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import AuditEvent
from apps.documents.models import (
    Document,
    DocumentType,
    Minutes,
)
from apps.documents.tests.conftest import (
    DigitalSignatureFactory,
    DocumentFactory,
    DocumentVersionFactory,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


class FakeStorage:
    """In-memory stand-in for MinIOStorage (presign/exists/open interface)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def build_object_key(self, institution_id, document_id, version, filename):
        return f"documents/{institution_id}/{document_id}/v{version}/{filename}"

    def presign_put(self, object_key, expires=None):
        return f"https://minio.example/put/{object_key}"

    def presign_get(self, object_key, expires=None):
        return f"https://minio.example/get/{object_key}"

    def exists(self, object_key):
        return object_key in self.objects

    def open(self, object_key, mode="rb"):
        return io.BytesIO(self.objects[object_key])

    def put(self, object_key, data):
        self.objects[object_key] = data


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_call(institution):
    from apps.calls.models import Call, CallType

    return Call.objects.create(
        institution=institution,
        title="Test Call",
        description="Desc",
        call_type=CallType.INTERNAL,
    )


def _acta_type():
    # Seeded by migration 0001_initial — factory would violate unique code.
    return DocumentType.objects.get(code="acta_inicio")


def _non_acta_type():
    return DocumentType.objects.get(code="informe_final")


def _signed_document(institution, user):
    """Document whose single version is signed (flag set via update, like the service)."""
    doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
    version = DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
    DigitalSignatureFactory(document_version=version, signer=user, sha256=version.sha256)
    Document.objects.filter(pk=doc.pk).update(is_signed=True)
    return doc


# ════════════════════════════════════════════════════════
# DocumentService.presign — new document + v1 key
# ════════════════════════════════════════════════════════


class TestPresignNewDocument:
    def test_returns_presigned_url_object_key_and_document_id(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        storage = FakeStorage()

        result = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            storage=storage,
        )

        assert set(result.keys()) == {"upload_url", "object_key", "document_id"}
        assert result["upload_url"].startswith("https://minio.example/put/")
        assert result["object_key"] == (
            f"documents/{institution.pk}/{result['document_id']}/v1/file.pdf"
        )
        assert uuid.UUID(result["document_id"])

    def test_creates_document_row_with_metadata(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        doc_type = _acta_type()

        result = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            storage=FakeStorage(),
        )

        doc = Document.objects.get(pk=result["document_id"])
        assert doc.institution_id == institution.pk
        assert doc.doc_type_id == doc_type.pk
        assert doc.title == "file.pdf"
        assert doc.created_by_id == user.pk
        assert doc.is_signed is False

    def test_unknown_doc_type_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="not_a_type",
                filename="file.pdf",
                content_type="application/pdf",
                storage=FakeStorage(),
            )

    def test_empty_filename_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="acta_inicio",
                filename="",
                content_type="application/pdf",
                storage=FakeStorage(),
            )

    def test_path_traversal_filename_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="acta_inicio",
                filename="../evil.pdf",
                content_type="application/pdf",
                storage=FakeStorage(),
            )

    def test_entity_institution_mismatch_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution("A")
        other = _make_institution("B")
        user = _make_user()
        call = _make_call(other)

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="acta_inicio",
                filename="file.pdf",
                content_type="application/pdf",
                entity_type="call",
                entity_id=call.pk,
                storage=FakeStorage(),
            )

    def test_unknown_entity_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="acta_inicio",
                filename="file.pdf",
                content_type="application/pdf",
                entity_type="call",
                entity_id=uuid.uuid4(),
                storage=FakeStorage(),
            )

    def test_entity_type_requires_entity_id(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()

        with pytest.raises(ValidationError):
            DocumentService.presign(
                institution=institution,
                user=user,
                doc_type="acta_inicio",
                filename="file.pdf",
                content_type="application/pdf",
                entity_type="call",
                entity_id=None,
                storage=FakeStorage(),
            )

    def test_binds_entity_fk(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        call = _make_call(institution)

        result = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            entity_type="call",
            entity_id=call.pk,
            storage=FakeStorage(),
        )

        doc = Document.objects.get(pk=result["document_id"])
        assert doc.entity_type == "call"
        assert doc.call_id == call.pk


# ════════════════════════════════════════════════════════
# DocumentService.presign_next_version — re-upload key
# ════════════════════════════════════════════════════════


class TestPresignNextVersion:
    def test_issues_key_for_next_version(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=user)

        result = DocumentService.presign_next_version(
            document=doc,
            user=user,
            filename="v2.pdf",
            content_type="application/pdf",
            storage=FakeStorage(),
        )

        assert result["version"] == 2
        assert result["object_key"] == (f"documents/{institution.pk}/{doc.pk}/v2/v2.pdf")
        assert result["upload_url"].startswith("https://minio.example/put/")

    def test_signed_document_rejected(self, db):
        from apps.documents.services import DocumentService, SignedDocumentImmutableError

        institution = _make_institution()
        user = _make_user()
        doc = _signed_document(institution, user)

        with pytest.raises(SignedDocumentImmutableError):
            DocumentService.presign_next_version(
                document=doc,
                user=user,
                filename="v2.pdf",
                content_type="application/pdf",
                storage=FakeStorage(),
            )


# ════════════════════════════════════════════════════════
# DocumentService.confirm — record version after upload
# ════════════════════════════════════════════════════════


class TestConfirmUpload:
    def test_confirms_upload_creates_version_v1(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        storage = FakeStorage()
        presign = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            storage=storage,
        )
        storage.put(presign["object_key"], b"file-content")

        version = DocumentService.confirm(
            document=Document.objects.get(pk=presign["document_id"]),
            object_key=presign["object_key"],
            user=user,
            size_bytes=12,
            mime_type="application/pdf",
            sha256=hashlib.sha256(b"file-content").hexdigest(),
            storage=storage,
        )

        assert version.version == 1
        assert version.uploaded_by_id == user.pk
        assert version.size_bytes == 12
        assert version.mime_type == "application/pdf"
        assert version.sha256 == hashlib.sha256(b"file-content").hexdigest()

    def test_confirm_emits_document_uploaded_audit(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        storage = FakeStorage()
        presign = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            storage=storage,
        )
        storage.put(presign["object_key"], b"file-content")

        DocumentService.confirm(
            document=Document.objects.get(pk=presign["document_id"]),
            object_key=presign["object_key"],
            user=user,
            size_bytes=12,
            mime_type="application/pdf",
            sha256="a" * 64,
            storage=storage,
        )

        event = AuditEvent.objects.get(event_type="DOCUMENT_UPLOADED")
        assert event.user_id == user.pk
        assert event.institution_id == institution.pk
        assert event.details["document_id"] == presign["document_id"]
        assert event.details["version"] == 1

    def test_wrong_object_key_rejected(self, db):
        from apps.documents.services import DocumentService, ObjectKeyMismatchError

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        # Key for the right document but a version that was never issued.
        with pytest.raises(ObjectKeyMismatchError):
            DocumentService.confirm(
                document=doc,
                object_key=f"documents/{institution.pk}/{doc.pk}/v99/other.pdf",
                user=user,
                size_bytes=1,
                mime_type="application/pdf",
                sha256="a" * 64,
                storage=FakeStorage(),
            )
        assert doc.versions.count() == 0

    def test_key_for_wrong_document_rejected(self, db):
        from apps.documents.services import DocumentService, ObjectKeyMismatchError

        institution = _make_institution()
        user = _make_user()
        doc_a = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        doc_b = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        wrong_key = f"documents/{institution.pk}/{doc_b.pk}/v1/file.pdf"
        with pytest.raises(ObjectKeyMismatchError):
            DocumentService.confirm(
                document=doc_a,
                object_key=wrong_key,
                user=user,
                size_bytes=1,
                mime_type="application/pdf",
                sha256="a" * 64,
                storage=FakeStorage(),
            )

    def test_reupload_bumps_version(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        storage = FakeStorage()
        presign = DocumentService.presign(
            institution=institution,
            user=user,
            doc_type="acta_inicio",
            filename="file.pdf",
            content_type="application/pdf",
            storage=storage,
        )
        doc = Document.objects.get(pk=presign["document_id"])
        storage.put(presign["object_key"], b"content-v1")
        DocumentService.confirm(
            document=doc,
            object_key=presign["object_key"],
            user=user,
            size_bytes=10,
            mime_type="application/pdf",
            sha256=hashlib.sha256(b"content-v1").hexdigest(),
            storage=storage,
        )

        next_presign = DocumentService.presign_next_version(
            document=doc,
            user=user,
            filename="v2.pdf",
            content_type="application/pdf",
            storage=storage,
        )
        storage.put(next_presign["object_key"], b"content-v2")
        DocumentService.confirm(
            document=doc,
            object_key=next_presign["object_key"],
            user=user,
            size_bytes=10,
            mime_type="application/pdf",
            sha256=hashlib.sha256(b"content-v2").hexdigest(),
            storage=storage,
        )

        versions = list(doc.versions.order_by("version"))
        assert [v.version for v in versions] == [1, 2]
        assert AuditEvent.objects.filter(event_type="DOCUMENT_UPLOADED").count() == 2

    def test_signed_document_version_bump_rejected(self, db):
        from apps.documents.services import DocumentService, SignedDocumentImmutableError

        institution = _make_institution()
        user = _make_user()
        doc = _signed_document(institution, user)

        with pytest.raises(SignedDocumentImmutableError):
            DocumentService.confirm(
                document=doc,
                object_key=f"documents/{institution.pk}/{doc.pk}/v2/file.pdf",
                user=user,
                size_bytes=1,
                mime_type="application/pdf",
                sha256="a" * 64,
                storage=FakeStorage(),
            )

    def test_object_missing_in_storage_rejected(self, db):
        from apps.documents.services import DocumentService

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        with pytest.raises(ValidationError):
            DocumentService.confirm(
                document=doc,
                object_key=f"documents/{institution.pk}/{doc.pk}/v1/file.pdf",
                user=user,
                size_bytes=1,
                mime_type="application/pdf",
                sha256="a" * 64,
                storage=FakeStorage(),
            )
        assert doc.versions.count() == 0

    def test_storage_unavailable_maps_to_503_error(self, db):
        from apps.documents.services import DocumentService, StorageUnavailableError

        class BrokenStorage(FakeStorage):
            def exists(self, object_key):
                raise ConnectionError("minio down")

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        with pytest.raises(StorageUnavailableError):
            DocumentService.confirm(
                document=doc,
                object_key=f"documents/{institution.pk}/{doc.pk}/v1/file.pdf",
                user=user,
                size_bytes=1,
                mime_type="application/pdf",
                sha256="a" * 64,
                storage=BrokenStorage(),
            )


# ════════════════════════════════════════════════════════
# SignatureService.sign — GET→SHA-256→sign→lock
# ════════════════════════════════════════════════════════


class TestSignVersion:
    def _unsigned_version(self, institution, user, data=b"file-content"):
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        storage = FakeStorage()
        version = DocumentVersionFactory(
            document=doc,
            version=1,
            sha256=hashlib.sha256(data).hexdigest(),
            uploaded_by=user,
        )
        storage.put(version.object_key, data)
        return doc, version, storage

    def test_signs_unsigned_version_and_locks_document(self, db):
        from apps.documents.services import SignatureService

        institution = _make_institution()
        user = _make_user()
        doc, version, storage = self._unsigned_version(institution, user)

        signature = SignatureService.sign(
            document=doc, version_number=1, user=user, storage=storage
        )

        assert signature.document_version_id == version.pk
        assert signature.signer_id == user.pk
        assert signature.sha256 == hashlib.sha256(b"file-content").hexdigest()
        # Lock applied via update() — must be visible when re-fetched.
        assert Document.objects.get(pk=doc.pk).is_signed is True

    def test_sign_emits_document_signed_audit(self, db):
        from apps.documents.services import SignatureService

        institution = _make_institution()
        user = _make_user()
        doc, version, storage = self._unsigned_version(institution, user)

        SignatureService.sign(document=doc, version_number=1, user=user, storage=storage)

        event = AuditEvent.objects.get(event_type="DOCUMENT_SIGNED")
        assert event.user_id == user.pk
        assert event.institution_id == institution.pk
        assert event.details["document_id"] == str(doc.pk)
        assert event.details["version"] == 1
        assert event.details["sha256"] == hashlib.sha256(b"file-content").hexdigest()

    def test_version_not_found(self, db):
        from apps.documents.services import SignatureService, VersionNotFoundError

        institution = _make_institution()
        user = _make_user()
        doc, _, storage = self._unsigned_version(institution, user)

        with pytest.raises(VersionNotFoundError):
            SignatureService.sign(document=doc, version_number=99, user=user, storage=storage)

    def test_re_sign_denied(self, db):
        from apps.documents.services import SignatureService, VersionAlreadySignedError

        institution = _make_institution()
        user = _make_user()
        doc, version, storage = self._unsigned_version(institution, user)
        SignatureService.sign(document=doc, version_number=1, user=user, storage=storage)

        with pytest.raises(VersionAlreadySignedError):
            SignatureService.sign(document=doc, version_number=1, user=user, storage=storage)

    def test_hash_mismatch_aborts_signing(self, db):
        from apps.documents.services import IntegrityCheckError, SignatureService

        institution = _make_institution()
        user = _make_user()
        doc, version, storage = self._unsigned_version(institution, user)
        # Tamper with the object AFTER confirm: bytes differ from recorded hash.
        storage.objects[version.object_key] = b"tampered-content"

        with pytest.raises(IntegrityCheckError):
            SignatureService.sign(document=doc, version_number=1, user=user, storage=storage)

        assert version.signatures.count() == 0
        assert Document.objects.get(pk=doc.pk).is_signed is False

    def test_signed_document_rejected(self, db):
        """Signing a NEW version of a locked document → immutable error (RF-066)."""
        from apps.documents.services import (
            SignatureService,
            SignedDocumentImmutableError,
        )

        institution = _make_institution()
        user = _make_user()
        doc = _signed_document(institution, user)
        # v1 is signed (document locked); v2 exists but is unsigned.
        DocumentVersionFactory(document=doc, version=2, uploaded_by=user)

        with pytest.raises(SignedDocumentImmutableError):
            SignatureService.sign(document=doc, version_number=2, user=user, storage=FakeStorage())

    def test_storage_unavailable_maps_to_503_error(self, db):
        from apps.documents.services import SignatureService, StorageUnavailableError

        class BrokenStorage(FakeStorage):
            def open(self, object_key, mode="rb"):
                raise ConnectionError("minio down")

        institution = _make_institution()
        user = _make_user()
        doc, version, _ = self._unsigned_version(institution, user)

        with pytest.raises(StorageUnavailableError):
            SignatureService.sign(
                document=doc, version_number=1, user=user, storage=BrokenStorage()
            )

    def test_lock_flag_bypasses_model_save_guard(self, db):
        """RF-066: after signing, a plain save() must still raise — the
        service must have used update() to flip is_signed."""
        from apps.documents.services import SignatureService

        institution = _make_institution()
        user = _make_user()
        doc, version, storage = self._unsigned_version(institution, user)

        SignatureService.sign(document=doc, version_number=1, user=user, storage=storage)

        fresh = Document.objects.get(pk=doc.pk)
        assert fresh.is_signed is True
        with pytest.raises(ValidationError):
            fresh.save()


# ════════════════════════════════════════════════════════
# MinutesService.create
# ════════════════════════════════════════════════════════


class TestMinutesService:
    def test_creates_minutes_and_emits_audit(self, db):
        from apps.documents.services import MinutesService

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        minutes = MinutesService.create(
            institution=institution,
            user=user,
            acta_type=Minutes.ActaType.INICIO,
            document=doc,
        )

        assert minutes.acta_type == "inicio"
        assert minutes.document_id == doc.pk
        assert minutes.institution_id == institution.pk
        assert minutes.created_by_id == user.pk
        event = AuditEvent.objects.get(event_type="MINUTES_CREATED")
        assert event.details["minutes_id"] == str(minutes.pk)
        assert event.details["acta_type"] == "inicio"

    def test_invalid_acta_type_rejected(self, db):
        from apps.documents.services import MinutesService

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        with pytest.raises(ValidationError):
            MinutesService.create(
                institution=institution,
                user=user,
                acta_type="not_an_acta",
                document=doc,
            )

    def test_non_acta_document_rejected(self, db):
        from apps.documents.services import MinutesService

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(
            institution=institution,
            doc_type=_non_acta_type(),
            created_by=user,
        )

        with pytest.raises(ValidationError):
            MinutesService.create(
                institution=institution,
                user=user,
                acta_type=Minutes.ActaType.INICIO,
                document=doc,
            )

    def test_document_from_other_institution_rejected(self, db):
        from apps.documents.services import MinutesService

        institution = _make_institution("A")
        other = _make_institution("B")
        user = _make_user()
        doc = DocumentFactory(institution=other, doc_type=_acta_type(), created_by=user)

        with pytest.raises(ValidationError):
            MinutesService.create(
                institution=institution,
                user=user,
                acta_type=Minutes.ActaType.INICIO,
                document=doc,
            )

    def test_project_from_other_institution_rejected(self, db):
        from apps.documents.services import MinutesService
        from apps.projects.tests.conftest import ProjectFactory

        institution = _make_institution("A")
        other = _make_institution("B")
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        project = ProjectFactory(institution=other)

        with pytest.raises(ValidationError):
            MinutesService.create(
                institution=institution,
                user=user,
                acta_type=Minutes.ActaType.INICIO,
                document=doc,
                project=project,
            )

    def test_signed_backing_document_rejected(self, db):
        from apps.documents.services import MinutesService

        institution = _make_institution()
        user = _make_user()
        doc = _signed_document(institution, user)

        with pytest.raises(ValidationError):
            MinutesService.create(
                institution=institution,
                user=user,
                acta_type=Minutes.ActaType.INICIO,
                document=doc,
            )
