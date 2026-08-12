"""Django admin registration for calls models.

Registers all 4 entities:
Call → CallDocument → CallProject → CallStateLog.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import Call, CallDocument, CallProject, CallStateLog


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "status",
        "call_type",
        "institution",
        "submission_start",
        "submission_end",
    ]
    search_fields = ["title", "description"]
    list_filter = ["status", "call_type", "institution"]
    raw_id_fields = ["institution"]


@admin.register(CallDocument)
class CallDocumentAdmin(admin.ModelAdmin):
    list_display = ["call", "name", "doc_type", "created_at"]
    search_fields = ["name"]
    list_filter = ["doc_type"]
    raw_id_fields = ["call"]


@admin.register(CallProject)
class CallProjectAdmin(admin.ModelAdmin):
    list_display = ["call", "project", "linked_at"]
    raw_id_fields = ["call", "project"]


@admin.register(CallStateLog)
class CallStateLogAdmin(admin.ModelAdmin):
    list_display = ["call", "from_state", "to_state", "triggered_by", "created_at"]
    list_filter = ["from_state", "to_state"]
    raw_id_fields = ["call", "triggered_by"]
