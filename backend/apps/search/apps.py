from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Search"

    def ready(self):
        # Signals (post_save/post_delete receivers) land in PR 3 —
        # this stub keeps the app wiring in place for the foundation.
        pass
