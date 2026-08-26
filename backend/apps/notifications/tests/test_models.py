"""
Model tests for notifications app — STRICT TDD (RED phase).

Tests define the expected behavior of the 4-entity notifications module:
Notification, NotificationTemplate, NotificationLog, UserPreference.

Spec reference:  openspec/changes/notifications/spec.md — Data Model
Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts

RED PHASE: Tests fail because apps/notifications/models.py does not exist.
"""

import uuid

import pytest
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import IntegrityError, transaction

from apps.notifications.models import (
    Notification,
    NotificationLog,
    NotificationTemplate,
    UserPreference,
)

# Seeded template codes (data migration in 0001_initial).
SEEDED_TEMPLATE_CODES = {
    "PROJECT_SUBMITTED",
    "PROGRESS_OBSERVED",
    "DOCUMENT_SIGNED",
    "BUDGET_OVERRUN_ATTEMPTED",
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(
        name=f"Test University {code}",
        code=code,
    )


def _make_user(email="recipient@test.edu"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_template(code=None):
    code = code or f"TEST_TEMPLATE_{uuid.uuid4().hex[:8]}"
    return NotificationTemplate.objects.create(
        code=code,
        title_template="Test title template",
        body_template="Test body template with {{ context }}.",
    )


def _make_notification(institution, recipient, template, **kwargs):
    defaults = {
        "event_type": "TEST_EVENT",
        "title": "Test notification",
        "body": "Notification body",
    }
    defaults.update(kwargs)
    return Notification.objects.create(
        institution=institution,
        recipient=recipient,
        template=template,
        **defaults,
    )


# ──────────────────────────────────────────────
# Notification Creation
# ──────────────────────────────────────────────


class TestNotificationCreation:
    """Notification model field behavior and defaults."""

    def test_create_notification_minimal(self, db):
        """Notification persists institution, recipient, template, event data."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()

        notification = _make_notification(
            inst,
            user,
            template,
            event_type="PROJECT_SUBMITTED",
            title="Project submitted",
            body="Your project was submitted for review.",
            entity_type="project",
            entity_id=uuid.uuid4(),
        )

        assert notification.id is not None
        assert isinstance(notification.id, uuid.UUID)
        assert notification.institution == inst
        assert notification.recipient == user
        assert notification.template == template
        assert notification.event_type == "PROJECT_SUBMITTED"
        assert notification.title == "Project submitted"
        assert notification.body == "Your project was submitted for review."
        assert notification.context == {}
        assert notification.entity_type == "project"
        assert notification.entity_id is not None
        assert notification.read_at is None
        assert notification.created_at is not None

    def test_is_read_defaults_false(self, db):
        """is_read defaults to False and read_at stays None on creation."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()

        notification = _make_notification(inst, user, template)

        assert notification.is_read is False
        assert notification.read_at is None

    def test_entity_link_optional(self, db):
        """entity_type/entity_id are nullable (no GenericForeignKey)."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()

        notification = _make_notification(inst, user, template)

        assert notification.entity_type is None
        assert notification.entity_id is None

    def test_str_representation(self, db):
        """__str__ surfaces recipient and event type."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()

        notification = _make_notification(
            inst, user, template, event_type="DOCUMENT_SIGNED"
        )

        assert "DOCUMENT_SIGNED" in str(notification)
        assert user.email in str(notification)


# ──────────────────────────────────────────────
# Notification Meta Contracts (design/tasks)
# ──────────────────────────────────────────────


class TestNotificationMeta:
    """Design contracts: unique event tuple, composite index, no GFK."""

    def test_unique_event_tuple_constraint_registered(self):
        """Unique (recipient, event_type, entity_type, entity_id) exists."""
        names = {c.name for c in Notification._meta.constraints}
        assert "uniq_notif_event_per_recipient" in names

    def test_recipient_read_created_index_registered(self):
        """Composite index (recipient, is_read, -created_at) exists."""
        index_names = {i.name for i in Notification._meta.indexes}
        assert "idx_notif_recipient_read_created" in index_names

    def test_event_type_indexed(self):
        """event_type is indexed (max 50, indexed per design)."""
        field = Notification._meta.get_field("event_type")
        assert field.db_index is True

    def test_no_generic_foreign_key(self):
        """Entity links are explicit columns, never a GenericForeignKey."""
        assert not any(
            isinstance(f, GenericForeignKey) for f in Notification._meta.private_fields
        )

    def test_unique_event_tuple_enforced(self, db):
        """Duplicate event tuple for the same recipient raises IntegrityError."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()
        entity_id = uuid.uuid4()
        _make_notification(
            inst,
            user,
            template,
            event_type="PROGRESS_OBSERVED",
            entity_type="progress",
            entity_id=entity_id,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_notification(
                    inst,
                    user,
                    template,
                    event_type="PROGRESS_OBSERVED",
                    entity_type="progress",
                    entity_id=entity_id,
                )

    def test_different_entity_allowed(self, db):
        """Same recipient/event with a different entity_id is allowed."""
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()
        first = _make_notification(
            inst,
            user,
            template,
            event_type="PROGRESS_OBSERVED",
            entity_type="progress",
            entity_id=uuid.uuid4(),
        )

        second = _make_notification(
            inst,
            user,
            template,
            event_type="PROGRESS_OBSERVED",
            entity_type="progress",
            entity_id=uuid.uuid4(),
        )

        assert second.id != first.id
        assert second.entity_id is not None
        assert second.entity_id != first.entity_id


# ──────────────────────────────────────────────
# NotificationTemplate
# ──────────────────────────────────────────────


class TestNotificationTemplate:
    """NotificationTemplate catalog behavior."""

    def test_create_template(self, db):
        """Template stores code, title/body templates, is_active default True."""
        template = _make_template("TEST_TEMPLATE")

        assert template.id is not None
        assert isinstance(template.id, uuid.UUID)
        assert template.code == "TEST_TEMPLATE"
        assert template.title_template == "Test title template"
        assert "{{ context }}" in template.body_template
        assert template.is_active is True

    def test_code_unique(self, db):
        """Duplicate template code raises IntegrityError."""
        _make_template("DUP_CODE")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_template("DUP_CODE")

    def test_inactive_template_allowed(self, db):
        """is_active=False is a valid state (suppresses creation per spec)."""
        template = NotificationTemplate.objects.create(
            code="INACTIVE_TEMPLATE",
            title_template="Inactive",
            body_template="Inactive body",
            is_active=False,
        )

        assert template.is_active is False

    def test_seeded_templates_exist(self, db):
        """Data migration seeds the 4 event-type templates."""
        codes = set(NotificationTemplate.objects.values_list("code", flat=True))
        assert SEEDED_TEMPLATE_CODES <= codes


# ──────────────────────────────────────────────
# NotificationLog
# ──────────────────────────────────────────────


class TestNotificationLogCreation:
    """NotificationLog model field behavior and defaults."""

    def _notification(self):
        inst = _make_institution("TU")
        user = _make_user()
        template = _make_template()
        return _make_notification(inst, user, template)

    def test_create_log(self, db):
        """Log persists channel, recipient email, pending status, attempt 0."""
        notification = self._notification()

        log = NotificationLog.objects.create(
            notification=notification,
            channel="email",
            recipient_email=notification.recipient.email,
        )

        assert log.id is not None
        assert isinstance(log.id, uuid.UUID)
        assert log.notification == notification
        assert log.channel == "email"
        assert log.recipient_email == notification.recipient.email
        assert log.status == "pending"
        assert log.attempt_count == 0
        assert log.last_error is None
        assert log.created_at is not None
        assert log.updated_at is not None

    def test_log_notification_nullable(self, db):
        """notification FK is nullable (log-only records allowed)."""
        log = NotificationLog.objects.create(
            channel="email",
            recipient_email="orphan@test.edu",
        )

        assert log.notification is None

    def test_failed_status_with_error(self, db):
        """Failed deliveries persist status, attempt count, and last_error."""
        notification = self._notification()

        log = NotificationLog.objects.create(
            notification=notification,
            channel="email",
            recipient_email=notification.recipient.email,
            status="failed",
            attempt_count=3,
            last_error="SMTP connection refused",
        )

        assert log.status == "failed"
        assert log.attempt_count == 3
        assert log.last_error == "SMTP connection refused"


# ──────────────────────────────────────────────
# UserPreference
# ──────────────────────────────────────────────


class TestUserPreference:
    """UserPreference model behavior and unique user constraint."""

    def test_create_preference(self, db):
        """Preference defaults to email channel, enabled True, timestamps."""
        user = _make_user()

        preference = UserPreference.objects.create(user=user)

        assert preference.id is not None
        assert isinstance(preference.id, uuid.UUID)
        assert preference.user == user
        assert preference.channel == "email"
        assert preference.enabled is True
        assert preference.created_at is not None
        assert preference.updated_at is not None

    def test_user_unique(self, db):
        """A second preference row for the same user raises IntegrityError."""
        user = _make_user()
        UserPreference.objects.create(user=user)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserPreference.objects.create(user=user)

    def test_email_disabled(self, db):
        """enabled=False persists (email opt-out per channel semantics)."""
        user = _make_user()

        preference = UserPreference.objects.create(user=user, enabled=False)

        assert preference.enabled is False
