"""Django app configuration for the researchers module."""
from django.apps import AppConfig


class ResearchersConfig(AppConfig):
    """Application config for the researchers app (SIGPI §6.3)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.researchers"
    verbose_name = "Researchers"
