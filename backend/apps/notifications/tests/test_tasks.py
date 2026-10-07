"""
Celery dispatch task tests — STRICT TDD (RED phase).

Covers the Phase 3 dispatch contract (design.md — Data Flow and
Channel Semantics; spec NFR Retry / Acceptance Criteria):

- dispatch_notification writes a NotificationLog row (channel=email,
  status=sent) for an enabled recipient — log-only, no SMTP
- a missing Notification is skipped gracefully (no raise)
- UserPreference email opt-out skips dispatch (task and receiver)
- delivery failures persist last_error and attempt_count and retry
  with exponential backoff (countdown 60×2^n), max 3 retries
- receivers enqueue dispatch_notification.delay via transaction.on_commit
  once per CREATED row, only when email is enabled for the recipient
- retention beat schedule (read 90d / unread 365d / logs 12m) is
  registered in config.celery
- cleanup_old_notifications purges read rows past READ_DAYS, unread rows
  past UNREAD_DAYS and NotificationLog rows past LOG_DAYS, across all
  tenants, returning a counts dict
"""

import uuid
from datetime import date, timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationLog,
    NotificationLogStatus,
    NotificationTemplate,
    UserPreference,
)
from apps.notifications.tasks import cleanup_old_notifications, dispatch_notification
from apps.projects.models import Project

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_user(email="user@test.edu"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_role(name, level):
    """Look up a seeded Role by name (fall back to create for new roles)."""
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(name=name, defaults={"level": level})
    return role


def _make_center(institution, code="C1"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution,
        code=code,
        name=f"Center {code}",
    )


def _make_membership(user, institution, role, center=None):
    from apps.accounts.models import InstitutionMembership

    membership = InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=role,
    )
    if center is not None:
        membership.centers.add(center)
    return membership


def _make_researcher(institution, user=None):
    from apps.researchers.models import Researcher

    return Researcher.objects.create(
        institution=institution,
        user=user,
        first_name="Jane",
        last_name="Doe",
        document_type="CC",
        document_number=uuid.uuid4().hex[:16],
        primary_email=user.email if user else "pi@test.edu",
    )


def _make_project(institution, center=None, researcher=None):
    center = center or _make_center(institution)
    researcher = researcher or _make_researcher(institution)
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=researcher,
        title=f"Project {uuid.uuid4().hex[:8]}",
        abstract="Abstract",
        objectives="Objectives",
        methodology="Methodology",
        expected_results="Expected results",
        keywords="test",
        start_date=date(2026, 1, 1),
        estimated_end_date=date(2026, 12, 31),
    )


def _make_notification(email="recipient@test.edu", code="TU"):
    """A Notification row as created by the receivers (seeded template)."""
    inst = _make_institution(code)
    user = _make_user(email)
    template = NotificationTemplate.objects.get(code="PROJECT_SUBMITTED")
    return Notification.objects.create(
        institution=inst,
        recipient=user,
        event_type="PROJECT_SUBMITTED",
        template=template,
        title="Test title",
        body="Test body",
    )


def _age_notification(notification, *, created_days_ago=0, read_days_ago=None):
    """Push a notification's timestamps into the past.

    ``created_at`` is ``auto_now_add`` and ``read_at`` is set by the app, so
    the test moves them through a queryset ``update`` (which bypasses
    ``auto_now_add``) rather than a model ``save``.
    """
    now = timezone.now()
    Notification.objects.filter(pk=notification.pk).update(
        created_at=now - timedelta(days=created_days_ago),
        is_read=read_days_ago is not None,
        read_at=None if read_days_ago is None else now - timedelta(days=read_days_ago),
    )
    return notification


def _make_log(*, created_days_ago=0, notification=None):
    """A NotificationLog row with a controlled ``created_at``."""
    log = NotificationLog.objects.create(
        notification=notification,
        recipient_email="log@test.edu",
    )
    NotificationLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timedelta(days=created_days_ago)
    )
    return log


def _make_director_project():
    """A submit scenario: active center director + project (RN-1)."""
    inst = _make_institution()
    director = _make_user("director@test.edu")
    center = _make_center(inst)
    director_role = _make_role("Director de Centro", 3)
    _make_membership(director, inst, director_role, center=center)
    researcher = _make_researcher(inst, user=_make_user("pi@test.edu"))
    project = _make_project(inst, center=center, researcher=researcher)
    return inst, director, project


def _emit_project_submitted(project, user):
    from apps.project_workflow.signals import project_state_changed

    project_state_changed.send(
        sender=Project,
        project=project,
        from_state="borrador",
        to_state="enviado",
        triggered_by=user,
    )


# ──────────────────────────────────────────────
# dispatch_notification — log-only email stub
# ──────────────────────────────────────────────


class TestDispatchNotificationTask:
    """dispatch_notification writes a log record; never sends SMTP."""

    def test_creates_notification_log_with_status_sent(self, db):
        notification = _make_notification()

        result = dispatch_notification(str(notification.pk), str(notification.institution_id))

        assert result["status"] == NotificationLogStatus.SENT
        log = NotificationLog.objects.get(notification=notification)
        assert log.channel == "email"
        assert log.status == NotificationLogStatus.SENT
        assert log.recipient_email == notification.recipient.email
        assert log.attempt_count == 1
        assert log.last_error is None

    def test_missing_notification_is_skipped_gracefully(self, db, caplog):
        result = dispatch_notification(str(uuid.uuid4()), str(uuid.uuid4()))

        assert result["status"] == "skipped"
        assert result["reason"] == "notification_not_found"
        assert NotificationLog.objects.count() == 0
        assert any("not found" in r.getMessage() for r in caplog.records)

    def test_email_disabled_preference_skips_dispatch(self, db):
        notification = _make_notification()
        UserPreference.objects.create(
            user=notification.recipient,
            channel="email",
            enabled=False,
        )

        result = dispatch_notification(str(notification.pk), str(notification.institution_id))

        assert result["status"] == "skipped"
        assert result["reason"] == "email_disabled"
        assert NotificationLog.objects.count() == 0

    def test_no_preference_row_defaults_to_email_enabled(self, db):
        notification = _make_notification()

        result = dispatch_notification(str(notification.pk), str(notification.institution_id))

        assert result["status"] == NotificationLogStatus.SENT
        assert NotificationLog.objects.filter(notification=notification).exists()

    def test_explicitly_enabled_preference_still_dispatches(self, db):
        notification = _make_notification()
        UserPreference.objects.create(
            user=notification.recipient,
            channel="email",
            enabled=True,
        )

        result = dispatch_notification(str(notification.pk), str(notification.institution_id))

        assert result["status"] == NotificationLogStatus.SENT
        assert NotificationLog.objects.filter(notification=notification).exists()


# ──────────────────────────────────────────────
# Missing institution — fail loudly
# ──────────────────────────────────────────────


class TestDispatchRequiresInstitution:
    """A dispatch with no institution fails loudly, never silently skips."""

    def test_missing_institution_raises(self, db):
        notification = _make_notification()

        with pytest.raises(ValueError, match="institution_id"):
            dispatch_notification(str(notification.pk))

    def test_none_institution_raises(self, db):
        notification = _make_notification()

        with pytest.raises(ValueError, match="institution_id"):
            dispatch_notification(str(notification.pk), None)

    def test_missing_institution_writes_no_log(self, db):
        notification = _make_notification()

        with pytest.raises(ValueError):
            dispatch_notification(str(notification.pk))

        assert NotificationLog.objects.count() == 0


# ──────────────────────────────────────────────
# Retry contract (spec NFR)
# ──────────────────────────────────────────────


class TestDispatchRetry:
    """Failures persist last_error/attempt_count; countdown 60×2^n."""

    def test_delivery_failure_persists_last_error_and_attempt_count(self, db):
        notification = _make_notification()

        with (
            mock.patch(
                "apps.notifications.tasks._deliver_email_stub",
                side_effect=RuntimeError("smtp down"),
            ),
            mock.patch.object(
                dispatch_notification,
                "retry",
                side_effect=RuntimeError("smtp down"),
            ) as retry_mock,
        ):
            with pytest.raises(RuntimeError):
                dispatch_notification(str(notification.pk), str(notification.institution_id))

        retry_mock.assert_called_once()
        log = NotificationLog.objects.get(notification=notification)
        assert log.status == NotificationLogStatus.FAILED
        assert log.last_error == "smtp down"
        assert log.attempt_count == 1

    def test_retry_uses_exponential_backoff_countdown(self, db):
        notification = _make_notification()

        with (
            mock.patch(
                "apps.notifications.tasks._deliver_email_stub",
                side_effect=RuntimeError("boom"),
            ),
            mock.patch.object(
                dispatch_notification,
                "retry",
                side_effect=RuntimeError("boom"),
            ) as retry_mock,
        ):
            with pytest.raises(RuntimeError):
                dispatch_notification(str(notification.pk), str(notification.institution_id))

        kwargs = retry_mock.call_args.kwargs
        assert kwargs["countdown"] == 60 * (2**0)  # first retry: 60×2^0

    def test_task_allows_up_to_three_retries(self):
        assert dispatch_notification.max_retries == 3


# ──────────────────────────────────────────────
# Receiver → Celery wiring (transaction.on_commit)
# ──────────────────────────────────────────────


class TestReceiverEnqueuesDispatch:
    """Receivers schedule dispatch on commit; email gated by preference."""

    def test_receiver_enqueues_task_on_transaction_commit(self, db):
        inst, director, project = _make_director_project()

        with (
            mock.patch(
                "apps.notifications.receivers.transaction.on_commit",
                side_effect=lambda fn: fn(),
            ) as on_commit,
            mock.patch("apps.notifications.receivers.dispatch_notification.delay") as delay,
        ):
            _emit_project_submitted(project, director)

        on_commit.assert_called_once()
        notification = Notification.objects.get(recipient=director)
        delay.assert_called_once_with(str(notification.pk), str(notification.institution_id))

    def test_email_disabled_does_not_enqueue(self, db):
        inst, director, project = _make_director_project()
        UserPreference.objects.create(user=director, channel="email", enabled=False)

        with (
            mock.patch(
                "apps.notifications.receivers.transaction.on_commit",
                side_effect=lambda fn: fn(),
            ),
            mock.patch("apps.notifications.receivers.dispatch_notification.delay") as delay,
        ):
            _emit_project_submitted(project, director)

        delay.assert_not_called()
        # In-app delivery is unaffected by the email opt-out.
        assert Notification.objects.filter(recipient=director).count() == 1

    def test_only_created_rows_enqueue_once(self, db):
        inst, director, project = _make_director_project()

        with (
            mock.patch(
                "apps.notifications.receivers.transaction.on_commit",
                side_effect=lambda fn: fn(),
            ),
            mock.patch("apps.notifications.receivers.dispatch_notification.delay") as delay,
        ):
            _emit_project_submitted(project, director)
            _emit_project_submitted(project, director)  # dedup — no re-enqueue

        delay.assert_called_once()


# ──────────────────────────────────────────────
# Retention beat schedule (spec NFR Retention)
# ──────────────────────────────────────────────


class TestRetentionBeatSchedule:
    """The beat entry names the cleanup_old_notifications task."""

    def test_cleanup_beat_entry_configured(self):
        from config.celery import app

        schedule = app.conf.beat_schedule
        assert "cleanup-old-notifications" in schedule
        entry = schedule["cleanup-old-notifications"]
        assert entry["task"] == "cleanup_old_notifications"


# ──────────────────────────────────────────────
# Retention cleanup task (spec NFR Retention)
# ──────────────────────────────────────────────


class TestCleanupOldNotifications:
    """Retention purge — hard delete across all tenants, counts observable."""

    def test_read_notification_past_window_is_deleted(self, db):
        notification = _age_notification(_make_notification(), read_days_ago=91)

        counts = cleanup_old_notifications()

        assert not Notification.objects.filter(pk=notification.pk).exists()
        assert counts["read_deleted"] == 1

    def test_recent_read_notification_is_kept(self, db):
        notification = _age_notification(_make_notification(), read_days_ago=10)

        counts = cleanup_old_notifications()

        assert Notification.objects.filter(pk=notification.pk).exists()
        assert counts["read_deleted"] == 0

    def test_unread_notification_past_window_is_deleted(self, db):
        notification = _age_notification(_make_notification(), created_days_ago=366)

        counts = cleanup_old_notifications()

        assert not Notification.objects.filter(pk=notification.pk).exists()
        assert counts["unread_deleted"] == 1

    def test_recent_unread_notification_is_kept(self, db):
        notification = _age_notification(_make_notification(), created_days_ago=10)

        counts = cleanup_old_notifications()

        assert Notification.objects.filter(pk=notification.pk).exists()
        assert counts["unread_deleted"] == 0

    def test_old_log_is_deleted_and_recent_log_kept(self, db):
        old_log = _make_log(created_days_ago=366)
        recent_log = _make_log(created_days_ago=10)

        counts = cleanup_old_notifications()

        assert not NotificationLog.objects.filter(pk=old_log.pk).exists()
        assert NotificationLog.objects.filter(pk=recent_log.pk).exists()
        assert counts["logs_deleted"] == 1

    def test_read_window_setting_changes_the_boundary(self, db, settings):
        settings.NOTIFICATIONS_RETENTION_READ_DAYS = 30
        notification = _age_notification(_make_notification(), read_days_ago=31)

        counts = cleanup_old_notifications()

        assert not Notification.objects.filter(pk=notification.pk).exists()
        assert counts["read_deleted"] == 1

    def test_unread_window_setting_changes_the_boundary(self, db, settings):
        settings.NOTIFICATIONS_RETENTION_UNREAD_DAYS = 30
        notification = _age_notification(_make_notification(), created_days_ago=31)

        counts = cleanup_old_notifications()

        assert not Notification.objects.filter(pk=notification.pk).exists()
        assert counts["unread_deleted"] == 1

    def test_log_window_setting_changes_the_boundary(self, db, settings):
        settings.NOTIFICATIONS_RETENTION_LOG_DAYS = 30
        log = _make_log(created_days_ago=31)

        counts = cleanup_old_notifications()

        assert not NotificationLog.objects.filter(pk=log.pk).exists()
        assert counts["logs_deleted"] == 1

    def test_returns_counts_dict_of_purges(self, db):
        _age_notification(_make_notification(email="read@test.edu", code="TUR"), read_days_ago=200)
        _age_notification(
            _make_notification(email="unread@test.edu", code="TUU"), created_days_ago=400
        )
        _make_log(created_days_ago=400)

        counts = cleanup_old_notifications()

        assert counts == {"read_deleted": 1, "unread_deleted": 1, "logs_deleted": 1}
