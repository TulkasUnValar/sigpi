"""
Notifications module — transversal tenant-safe notification models (SIGPI §13.5).

Implements the data model defined in design.md and spec.md:
- Notification: in-app notification row, denormalized institution for RLS,
  unique event tuple (recipient, event_type, entity_type, entity_id) for dedup
- NotificationTemplate: catalog of renderable templates (seeded for 4 event types)
- NotificationLog: log-only email delivery record written by the Celery stub
- UserPreference: per-user channel opt-out (email enabled/disabled)

Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
Spec reference:   openspec/changes/notifications/spec.md — Data Model

No GenericForeignKey: entity links are explicit (entity_type + entity_id) columns.
"""

import uuid

from django.db import models

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class NotificationChannel(models.TextChoices):
    """Delivery channels supported by the notifications module."""

    EMAIL = "email", "Email"


class NotificationLogStatus(models.TextChoices):
    """Delivery status of a NotificationLog record."""

    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


# ──────────────────────────────────────────────
# NotificationTemplate
# ──────────────────────────────────────────────


class NotificationTemplate(models.Model):
    """Renderable catalog template for a notification event type.

    Catalog data: seeded by migration 0001 for the 4 event types and
    visible to every tenant (global RLS policy). An inactive template
    suppresses notification creation (spec RN-* inactive-template skip).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Event-type code this template renders (e.g. PROJECT_SUBMITTED)",
    )
    title_template = models.CharField(max_length=255)
    body_template = models.TextField()
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive templates suppress notification creation",
    )

    class Meta:
        db_table = "notifications_notificationtemplate"
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


# ──────────────────────────────────────────────
# Notification
# ──────────────────────────────────────────────


class Notification(models.Model):
    """In-app notification delivered synchronously inside the sender transaction.

    Design decisions:
    - institution FK is denormalized for O(1) RLS tenant isolation
    - unique (recipient, event_type, entity_type, entity_id) tuple makes
      receiver get_or_create idempotent under retries
    - entity_type/entity_id are explicit nullable columns — never a
      GenericForeignKey
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="Denormalized institution for RLS tenant isolation",
    )
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    event_type = models.CharField(max_length=50, db_index=True)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    context = models.JSONField(default=dict)
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notification"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "event_type", "entity_type", "entity_id"],
                name="uniq_notif_event_per_recipient",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="idx_notif_recipient_read_created",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} — {self.recipient.email}"


# ──────────────────────────────────────────────
# NotificationLog
# ──────────────────────────────────────────────


class NotificationLog(models.Model):
    """Log-only email delivery record written by the dispatch task (no SMTP).

    notification FK is nullable to allow log-only records; CASCADE keeps
    the RLS scope invariant (a log always inherits its notification's
    institution while the notification exists).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="logs",
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    recipient_email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=NotificationLogStatus.choices,
        default=NotificationLogStatus.PENDING,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_notificationlog"
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.recipient_email} — {self.status}"


# ──────────────────────────────────────────────
# UserPreference
# ──────────────────────────────────────────────


class UserPreference(models.Model):
    """Per-user channel opt-out (email enabled/disabled).

    Preferences are user-global: one row per user (unique FK), scoped
    through the caller's active institution membership for RLS.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_userpreference"
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"
        ordering = ["user"]

    def __str__(self) -> str:
        return f"{self.user.email} — {self.channel}"
