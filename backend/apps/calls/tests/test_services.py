"""
Service layer tests for calls app — STRICT TDD (RED phase).

Tests define expected behavior of:
- CallService: create, update, delete, 5 FSM orchestration methods, _log_transition
- CallDocumentService: add, update, remove with terminal-state guard
- CallProjectService: link (abierta-only guard), unlink

Spec reference:  openspec/changes/calls/spec.md — RF-067 through RF-070
Design reference: openspec/changes/calls/design.md — Service Layer

RED PHASE: Tests fail because services.py does not exist.
"""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.calls.models import (
    Call,
    CallDocument,
    CallProject,
    CallStateLog,
    CallStatus,
    CallType,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(email=f"user_{User.objects.count()}@test.edu")


# ──────────────────────────────────────────────
# CallService.create()
# ──────────────────────────────────────────────


class TestCallServiceCreate:
    """CallService.create() — call creation with business rules."""

    def test_create_call_borrador(self, db):
        """create() returns a Call with status='borrador'."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory()
        institution = call.institution
        created = CallService.create(
            institution=institution,
            user=user,
            title="Research Grant 2026",
            description="Funding for AI projects",
            call_type=CallType.INTERNAL,
        )

        assert created.pk is not None
        assert created.status == CallStatus.BORRADOR
        assert created.institution == institution
        assert created.title == "Research Grant 2026"
        assert created.call_type == CallType.INTERNAL
        assert created.external_entity == ""

    def test_create_external_call(self, db):
        """create() allows external call with external_entity."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory()
        institution = call.institution
        created = CallService.create(
            institution=institution,
            user=user,
            title="External Grant",
            description="External funding",
            call_type=CallType.EXTERNAL,
            external_entity="CONAHCYT",
        )

        assert created.call_type == CallType.EXTERNAL
        assert created.external_entity == "CONAHCYT"

    def test_create_rejects_internal_with_entity(self, db):
        """create() raises ValidationError for internal call with entity."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory.build()
        with pytest.raises(ValidationError, match=r"external entity"):
            CallService.create(
                institution=call.institution,
                user=user,
                title="Test",
                description="Desc",
                call_type=CallType.INTERNAL,
                external_entity="CONAHCYT",
            )

    def test_create_rejects_external_without_entity(self, db):
        """create() raises ValidationError for external call without entity."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory.build()
        with pytest.raises(ValidationError, match=r"External entity"):
            CallService.create(
                institution=call.institution,
                user=user,
                title="Test",
                description="Desc",
                call_type=CallType.EXTERNAL,
                external_entity="",
            )

    def test_create_rejects_invalid_dates(self, db):
        """create() raises ValidationError when submission_end < submission_start."""
        import datetime

        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory.build()
        with pytest.raises(ValidationError, match=r"Submission end"):
            CallService.create(
                institution=call.institution,
                user=user,
                title="Test",
                description="Desc",
                call_type=CallType.INTERNAL,
                submission_start=datetime.date(2026, 6, 1),
                submission_end=datetime.date(2026, 1, 1),
            )

    def test_create_accepts_valid_dates(self, db):
        """create() succeeds when submission_end >= submission_start."""
        import datetime

        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory()
        created = CallService.create(
            institution=call.institution,
            user=user,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            submission_start=datetime.date(2026, 1, 1),
            submission_end=datetime.date(2026, 6, 30),
        )
        assert created.submission_start == datetime.date(2026, 1, 1)
        assert created.submission_end == datetime.date(2026, 6, 30)


# ──────────────────────────────────────────────
# CallService.update()
# ──────────────────────────────────────────────


class TestCallServiceUpdate:
    """CallService.update() — call updates with terminal-state guard."""

    def test_update_borrador_succeeds(self, db):
        """update() on non-terminal call updates fields."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.BORRADOR, title="Original")
        updated = CallService.update(call, title="Updated Title")

        assert updated.title == "Updated Title"
        call.refresh_from_db()
        assert call.title == "Updated Title"

    def test_update_terminal_raises(self, db):
        """update() on terminal call raises ValidationError."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.ARCHIVADA, title="Terminal")
        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            CallService.update(call, title="Should fail")

    def test_update_rejects_invalid_dates(self, db):
        """update() raises ValidationError when date ordering is violated."""
        import datetime

        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        with pytest.raises(ValidationError, match=r"Submission end"):
            CallService.update(
                call,
                submission_start=datetime.date(2026, 6, 1),
                submission_end=datetime.date(2026, 1, 1),
            )


# ──────────────────────────────────────────────
# CallService.delete()
# ──────────────────────────────────────────────


class TestCallServiceDelete:
    """CallService.delete() — delete guard (borrador only, no linked projects)."""

    def test_delete_borrador_succeeds(self, db):
        """delete() removes a call in borrador with no linked projects."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        pk = call.pk
        CallService.delete(call)
        assert not Call.objects.filter(pk=pk).exists()

    def test_delete_non_borrador_raises(self, db):
        """delete() raises ValidationError when call is not borrador."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.ABIERTA)
        with pytest.raises(ValidationError, match=r"[Bb]orrador"):
            CallService.delete(call)

    def test_delete_with_linked_projects_raises(self, db):
        """delete() raises ValidationError when call has linked projects."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory, CallProjectFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        CallProjectFactory(call=call)
        with pytest.raises(ValidationError, match=r"[Ll]inked"):
            CallService.delete(call)


# ──────────────────────────────────────────────
# CallService FSM orchestration (5 methods)
# ──────────────────────────────────────────────


class TestCallServiceFSM:
    """FSM orchestration: each method calls model transition + saves + logs + emits audit."""

    def _make_user(self):
        from apps.accounts.models import User

        return User.objects.create_user(email=f"user_{User.objects.count()}@test.edu")

    def _transition(self, call, user, method_name, **kwargs):
        """Helper to call a service FSM method and verify results."""
        from apps.calls.services import CallService

        from_state = call.status
        method = getattr(CallService, method_name)
        updated = method(call, user, **kwargs)

        # Assert state changed
        assert updated.status != from_state
        # Assert CallStateLog created
        log = CallStateLog.objects.filter(call=call).latest("created_at")
        assert log.from_state == from_state
        assert log.to_state == updated.status
        assert log.triggered_by == user

        return updated, log

    # ── open_call() ───────────────────────────

    def test_open_call_borrador_to_abierta(self, db):
        """open_call() transitions borrador → abierta with logging and audit."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.BORRADOR)

        with patch("apps.calls.services.AuditEventEmitter") as mock_emitter_class:
            mock_emitter = mock_emitter_class.return_value
            updated = CallService.open_call(call, user)

        assert updated.status == CallStatus.ABIERTA
        log = CallStateLog.objects.get(call=call)
        assert log.from_state == CallStatus.BORRADOR
        assert log.to_state == CallStatus.ABIERTA
        assert log.triggered_by == user
        mock_emitter.emit.assert_called_once()
        call_kwargs = mock_emitter.emit.call_args[1]
        assert call_kwargs["event_type"] == "CALL_STATE_CHANGE"
        assert call_kwargs["user"] == user

    # ── close_call() ────────────────────────────

    def test_close_call_abierta_to_cerrada(self, db):
        """close_call() transitions abierta → cerrada."""
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.ABIERTA)

        with patch("apps.calls.services.AuditEventEmitter"):
            updated, log = self._transition(call, user, "close_call")

        assert updated.status == CallStatus.CERRADA

    # ── start_evaluation() ──────────────────────

    def test_start_evaluation_cerrada_to_en_evaluacion(self, db):
        """start_evaluation() transitions cerrada → en_evaluacion."""
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.CERRADA)

        with patch("apps.calls.services.AuditEventEmitter"):
            updated, log = self._transition(call, user, "start_evaluation")

        assert updated.status == CallStatus.EN_EVALUACION

    # ── publish_results() ───────────────────────

    def test_publish_results_en_evaluacion_to_resultados(self, db):
        """publish_results() transitions en_evaluacion → resultados_publicados."""
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.EN_EVALUACION)

        with patch("apps.calls.services.AuditEventEmitter"):
            updated, log = self._transition(call, user, "publish_results")

        assert updated.status == CallStatus.RESULTADOS_PUBLICADOS

    # ── archive() ───────────────────────────────

    def test_archive_from_cerrada(self, db):
        """archive() transitions cerrada → archivada (terminal)."""
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.CERRADA)

        with patch("apps.calls.services.AuditEventEmitter"):
            updated, log = self._transition(call, user, "archive")

        assert updated.status == CallStatus.ARCHIVADA

    def test_archive_from_resultados_publicados(self, db):
        """archive() transitions resultados_publicados → archivada."""
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.RESULTADOS_PUBLICADOS)

        with patch("apps.calls.services.AuditEventEmitter"):
            updated, log = self._transition(call, user, "archive")

        assert updated.status == CallStatus.ARCHIVADA

    def test_fsm_invalid_transition_raises(self, db):
        """FSM method on wrong state raises TransitionNotAllowed."""
        from django_fsm import TransitionNotAllowed

        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.ABIERTA)

        with pytest.raises(TransitionNotAllowed):
            CallService.open_call(call, user)

    # ── Cross-cutting: audit event emission ─────

    def test_fsm_emits_audit_event(self, db):
        """Every FSM method emits an AuditEvent via AuditEventEmitter."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = self._make_user()
        call = CallFactory(status=CallStatus.BORRADOR)

        with patch("apps.calls.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            CallService.open_call(call, user)

        mock_emitter.emit.assert_called_once()
        call_kwargs = mock_emitter.emit.call_args[1]
        assert call_kwargs["event_type"] == "CALL_STATE_CHANGE"
        assert call_kwargs["user"] == user
        assert call_kwargs["institution_id"] == call.institution_id
        assert "from_state" in call_kwargs["details"]
        assert "to_state" in call_kwargs["details"]


# ──────────────────────────────────────────────
# CallService._log_transition()
# ──────────────────────────────────────────────


class TestLogTransition:
    """CallService._log_transition() — creates CallStateLog + emits AuditEvent."""

    def test_creates_state_log(self, db):
        """_log_transition() creates a CallStateLog row."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.BORRADOR)

        with patch("apps.calls.services.AuditEventEmitter"):
            CallService._log_transition(
                call,
                CallStatus.BORRADOR,
                CallStatus.ABIERTA,
                user,
                reason="Opened for submissions.",
            )

        log = CallStateLog.objects.get(call=call)
        assert log.from_state == CallStatus.BORRADOR
        assert log.to_state == CallStatus.ABIERTA
        assert log.triggered_by == user
        assert log.reason == "Opened for submissions."

    def test_emits_audit_event(self, db):
        """_log_transition() emits an AuditEvent."""
        from apps.calls.services import CallService
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory()

        with patch("apps.calls.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            CallService._log_transition(call, CallStatus.BORRADOR, CallStatus.ABIERTA, user)

        mock_emitter.emit.assert_called_once_with(
            event_type="CALL_STATE_CHANGE",
            user=user,
            institution_id=call.institution_id,
            details={
                "call_id": str(call.pk),
                "from_state": CallStatus.BORRADOR,
                "to_state": CallStatus.ABIERTA,
                "triggered_by": user.email if user else None,
            },
        )


# ──────────────────────────────────────────────
# CallDocumentService
# ──────────────────────────────────────────────


class TestCallDocumentService:
    """CallDocumentService — add, update, remove with terminal-state guard."""

    def test_add_document_succeeds(self, db):
        """add() creates a CallDocument for non-terminal call."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        doc = CallDocumentService.add(
            call,
            name="Convocatoria.pdf",
            doc_type="convocatoria",
            external_url="https://storage.example.com/convocatoria.pdf",
        )

        assert doc.pk is not None
        assert doc.call == call
        assert doc.name == "Convocatoria.pdf"
        assert doc.doc_type == "convocatoria"

    def test_add_document_terminal_raises(self, db):
        """add() raises ValidationError when call is terminal."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.ARCHIVADA)
        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            CallDocumentService.add(
                call,
                name="Doc",
                doc_type="otro",
                external_url="https://example.com/doc.pdf",
            )

    def test_update_document_succeeds(self, db):
        """update() changes fields for non-terminal parent."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallDocumentFactory, CallFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        doc = CallDocumentFactory(call=call, name="Original")

        updated = CallDocumentService.update(doc, name="Updated")
        assert updated.name == "Updated"

    def test_update_document_terminal_raises(self, db):
        """update() raises when parent call is terminal."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallDocumentFactory, CallFactory

        call = CallFactory(status=CallStatus.ARCHIVADA)
        doc = CallDocumentFactory(call=call)

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            CallDocumentService.update(doc, name="Should fail")

    def test_remove_document_succeeds(self, db):
        """remove() deletes document for non-terminal parent."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallDocumentFactory, CallFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        doc = CallDocumentFactory(call=call)

        CallDocumentService.remove(doc)
        assert not CallDocument.objects.filter(pk=doc.pk).exists()

    def test_remove_document_terminal_raises(self, db):
        """remove() raises when parent call is terminal."""
        from apps.calls.services import CallDocumentService
        from apps.calls.tests.conftest import CallDocumentFactory, CallFactory

        call = CallFactory(status=CallStatus.ARCHIVADA)
        doc = CallDocumentFactory(call=call)

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            CallDocumentService.remove(doc)


# ──────────────────────────────────────────────
# CallProjectService
# ──────────────────────────────────────────────


class TestCallProjectService:
    """CallProjectService — link (abierta-only guard), unlink."""

    def test_link_project_to_abierta_succeeds(self, db):
        """link() creates CallProject when call is abierta."""
        from apps.calls.services import CallProjectService
        from apps.calls.tests.conftest import CallFactory
        from apps.projects.tests.conftest import ProjectFactory

        call = CallFactory(status=CallStatus.ABIERTA)
        project = ProjectFactory(institution=call.institution)

        cp = CallProjectService.link(call, project)
        assert cp.pk is not None
        assert cp.call == call
        assert cp.project == project

    def test_link_project_to_non_abierta_raises(self, db):
        """link() raises ValidationError when call is not abierta."""
        from apps.calls.services import CallProjectService
        from apps.calls.tests.conftest import CallFactory
        from apps.projects.tests.conftest import ProjectFactory

        call = CallFactory(status=CallStatus.BORRADOR)
        project = ProjectFactory(institution=call.institution)

        with pytest.raises(ValidationError, match=r"[Oo]pen calls"):
            CallProjectService.link(call, project)

    def test_link_duplicate_project_raises(self, db):
        """link() raises IntegrityError/ValidationError for duplicate project."""
        from apps.calls.services import CallProjectService
        from apps.calls.tests.conftest import CallFactory
        from apps.projects.tests.conftest import ProjectFactory

        call1 = CallFactory(status=CallStatus.ABIERTA)
        call2 = CallFactory(status=CallStatus.ABIERTA, institution=call1.institution)
        project = ProjectFactory(institution=call1.institution)

        CallProjectService.link(call1, project)

        with pytest.raises((ValidationError, IntegrityError)):
            CallProjectService.link(call2, project)

    def test_link_same_project_to_same_call_raises(self, db):
        """link() raises error when linking same project to same call twice."""
        from apps.calls.services import CallProjectService
        from apps.calls.tests.conftest import CallFactory
        from apps.projects.tests.conftest import ProjectFactory

        call = CallFactory(status=CallStatus.ABIERTA)
        project = ProjectFactory(institution=call.institution)

        CallProjectService.link(call, project)
        with pytest.raises((ValidationError, IntegrityError)):
            CallProjectService.link(call, project)

    def test_unlink_project_succeeds(self, db):
        """unlink() deletes the CallProject association."""
        from apps.calls.services import CallProjectService
        from apps.calls.tests.conftest import CallProjectFactory

        cp = CallProjectFactory()
        pk = cp.pk
        CallProjectService.unlink(cp)
        assert not CallProject.objects.filter(pk=pk).exists()
