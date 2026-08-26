from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Search"

    def ready(self):
        # Importing the receivers module connects every @receiver with a
        # dispatch_uid — ORM save/delete → on_commit → Celery enqueue.
        from apps.search import signals  # noqa: F401
