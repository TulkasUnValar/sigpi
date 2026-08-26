"""
Celery tasks for the notifications module — email dispatch (log-only).

Phase 3 delivery contract (design.md — Data Flow / Channel Semantics;
spec NFR Retry / Acceptance Criteria):

- dispatch_notification(notification_id) writes a NotificationLog row
  per enabled email recipient with status=sent — STUB, no SMTP
- a missing Notification is skipped gracefully (warning, no raise)
- UserPreference email opt-out skips dispatch (the task double-checks
  the preference the receiver already checked before enqueuing)
- delivery failures persist last_error + attempt_count and retry up to
  3 times with exponential backoff (countdown 60×2^n)
"""

import logging

from celery import shared_task

from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationLog,
    NotificationLogStatus,
    UserPreference,
)

logger = logging.getLogger(__name__)

# Retry contract (spec NFR): up to 3 retries, exponential backoff 60×2^n.
MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 60


def email_channel_enabled(user) -> bool:
    """Email is enabled unless the user opted out via UserPreference.

    Default is enabled when no preference row exists (spec: enabled
    default true — "Default: both enabled").
    """
    preference = UserPreference.objects.filter(
        user=user, channel=NotificationChannel.EMAIL
    ).first()
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
def dispatch_notification(self, notification_id):
    """Deliver a Notification by email — log-only stub (no SMTP).

    Returns a dict describing the outcome: {"status": "sent"} or
    {"status": "skipped", "reason": ...}.
    """
    logger.info(
        "Dispatch attempt %d for notification %s",
        self.request.retries + 1,
        notification_id,
    )

    try:
        notification = Notification.objects.select_related("recipient").get(
            pk=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning(
            "Notification %s not found; skipping dispatch", notification_id
        )
        return {"status": "skipped", "reason": "notification_not_found"}

    if not email_channel_enabled(notification.recipient):
        logger.info(
            "Email disabled for %s; skipping dispatch", notification.recipient.email
        )
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
