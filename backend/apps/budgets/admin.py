"""Django admin registration for budgets models.

Registers all 5 entities:
Budget → BudgetLine → FundingSource → BudgetExecution → BudgetAttachment.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.

Design reference: openspec/changes/budgets/design.md
"""

from django.contrib import admin

from .models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    FundingSource,
)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status",
        "project",
        "institution",
        "approved_amount",
        "created_at",
    ]
    search_fields = ["name"]
    list_filter = ["status", "institution"]
    raw_id_fields = ["project", "institution"]


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ["budget", "name", "approved_amount"]
    search_fields = ["name"]
    list_filter = ["budget"]
    raw_id_fields = ["budget"]


@admin.register(FundingSource)
class FundingSourceAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "amount"]
    search_fields = ["name"]
    list_filter = ["project"]
    raw_id_fields = ["project"]


@admin.register(BudgetExecution)
class BudgetExecutionAdmin(admin.ModelAdmin):
    list_display = ["line", "amount", "executed_at", "authorized_by", "authorized_at"]
    list_filter = ["executed_at"]
    raw_id_fields = ["line", "authorized_by"]


@admin.register(BudgetAttachment)
class BudgetAttachmentAdmin(admin.ModelAdmin):
    list_display = ["budget", "name", "doc_type", "external_url", "created_at"]
    search_fields = ["name"]
    list_filter = ["doc_type"]
    raw_id_fields = ["budget"]
