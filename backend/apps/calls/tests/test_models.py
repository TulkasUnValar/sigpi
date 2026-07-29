"""
Model tests for calls app — STRICT TDD.

Tests define the expected behavior of the 4-entity calls module:
Call, CallDocument, CallProject, CallStateLog.

Spec reference:  openspec/changes/calls/spec.md
Design reference: openspec/changes/calls/design.md

RED PHASE: All tests fail because models are empty stubs.
"""

import datetime
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_fsm import TransitionNotAllowed

from apps.calls.models import (
    TERMINAL_STATES,
    Call,
    CallDocument,
    CallDocumentType,
    CallProject,
    CallStateLog,
    CallStatus,
    CallType,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(
        name=f"Test University {code}",
        code=code,
    )


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_project(institution):
    import datetime as dt
    import uuid as _uuid

    from apps.institutions.models import ResearchCenter
    from apps.projects.models import Project
    from apps.researchers.models import Researcher

    center = ResearchCenter.objects.create(
        institution=institution,
        name="Test Center",
        code="TC",
    )
    researcher = Researcher.objects.create(
        institution=institution,
        first_name="Maria",
        last_name="Gomez",
        document_type="CC",
        document_number=f"DN-{_uuid.uuid4().hex[:8]}",
        primary_email=f"maria.{_uuid.uuid4().hex[:4]}@test.edu",
    )
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=researcher,
        title="Test Project",
        abstract="An abstract",
        objectives="Objectives text",
        methodology="Methodology text",
        expected_results="Expected results text",
        keywords="ai, nlp",
        start_date=dt.date(2026, 1, 1),
        estimated_end_date=dt.date(2026, 12, 31),
    )


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestCallStatusEnum:
    """CallStatus TextChoices has 6 states."""

    def test_all_six_states_defined(self):
        """All 6 FSM states are present in CallStatus."""
        expected = {
            "borrador",
            "abierta",
            "cerrada",
            "en_evaluacion",
            "resultados_publicados",
            "archivada",
        }
        actual = {choice[0] for choice in CallStatus.choices}
        assert actual == expected

    def test_terminal_states_constant(self):
        """TERMINAL_STATES contains archivada."""
        assert CallStatus.ARCHIVADA in TERMINAL_STATES
        assert CallStatus.BORRADOR not in TERMINAL_STATES
        assert CallStatus.ABIERTA not in TERMINAL_STATES


class TestCallTypeEnum:
    """CallType TextChoices has 2 types."""

    def test_both_types_defined(self):
        expected = {"internal", "external"}
        actual = {choice[0] for choice in CallType.choices}
        assert actual == expected


class TestCallDocumentTypeEnum:
    """CallDocumentType TextChoices has 5 types."""

    def test_all_five_types_defined(self):
        expected = {"convocatoria", "anexo", "reglamento", "resultado", "otro"}
        actual = {choice[0] for choice in CallDocumentType.choices}
        assert actual == expected


# ──────────────────────────────────────────────
# Call Model Field Tests
# ──────────────────────────────────────────────


class TestCallFields:
    """Call model field behavior and defaults."""

    def test_create_call_minimal(self, db):
        """Call can be created with required fields, defaults to borrador."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Research Grant 2026",
            description="Funding for AI projects",
            call_type=CallType.INTERNAL,
        )
        assert call.id is not None
        assert isinstance(call.id, uuid.UUID)
        assert call.institution == inst
        assert call.status == CallStatus.BORRADOR
        assert call.title == "Research Grant 2026"
        assert call.external_entity == ""
        assert call.submission_start is None
        assert call.submission_end is None
        assert call.evaluation_start is None
        assert call.evaluation_end is None

    def test_create_call_external(self, db):
        """External call requires external_entity."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="External Grant",
            description="External funding",
            call_type=CallType.EXTERNAL,
            external_entity="CONAHCYT",
        )
        assert call.call_type == CallType.EXTERNAL
        assert call.external_entity == "CONAHCYT"

    def test_str_representation(self, db):
        """Call __str__ returns the title."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="AI Grant",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        assert str(call) == "AI Grant"

    def test_timestamps_auto_set(self, db):
        """created_at and updated_at are set automatically."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        assert call.created_at is not None
        assert call.updated_at is not None


# ──────────────────────────────────────────────
# Call clean() Validation Tests
# ──────────────────────────────────────────────


class TestCallCleanValidation:
    """Call.clean() enforces type/entity and date ordering rules."""

    def test_clean_rejects_internal_with_entity(self, db):
        """Internal call with external_entity raises ValidationError."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            external_entity="CONAHCYT",
        )
        with pytest.raises(ValidationError):
            call.full_clean()

    def test_clean_rejects_external_without_entity(self, db):
        """External call without external_entity raises ValidationError."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.EXTERNAL,
            external_entity="",
        )
        with pytest.raises(ValidationError):
            call.full_clean()

    def test_clean_rejects_submission_end_before_start(self, db):
        """submission_end < submission_start raises ValidationError."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            submission_start=datetime.date(2026, 6, 1),
            submission_end=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            call.full_clean()

    def test_clean_rejects_evaluation_end_before_start(self, db):
        """evaluation_end < evaluation_start raises ValidationError."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            evaluation_start=datetime.date(2026, 6, 1),
            evaluation_end=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            call.full_clean()

    def test_clean_accepts_valid_dates(self, db):
        """Valid date ordering passes clean() without error."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            submission_start=datetime.date(2026, 1, 1),
            submission_end=datetime.date(2026, 6, 30),
            evaluation_start=datetime.date(2026, 7, 1),
            evaluation_end=datetime.date(2026, 12, 31),
        )
        call.full_clean()  # should not raise

    def test_clean_accepts_null_dates(self, db):
        """All dates null passes clean() without error."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.EXTERNAL,
            external_entity="CONAHCYT",
        )
        call.full_clean()  # should not raise


# ──────────────────────────────────────────────
# Call DB CHECK Constraint Tests
# ──────────────────────────────────────────────


class TestCallCheckConstraints:
    """DB CHECK constraints enforce integrity at database level."""

    def test_check_constraints_exist(self):
        """All CHECK constraints are registered in Meta.constraints."""
        constraint_names = {c.name for c in Call._meta.constraints}
        assert "check_internal_no_entity" in constraint_names
        assert "check_external_has_entity" in constraint_names
        assert "check_submission_dates" in constraint_names
        assert "check_evaluation_dates" in constraint_names

    def test_validate_constraints_rejects_internal_with_entity(self, db):
        """validate_constraints() catches internal call with entity."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            external_entity="CONAHCYT",
        )
        with pytest.raises(ValidationError):
            call.validate_constraints()

    def test_validate_constraints_rejects_external_without_entity(self, db):
        """validate_constraints() catches external call without entity."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.EXTERNAL,
            external_entity="",
        )
        with pytest.raises(ValidationError):
            call.validate_constraints()

    def test_validate_constraints_rejects_submission_end_before_start(self, db):
        """validate_constraints() catches submission_end < submission_start."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            submission_start=datetime.date(2026, 6, 1),
            submission_end=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            call.validate_constraints()

    def test_validate_constraints_rejects_evaluation_end_before_start(self, db):
        """validate_constraints() catches evaluation_end < evaluation_start."""
        inst = _make_institution("TU")
        call = Call(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            evaluation_start=datetime.date(2026, 6, 1),
            evaluation_end=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            call.validate_constraints()


# ──────────────────────────────────────────────
# CallDocument Tests
# ──────────────────────────────────────────────


class TestCallDocumentFields:
    """CallDocument model field behavior."""

    def test_create_document(self, db):
        """CallDocument stores name, type, and external URL (RF-069)."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        doc = CallDocument.objects.create(
            call=call,
            name="Convocatoria.pdf",
            doc_type=CallDocumentType.CONVOCATORIA,
            external_url="https://storage.example.com/convocatoria.pdf",
        )
        assert doc.name == "Convocatoria.pdf"
        assert doc.doc_type == CallDocumentType.CONVOCATORIA
        assert doc.external_url == "https://storage.example.com/convocatoria.pdf"
        assert doc.call == call
        assert doc.created_at is not None

    def test_doc_type_choices_valid(self, db):
        """All CallDocumentType choices are valid."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        for dtype in ("convocatoria", "anexo", "reglamento", "resultado", "otro"):
            doc = CallDocument(
                call=call,
                name=f"doc.{dtype}",
                doc_type=dtype,
                external_url=f"https://example.com/{dtype}",
            )
            doc.full_clean()  # should not raise

    def test_doc_type_invalid_choice(self, db):
        """Invalid doc_type raises ValidationError."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        doc = CallDocument(
            call=call,
            name="file.txt",
            doc_type="invalid",
            external_url="https://example.com/file.txt",
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_str_representation(self, db):
        """CallDocument __str__ includes name and type."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        doc = CallDocument.objects.create(
            call=call,
            name="Convocatoria.pdf",
            doc_type=CallDocumentType.CONVOCATORIA,
            external_url="https://example.com/convocatoria.pdf",
        )
        assert "Convocatoria.pdf" in str(doc)


# ──────────────────────────────────────────────
# CallProject Tests
# ──────────────────────────────────────────────


class TestCallProjectFields:
    """CallProject model field behavior and constraints."""

    def test_create_call_project(self, db):
        """CallProject links a Project to a Call."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        project = _make_project(inst)
        cp = CallProject.objects.create(call=call, project=project)
        assert cp.call == call
        assert cp.project == project
        assert cp.linked_at is not None

    def test_unique_project_constraint(self, db):
        """UniqueConstraint (project) enforced — one call per project."""
        inst = _make_institution("TU")
        call1 = Call.objects.create(
            institution=inst,
            title="Call 1",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        call2 = Call.objects.create(
            institution=inst,
            title="Call 2",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        project = _make_project(inst)
        CallProject.objects.create(call=call1, project=project)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                CallProject.objects.create(call=call2, project=project)

    def test_str_representation(self, db):
        """CallProject __str__ includes call and project."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test Call",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        project = _make_project(inst)
        cp = CallProject.objects.create(call=call, project=project)
        assert "Test Call" in str(cp)


# ──────────────────────────────────────────────
# CallStateLog Tests
# ──────────────────────────────────────────────


class TestCallStateLogFields:
    """CallStateLog model field behavior."""

    def test_create_state_log(self, db):
        """CallStateLog records from_state, to_state, triggered_by."""
        user = _make_user("admin@test.edu")
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        log = CallStateLog.objects.create(
            call=call,
            from_state=CallStatus.BORRADOR,
            to_state=CallStatus.ABIERTA,
            triggered_by=user,
            reason="Opened for submissions.",
        )
        assert log.call == call
        assert log.from_state == CallStatus.BORRADOR
        assert log.to_state == CallStatus.ABIERTA
        assert log.triggered_by == user
        assert log.reason == "Opened for submissions."
        assert log.created_at is not None

    def test_triggered_by_nullable(self, db):
        """triggered_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        log = CallStateLog.objects.create(
            call=call,
            from_state=CallStatus.BORRADOR,
            to_state=CallStatus.ABIERTA,
        )
        assert log.triggered_by is None

    def test_reason_blank_by_default(self, db):
        """reason defaults to empty string."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        log = CallStateLog.objects.create(
            call=call,
            from_state=CallStatus.BORRADOR,
            to_state=CallStatus.ABIERTA,
        )
        assert log.reason == ""

    def test_str_representation(self, db):
        """CallStateLog __str__ includes states."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        log = CallStateLog.objects.create(
            call=call,
            from_state=CallStatus.BORRADOR,
            to_state=CallStatus.ABIERTA,
        )
        assert CallStatus.BORRADOR in str(log)
        assert CallStatus.ABIERTA in str(log)


# ──────────────────────────────────────────────
# FSM Transition Tests — Valid Transitions
# ──────────────────────────────────────────────


class TestFsmValidTransitions:
    """Every valid FSM transition succeeds (5 transitions)."""

    def test_open_call_borrador_to_abierta(self, db):
        """open_call(): borrador → abierta."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        assert call.status == CallStatus.BORRADOR
        call.open_call()
        call.save()
        assert call.status == CallStatus.ABIERTA

    def test_close_call_abierta_to_cerrada(self, db):
        """close_call(): abierta → cerrada."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.ABIERTA,
        )
        call.close_call()
        call.save()
        assert call.status == CallStatus.CERRADA

    def test_start_evaluation_cerrada_to_en_evaluacion(self, db):
        """start_evaluation(): cerrada → en_evaluacion."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.CERRADA,
        )
        call.start_evaluation()
        call.save()
        assert call.status == CallStatus.EN_EVALUACION

    def test_publish_results_en_evaluacion_to_resultados(self, db):
        """publish_results(): en_evaluacion → resultados_publicados."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.EN_EVALUACION,
        )
        call.publish_results()
        call.save()
        assert call.status == CallStatus.RESULTADOS_PUBLICADOS

    def test_archive_from_resultados_publicados(self, db):
        """archive(): resultados_publicados → archivada (terminal)."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.RESULTADOS_PUBLICADOS,
        )
        call.archive()
        call.save()
        assert call.status == CallStatus.ARCHIVADA

    def test_archive_from_cerrada(self, db):
        """archive(): cerrada → archivada (terminal)."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.CERRADA,
        )
        call.archive()
        call.save()
        assert call.status == CallStatus.ARCHIVADA


# ──────────────────────────────────────────────
# FSM Transition Tests — Invalid Transitions
# ──────────────────────────────────────────────


class TestFsmInvalidTransitions:
    """Invalid transitions raise TransitionNotAllowed."""

    def test_open_call_from_abierta_fails(self, db):
        """open_call() from abierta raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.ABIERTA,
        )
        with pytest.raises(TransitionNotAllowed):
            call.open_call()

    def test_close_call_from_borrador_fails(self, db):
        """close_call() from borrador raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        with pytest.raises(TransitionNotAllowed):
            call.close_call()

    def test_publish_results_from_borrador_fails(self, db):
        """publish_results() from borrador raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        with pytest.raises(TransitionNotAllowed):
            call.publish_results()

    def test_start_evaluation_from_abierta_fails(self, db):
        """start_evaluation() from abierta raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.ABIERTA,
        )
        with pytest.raises(TransitionNotAllowed):
            call.start_evaluation()


# ──────────────────────────────────────────────
# FSM Terminal State Blocking Tests
# ──────────────────────────────────────────────


class TestFsmTerminalStateBlocking:
    """Terminal state (archivada) blocks all outbound transitions."""

    def test_archivada_blocks_all_transitions(self, db):
        """No transition is valid from archivada (terminal)."""
        inst = _make_institution("TU")
        call = Call.objects.create(
            institution=inst,
            title="Test",
            description="Desc",
            call_type=CallType.INTERNAL,
            status=CallStatus.ARCHIVADA,
        )
        for method in [
            "open_call",
            "close_call",
            "start_evaluation",
            "publish_results",
            "archive",
        ]:
            with pytest.raises(TransitionNotAllowed):
                getattr(call, method)()


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestCallFactory:
    """CallFactory produces valid Call instances."""

    def test_factory_creates_call(self, db):
        """CallFactory creates a Call with all required fields."""
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory()
        assert call.id is not None
        assert call.title
        assert call.description
        assert call.call_type in {CallType.INTERNAL, CallType.EXTERNAL}
        assert call.status == CallStatus.BORRADOR

    def test_factory_external_trait(self, db):
        """CallFactory external trait produces external call with entity."""
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(external=True)
        assert call.call_type == CallType.EXTERNAL
        assert call.external_entity != ""

    def test_factory_abierta_trait(self, db):
        """CallFactory abierta trait produces call in abierta state."""
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status=CallStatus.ABIERTA)
        assert call.status == CallStatus.ABIERTA


class TestCallDocumentFactory:
    """CallDocumentFactory produces valid CallDocument instances."""

    def test_factory_creates_document(self, db):
        """CallDocumentFactory creates a document linked to a call."""
        from apps.calls.tests.conftest import CallDocumentFactory

        doc = CallDocumentFactory()
        assert doc.id is not None
        assert doc.name
        assert doc.call is not None
        assert doc.external_url


class TestCallProjectFactory:
    """CallProjectFactory produces valid CallProject instances."""

    def test_factory_creates_call_project(self, db):
        """CallProjectFactory creates a CallProject link."""
        from apps.calls.tests.conftest import CallProjectFactory

        cp = CallProjectFactory()
        assert cp.id is not None
        assert cp.call is not None
        assert cp.project is not None
        assert cp.linked_at is not None
