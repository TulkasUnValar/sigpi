"""Django admin registration for project_workflow models.

Registers all 4 entities:
WorkflowTemplate → WorkflowStep → WorkflowInstance → WorkflowAction.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import (
    WorkflowAction,
    WorkflowInstance,
    WorkflowStep,
    WorkflowTemplate,
)


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "center", "is_active", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["is_active", "institution"]
    raw_id_fields = ["institution", "center"]


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ["template", "order", "name", "role_required", "deadline_days"]
    search_fields = ["name", "template__name"]
    list_filter = ["role_required"]
    raw_id_fields = ["template"]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ["project_id", "institution", "template", "status", "deadline_date", "created_at"]
    search_fields = ["project_id"]
    list_filter = ["status", "institution"]
    raw_id_fields = ["institution", "template", "current_step"]


@admin.register(WorkflowAction)
class WorkflowActionAdmin(admin.ModelAdmin):
    list_display = ["instance", "action", "acted_by", "created_at"]
    search_fields = ["observation_text", "instance__project_id"]
    list_filter = ["action"]
    raw_id_fields = ["instance", "step", "acted_by"]
