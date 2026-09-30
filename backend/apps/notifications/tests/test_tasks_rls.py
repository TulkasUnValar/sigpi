"""Real-PostgreSQL proof that ``dispatch_notification`` needs its tenant context.

These tests run as the least-privilege ``sigpi_app`` role (via the
``postgres_app_role`` fixture), so row-level security actually applies to the
reads and writes the task performs. They prove the context is load-bearing:

- with the institution passed the task finds its Notification and writes the
  dispatch log
- with no context (or the wrong institution) the same protected read finds
  nothing — the non-vacuity control that stops the positive case from passing
  even if the context did nothing

The task is exercised by calling it directly (no broker): it is eager-callable,
and ``get_client`` is mocked where the search task would otherwise reach out.
"""

import pytest

from apps.notifications.models import Notification, NotificationLog, NotificationTemplate
from apps.notifications.tasks import dispatch_notification
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
