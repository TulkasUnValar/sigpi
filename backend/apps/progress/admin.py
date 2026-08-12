"""Django admin registration for progress models.

Registers all 4 entities:
ProgressReport → ProgressReview → ProgressDocument → ProgressStateLog.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "project",
        "status",
        "cumulative_percentage",
        "period_start",
        "period_end",
        "created_by",
        "created_at",
    ]
    search_fields = ["description", "activities"]
    list_filter = ["status", "institution"]
    raw_id_fields = ["institution", "project", "created_by"]


@admin.register(ProgressReview)
class ProgressReviewAdmin(admin.ModelAdmin):
    list_display = [
        "progress_report",
        "reviewed_by",
        "review_type",
        "created_at",
    ]
    search_fields = ["review_text"]
    list_filter = ["review_type"]
    raw_id_fields = ["progress_report", "reviewed_by"]


@admin.register(ProgressDocument)
class ProgressDocumentAdmin(admin.ModelAdmin):
    list_display = ["progress_report", "name", "doc_type", "uploaded_at"]
    search_fields = ["name"]
    list_filter = ["doc_type"]
    raw_id_fields = ["progress_report"]


@admin.register(ProgressStateLog)
class ProgressStateLogAdmin(admin.ModelAdmin):
    list_display = [
        "progress_report",
        "from_state",
        "to_state",
        "triggered_by",
        "created_at",
    ]
    list_filter = ["from_state", "to_state"]
    raw_id_fields = ["progress_report", "triggered_by"]
