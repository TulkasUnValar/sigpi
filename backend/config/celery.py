"""
Celery configuration for SIGPI backend.

Design reference: openspec/changes/auth/design.md — Role Sync Flow
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("sigpi")

# Use Django settings for configuration
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

# ──────────────────────────────────────────────────────────
# Beat Schedule
# ──────────────────────────────────────────────────────────

app.conf.beat_schedule = {
    "sync-keycloak-roles-every-5-min": {
        "task": "sync_keycloak_roles",
        "schedule": 300.0,  # Every 5 minutes (300 seconds)
        "options": {"expires": 240},  # Task expires after 4 minutes
    },
}

app.conf.timezone = "America/Bogota"
