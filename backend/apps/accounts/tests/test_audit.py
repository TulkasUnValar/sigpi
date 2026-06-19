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
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution

# ── RED: These imports WILL fail until audit.py is created ──
from apps.accounts.audit import (
    AuditEvent,
    AuditEventEmitter,
    AuditEventType,
)


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
        e1 = AuditEvent.objects.create(
            user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.1",
        )
        e2 = AuditEvent.objects.create(
            user=user, event_type=AuditEventType.LOGOUT, ip_address="10.0.0.1",
        )
        events = list(AuditEvent.objects.all())
        assert events[0].timestamp >= events[1].timestamp

    def test_filter_by_event_type(self, db):
        """Events can be filtered by event_type."""
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.1")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGIN, ip_address="10.0.0.2")
        AuditEvent.objects.create(user=user, event_type=AuditEventType.LOGOUT, ip_address="10.0.0.1")

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
