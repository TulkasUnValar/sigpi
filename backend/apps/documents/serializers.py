"""
DRF serializers for the documents module (Phase 4.2).

Provides the API contract serializers from design.md:
- DocumentTypeSerializer — code/label; authoritative seeded table (read-only)
- DocumentSerializer — metadata with derived current_version and signature
  metadata; only title is writable (entity/type/institution locked at presign)
- DocumentVersionSerializer — append-only upload history (RF-D03)
- DigitalSignatureSerializer — append-only signature record (RF-D04)
- MinutesSerializer — acta_type/project/document writable; institution and
  audit fields set by the view/service (RF-D07)

Design reference: openspec/changes/attachments/design.md — Serializer Mapping
Spec reference:   openspec/changes/attachments/specs/documents/spec.md
"""

from django.db.models import Max
from rest_framework import serializers

from apps.documents.models import (
    DigitalSignature,
    Document,
    DocumentType,
    DocumentVersion,
    Minutes,
)

# ──────────────────────────────────────────────
# DocumentTypeSerializer
# ──────────────────────────────────────────────


class DocumentTypeSerializer(serializers.ModelSerializer):
    """Read-only view of the seeded 12-row DocumentType table (RF-D08)."""

    class Meta:
        model = DocumentType
        fields = ["id", "code", "label"]
        read_only_fields = ["id", "code", "label"]


# ──────────────────────────────────────────────
# DocumentSerializer
# ──────────────────────────────────────────────


class DocumentSerializer(serializers.ModelSerializer):
    """Document metadata row.

    Read-only: institution, entity binding, doc_type, is_signed, and the
    derived current_version / signature fields. Only title is writable —
    signed documents are additionally protected by the model clean() guard
    (RF-066) and the service layer.
    """

    doc_type = DocumentTypeSerializer(read_only=True)
    entity_id = serializers.SerializerMethodField()
    current_version = serializers.SerializerMethodField()
    signature = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
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
        ]
        read_only_fields = [
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
        ]

    def get_entity_id(self, obj):
        """Return the pk of whichever explicit entity FK is bound."""
        for field in Document.ENTITY_FIELDS.values():
            fk_id = getattr(obj, f"{field}_id", None)
            if fk_id:
                return str(fk_id)
        return None

    def get_current_version(self, obj):
        """Derived current version = max version row (RF-D03)."""
        return obj.versions.aggregate(max_version=Max("version"))["max_version"]

    def get_signature(self, obj):
        """Latest signature metadata for signed queries (RF-D05)."""
        signature = (
            DigitalSignature.objects.filter(document_version__document=obj)
            .select_related("signer")
            .order_by("-signed_at")
            .first()
        )
        if signature is None:
            return None
        return {
            "signer": signature.signer.email if signature.signer else None,
            "signed_at": signature.signed_at.isoformat(),
            "sha256": signature.sha256,
        }


# ──────────────────────────────────────────────
# DocumentVersionSerializer
# ──────────────────────────────────────────────


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Append-only version history row — created only by DocumentService."""

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "version",
            "object_key",
            "sha256",
            "size_bytes",
            "mime_type",
            "uploaded_by",
            "uploaded_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────
# DigitalSignatureSerializer
# ──────────────────────────────────────────────


class DigitalSignatureSerializer(serializers.ModelSerializer):
    """Append-only signature record — created only by SignatureService."""

    class Meta:
        model = DigitalSignature
        fields = [
            "id",
            "document_version",
            "signer",
            "signed_at",
            "sha256",
            "signer_metadata",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────
# MinutesSerializer
# ──────────────────────────────────────────────


class MinutesSerializer(serializers.ModelSerializer):
    """Minutes (acta) row. institution/created_by set by the view/service."""

    class Meta:
        model = Minutes
        fields = [
            "id",
            "acta_type",
            "project",
            "institution",
            "document",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "created_by",
            "created_at",
            "updated_at",
        ]
