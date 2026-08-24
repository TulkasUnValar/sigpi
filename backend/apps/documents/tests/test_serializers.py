"""
Serializer tests for the documents module — STRICT TDD (RED phase).

Covers the Phase 4 serializer contracts from design.md:
- DocumentTypeSerializer: code/label, read-only.
- DocumentSerializer: institution/entity/doc_type/is_signed read-only,
  title writable, derived current_version and signature metadata.
- DocumentVersionSerializer / DigitalSignatureSerializer: append-only.
- MinutesSerializer: acta_type/project/document writable, institution
  and audit fields read-only.

RED PHASE: serializers.py does not exist yet — all tests fail on import.
"""

from apps.documents.models import (
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
    return DocumentType.objects.get(code="acta_inicio")


# ════════════════════════════════════════════════════════
# DocumentTypeSerializer
# ════════════════════════════════════════════════════════


class TestDocumentTypeSerializer:
    def test_fields(self, db):
        from apps.documents.serializers import DocumentTypeSerializer

        doc_type = DocumentType.objects.get(code="acta_inicio")
        data = DocumentTypeSerializer(instance=doc_type).data

        assert set(data.keys()) == {"id", "code", "label"}
        assert data["code"] == "acta_inicio"
        assert data["label"]

    def test_all_fields_read_only(self, db):
        from apps.documents.serializers import DocumentTypeSerializer

        assert DocumentTypeSerializer.Meta.read_only_fields == [
            "id",
            "code",
            "label",
        ]


# ════════════════════════════════════════════════════════
# DocumentSerializer
# ════════════════════════════════════════════════════════


class TestDocumentSerializer:
    def test_fields(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        data = DocumentSerializer(instance=doc).data

        assert set(data.keys()) == {
            "id",
            "institution",
            "project",
            "entity_type",
            "entity_id",
            "doc_type",
            "title",
            "is_signed",
            "current_version",
            "signature",
            "created_by",
            "created_at",
            "updated_at",
        }
        assert data["id"] == str(doc.pk)
        assert data["title"] == doc.title
        assert data["is_signed"] is False
        assert data["entity_type"] is None
        assert data["entity_id"] is None

    def test_doc_type_nested_with_code_and_label(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        data = DocumentSerializer(instance=doc).data

        assert data["doc_type"]["code"] == "acta_inicio"
        assert set(data["doc_type"].keys()) == {"id", "code", "label"}

    def test_current_version_derived_from_latest_row(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
        DocumentVersionFactory(document=doc, version=2, uploaded_by=user)

        data = DocumentSerializer(instance=doc).data

        assert data["current_version"] == 2

    def test_current_version_none_without_versions(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        data = DocumentSerializer(instance=doc).data

        assert data["current_version"] is None

    def test_signature_none_when_unsigned(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        data = DocumentSerializer(instance=doc).data

        assert data["signature"] is None

    def test_signature_metadata_when_signed(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        version = DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
        DigitalSignatureFactory(document_version=version, signer=user, sha256=version.sha256)

        data = DocumentSerializer(instance=doc).data

        assert data["signature"]["signer"] == user.email
        assert data["signature"]["sha256"] == version.sha256
        assert data["signature"]["signed_at"]

    def test_entity_id_resolves_bound_fk(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        call = _make_call(institution)
        doc = DocumentFactory(
            institution=institution,
            doc_type=_acta_type(),
            created_by=user,
            entity_type="call",
            call=call,
        )

        data = DocumentSerializer(instance=doc).data

        assert data["entity_type"] == "call"
        assert data["entity_id"] == str(call.pk)

    def test_read_only_fields(self, db):
        from apps.documents.serializers import DocumentSerializer

        assert set(DocumentSerializer.Meta.read_only_fields) == {
            "id",
            "institution",
            "project",
            "entity_type",
            "entity_id",
            "doc_type",
            "is_signed",
            "current_version",
            "signature",
            "created_by",
            "created_at",
            "updated_at",
        }

    def test_title_writable_on_partial_update(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        serializer = DocumentSerializer(instance=doc, data={"title": "Renamed"}, partial=True)
        assert serializer.is_valid() is True
        updated = serializer.save()
        updated.refresh_from_db()

        assert updated.title == "Renamed"

    def test_read_only_fields_ignored_on_write(self, db):
        from apps.documents.serializers import DocumentSerializer

        institution = _make_institution()
        other = _make_institution("B")
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)

        serializer = DocumentSerializer(
            instance=doc,
            data={"title": "New", "institution": other.pk, "is_signed": True},
            partial=True,
        )
        assert serializer.is_valid() is True
        updated = serializer.save()
        updated.refresh_from_db()

        assert updated.institution_id == institution.pk
        assert updated.is_signed is False


# ════════════════════════════════════════════════════════
# DocumentVersionSerializer
# ════════════════════════════════════════════════════════


class TestDocumentVersionSerializer:
    def test_fields(self, db):
        from apps.documents.serializers import DocumentVersionSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        version = DocumentVersionFactory(document=doc, version=1, uploaded_by=user)

        data = DocumentVersionSerializer(instance=version).data

        assert set(data.keys()) == {
            "id",
            "document",
            "version",
            "object_key",
            "sha256",
            "size_bytes",
            "mime_type",
            "uploaded_by",
            "uploaded_at",
        }
        assert data["version"] == 1
        assert data["sha256"] == version.sha256

    def test_all_fields_read_only(self, db):
        from apps.documents.serializers import DocumentVersionSerializer

        assert set(DocumentVersionSerializer.Meta.read_only_fields) == {
            "id",
            "document",
            "version",
            "object_key",
            "sha256",
            "size_bytes",
            "mime_type",
            "uploaded_by",
            "uploaded_at",
        }


# ════════════════════════════════════════════════════════
# DigitalSignatureSerializer
# ════════════════════════════════════════════════════════


class TestDigitalSignatureSerializer:
    def test_fields(self, db):
        from apps.documents.serializers import DigitalSignatureSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        version = DocumentVersionFactory(document=doc, version=1, uploaded_by=user)
        signature = DigitalSignatureFactory(
            document_version=version, signer=user, sha256=version.sha256
        )

        data = DigitalSignatureSerializer(instance=signature).data

        assert set(data.keys()) == {
            "id",
            "document_version",
            "signer",
            "signed_at",
            "sha256",
            "signer_metadata",
        }
        assert data["signer"] == user.pk
        assert data["sha256"] == version.sha256

    def test_all_fields_read_only(self, db):
        from apps.documents.serializers import DigitalSignatureSerializer

        assert set(DigitalSignatureSerializer.Meta.read_only_fields) == {
            "id",
            "document_version",
            "signer",
            "signed_at",
            "sha256",
            "signer_metadata",
        }


# ════════════════════════════════════════════════════════
# MinutesSerializer
# ════════════════════════════════════════════════════════


class TestMinutesSerializer:
    def test_fields(self, db):
        from apps.documents.serializers import MinutesSerializer

        institution = _make_institution()
        user = _make_user()
        doc = DocumentFactory(institution=institution, doc_type=_acta_type(), created_by=user)
        minutes = Minutes.objects.create(
            acta_type=Minutes.ActaType.INICIO,
            institution=institution,
            document=doc,
            created_by=user,
        )

        data = MinutesSerializer(instance=minutes).data

        assert set(data.keys()) == {
            "id",
            "acta_type",
            "project",
            "institution",
            "document",
            "created_by",
            "created_at",
            "updated_at",
        }
        assert data["acta_type"] == "inicio"
        assert data["document"] == doc.pk

    def test_read_only_fields(self, db):
        from apps.documents.serializers import MinutesSerializer

        assert set(MinutesSerializer.Meta.read_only_fields) == {
            "id",
            "institution",
            "created_by",
            "created_at",
            "updated_at",
        }

    def test_create_fields_writable(self, db):
        from apps.documents.serializers import MinutesSerializer

        writable = set(MinutesSerializer.Meta.fields) - set(MinutesSerializer.Meta.read_only_fields)
        assert writable == {"acta_type", "project", "document"}
