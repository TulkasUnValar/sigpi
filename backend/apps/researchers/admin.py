"""Django admin registration for researchers models.

Registers all 4 entities:
Researcher → ResearcherAffiliation → ExternalProfile → ResearcherAttachment.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""
from django.contrib import admin

from .models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)


@admin.register(Researcher)
class ResearcherAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "document_number",
        "institution",
        "is_active",
        "completeness_score",
        "created_at",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "document_number",
        "primary_email",
    ]
    list_filter = ["is_active", "institution"]
    raw_id_fields = ["user", "institution"]

    @admin.display(description="Full Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description="Completeness")
    def completeness_score(self, obj):
        """Delegates to the service layer for consistency."""
        from .services import ResearcherProfileService

        return ResearcherProfileService.calculate_completeness(obj)


@admin.register(ResearcherAffiliation)
class ResearcherAffiliationAdmin(admin.ModelAdmin):
    list_display = ["researcher", "center", "group", "line", "is_primary"]
    search_fields = ["researcher__first_name", "researcher__last_name"]
    list_filter = ["is_primary"]
    raw_id_fields = ["researcher", "center", "group", "line"]


@admin.register(ExternalProfile)
class ExternalProfileAdmin(admin.ModelAdmin):
    list_display = ["researcher", "provider", "url"]
    search_fields = ["researcher__first_name", "researcher__last_name"]
    list_filter = ["provider"]
    raw_id_fields = ["researcher"]


@admin.register(ResearcherAttachment)
class ResearcherAttachmentAdmin(admin.ModelAdmin):
    list_display = ["researcher", "name", "attachment_type", "external_url"]
    search_fields = ["researcher__first_name", "name"]
    list_filter = ["type"]
    raw_id_fields = ["researcher"]

    @admin.display(description="Attachment Type")
    def attachment_type(self, obj):
        return obj.get_type_display()
