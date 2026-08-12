"""
Service layer for calls — business logic + FSM orchestration.

CallService: CRUD + 5 FSM transition methods + _log_transition.
CallDocumentService: document management with terminal-state guard.
CallProjectService: project linking with state guard (abierta only).

All state transitions are centralized here — views never call
django-fsm @transition methods directly.

Design reference: openspec/changes/calls/design.md — Service Layer
Spec reference:   openspec/changes/calls/spec.md — RF-067 through RF-070
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.audit import AuditEventEmitter
from apps.calls.models import (
    TERMINAL_STATES,
    Call,
    CallDocument,
    CallProject,
    CallStateLog,
)
from apps.calls.signals import call_state_changed

# ── Terminal-state validation helper ───────────────────────


def _validate_not_terminal(call):
    """Reject mutations if the call is in a terminal state."""
    if call.status in TERMINAL_STATES:
        raise ValidationError("Call is in a terminal state and cannot be modified.")


# ──────────────────────────────────────────────
# CallService
# ──────────────────────────────────────────────


class CallService:
    """CRUD and FSM orchestration for the Call model.

    All methods are static — this is a plain Python class, not a
    Django model. Service signatures accept model instances and
    raw values, not ORM primitives.
    """

    # ── CRUD ───────────────────────────────────────────

    @staticmethod
    def create(institution, user, **data):
        """Create a Call with status='borrador'.

        Validates type/entity rules and date ordering via model
        full_clean().
        """
        call = Call(
            institution=institution,
            status="borrador",
            **data,
        )
        call.full_clean()
        call.save()
        return call

    @staticmethod
    def update(call, **data):
        """Update a Call — rejected if terminal.

        Delegates to model full_clean() + save() for validation.
        Only fields present in data are updated.
        """
        _validate_not_terminal(call)

        for field, value in data.items():
            setattr(call, field, value)
        call.full_clean()
        call.save()
        return call

    @staticmethod
    def delete(call):
        """Delete a Call — rejected if not borrador or has linked projects."""
        if call.status != "borrador":
            raise ValidationError("Only calls in borrador can be deleted.")

        if call.call_projects.exists():
            raise ValidationError("Cannot delete a call with linked projects.")

        call.delete()

    # ── FSM Orchestration ──────────────────────────────

    @staticmethod
    def open_call(call, user):
        """borrador → abierta. Uses select_for_update + _log_transition."""
        from_state = call.status
        with transaction.atomic():
            locked = Call.objects.select_for_update().get(pk=call.pk)
            locked.open_call()
            locked.save()
            CallService._log_transition(locked, from_state, locked.status, user)
            return locked

    @staticmethod
    def close_call(call, user):
        """abierta → cerrada."""
        from_state = call.status
        with transaction.atomic():
            locked = Call.objects.select_for_update().get(pk=call.pk)
            locked.close_call()
            locked.save()
            CallService._log_transition(locked, from_state, locked.status, user)
            return locked

    @staticmethod
    def start_evaluation(call, user):
        """cerrada → en_evaluacion."""
        from_state = call.status
        with transaction.atomic():
            locked = Call.objects.select_for_update().get(pk=call.pk)
            locked.start_evaluation()
            locked.save()
            CallService._log_transition(locked, from_state, locked.status, user)
            return locked

    @staticmethod
    def publish_results(call, user):
        """en_evaluacion → resultados_publicados."""
        from_state = call.status
        with transaction.atomic():
            locked = Call.objects.select_for_update().get(pk=call.pk)
            locked.publish_results()
            locked.save()
            CallService._log_transition(locked, from_state, locked.status, user)
            return locked

    @staticmethod
    def archive(call, user):
        """cerrada | resultados_publicados → archivada (terminal)."""
        from_state = call.status
        with transaction.atomic():
            locked = Call.objects.select_for_update().get(pk=call.pk)
            locked.archive()
            locked.save()
            CallService._log_transition(locked, from_state, locked.status, user)
            return locked

    # ── Audit / Logging ────────────────────────────────

    @staticmethod
    def _log_transition(call, from_state, to_state, user, reason=""):
        """Create CallStateLog + emit AuditEvent.

        Private helper called by every FSM orchestration method.
        Two side-effects:
        1. Write a CallStateLog row (domain audit).
        2. Emit an AuditEvent via AuditEventEmitter (global audit).
        """
        CallStateLog.objects.create(
            call=call,
            from_state=from_state,
            to_state=to_state,
            triggered_by=user,
            reason=reason,
        )
        call_state_changed.send(
            sender=CallService,
            call=call,
            from_state=from_state,
            to_state=to_state,
            triggered_by=user,
        )
        AuditEventEmitter().emit(
            event_type="CALL_STATE_CHANGE",
            user=user,
            institution_id=call.institution_id,
            details={
                "call_id": str(call.pk),
                "from_state": from_state,
                "to_state": to_state,
                "triggered_by": user.email if user else None,
            },
        )


# ──────────────────────────────────────────────
# CallDocumentService
# ──────────────────────────────────────────────


class CallDocumentService:
    """Document management with terminal-state guard."""

    @staticmethod
    def add(call, name, doc_type, external_url):
        """Add a document metadata record — rejected if call is terminal."""
        _validate_not_terminal(call)

        doc = CallDocument(
            call=call,
            name=name,
            doc_type=doc_type,
            external_url=external_url,
        )
        doc.full_clean()
        doc.save()
        return doc

    @staticmethod
    def update(document, **data):
        """Update document fields — rejected if parent call is terminal."""
        _validate_not_terminal(document.call)

        for field, value in data.items():
            setattr(document, field, value)
        document.full_clean()
        document.save()
        return document

    @staticmethod
    def remove(document):
        """Delete a document — rejected if parent call is terminal."""
        _validate_not_terminal(document.call)
        document.delete()


# ──────────────────────────────────────────────
# CallProjectService
# ──────────────────────────────────────────────


class CallProjectService:
    """Project linking with state guard (abierta only)."""

    @staticmethod
    def link(call, project):
        """Link a Project to a Call — rejected if call is not abierta.

        UniqueConstraint(project) enforces one call per project at DB level.
        """
        if call.status != "abierta":
            raise ValidationError("Projects can only be linked to open calls.")

        cp = CallProject(call=call, project=project)
        try:
            cp.full_clean()
            cp.save()
        except IntegrityError:
            raise ValidationError("Project is already associated with a call.")
        return cp

    @staticmethod
    def unlink(call_project):
        """Delete the CallProject association."""
        call_project.delete()
