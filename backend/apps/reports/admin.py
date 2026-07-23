"""Django admin registration for reports models.

Registers Report, ReportTemplate, and ReportApproval with list_display,
search_fields, list_filter, and readonly_fields for audit timestamps.
"""

from django.contrib import admin

from apps.reports.models import Report, ReportApproval, ReportTemplate


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "report_type",
        "status",
        "institution",
        "created_by",
        "created_at",
    ]
    search_fields = [
        "title",
    ]
    list_filter = [
        "report_type",
        "status",
        "institution",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    raw_id_fields = [
        "institution",
        "created_by",
    ]


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "report_type",
        "institution",
        "is_active",
    ]
    search_fields = [
        "name",
    ]
    list_filter = [
        "report_type",
        "is_active",
    ]
    raw_id_fields = [
        "institution",
    ]


@admin.register(ReportApproval)
class ReportApprovalAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "report",
        "approved_by",
        "status",
        "approved_at",
    ]
    list_filter = [
        "status",
    ]
    readonly_fields = [
        "approved_at",
    ]
    raw_id_fields = [
        "report",
        "approved_by",
    ]
