"""Django admin registration for accounts models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import InstitutionMembership, Role, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin — email is the identifier, no username."""

    ordering = ["email"]
    list_display = [
        "email",
        "auth_source",
        "is_active",
        "is_superuser",
        "last_login",
        "date_joined",
    ]
    list_filter = ["auth_source", "is_active", "is_superuser"]
    search_fields = ["email", "keycloak_uuid"]
    readonly_fields = ["date_joined", "last_login", "id"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Keycloak",
            {"fields": ("keycloak_uuid", "auth_source")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Timestamps", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "auth_source",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "keycloak_role_name"]
    list_filter = ["level"]
    search_fields = ["name", "keycloak_role_name"]
    ordering = ["level"]


@admin.register(InstitutionMembership)
class InstitutionMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "institution", "role", "is_primary", "is_active", "joined_at"]
    list_filter = ["is_primary", "is_active", "role", "institution"]
    search_fields = ["user__email", "institution__name"]
    raw_id_fields = ["user", "institution", "role"]
    filter_horizontal = ["centers"]
