"""
AuditConfig — app wiring for the audit module.

``ready()`` connects the CRUD signal receivers for the tracked models
using ``dispatch_uid`` (preventing duplicate connections).

Design reference: openspec/changes/audit/design.md
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self):
        """Connect CRUD audit signal receivers when the app is ready."""
        from apps.audit import signals

        signals.connect_signals()
