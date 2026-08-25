"""
AuditEventEmitter extension tests — STRICT TDD.

Tests verify the PR 2 emitter extension:
- Backward compatibility: the legacy emit() signature still works unchanged.
- New keyword-only kwargs (entity_type, entity_id, action, old_values,
  new_values, project_id) are forwarded and persisted.
- AuditEventType choices include the new generic CRUD types.

Design reference: openspec/changes/audit/design.md
Spec reference: openspec/changes/audit/specs/audit/spec.md (RA-1, RA-2)
"""

import uuid

import pytest

from apps.accounts.audit import AuditEvent, AuditEventEmitter, AuditEventType
from apps.accounts.models import User
from apps.institutions.models import Institution


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


# ──────────────────────────────────────────────────────────
# Backward compatibility
# ──────────────────────────────────────────────────────────


class TestEmitterBackwardCompatibility:
    """Legacy callers must keep working with the extended emit()."""

    def test_legacy_keyword_call_still_works(self, db, institution):
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.LOGIN,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            details={"auth_source": "local"},
        )

        assert event.event_type == "LOGIN"
        assert event.user == user
        assert event.institution_id == institution.id
        assert event.details == {"auth_source": "local"}
        # New kwargs default to None for legacy callers.
        assert event.entity_type is None
        assert event.entity_id is None
        assert event.action is None
        assert event.old_values is None
        assert event.new_values is None
        assert event.project_id is None

    def test_legacy_positional_call_still_works(self, db):
        emitter = AuditEventEmitter()
        event = emitter.emit(AuditEventType.LOGOUT)
        assert event.event_type == "LOGOUT"
        assert AuditEvent.objects.count() == 1

    def test_emit_returns_audit_event_instance(self, db):
        emitter = AuditEventEmitter()
        event = emitter.emit(AuditEventType.LOGIN)
        assert isinstance(event, AuditEvent)


# ──────────────────────────────────────────────────────────
# New keyword-only kwargs
# ──────────────────────────────────────────────────────────


class TestEmitterNewKwargs:
    """New traceability kwargs are forwarded and persisted."""

    def test_new_kwargs_persisted(self, db, institution):
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        entity_id = uuid.uuid4()
        project_id = uuid.uuid4()
        emitter = AuditEventEmitter()

        event = emitter.emit(
            event_type=AuditEventType.CREATE,
            user=user,
            ip_address="10.0.0.1",
            institution_id=institution.id,
            entity_type="project",
            entity_id=entity_id,
            action="CREATE",
            old_values={"status": "borrador"},
            new_values={"title": "Nuevo proyecto"},
            project_id=project_id,
        )

        assert event.entity_type == "project"
        assert event.entity_id == entity_id
        assert event.action == "CREATE"
        assert event.old_values == {"status": "borrador"}
        assert event.new_values == {"title": "Nuevo proyecto"}
        assert event.project_id == project_id
        assert event.event_type == "CREATE"

    def test_new_kwargs_default_to_none(self, db):
        emitter = AuditEventEmitter()
        event = emitter.emit(event_type=AuditEventType.DELETE)
        assert event.entity_type is None
        assert event.entity_id is None
        assert event.action is None
        assert event.old_values is None
        assert event.new_values is None
        assert event.project_id is None

    def test_create_event_combined_with_legacy_kwargs(self, db, institution):
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        emitter = AuditEventEmitter()
        event = emitter.emit(
            event_type=AuditEventType.CREATE,
            user=user,
            institution_id=institution.id,
            entity_type="project",
            action="CREATE",
        )
        assert event.event_type == "CREATE"
        assert event.entity_type == "project"
        assert event.user == user
        assert event.institution_id == institution.id


# ──────────────────────────────────────────────────────────
# AuditEventType choices
# ──────────────────────────────────────────────────────────


class TestAuditEventTypeChoices:
    """New generic CRUD event types are registered."""

    @pytest.mark.parametrize(
        "value",
        ["CREATE", "UPDATE", "DELETE", "STATE_CHANGE", "DOCUMENT_DOWNLOADED"],
    )
    def test_new_types_in_choices(self, value):
        assert value in {v for v, _l in AuditEventType.choices}

    def test_legacy_types_preserved(self):
        for value in (
            "LOGIN",
            "LOGOUT",
            "ROLE_CHANGE",
            "BUDGET_CREATED",
            "DOCUMENT_UPLOADED",
            "PERMISSION_DENIED",
        ):
            assert value in {v for v, _l in AuditEventType.choices}
