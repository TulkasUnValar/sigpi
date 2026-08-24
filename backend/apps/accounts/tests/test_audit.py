"""
Audit event tests for SIGPI auth audit events — STRICT TDD.

Tests define the expected behavior of:
- AuditEvent model: stores auth events queryably
- Event types: LOGIN, LOGOUT, FAILED_LOGIN, INSTITUTION_SWITCH, ROLE_CHANGE, PERMISSION_DENIED
- Audit event emitter: creates events from views/tasks
- Event fields: timestamp, user, event_type, ip_address, institution_id, details

Spec references: FR-007
Design reference: openspec/changes/auth/design.md — AuditEventEmitter
"""

from unittest.mock import MagicMock

import pytest
from django.utils import timezone

# ── RED: These imports WILL fail until audit.py is created ──
from apps.accounts.audit import (
    AuditEvent,
    AuditEventEmitter,
    AuditEventType,
)
from apps.accounts.models import User
from apps.institutions.models import Institution

# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


# ──────────────────────────────────────────────────────────
# Test AuditEventType Enum
# ──────────────────────────────────────────────────────────


class TestAuditEventType:
    """Tests for the AuditEventType choices enum."""

    def test_event_types_defined(self):
        """All specified event types are defined."""
        assert hasattr(AuditEventType, "LOGIN")
        assert hasattr(AuditEventType, "LOGOUT")
        assert hasattr(AuditEventType, "FAILED_LOGIN")
        assert hasattr(AuditEventType, "INSTITUTION_SWITCH")
        assert hasattr(AuditEventType, "ROLE_CHANGE")
        assert hasattr(AuditEventType, "PERMISSION_DENIED")

    def test_event_type_values_match(self):
        """Event type values match the design spec."""
        assert AuditEventType.LOGIN == "LOGIN"
        assert AuditEventType.LOGOUT == "LOGOUT"
        assert AuditEventType.FAILED_LOGIN == "FAILED_LOGIN"
        assert AuditEventType.INSTITUTION_SWITCH == "INSTITUTION_SWITCH"
        assert AuditEventType.ROLE_CHANGE == "ROLE_CHANGE"
        assert AuditEventType.PERMISSION_DENIED == "PERMISSION_DENIED"

    def test_budget_event_types_defined(self):
        """Budget audit event types (RN-021) are defined."""
        assert hasattr(AuditEventType, "BUDGET_CREATED")
        assert hasattr(AuditEventType, "BUDGET_UPDATED")
        assert hasattr(AuditEventType, "BUDGET_EXECUTION_ADDED")

    def test_budget_event_type_values_match(self):
        """Budget event type values match the spec (auth delta FR-007)."""
        assert AuditEventType.BUDGET_CREATED == "BUDGET_CREATED"
        assert AuditEventType.BUDGET_UPDATED == "BUDGET_UPDATED"
        assert AuditEventType.BUDGET_EXECUTION_ADDED == "BUDGET_EXECUTION_ADDED"

    def test_budget_event_types_in_choices(self):
        """Budget event types are registered in the TextChoices choices."""
        choice_values = {value for value, _label in AuditEventType.choices}
        assert "BUDGET_CREATED" in choice_values
        assert "BUDGET_UPDATED" in choice_values
        assert "BUDGET_EXECUTION_ADDED" in choice_values

    def test_document_event_types_defined(self):
        """Document/Minutes audit event types (SPEC §6.7) are defined."""
        assert hasattr(AuditEventType, "DOCUMENT_UPLOADED")
        assert hasattr(AuditEventType, "DOCUMENT_SIGNED")
        assert hasattr(AuditEventType, "MINUTES_CREATED")

    def test_document_event_type_values_match(self):
        """Document event type values match the spec (auth delta FR-007)."""
        assert AuditEventType.DOCUMENT_UPLOADED == "DOCUMENT_UPLOADED"
        assert AuditEventType.DOCUMENT_SIGNED == "DOCUMENT_SIGNED"
        assert AuditEventType.MINUTES_CREATED == "MINUTES_CREATED"

    def test_document_event_types_in_choices(self):
        """Document event types are registered in the TextChoices choices."""
        choice_values = {value for value, _label in AuditEventType.choices}
        assert "DOCUMENT_UPLOADED" in choice_values
        assert "DOCUMENT_SIGNED" in choice_values
        assert "MINUTES_CREATED" in choice_values

    def test_legacy_event_types_preserved(self):
        """All prior members remain valid after the extension (auth spec)."""
        for value in (
            "LOGIN",
            "LOGOUT",
            "FAILED_LOGIN",
            "INSTITUTION_SWITCH",
            "ROLE_CHANGE",
            "PERMISSION_DENIED",
            "PROGRESS_STATE_CHANGE",
            "REPORT_GENERATED",
            "REPORT_APPROVED",
            "BUDGET_CREATED",
            "BUDGET_UPDATED",
            "BUDGET_EXECUTION_ADDED",
        ):
            assert value in {v for v, _l in AuditEventType.choices}, value


# ──────────────────────────────────────────────────────────
# Test AuditEvent Model
# ──────────────────────────────────────────────────────────


class TestAuditEventModel:
    """Tests for the AuditEvent database model."""

    def test_create_audit_event(self, db, institution):
        """An AuditEvent can be created with all fields."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        event = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGIN,
            ip_address="192.168.1.1",
            institution_id=institution.id,
            details={"auth_source": "local", "success": True},
        )
        assert event.pk is not None
        assert event.event_type == "LOGIN"
        assert event.ip_address == "192.168.1.1"
        assert event.institution_id == institution.id
        assert event.details == {"auth_source": "local", "success": True}

    def test_audit_event_timestamp_auto_set(self, db):
        """Timestamp is automatically set on creation."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        before = timezone.now()
        event = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGOUT,
            ip_address="10.0.0.1",
        )
        after = timezone.now()
        assert before <= event.timestamp <= after

    def test_audit_event_nullable_fields(self, db):
        """institution_id and details are nullable."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        event = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.FAILED_LOGIN,
            ip_address="10.0.0.1",
        )
        assert event.institution_id is None
        assert event.details is None

    def test_audit_event_user_fk(self, db):
        """AuditEvent is linked to a User via FK."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        event = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGIN,
            ip_address="10.0.0.1",
        )
        assert event.user == user
        assert event.user.email == "u@test.com"

    def test_audit_event_str_representation(self, db):
        """String representation is useful for debugging."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        event = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGIN,
            ip_address="10.0.0.1",
        )
        str_repr = str(event)
        assert "LOGIN" in str_repr
        assert "u@test.com" in str_repr

    def test_audit_event_ordering(self, db):
        """Events are ordered by timestamp descending (newest first)."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        _e1 = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGIN,
            ip_address="10.0.0.1",
        )
        _e2 = AuditEvent.objects.create(
            user=user,
            event_type=AuditEventType.LOGOUT,
            ip_address="10.0.0.1",
        )
        events = list(AuditEvent.objects.all())
        assert events[0].timestamp >= events[1].timestamp

    def test_filter_by_event_type(self, db):
        """Events can be filtered by event_type."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.1")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.2")
        AuditEvent.objects.create(
            user=user, event_type=AuditEventType.LOGOUT, ip_address="10.0.0.1"
        )

        assert AuditEvent.objects.filter(event_type="LOGIN").count() == 2
        assert AuditEvent.objects.filter(event_type="LOGOUT").count() == 1

    def test_filter_by_user(self, db):
        """Events can be filtered by user."""
        u1 = User.objects.create_user(email="u1@test.com", auth_source="local", password="pass")
        u2 = User.objects.create_user(email="u2@test.com", auth_source="local", password="pass")
        AuditEvent.objects.create(user=u1, event_type=AuditEventType.LOGIN, ip_address="10.0.0.1")
        AuditEvent.objects.create(user=u2, event_type=AuditEventType.LOGIN, ip_address="10.0.0.2")

        assert AuditEvent.objects.filter(user=u1).count() == 1
        assert AuditEvent.objects.filter(user=u2).count() == 1

    def test_filter_by_date_range(self, db):
        """Events can be filtered by date range."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.1")

        now = timezone.now()
        yesterday = now - timezone.timedelta(days=1)
        tomorrow = now + timezone.timedelta(days=1)

        assert AuditEvent.objects.filter(timestamp__gte=yesterday).count() == 1
        assert AuditEvent.objects.filter(timestamp__gte=tomorrow).count() == 0


# ──────────────────────────────────────────────────────────
# Test AuditEventEmitter
# ──────────────────────────────────────────────────────────


class TestAuditEventEmitter:
    """Tests for the AuditEventEmitter that creates audit events programmatically."""

    def test_emit_login_event(self, db, institution):
        """Emitter creates a LOGIN audit event."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.LOGIN,
            user=user,
            ip_address="192.168.1.100",
            institution_id=institution.id,
            details={"auth_source": "local"},
        )

        assert event.event_type == "LOGIN"
        assert event.user == user
        assert event.ip_address == "192.168.1.100"
        assert event.institution_id == institution.id
        assert event.details == {"auth_source": "local"}
        assert AuditEvent.objects.count() == 1

    def test_emit_logout_event(self, db):
        """Emitter creates a LOGOUT audit event."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.LOGOUT,
            user=user,
            ip_address="10.0.0.1",
        )

        assert event.event_type == "LOGOUT"
        assert AuditEvent.objects.count() == 1

    def test_emit_failed_login_event(self, db):
        """Emitter creates a FAILED_LOGIN event (no user required)."""
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.FAILED_LOGIN,
            user=None,
            ip_address="192.168.1.1",
            details={"email_attempted": "bad@test.com", "reason": "invalid_credentials"},
        )

        assert event.event_type == "FAILED_LOGIN"
        assert event.user is None
        assert event.details == {"email_attempted": "bad@test.com", "reason": "invalid_credentials"}

    def test_emit_institution_switch_event(self, db, institution):
        """Emitter creates an INSTITUTION_SWITCH event."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        other_inst = Institution.objects.create(name="Other", code="OTH")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.INSTITUTION_SWITCH,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"previous_institution_id": str(other_inst.id)},
        )

        assert event.event_type == "INSTITUTION_SWITCH"
        assert event.details["previous_institution_id"] == str(other_inst.id)

    def test_emit_permission_denied_event(self, db, institution):
        """Emitter creates a PERMISSION_DENIED event."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.PERMISSION_DENIED,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"action": "delete_project", "resource_id": "uuid-123"},
        )

        assert event.event_type == "PERMISSION_DENIED"
        assert event.details["action"] == "delete_project"

    def test_emit_returns_audit_event_instance(self, db):
        """emit() returns the created AuditEvent instance."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()
        event = emitter.emit(
            event_type=AuditEventType.LOGIN,
            user=user,
            ip_address="10.0.0.1",
        )
        assert isinstance(event, AuditEvent)

    def test_emit_multiple_events(self, db):
        """Multiple events can be emitted without issues."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        emitter.emit(AuditEventType.LOGIN, user=user, ip_address="10.0.0.1")
        emitter.emit(AuditEventType.LOGOUT, user=user, ip_address="10.0.0.1")
        emitter.emit(AuditEventType.LOGIN, user=user, ip_address="10.0.0.2")

        assert AuditEvent.objects.count() == 3

    def test_extract_ip_from_request(self, db):
        """Helper extracts IP address from Django request."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "203.0.113.42"}

        ip = AuditEventEmitter.extract_ip(request)
        assert ip == "203.0.113.42"

    def test_extract_ip_from_x_forwarded_for(self, db):
        """Helper extracts IP from X-Forwarded-For header."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "10.0.0.1",
            "HTTP_X_FORWARDED_FOR": "203.0.113.42, 10.0.0.1",
        }

        ip = AuditEventEmitter.extract_ip(request)
        assert ip == "203.0.113.42"

    def test_extract_ip_fallback(self, db):
        """Helper falls back to REMOTE_ADDR when no X-Forwarded-For."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.1"}

        ip = AuditEventEmitter.extract_ip(request)
        assert ip == "192.168.1.1"

    def test_emit_document_uploaded_event(self, db, institution):
        """Emitter creates a DOCUMENT_UPLOADED event (SPEC §6.7)."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.DOCUMENT_UPLOADED,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"document_id": "doc-1", "version": 1},
        )

        assert event.event_type == "DOCUMENT_UPLOADED"
        assert event.user == user
        assert event.details == {"document_id": "doc-1", "version": 1}
        assert event.institution_id == institution.id

    def test_emit_document_signed_event(self, db, institution):
        """Emitter creates a DOCUMENT_SIGNED event with hash metadata."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.DOCUMENT_SIGNED,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"document_id": "doc-1", "version": 2, "sha256": "a" * 64},
        )

        assert event.event_type == "DOCUMENT_SIGNED"
        assert event.details["document_id"] == "doc-1"
        assert event.details["version"] == 2
        assert event.details["sha256"] == "a" * 64

    def test_emit_minutes_created_event(self, db, institution):
        """Emitter creates a MINUTES_CREATED event with acta type."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.MINUTES_CREATED,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"minutes_id": "min-1", "acta_type": "inicio"},
        )

        assert event.event_type == "MINUTES_CREATED"
        assert event.details == {"minutes_id": "min-1", "acta_type": "inicio"}
        assert AuditEvent.objects.count() == 1

    def test_document_events_queryable_by_type(self, db, institution):
        """DOCUMENT_* events can be filtered from the AuditEvent model."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()
        emitter.emit(
            event_type=AuditEventType.DOCUMENT_UPLOADED,
            user=user,
            institution_id=institution.id,
        )
        emitter.emit(
            event_type=AuditEventType.DOCUMENT_SIGNED,
            user=user,
            institution_id=institution.id,
        )
        emitter.emit(
            event_type=AuditEventType.MINUTES_CREATED,
            user=user,
            institution_id=institution.id,
        )

        assert AuditEvent.objects.filter(event_type="DOCUMENT_UPLOADED").count() == 1
        assert AuditEvent.objects.filter(event_type="DOCUMENT_SIGNED").count() == 1
        assert AuditEvent.objects.filter(event_type="MINUTES_CREATED").count() == 1
