"""
Django admin configuration for the documents app.

Registers the 5 models. Signed documents are read-only (RF-066):
- Document: every field becomes read-only and deletion is forbidden
  once the document is signed.
- Minutes: read-only and undeletable once the backing document is signed.
- DocumentVersion / DigitalSignature: append-only — no add/change/delete
  (immutable upload and signature history).

Spec reference:  openspec/changes/attachments/specs/documents/spec.md
Design reference: openspec/changes/attachments/design.md
"""

from django.contrib import admin

from .models import DigitalSignature, Document, DocumentType, DocumentVersion, Minutes


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    """Fixed document types — the authoritative 12-row choice set (RF-D08)."""

    list_display = ("code", "label")
    search_fields = ("code", "label")
    ordering = ("code",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Document metadata rows; signed documents are fully read-only."""

    list_display = ("title", "institution", "doc_type", "entity_type", "is_signed", "created_at")
    list_filter = ("doc_type", "entity_type", "is_signed")
    search_fields = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.versions.filter(signatures__isnull=False).exists():
            # RF-066: every field is read-only for signed documents.
            return [f.name for f in self.model._meta.fields] + fields
        return fields

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.versions.filter(signatures__isnull=False).exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    """Upload history — append-only (immutable version records, RF-D03)."""

    list_display = ("document", "version", "mime_type", "size_bytes", "uploaded_by", "uploaded_at")
    list_filter = ("mime_type",)
    search_fields = ("object_key",)
    readonly_fields = (
        "id",
        "document",
        "version",
        "object_key",
        "sha256",
        "size_bytes",
        "mime_type",
        "uploaded_by",
        "uploaded_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DigitalSignature)
class DigitalSignatureAdmin(admin.ModelAdmin):
    """Signature records — append-only (immutable signature history, RF-D04)."""

    list_display = ("document_version", "signer", "signed_at")
    search_fields = ("sha256",)
    readonly_fields = (
        "id",
        "document_version",
        "signer",
        "signed_at",
        "sha256",
        "signer_metadata",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Minutes)
class MinutesAdmin(admin.ModelAdmin):
    """Acta rows; read-only once the backing document is signed."""

    list_display = ("acta_type", "project", "institution", "document", "created_by", "created_at")
    list_filter = ("acta_type", "institution")
    search_fields = ("document__title",)
    readonly_fields = ("id", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.document.versions.filter(signatures__isnull=False).exists():
            # RF-D07: an acta backed by a signed document is immutable.
            return [f.name for f in self.model._meta.fields] + fields
        return fields

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.document.versions.filter(signatures__isnull=False).exists():
            return False
        return super().has_delete_permission(request, obj)
