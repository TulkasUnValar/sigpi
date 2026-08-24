"""
Model tests for the documents app — STRICT TDD.

Tests define the expected model behavior for the 5-entity documents
module: DocumentType, Document, DocumentVersion, DigitalSignature,
Minutes. Admin read-only rules live in test_admin.py.

Spec reference:  openspec/changes/attachments/specs/documents/spec.md
Design reference: openspec/changes/attachments/design.md

RED PHASE: All tests fail because models.py does not exist.
"""

import re
import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.documents.models import (
    DOCUMENT_TYPES,
    DigitalSignature,
    Document,
    DocumentType,
    DocumentVersion,
    EntityType,
    Minutes,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

DOC_TYPE_CODES = {
    "acta_inicio",
    "acta_comite",
    "acta_aprobacion",
    "acta_cierre",
    "formulacion_proyecto",
    "informe_parcial",
    "informe_final",
    "evidencia_producto",
    "presupuesto",
    "carta_aval",
    "certificacion",
    "otro",
}


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


def _make_report(institution, created_by):
    from apps.reports.models import Report, ReportType

    return Report.objects.create(
        title="Test Report",
        report_type=ReportType.PROJECT,
        entity_id=uuid.uuid4(),
        institution=institution,
        created_by=created_by,
    )


def _make_signed_document(institution, user):
    """Document with one signed version — immutable per RF-066."""
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


# Import factories after model imports (local to avoid import order issues).
from apps.documents.tests.conftest import (  # noqa: E402
    DigitalSignatureFactory,
    DocumentFactory,
    DocumentTypeFactory,
    DocumentVersionFactory,
    MinutesFactory,
)

# ──────────────────────────────────────────────
# DocumentType Tests
# ──────────────────────────────────────────────


class TestDocumentType:
    """DocumentType: 12 fixed codes seeded by migration 0001_initial."""

    def test_document_types_constant_has_exactly_12(self):
        """DOCUMENT_TYPES defines exactly the 12 SPEC §6.7 codes."""
        assert len(DOCUMENT_TYPES) == 12
        codes = {code for code, _label in DOCUMENT_TYPES}
        assert codes == DOC_TYPE_CODES
        assert all(label for _code, label in DOCUMENT_TYPES)

    def test_seed_migration_populates_12_types(self, db):
        """After migrations, DocumentType holds exactly the 12 fixed rows."""
        assert DocumentType.objects.count() == 12
        codes = set(DocumentType.objects.values_list("code", flat=True))
        assert codes == DOC_TYPE_CODES

    def test_duplicate_code_rejected(self, db):
        """UniqueConstraint on code rejects duplicate DocumentType rows."""
        from django.db import IntegrityError, transaction

        DocumentType.objects.create(code="custom_type", label="First")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DocumentType.objects.create(code="custom_type", label="Second")

    def test_str_returns_label(self, db):
        """DocumentType __str__ returns the human label."""
        dt = DocumentType.objects.get(code="acta_inicio")
        assert str(dt) == dt.label
        assert dt.label


# ──────────────────────────────────────────────
# Document Tests
# ──────────────────────────────────────────────


class TestDocumentFields:
    """Document model field behavior and defaults."""

    def test_create_document_minimal(self, db):
        """Document persists UUID pk, institution, doc_type, title, flags."""
        inst = _make_institution("TU")
        user = _make_user("owner@test.edu")
        doc = Document.objects.create(
            institution=inst,
            doc_type=DocumentType.objects.get(code="informe_parcial"),
            title="Parcial Q1",
            created_by=user,
        )
        assert isinstance(doc.id, uuid.UUID)
        assert doc.institution == inst
        assert doc.doc_type.code == "informe_parcial"
        assert doc.title == "Parcial Q1"
        assert doc.is_signed is False
        assert doc.entity_type is None
        assert doc.project_id is None
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_str_representation(self, db):
        """Document __str__ returns the title."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Acta", created_by=user
        )
        assert str(doc) == "Acta"

    def test_entity_type_enum(self):
        """EntityType exposes the 4 bindable entity kinds."""
        assert {c[0] for c in EntityType.choices} == {"advance", "report", "product", "call"}


class TestDocumentEntityBinding:
    """Document.clean() enforces entity_type ↔ explicit FK consistency."""

    def test_clean_accepts_entity_type_with_matching_fk(self, db):
        """entity_type=call with call FK set passes clean()."""
        inst = _make_institution("TU")
        call = _make_call(inst)
        doc = Document(
            institution=inst,
            doc_type=DocumentTypeFactory(),
            title="Acta Comite",
            entity_type=EntityType.CALL,
            call=call,
        )
        doc.full_clean()  # must not raise

    def test_clean_rejects_entity_type_without_fk(self, db):
        """entity_type set without the matching FK raises ValidationError."""
        inst = _make_institution("TU")
        doc = Document(
            institution=inst,
            doc_type=DocumentTypeFactory(),
            title="Acta",
            entity_type=EntityType.CALL,
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_clean_rejects_entity_fk_without_entity_type(self, db):
        """Entity FK set without entity_type raises ValidationError."""
        inst = _make_institution("TU")
        call = _make_call(inst)
        doc = Document(
            institution=inst,
            doc_type=DocumentTypeFactory(),
            title="Acta",
            call=call,
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_clean_rejects_conflicting_entity_fks(self, db):
        """Two entity FKs under one entity_type raises ValidationError."""
        inst = _make_institution("TU")
        user = _make_user()
        call = _make_call(inst)
        report = _make_report(inst, user)
        doc = Document(
            institution=inst,
            doc_type=DocumentTypeFactory(),
            title="Acta",
            entity_type=EntityType.CALL,
            call=call,
            report=report,
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_clean_accepts_report_binding(self, db):
        """entity_type=report with report FK set passes clean()."""
        inst = _make_institution("TU")
        user = _make_user()
        report = _make_report(inst, user)
        doc = Document(
            institution=inst,
            doc_type=DocumentTypeFactory(),
            title="Evidencia",
            entity_type=EntityType.REPORT,
            report=report,
        )
        doc.full_clean()  # must not raise


class TestDocumentImmutability:
    """RF-066 model layer: clean() rejects modification of signed docs."""

    def test_clean_rejects_signed_document_modification(self, db):
        """full_clean() on a signed document raises ValidationError."""
        inst = _make_institution("TU")
        user = _make_user("signer@test.edu")
        doc = _make_signed_document(inst, user)
        assert doc.versions.first().signatures.exists()  # setup proof: version is signed
        doc.title = "Tampered"
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_clean_allows_unsigned_document_modification(self, db):
        """full_clean() on an unsigned document passes."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Draft", created_by=user
        )
        doc.title = "Renamed"
        doc.full_clean()  # must not raise

    def test_clean_allows_new_signed_flag_on_unsigned_doc(self, db):
        """A document without signed versions may still flip is_signed."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Draft", created_by=user
        )
        doc.is_signed = True
        doc.full_clean()  # must not raise — no version is signed yet


# ──────────────────────────────────────────────
# DocumentVersion Tests
# ──────────────────────────────────────────────


class TestDocumentVersionFields:
    """DocumentVersion field behavior, sha256 format, and ordering."""

    def test_create_version(self, db):
        """Version persists upload metadata (RF-D02)."""
        inst = _make_institution("TU")
        user = _make_user("uploader@test.edu")
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key=f"documents/{inst.id}/{doc.id}/v1/file.pdf",
            sha256="ab" * 32,
            size_bytes=4096,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        assert v.document == doc
        assert v.version == 1
        assert v.object_key == f"documents/{inst.id}/{doc.id}/v1/file.pdf"
        assert v.sha256 == "ab" * 32
        assert v.size_bytes == 4096
        assert v.mime_type == "application/pdf"
        assert v.uploaded_by == user
        assert v.uploaded_at is not None

    def test_sha256_accepts_lowercase_hex_64(self, db):
        """64-char lowercase hex sha256 passes clean()."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion(
            document=doc,
            version=1,
            object_key="k",
            sha256="0123456789abcdef" * 4,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        v.full_clean()  # must not raise

    def test_sha256_rejects_uppercase(self, db):
        """Uppercase hex sha256 raises ValidationError."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion(
            document=doc,
            version=1,
            object_key="k",
            sha256="A" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        with pytest.raises(ValidationError):
            v.full_clean()

    def test_sha256_rejects_short_hash(self, db):
        """Short sha256 raises ValidationError."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion(
            document=doc,
            version=1,
            object_key="k",
            sha256="abc123",
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        with pytest.raises(ValidationError):
            v.full_clean()

    def test_sha256_rejects_non_hex(self, db):
        """Non-hex characters raise ValidationError."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion(
            document=doc,
            version=1,
            object_key="k",
            sha256="z" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        with pytest.raises(ValidationError):
            v.full_clean()

    def test_version_zero_rejected(self, db):
        """version=0 raises ValidationError (version >= 1)."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        v = DocumentVersion(
            document=doc,
            version=0,
            object_key="k",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        with pytest.raises(ValidationError):
            v.full_clean()

    def test_versions_ordered_descending(self, db):
        """Meta ordering returns newest version first (RF-D03)."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key="k1",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        DocumentVersion.objects.create(
            document=doc,
            version=2,
            object_key="k2",
            sha256="b" * 64,
            size_bytes=2,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        versions = list(doc.versions.all())
        assert [v.version for v in versions] == [2, 1]


class TestDocumentVersionUnique:
    """UniqueConstraint (document, version) enforces version ordering."""

    def test_unique_constraint_declared(self):
        """Meta.constraints declares unique_version_per_document."""
        names = {c.name for c in DocumentVersion._meta.constraints}
        assert "unique_version_per_document" in names

    def test_duplicate_version_rejected(self, db):
        """Creating a second version row with same number raises."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key="k1",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        dup = DocumentVersion(
            document=doc,
            version=1,
            object_key="k1b",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        with pytest.raises(ValidationError):
            dup.full_clean()


# ──────────────────────────────────────────────
# DigitalSignature Tests
# ──────────────────────────────────────────────


class TestDigitalSignature:
    """DigitalSignature: one per version, sha256 format, metadata."""

    def test_create_signature(self, db):
        """Signature persists signer, signed_at, sha256, metadata."""
        inst = _make_institution("TU")
        user = _make_user("signer@test.edu")
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        version = DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key="k",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        sig = DigitalSignature.objects.create(
            document_version=version,
            signer=user,
            sha256="a" * 64,
            signer_metadata={"ip": "10.0.0.1", "agent": "pytest"},
        )
        assert sig.document_version == version
        assert sig.signer == user
        assert sig.sha256 == "a" * 64
        assert sig.signer_metadata == {"ip": "10.0.0.1", "agent": "pytest"}
        assert sig.signed_at is not None

    def test_invalid_sha256_rejected(self, db):
        """Signature sha256 must be 64-char lowercase hex."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        version = DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key="k",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        sig = DigitalSignature(
            document_version=version, signer=user, sha256="NOT_HEX", signer_metadata={}
        )
        with pytest.raises(ValidationError):
            sig.full_clean()

    def test_one_signature_per_version(self, db):
        """UniqueConstraint on document_version blocks re-signing."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Doc", created_by=user
        )
        version = DocumentVersion.objects.create(
            document=doc,
            version=1,
            object_key="k",
            sha256="a" * 64,
            size_bytes=1,
            mime_type="application/pdf",
            uploaded_by=user,
        )
        DigitalSignature.objects.create(
            document_version=version, signer=user, sha256="a" * 64, signer_metadata={}
        )
        dup = DigitalSignature(
            document_version=version, signer=user, sha256="a" * 64, signer_metadata={}
        )
        with pytest.raises(ValidationError):
            dup.full_clean()

    def test_unique_constraint_declared(self):
        """Meta.constraints declares unique_signature_per_version."""
        names = {c.name for c in DigitalSignature._meta.constraints}
        assert "unique_signature_per_version" in names


# ──────────────────────────────────────────────
# Minutes Tests
# ──────────────────────────────────────────────


class TestMinutes:
    """Minutes: 4 acta types, institution denormalization, immutability."""

    def test_acta_type_enum_has_four_values(self):
        """Minutes.ActaType defines inicio/comite/aprobacion/cierre."""
        assert {c[0] for c in Minutes.ActaType.choices} == {
            "inicio",
            "comite",
            "aprobacion",
            "cierre",
        }

    def test_create_minutes(self, db):
        """Minutes row links acta_type, project, institution, document."""
        inst = _make_institution("TU")
        user = _make_user("creator@test.edu")
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Acta", created_by=user
        )
        minutes = Minutes.objects.create(
            acta_type=Minutes.ActaType.INICIO,
            institution=inst,
            document=doc,
            created_by=user,
        )
        assert minutes.acta_type == "inicio"
        assert minutes.institution == inst
        assert minutes.document == doc
        assert minutes.created_by == user
        assert minutes.created_at is not None
        assert minutes.project_id is None

    def test_all_four_acta_types_valid(self, db):
        """Each of the 4 acta_type values passes full_clean()."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Acta", created_by=user
        )
        for acta in ("inicio", "comite", "aprobacion", "cierre"):
            m = Minutes(acta_type=acta, institution=inst, document=doc, created_by=user)
            m.full_clean()  # must not raise

    def test_invalid_acta_type_rejected(self, db):
        """Unknown acta_type raises ValidationError."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Acta", created_by=user
        )
        m = Minutes(acta_type="resolucion", institution=inst, document=doc, created_by=user)
        with pytest.raises(ValidationError):
            m.full_clean()

    def test_signed_document_acta_rejected(self, db):
        """Creating a Minutes for a signed document raises (RF-D07)."""
        inst = _make_institution("TU")
        user = _make_user("creator@test.edu")
        doc = _make_signed_document(inst, user)
        m = Minutes(
            acta_type=Minutes.ActaType.INICIO,
            institution=inst,
            document=doc,
            created_by=user,
        )
        with pytest.raises(ValidationError):
            m.full_clean()

    def test_str_representation(self, db):
        """Minutes __str__ includes acta type display."""
        inst = _make_institution("TU")
        user = _make_user()
        doc = Document.objects.create(
            institution=inst, doc_type=DocumentTypeFactory(), title="Acta", created_by=user
        )
        m = Minutes.objects.create(
            acta_type=Minutes.ActaType.COMITE,
            institution=inst,
            document=doc,
            created_by=user,
        )
        assert "Comité" in str(m)


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestFactories:
    """Factories produce valid persisted instances."""

    def test_document_factory(self, db):
        """DocumentFactory creates an unsigned document with all fields."""
        doc = DocumentFactory()
        assert doc.id is not None
        assert doc.institution_id is not None
        assert doc.doc_type_id is not None
        assert doc.title
        assert doc.is_signed is False

    def test_version_factory(self, db):
        """DocumentVersionFactory creates v1 with valid sha256."""
        v = DocumentVersionFactory()
        assert v.version >= 1
        assert re.fullmatch(r"[0-9a-f]{64}", v.sha256)
        assert v.object_key.startswith("documents/")

    def test_signature_factory(self, db):
        """DigitalSignatureFactory creates a signature for a version."""
        sig = DigitalSignatureFactory()
        assert sig.document_version_id is not None
        assert sig.signer_id is not None
        assert re.fullmatch(r"[0-9a-f]{64}", sig.sha256)
        assert sig.signed_at is not None

    def test_minutes_factory(self, db):
        """MinutesFactory creates an acta row backed by a document."""
        minutes = MinutesFactory()
        assert minutes.document_id is not None
        assert minutes.institution_id == minutes.document.institution_id
        assert minutes.acta_type in Minutes.ActaType.values
