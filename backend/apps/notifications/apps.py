from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        # Importing the receivers module connects every @receiver with a
        # dispatch_uid. Signals live in their emitting modules (design
        # decision — event boundary) to avoid circular imports.
        from apps.notifications import receivers  # noqa: F401
