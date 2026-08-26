"""Django admin registration for notifications models.

Registers all 4 entities:
Notification → NotificationTemplate → NotificationLog → UserPreference.

Each admin exposes list_display, search_fields, list_filter, and raw_id_fields
suitable for multi-tenant management with FK-heavy models.
"""

from django.contrib import admin

from .models import (
    Notification,
    NotificationLog,
    NotificationTemplate,
    UserPreference,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "recipient",
        "event_type",
        "is_read",
        "institution",
        "created_at",
    ]
    search_fields = ["title", "body", "recipient__email", "event_type"]
    list_filter = ["is_read", "event_type", "institution"]
    raw_id_fields = ["institution", "recipient", "template"]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["code", "title_template", "is_active"]
    search_fields = ["code", "title_template", "body_template"]
    list_filter = ["is_active"]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        "recipient_email",
        "notification",
        "channel",
        "status",
        "attempt_count",
        "created_at",
    ]
    search_fields = ["recipient_email", "last_error"]
    list_filter = ["channel", "status"]
    raw_id_fields = ["notification"]


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "channel", "enabled", "updated_at"]
    search_fields = ["user__email"]
    list_filter = ["channel", "enabled"]
    raw_id_fields = ["user"]
