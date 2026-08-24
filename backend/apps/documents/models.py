"""
Documents — Attachments, Acts and Digital Signature module (SIGPI §6.7).

Implements the data model defined in design.md and spec.md:
- DocumentType: 12 fixed types per SPEC §6.7 (seeded by 0001_initial)
- Document: institution-scoped metadata row, nullable explicit entity
  FKs (Project, ProgressReport, Report, ResearchProduct, Call), signed flag
- DocumentVersion: immutable upload history, unique (document, version),
  server-verified SHA-256 (64 lowercase hex)
- DigitalSignature: one per version, locks the version (RF-066)
- Minutes: actas of 4 types backed by a Document

Design reference: openspec/changes/attachments/design.md
Spec reference:   openspec/changes/attachments/specs/documents/spec.md
"""

import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models

# ──────────────────────────────────────────────
# Fixed Document Types (SPEC §6.7) — seeded by migration 0001_initial
# ──────────────────────────────────────────────

DOCUMENT_TYPES: list[tuple[str, str]] = [
    ("acta_inicio", "Acta de Inicio"),
    ("acta_comite", "Acta de Comité"),
    ("acta_aprobacion", "Acta de Aprobación"),
    ("acta_cierre", "Acta de Cierre"),
    ("formulacion_proyecto", "Formulación de Proyecto"),
    ("informe_parcial", "Informe Parcial"),
    ("informe_final", "Informe Final"),
    ("evidencia_producto", "Evidencia de Producto"),
    ("presupuesto", "Presupuesto"),
    ("carta_aval", "Carta Aval"),
    ("certificacion", "Certificación"),
    ("otro", "Otro"),
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class EntityType(models.TextChoices):
    """Bindable entity kinds for Document (explicit FK set, no GFK)."""

    ADVANCE = "advance", "Advance"
    REPORT = "report", "Report"
    PRODUCT = "product", "Product"
    CALL = "call", "Call"


# ──────────────────────────────────────────────
# DocumentType
# ──────────────────────────────────────────────


class DocumentType(models.Model):
    """Fixed document type code/label pair (12 rows, SPEC §6.7).

    The authoritative closed choice set is the seeded table; services
    and serializers read from here (RF-D08). Rows are inserted by the
    ``0001_initial`` data migration.
    """

    code = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_documenttype"
        verbose_name = "Document Type"
        verbose_name_plural = "Document Types"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.label


# ──────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────


class Document(models.Model):
    """Metadata row for an object stored in MinIO.

    Institution-scoped with denormalized institution_id for RLS.
    Entity binding uses explicit nullable FKs — no GenericForeignKey
    (design decision: referential integrity + RLS).

    Field-level constraints:
      - RF-D08: doc_type is a FK to the 12-row DocumentType table.
      - RF-066: clean() raises when any version is signed (immutable).
      - entity_type/FK consistency validated in clean().
    """

    # entity_type value → explicit FK field name
    ENTITY_FIELDS = {
        EntityType.ADVANCE: "progress",
        EntityType.REPORT: "report",
        EntityType.PRODUCT: "product",
        EntityType.CALL: "call",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attached_documents",
    )
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        null=True,
        blank=True,
    )
    progress = models.ForeignKey(
        "progress.ProgressReport",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attached_documents",
    )
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attached_documents",
    )
    product = models.ForeignKey(
        "products.ResearchProduct",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attached_documents",
    )
    call = models.ForeignKey(
        "calls.Call",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attached_documents",
    )
    doc_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    is_signed = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_document"
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["institution", "is_signed"],
                name="idx_doc_inst_signed",
            ),
            models.Index(
                fields=["doc_type"],
                name="idx_doc_type",
            ),
            models.Index(
                fields=["entity_type"],
                name="idx_doc_entity_type",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        errors = {}

        # entity_type ↔ explicit FK consistency.
        if self.entity_type:
            field = self.ENTITY_FIELDS.get(self.entity_type)
            if field is None:
                errors["entity_type"] = f"Unknown entity type: {self.entity_type}"
            else:
                if not getattr(self, f"{field}_id"):
                    errors["entity_type"] = (
                        f"entity_type '{self.entity_type}' requires a {field} reference."
                    )
                for other in self.ENTITY_FIELDS.values():
                    if other != field and getattr(self, f"{other}_id"):
                        errors[other] = (
                            f"Cannot combine {other} with entity_type '{self.entity_type}'."
                        )
        else:
            for field in self.ENTITY_FIELDS.values():
                if getattr(self, f"{field}_id"):
                    errors[field] = f"{field} reference requires entity_type to be set."

        # RF-066: signed documents are immutable at the model layer too.
        if self.pk and self.versions.filter(signatures__isnull=False).exists():
            errors["__all__"] = "Signed documents are immutable"

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# DocumentVersion
# ──────────────────────────────────────────────


class DocumentVersion(models.Model):
    """Immutable upload-history row (RF-D03).

    A new row is created on every re-upload with an incremented
    ``version``; unique (document, version) enforces ordering at the
    database level. ``sha256`` is the server-verified object hash
    (64 lowercase hex chars, RF-D04).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version = models.PositiveIntegerField()
    object_key = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64)
    size_bytes = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_versions",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_documentversion"
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"
        ordering = ["document", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version"],
                name="unique_version_per_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_id} v{self.version}"

    def clean(self):
        super().clean()
        errors = {}
        if self.version is not None and self.version < 1:
            errors["version"] = "Version must be >= 1."
        if self.sha256 and not _SHA256_RE.fullmatch(self.sha256):
            errors["sha256"] = "sha256 must be a 64-character lowercase hexadecimal string."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# DigitalSignature
# ──────────────────────────────────────────────


class DigitalSignature(models.Model):
    """SHA-256 digital signature locking one document version (RF-D04).

    One signature per version (unique document_version). The hash is
    computed server-side from the MinIO object bytes — frontend-supplied
    hashes are never trusted. Signing makes the document immutable
    (RF-066) via ``Document.clean()``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name="signatures",
    )
    signer = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signatures",
    )
    signed_at = models.DateTimeField(auto_now_add=True)
    sha256 = models.CharField(max_length=64)
    signer_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "documents_digitalsignature"
        verbose_name = "Digital Signature"
        verbose_name_plural = "Digital Signatures"
        ordering = ["-signed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document_version"],
                name="unique_signature_per_version",
            ),
        ]

    def __str__(self) -> str:
        return f"signature v{self.document_version.version} by {self.signer or 'unknown'}"

    def clean(self):
        super().clean()
        if self.sha256 and not _SHA256_RE.fullmatch(self.sha256):
            raise ValidationError(
                {"sha256": "sha256 must be a 64-character lowercase hexadecimal string."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# Minutes
# ──────────────────────────────────────────────


class Minutes(models.Model):
    """Acta (minutes) of four types, backed by an acta_* Document (RF-D07).

    Institution-scoped with denormalized institution_id for RLS.
    A Minutes row is immutable once its backing document is signed.
    """

    class ActaType(models.TextChoices):
        INICIO = "inicio", "Inicio"
        COMITE = "comite", "Comité"
        APROBACION = "aprobacion", "Aprobación"
        CIERRE = "cierre", "Cierre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    acta_type = models.CharField(max_length=20, choices=ActaType.choices)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minutes",
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="minutes",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="minutes",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="minutes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_minutes"
        verbose_name = "Minutes"
        verbose_name_plural = "Minutes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["institution", "acta_type"],
                name="idx_minutes_inst_type",
            ),
            models.Index(
                fields=["project"],
                name="idx_minutes_project",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_acta_type_display()} ({self.document_id})"

    def clean(self):
        super().clean()
        # RF-D07: an acta backed by a signed document is immutable.
        if self.document_id and self.document.versions.filter(signatures__isnull=False).exists():
            raise ValidationError({"document": "Signed documents are immutable"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
