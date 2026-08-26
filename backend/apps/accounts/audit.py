"""
SIGPI Auth Audit Events.

Implements FR-007: The system MUST emit audit events for login, logout,
role change, and permission denied.

Design reference: openspec/changes/auth/design.md — AuditEventEmitter
"""

import uuid

from django.db import models
from django.utils import timezone

# ──────────────────────────────────────────────────────────
# AuditEventType (Enum via TextChoices)
# ──────────────────────────────────────────────────────────


class AuditEventType(models.TextChoices):
    """Types of auth audit events."""

    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    FAILED_LOGIN = "FAILED_LOGIN", "Failed Login"
    INSTITUTION_SWITCH = "INSTITUTION_SWITCH", "Institution Switch"
    ROLE_CHANGE = "ROLE_CHANGE", "Role Change"
    PERMISSION_DENIED = "PERMISSION_DENIED", "Permission Denied"
    PROGRESS_STATE_CHANGE = "PROGRESS_STATE_CHANGE", "Progress State Change"
    REPORT_GENERATED = "REPORT_GENERATED", "Report Generated"
    REPORT_APPROVED = "REPORT_APPROVED", "Report Approved"
    BUDGET_CREATED = "BUDGET_CREATED", "Budget Created"
    BUDGET_UPDATED = "BUDGET_UPDATED", "Budget Updated"
    BUDGET_EXECUTION_ADDED = "BUDGET_EXECUTION_ADDED", "Budget Execution Added"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Document Uploaded"
    DOCUMENT_SIGNED = "DOCUMENT_SIGNED", "Document Signed"
    MINUTES_CREATED = "MINUTES_CREATED", "Minutes Created"
    CREATE = "CREATE", "Created"
    UPDATE = "UPDATE", "Updated"
    DELETE = "DELETE", "Deleted"
    STATE_CHANGE = "STATE_CHANGE", "State Changed"
    DOCUMENT_DOWNLOADED = "DOCUMENT_DOWNLOADED", "Document Downloaded"


# ──────────────────────────────────────────────────────────
# AuditEvent Model
# ──────────────────────────────────────────────────────────


class AuditEvent(models.Model):
    """Records an auth-related event for audit purposes.

    Fields:
        id: UUID primary key.
        user: The Django User involved (nullable for failed logins).
        event_type: One of AuditEventType choices.
        timestamp: When the event occurred (auto-set on creation).
        ip_address: Client IP address.
        institution_id: Active institution at time of event (nullable).
        details: JSON-like dict with extra context (nullable).

    Design decisions:
        - Queryable: stored as a DB model, not just logs.
        - User nullable: failed login events may have no associated user.
        - Details: flexible JSON for event-specific data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(
        max_length=50,
        choices=AuditEventType.choices,
        db_index=True,
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    institution_id = models.UUIDField(null=True, blank=True, db_index=True)
    details = models.JSONField(null=True, blank=True)
    entity_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    action = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
    )
    old_values = models.JSONField(null=True, blank=True, default=dict)
    new_values = models.JSONField(null=True, blank=True, default=dict)
    project_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "accounts_auditevent"
        verbose_name = "Audit Event"
        verbose_name_plural = "Audit Events"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["project_id", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self) -> str:
        user_label = self.user.email if self.user else "anonymous"
        return f"{self.event_type} — {user_label} @ {self.timestamp.isoformat()}"


# ──────────────────────────────────────────────────────────
# AuditEventEmitter
# ──────────────────────────────────────────────────────────


class AuditEventEmitter:
    """Creates audit events programmatically.

    Usage:
        emitter = AuditEventEmitter()
        emitter.emit(
            event_type=AuditEventType.LOGIN,
            user=request.user,
            ip_address=AuditEventEmitter.extract_ip(request),
            institution_id=request.institution_id,
            details={"auth_source": "keycloak"},
        )
    """

    @staticmethod
    def extract_ip(request) -> str | None:
        """Extract the client IP address from a Django request.

        Checks X-Forwarded-For first, then falls back to REMOTE_ADDR.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded_for:
            # Take the first (client) IP in the chain
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def emit(
        self,
        event_type: str,
        user=None,
        ip_address: str | None = None,
        institution_id=None,
        details: dict | None = None,
        *,
        entity_type: str | None = None,
        entity_id=None,
        action: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        project_id=None,
    ) -> AuditEvent:
        """Create and persist an AuditEvent.

        Args:
            event_type: One of AuditEventType values.
            user: The Django User (optional).
            ip_address: Client IP (optional).
            institution_id: UUID of active institution (optional).
            details: Extra context dict (optional).
            entity_type: Type of the tracked entity (e.g. "project").
            entity_id: UUID of the tracked entity (optional).
            action: The CRUD action value (CREATE/UPDATE/DELETE/...).
            old_values: JSON-safe dict of the prior state (optional).
            new_values: JSON-safe dict of the new state (optional).
            project_id: UUID of the related project (optional).

        The first five parameters preserve the legacy signature — existing
        positional/keyword callers keep working unchanged. The traceability
        fields are keyword-only and forwarded verbatim to AuditEvent.

        Returns:
            The created AuditEvent instance.
        """
        event = AuditEvent.objects.create(
            user=user,
            event_type=event_type,
            ip_address=ip_address,
            institution_id=institution_id,
            details=details,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            project_id=project_id,
        )
        return event
