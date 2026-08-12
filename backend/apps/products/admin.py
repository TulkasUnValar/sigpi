"""Django admin registration for products models.

Registers all 3 entities:
ResearchProduct → ProductAuthor → ProductAttachment.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import (
    ProductAttachment,
    ProductAuthor,
    ResearchProduct,
)


@admin.register(ResearchProduct)
class ResearchProductAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "type",
        "publication_year",
        "project",
        "institution",
        "created_at",
    ]
    search_fields = ["title", "description"]
    list_filter = ["type", "publication_year", "institution"]
    raw_id_fields = [
        "institution",
        "project",
        "created_by",
        "updated_by",
    ]


@admin.register(ProductAuthor)
class ProductAuthorAdmin(admin.ModelAdmin):
    list_display = ["product", "researcher", "is_principal", "order"]
    search_fields = ["researcher__first_name", "researcher__last_name"]
    list_filter = ["is_principal"]
    raw_id_fields = ["product", "researcher"]


@admin.register(ProductAttachment)
class ProductAttachmentAdmin(admin.ModelAdmin):
    list_display = ["product", "name", "doc_type", "external_url", "created_at"]
    search_fields = ["name"]
    list_filter = ["doc_type"]
    raw_id_fields = ["product"]
