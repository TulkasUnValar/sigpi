from django.apps import AppConfig


class ProjectWorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.project_workflow"
    verbose_name = "Project Workflow"

    def ready(self):
        """Import signal receivers when the app is ready."""
        import apps.project_workflow.signals  # noqa: F401
