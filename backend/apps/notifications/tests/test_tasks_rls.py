"""Real-PostgreSQL proof of the tenant context the notification tasks need.

These tests run as the least-privilege ``sigpi_app`` role (via the
``postgres_app_role`` fixture), so row-level security actually applies to the
reads and writes the tasks perform. They prove the context is load-bearing:

- ``dispatch_notification``: with the institution passed the task finds its
  Notification and writes the dispatch log
- with no context (or the wrong institution) the same protected read finds
  nothing — the non-vacuity control that stops the positive case from passing
  even if the context did nothing
- ``cleanup_old_notifications``: a cross-tenant system task with no institution
  to scope to; only the explicit RLS bypass lets it purge every tenant's
  expired rows

The tasks are exercised by calling them directly (no broker): they are
eager-callable, and ``get_client`` is mocked where the search task would
otherwise reach out.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notifications.models import Notification, NotificationLog, NotificationTemplate
from apps.notifications.tasks import cleanup_old_notifications, dispatch_notification
from config import tenant_context

TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def _set_rls(conn, institution_id, bypass):
    """Write both RLS GUCs at connection scope, exactly like production does."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


def _make_institution(code):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Institution {code}", code=code)


def _make_user(email):
    from apps.accounts.models import User

    return User.objects.create_user(email=email, auth_source="local")


def _make_notification(institution, recipient):
    """A Notification row as created by the receivers (seeded template)."""
    template = NotificationTemplate.objects.get(code="PROJECT_SUBMITTED")
    return Notification.objects.create(
        institution=institution,
        recipient=recipient,
        event_type="PROJECT_SUBMITTED",
        template=template,
        title="W3 notification",
        body="W3 body",
    )


class TestDispatchNotificationTenantContext:
    """The passed institution is what makes the task's protected read visible."""

    def test_context_is_what_makes_the_read_visible(self, postgres_app_role):
        conn = postgres_app_role
        institution = _make_institution("W3N")
        recipient = _make_user("w3n-recipient@test.edu")

        _set_rls(conn, None, bypass=True)
        notification = _make_notification(institution, recipient)
        tenant_context.clear(conn)

        # Non-vacuity control: the same protected read the task performs finds
        # nothing with no context. If the row were visible here, the positive
        # assertion below would prove nothing about the context.
        with pytest.raises(Notification.DoesNotExist):
            Notification.objects.select_related("recipient").get(pk=notification.pk)

        result = dispatch_notification(str(notification.pk), str(institution.pk))

        assert result["status"] == "sent"
        assert result["notification_id"] == str(notification.pk)

        _set_rls(conn, None, bypass=True)
        log = NotificationLog.objects.get(notification=notification)
        assert log.status == "sent"
        assert log.recipient_email == recipient.email

    def test_wrong_institution_cannot_see_the_row(self, postgres_app_role):
        conn = postgres_app_role
        institution = _make_institution("W3N")
        other = _make_institution("W3O")
        recipient = _make_user("w3n-recipient2@test.edu")

        _set_rls(conn, None, bypass=True)
        notification = _make_notification(institution, recipient)
        tenant_context.clear(conn)

        # A context for the wrong institution is as good as no context.
        result = dispatch_notification(str(notification.pk), str(other.pk))

        assert result == {"status": "skipped", "reason": "notification_not_found"}


def _age_notification(notification, *, created_days_ago=0, read_days_ago=None):
    """Push a notification's timestamps into the past (bypass must be active)."""
    now = timezone.now()
    Notification.objects.filter(pk=notification.pk).update(
        created_at=now - timedelta(days=created_days_ago),
        is_read=read_days_ago is not None,
        read_at=None if read_days_ago is None else now - timedelta(days=read_days_ago),
    )
    return notification


def _make_log(notification, *, created_days_ago=0):
    """A NotificationLog linked to ``notification``, with a controlled age."""
    log = NotificationLog.objects.create(
        notification=notification,
        recipient_email=notification.recipient.email,
    )
    NotificationLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timedelta(days=created_days_ago)
    )
    return log


class TestCleanupOldNotificationsTenantBypass:
    """The cleanup task purges every tenant through the RLS bypass."""

    def test_purges_expired_rows_of_both_tenants(self, postgres_app_role):
        conn = postgres_app_role
        inst_a = _make_institution("CLNA")
        inst_b = _make_institution("CLNB")
        user_a = _make_user("clna@test.edu")
        user_b = _make_user("clnb@test.edu")

        # Seed under the bypass: the notification/insert check also reads it.
        _set_rls(conn, None, bypass=True)
        expired_read_a = _age_notification(_make_notification(inst_a, user_a), read_days_ago=120)
        expired_unread_a = _age_notification(
            _make_notification(inst_a, user_a), created_days_ago=400
        )
        recent_a = _age_notification(_make_notification(inst_a, user_a), created_days_ago=10)
        expired_log_a = _make_log(recent_a, created_days_ago=400)
        recent_log_a = _make_log(recent_a, created_days_ago=10)

        expired_read_b = _age_notification(_make_notification(inst_b, user_b), read_days_ago=120)
        expired_unread_b = _age_notification(
            _make_notification(inst_b, user_b), created_days_ago=400
        )
        recent_b = _age_notification(_make_notification(inst_b, user_b), created_days_ago=10)
        expired_log_b = _make_log(recent_b, created_days_ago=400)
        recent_log_b = _make_log(recent_b, created_days_ago=10)

        # No tenant context: a DELETE here is default-deny. The task must
        # activate the bypass itself, or both tenants' rows would survive.
        tenant_context.clear(conn)

        counts = cleanup_old_notifications()

        _set_rls(conn, None, bypass=True)
        assert counts == {"read_deleted": 2, "unread_deleted": 2, "logs_deleted": 2}

        expired_notifications = Notification.objects.filter(
            pk__in=[
                expired_read_a.pk,
                expired_unread_a.pk,
                expired_read_b.pk,
                expired_unread_b.pk,
            ]
        )
        assert not expired_notifications.exists()
        assert Notification.objects.filter(pk__in=[recent_a.pk, recent_b.pk]).count() == 2

        expired_logs = NotificationLog.objects.filter(pk__in=[expired_log_a.pk, expired_log_b.pk])
        assert not expired_logs.exists()
        assert (
            NotificationLog.objects.filter(pk__in=[recent_log_a.pk, recent_log_b.pk]).count() == 2
        )
