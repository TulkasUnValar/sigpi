"""Django admin registration for institutions models.

Registers all 6 entities of the hierarchy:
Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""
from django.contrib import admin

from .models import (
    Facultad,
    Institution,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
    Sede,
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "status", "description", "is_active", "created_at"]
    search_fields = ["name", "code"]
    list_filter = ["is_active"]


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "code", "status", "is_active"]
    search_fields = ["name", "code", "institution__name"]
    list_filter = ["status", "is_active", "institution"]
    raw_id_fields = ["institution"]


@admin.register(Facultad)
class FacultadAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "sede", "code", "status", "is_active"]
    search_fields = ["name", "code", "institution__name"]
    list_filter = ["status", "is_active", "institution"]
    raw_id_fields = ["institution", "sede"]


@admin.register(ResearchCenter)
class ResearchCenterAdmin(admin.ModelAdmin):
    list_display = [
        "name", "institution", "code", "status", "description", "is_active",
    ]
    search_fields = ["name", "code", "institution__name"]
    list_filter = ["is_active", "institution"]
    raw_id_fields = ["institution"]


@admin.register(ResearchGroup)
class ResearchGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "center", "code", "status", "is_active"]
    search_fields = ["name", "code", "institution__name", "center__name"]
    list_filter = ["status", "is_active", "institution", "center"]
    raw_id_fields = ["institution", "center"]


@admin.register(ResearchLine)
class ResearchLineAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "group", "code", "status", "is_active"]
    search_fields = ["name", "code", "institution__name", "group__name"]
    list_filter = ["status", "is_active", "institution", "group"]
    raw_id_fields = ["institution", "group"]
