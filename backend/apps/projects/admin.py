"""Django admin registration for projects models.

Registers all 5 entities:
Project → ProjectMember → ProjectDocument → ProjectObservation → ProjectStateLog.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "status",
        "center",
        "institution",
        "principal_investigator",
        "start_date",
        "is_active",
    ]
    search_fields = ["title", "keywords"]
    list_filter = ["status", "center", "institution"]
    raw_id_fields = [
        "institution",
        "center",
        "group",
        "line",
        "principal_investigator",
    ]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ["project", "researcher", "role", "joined_at"]
    search_fields = ["researcher__first_name", "researcher__last_name"]
    list_filter = ["role"]
    raw_id_fields = ["project", "researcher"]


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ["project", "name", "doc_type", "uploaded_at"]
    search_fields = ["name"]
    list_filter = ["doc_type"]
    raw_id_fields = ["project"]


@admin.register(ProjectObservation)
class ProjectObservationAdmin(admin.ModelAdmin):
    list_display = ["project", "observed_by", "created_at"]
    search_fields = ["observation_text"]
    raw_id_fields = ["project", "observed_by"]


@admin.register(ProjectStateLog)
class ProjectStateLogAdmin(admin.ModelAdmin):
    list_display = ["project", "from_state", "to_state", "triggered_by", "created_at"]
    list_filter = ["from_state", "to_state"]
    raw_id_fields = ["project", "triggered_by"]
