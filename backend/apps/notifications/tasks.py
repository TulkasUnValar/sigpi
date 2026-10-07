"""
Celery tasks for the notifications module — email dispatch (log-only).

Phase 3 delivery contract (design.md — Data Flow / Channel Semantics;
spec NFR Retry / Acceptance Criteria):

- dispatch_notification(notification_id, institution_id) writes a
  NotificationLog row per enabled email recipient with status=sent — STUB,
  no SMTP
- the task runs its protected reads/writes inside an explicit tenant context
  (``config.tenant_context.tenant_context``); ``institution_id`` is passed in
  by the enqueuer because the task cannot read ``notifications_notification``
  to discover it without that very context. A missing institution fails loudly
  (``ValueError``) instead of silently doing nothing.
- a missing Notification is skipped gracefully (warning, no raise)
- UserPreference email opt-out skips dispatch (the task double-checks
  the preference the receiver already checked before enqueuing)
- delivery failures persist last_error + attempt_count and retry up to
  3 times with exponential backoff (countdown 60×2^n)
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationLog,
    NotificationLogStatus,
    UserPreference,
)
from config.tenant_context import tenant_context

logger = logging.getLogger(__name__)

# Retry contract (spec NFR): up to 3 retries, exponential backoff 60×2^n.
MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 60


def email_channel_enabled(user) -> bool:
    """Email is enabled unless the user opted out via UserPreference.

    Default is enabled when no preference row exists (spec: enabled
    default true — "Default: both enabled").
    """
    preference = UserPreference.objects.filter(user=user, channel=NotificationChannel.EMAIL).first()
    return preference is None or preference.enabled


def _deliver_email_stub(notification):
    """Log-only delivery stub — never sends SMTP (spec Channel Semantics).

    A real email sender replaces this in a later change; it must raise
    on failure so the retry contract (backoff + attempt tracking) applies.
    """
    logger.info(
        "EMAIL STUB: would notify %s for notification %s (event %s)",
        notification.recipient.email,
        notification.pk,
        notification.event_type,
    )


@shared_task(bind=True, name="dispatch_notification", max_retries=MAX_RETRIES)
def dispatch_notification(self, notification_id, institution_id=None):
    """Deliver a Notification by email — log-only stub (no SMTP).

    ``institution_id`` is a required argument in practice: it is passed by the
    enqueuing receiver, which still has the request/audit context. It has a
    default only so a missing argument reaches the explicit guard below instead
    of raising a bare ``TypeError``.

    Returns a dict describing the outcome: {"status": "sent"} or
    {"status": "skipped", "reason": ...}.
    """
    if not institution_id:
        # Fail loudly. A task that cannot establish a tenant context would read
        # the protected notifications tables through RLS, find nothing, log
        # "not found; skipping" and never send mail — the exact silent omission
        # this change removes. Raising surfaces the omission in Celery's failure
        # state and traceback; returning a "skipped" dict was rejected because it
        # reproduces the silent failure. This is a programming error, not a
        # transient fault, so it must not be retried.
        raise ValueError(
            "dispatch_notification requires institution_id; the enqueuer must "
            "pass it (the task cannot discover it from a protected table)."
        )

    logger.info(
        "Dispatch attempt %d for notification %s",
        self.request.retries + 1,
        notification_id,
    )

    with tenant_context(connection, institution_id):
        try:
            notification = Notification.objects.select_related("recipient").get(pk=notification_id)
        except Notification.DoesNotExist:
            logger.warning("Notification %s not found; skipping dispatch", notification_id)
            return {"status": "skipped", "reason": "notification_not_found"}

        if not email_channel_enabled(notification.recipient):
            logger.info("Email disabled for %s; skipping dispatch", notification.recipient.email)
            return {"status": "skipped", "reason": "email_disabled"}

        log, _ = NotificationLog.objects.update_or_create(
            notification=notification,
            channel=NotificationChannel.EMAIL,
            defaults={
                "recipient_email": notification.recipient.email,
                "status": NotificationLogStatus.PENDING,
                "attempt_count": self.request.retries + 1,
                "last_error": None,
            },
        )

        try:
            _deliver_email_stub(notification)
        except Exception as exc:
            log.status = NotificationLogStatus.FAILED
            log.last_error = str(exc)
            log.attempt_count = self.request.retries + 1
            log.save(update_fields=["status", "last_error", "attempt_count", "updated_at"])
            logger.exception("Email dispatch failed for notification %s", notification_id)
            raise self.retry(
                exc=exc,
                countdown=RETRY_BACKOFF_BASE_SECONDS * (2**self.request.retries),
            )

        log.status = NotificationLogStatus.SENT
        log.save(update_fields=["status", "updated_at"])
        return {"status": NotificationLogStatus.SENT, "notification_id": str(notification.pk)}


@shared_task(name="cleanup_old_notifications")
def cleanup_old_notifications():
    """Purge notifications and their logs past their retention windows.

    Runs across every tenant, so it has no institution to establish a tenant
    context with. ``tenant_context(..., bypass=True)`` activates the
    ``superadmin_bypass`` policy the notifications tables already carry;
    without it a DELETE under the least-privilege role is default-deny and
    silently affects zero rows. On SQLite the context is a no-op.

    A read row ages from ``read_at`` (purging it by ``created_at`` would drop
    a notification read yesterday just because it is old); an unread row ages
    from ``created_at``. Returns a counts dict so the outcome is observable.
    """
    now = timezone.now()
    read_cutoff = now - timedelta(days=settings.NOTIFICATIONS_RETENTION_READ_DAYS)
    unread_cutoff = now - timedelta(days=settings.NOTIFICATIONS_RETENTION_UNREAD_DAYS)
    log_cutoff = now - timedelta(days=settings.NOTIFICATIONS_RETENTION_LOG_DAYS)

    with tenant_context(connection, None, bypass=True):
        # QuerySet.delete()[0] also counts cascaded rows: purging a
        # notification drags its own NotificationLog rows with it.
        read_deleted, _ = Notification.objects.filter(
            read_at__isnull=False, read_at__lt=read_cutoff
        ).delete()
        unread_deleted, _ = Notification.objects.filter(
            read_at__isnull=True, created_at__lt=unread_cutoff
        ).delete()
        logs_deleted, _ = NotificationLog.objects.filter(created_at__lt=log_cutoff).delete()

    return {
        "read_deleted": read_deleted,
        "unread_deleted": unread_deleted,
        "logs_deleted": logs_deleted,
    }
