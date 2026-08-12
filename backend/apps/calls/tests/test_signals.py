"""
Signal tests for calls app — STRICT TDD (RED phase).

Tests define expected behavior of `call_state_changed` signal emission:
- Emitted after every successful Call FSM transition with correct kwargs
- NOT emitted when a transition fails

Spec reference:  openspec/changes/cross-module-integration/spec.md — FR-001
Design reference: openspec/changes/cross-module-integration/design.md — IP-1
"""

from unittest.mock import patch

import pytest
from django_fsm import TransitionNotAllowed

from apps.calls.models import CallStatus

# ── Helpers ────────────────────────────────────────────


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(email=f"user_{User.objects.count()}@test.edu")


# ──────────────────────────────────────────────
# call_state_changed signal (IP-1)
# ──────────────────────────────────────────────


class TestCallStateChangedSignal:
    """call_state_changed is dispatched on every successful FSM transition."""

    def test_signal_emitted_on_open_call(self, db):
        """borrador → abierta emits call_state_changed with correct kwargs."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.BORRADOR)

        with patch.object(call_state_changed, "send") as mock_send:
            CallService.open_call(call, user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["call"] == call
        assert kwargs["from_state"] == CallStatus.BORRADOR
        assert kwargs["to_state"] == CallStatus.ABIERTA
        assert kwargs["triggered_by"] == user

    def test_signal_emitted_on_close_call(self, db):
        """abierta → cerrada emits call_state_changed."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.ABIERTA)

        with patch.object(call_state_changed, "send") as mock_send:
            CallService.close_call(call, user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["from_state"] == CallStatus.ABIERTA
        assert kwargs["to_state"] == CallStatus.CERRADA
        assert kwargs["triggered_by"] == user

    def test_signal_emitted_on_start_evaluation(self, db):
        """cerrada → en_evaluacion emits call_state_changed."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.CERRADA)

        with patch.object(call_state_changed, "send") as mock_send:
            CallService.start_evaluation(call, user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["from_state"] == CallStatus.CERRADA
        assert kwargs["to_state"] == CallStatus.EN_EVALUACION

    def test_signal_emitted_on_publish_results(self, db):
        """en_evaluacion → resultados_publicados emits call_state_changed."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.EN_EVALUACION)

        with patch.object(call_state_changed, "send") as mock_send:
            CallService.publish_results(call, user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["from_state"] == CallStatus.EN_EVALUACION
        assert kwargs["to_state"] == CallStatus.RESULTADOS_PUBLICADOS

    def test_signal_emitted_on_archive(self, db):
        """cerrada → archivada emits call_state_changed."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.CERRADA)

        with patch.object(call_state_changed, "send") as mock_send:
            CallService.archive(call, user)

        mock_send.assert_called_once()
        kwargs = mock_send.call_args[1]
        assert kwargs["from_state"] == CallStatus.CERRADA
        assert kwargs["to_state"] == CallStatus.ARCHIVADA

    def test_no_signal_on_failed_transition(self, db):
        """Failed FSM transition does NOT emit call_state_changed."""
        from apps.calls.services import CallService
        from apps.calls.signals import call_state_changed
        from apps.calls.tests.conftest import CallFactory

        user = _make_user()
        call = CallFactory(status=CallStatus.ABIERTA)

        with patch.object(call_state_changed, "send") as mock_send:
            with pytest.raises(TransitionNotAllowed):
                CallService.open_call(call, user)

        mock_send.assert_not_called()
