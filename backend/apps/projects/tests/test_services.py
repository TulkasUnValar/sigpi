"""
Service layer tests for projects app — STRICT TDD (RED phase).

Tests define expected behavior of:
- ProjectService: create, update, 15 FSM orchestration methods, _log_transition
- ProjectMemberService: add, update, remove
- ProjectDocumentService: add, update, remove

Spec reference:  openspec/changes/projects/spec.md — RF-027 through RF-039
Design reference: openspec/changes/projects/design.md — Service Layer

RED PHASE: Tests fail because services.py does not exist.
"""
import datetime
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import (
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
    ProjectStatus,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_affiliation(researcher, center):
    """Create a ResearcherAffiliation for RN-009 validation."""
    from apps.researchers.models import ResearcherAffiliation

    return ResearcherAffiliation.objects.create(
        researcher=researcher,
        center=center,
        is_primary=True,
    )


# ──────────────────────────────────────────────
# ProjectService.create()
# ──────────────────────────────────────────────


class TestProjectServiceCreate:
    """ProjectService.create() — project creation with business rules."""

    def test_create_project_borrador(self, db):
        """create() returns a Project with status='borrador'."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.services import ProjectService
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)
        _make_affiliation(researcher, center)
        user = researcher.user

        project = ProjectService.create(
            institution=researcher.institution,
            center=center,
            principal_investigator=researcher,
            user=user,
            title="AI Research Project",
            abstract="Abstract text",
            objectives="Objectives text",
            methodology="Methodology text",
            expected_results="Expected results",
            keywords="ai, research",
            start_date=datetime.date(2025, 1, 1),
            estimated_end_date=datetime.date(2025, 12, 31),
        )

        assert project.pk is not None
        assert project.status == ProjectStatus.BORRADOR
        assert project.institution == researcher.institution
        assert project.center == center
        assert project.principal_investigator == researcher
        assert project.title == "AI Research Project"

    def test_create_rejects_missing_pi(self, db):
        """create() raises ValidationError when PI is None (RN-007)."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.services import ProjectService

        center = ResearchCenterFactory()

        with pytest.raises(ValidationError, match=r"investigator"):
            ProjectService.create(
                institution=center.institution,
                center=center,
                principal_investigator=None,
                user=None,
                title="Test",
                abstract="A",
                objectives="O",
                methodology="M",
                expected_results="E",
                start_date=datetime.date(2025, 1, 1),
                estimated_end_date=datetime.date(2025, 12, 31),
            )

    def test_create_rejects_missing_center(self, db):
        """create() raises ValidationError when center is None (RN-008)."""
        from apps.projects.services import ProjectService

        with pytest.raises(ValidationError, match=r"[Cc]enter"):
            ProjectService.create(
                institution=None,
                center=None,
                principal_investigator=None,
                user=None,
                title="Test",
                abstract="A",
                objectives="O",
                methodology="M",
                expected_results="E",
                start_date=datetime.date(2025, 1, 1),
                estimated_end_date=datetime.date(2025, 12, 31),
            )

    def test_create_rejects_pi_not_affiliated(self, db):
        """create() raises ValidationError when PI has no affiliation with center (RN-009)."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.services import ProjectService
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)
        # NO affiliation created

        with pytest.raises(ValidationError, match=r"[Aa]ffiliat"):
            ProjectService.create(
                institution=researcher.institution,
                center=center,
                principal_investigator=researcher,
                user=researcher.user,
                title="Test",
                abstract="A",
                objectives="O",
                methodology="M",
                expected_results="E",
                start_date=datetime.date(2025, 1, 1),
                estimated_end_date=datetime.date(2025, 12, 31),
            )

    def test_create_rejects_invalid_dates(self, db):
        """create() raises ValidationError when end_date < start_date (RN-013)."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.services import ProjectService
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)
        _make_affiliation(researcher, center)

        with pytest.raises(ValidationError, match=r"date"):
            ProjectService.create(
                institution=researcher.institution,
                center=center,
                principal_investigator=researcher,
                user=researcher.user,
                title="Test",
                abstract="A",
                objectives="O",
                methodology="M",
                expected_results="E",
                start_date=datetime.date(2025, 12, 31),
                estimated_end_date=datetime.date(2025, 1, 1),
            )


# ──────────────────────────────────────────────
# ProjectService.update()
# ──────────────────────────────────────────────


class TestProjectServiceUpdate:
    """ProjectService.update() — project updates with terminal-state guard."""

    def test_update_borrador_succeeds(self, db):
        """update() on non-terminal project updates fields."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(status="borrador", title="Original")
        updated = ProjectService.update(project, title="Updated Title")

        assert updated.title == "Updated Title"
        project.refresh_from_db()
        assert project.title == "Updated Title"

    def test_update_terminal_raises(self, db):
        """update() on terminal project raises ValidationError (RN-011)."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        for terminal_status in ["cerrado", "rechazado", "cancelado"]:
            project = ProjectFactory(status=terminal_status, title="Terminal")
            with pytest.raises(ValidationError, match=r"[Tt]erminal"):
                ProjectService.update(project, title="Should fail")


# ──────────────────────────────────────────────
# ProjectService FSM orchestration (15 methods)
# ──────────────────────────────────────────────


class TestProjectServiceFSM:
    """FSM orchestration: each method calls model transition + saves + logs + emits audit."""

    # ── Helpers ─────────────────────────────────

    def _make_user(self):
        from apps.projects.tests.conftest import UserFactory
        return UserFactory()

    def _transitions(self, project, user, method_name, **kwargs):
        """Helper to call a service FSM method on a project and verify results."""
        from apps.projects.services import ProjectService

        from_state = project.status
        method = getattr(ProjectService, method_name)
        updated = method(project, user, **kwargs)

        # Assert state changed
        assert updated.status != from_state
        # Assert ProjectStateLog created
        log = ProjectStateLog.objects.filter(project=project).latest("created_at")
        assert log.from_state == from_state
        assert log.to_state == updated.status
        assert log.triggered_by == user

        return updated, log

    # ── submit() ────────────────────────────────

    def test_submit_borrador_to_enviado(self, db):
        """submit() transitions borrador → enviado with logging and audit."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="borrador")

        with patch("apps.projects.services.AuditEventEmitter") as mock_emitter_class:
            mock_emitter = mock_emitter_class.return_value
            updated = ProjectService.submit(project, user)

        assert updated.status == ProjectStatus.ENVIADO
        log = ProjectStateLog.objects.get(project=project)
        assert log.from_state == ProjectStatus.BORRADOR
        assert log.to_state == ProjectStatus.ENVIADO
        assert log.triggered_by == user
        mock_emitter.emit.assert_called_once()
        call_kwargs = mock_emitter.emit.call_args[1]
        assert call_kwargs["event_type"] == "PROJECT_STATE_CHANGE"
        assert call_kwargs["user"] == user

    # ── accept_review() ─────────────────────────

    def test_accept_review_enviado_to_en_revision(self, db):
        """accept_review() transitions enviado → en_revision."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="enviado")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "accept_review")

        assert updated.status == ProjectStatus.EN_REVISION

    # ── approve() ───────────────────────────────

    def test_approve_en_revision_to_aprobado(self, db):
        """approve() transitions en_revision → aprobado."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_revision")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "approve")

        assert updated.status == ProjectStatus.APROBADO

    # ── observe() ───────────────────────────────

    def test_observe_en_revision_to_observado(self, db):
        """observe() transitions en_revision → observado AND creates ProjectObservation."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_revision")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.observe(
                project, user, observation_text="Missing methodology details"
            )

        assert updated.status == ProjectStatus.OBSERVADO
        # ProjectObservation must be created
        obs = ProjectObservation.objects.get(project=project)
        assert obs.observation_text == "Missing methodology details"
        assert obs.observed_by == user

    def test_observe_creates_state_log(self, db):
        """observe() creates ProjectStateLog."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_revision")

        with patch("apps.projects.services.AuditEventEmitter"):
            ProjectService.observe(project, user, observation_text="Need changes")

        log = ProjectStateLog.objects.get(project=project)
        assert log.from_state == ProjectStatus.EN_REVISION
        assert log.to_state == ProjectStatus.OBSERVADO

    # ── return_to_draft() ───────────────────────

    def test_return_to_draft_en_revision_to_borrador(self, db):
        """return_to_draft() transitions en_revision → borrador WITHOUT observation."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_revision")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.return_to_draft(project, user)

        assert updated.status == ProjectStatus.BORRADOR
        # NO ProjectObservation created
        assert not ProjectObservation.objects.filter(project=project).exists()

    def test_return_to_draft_from_observado(self, db):
        """return_to_draft() works from observado → borrador."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="observado")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.return_to_draft(project, user)

        assert updated.status == ProjectStatus.BORRADOR

    # ── reject() ────────────────────────────────

    def test_reject_en_revision_to_rechazado(self, db):
        """reject() transitions en_revision → rechazado (terminal)."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_revision")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "reject")

        assert updated.status == ProjectStatus.RECHAZADO

    # ── resubmit() ──────────────────────────────

    def test_resubmit_observado_to_enviado(self, db):
        """resubmit() transitions observado → enviado."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="observado")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "resubmit")

        assert updated.status == ProjectStatus.ENVIADO

    # ── start_execution() ───────────────────────

    def test_start_execution_aprobado_to_en_ejecucion(self, db):
        """start_execution() transitions aprobado → en_ejecucion."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="aprobado")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "start_execution")

        assert updated.status == ProjectStatus.EN_EJECUCION

    # ── suspend() ───────────────────────────────

    def test_suspend_en_ejecucion_to_suspendido(self, db):
        """suspend() transitions en_ejecucion → suspendido with reason."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_ejecucion")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.suspend(project, user, reason="Budget freeze")

        assert updated.status == ProjectStatus.SUSPENDIDO
        log = ProjectStateLog.objects.filter(project=project).latest("created_at")
        assert log.reason == "Budget freeze"

    # ── resume() ────────────────────────────────

    def test_resume_suspendido_to_en_ejecucion(self, db):
        """resume() transitions suspendido → en_ejecucion."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="suspendido")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "resume")

        assert updated.status == ProjectStatus.EN_EJECUCION

    # ── finalize() ─────────────────────────────

    def test_finalize_en_ejecucion_to_finalizado(self, db):
        """finalize() transitions en_ejecucion → finalizado with actual_end_date."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_ejecucion")
        end_date = datetime.date(2026, 6, 30)

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.finalize(project, user, actual_end_date=end_date)

        assert updated.status == ProjectStatus.FINALIZADO
        assert updated.actual_end_date == end_date

    # ── initiate_closure() ──────────────────────

    def test_initiate_closure_finalizado_to_en_cierre(self, db):
        """initiate_closure() transitions finalizado → en_cierre."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="finalizado")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "initiate_closure")

        assert updated.status == ProjectStatus.EN_CIERRE

    # ── close() ─────────────────────────────────

    def test_close_en_cierre_to_cerrado(self, db):
        """close() transitions en_cierre → cerrado (terminal)."""
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="en_cierre")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated, log = self._transitions(project, user, "close")

        assert updated.status == ProjectStatus.CERRADO

    # ── cancel() ────────────────────────────────

    def test_cancel_non_terminal_to_cancelado(self, db):
        """cancel() transitions any non-terminal → cancelado."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="borrador")

        with patch("apps.projects.services.AuditEventEmitter"):
            updated = ProjectService.cancel(project, user, reason="No longer needed")

        assert updated.status == ProjectStatus.CANCELADO
        log = ProjectStateLog.objects.filter(project=project).latest("created_at")
        assert log.reason == "No longer needed"

    def test_cancel_terminal_raises(self, db):
        """cancel() on already-terminal project raises ValidationError."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="cerrado")

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectService.cancel(project, user)

    # ── Cross-cutting: audit event emission ─────

    def test_fsm_emits_audit_event(self, db):
        """Every FSM method emits an AuditEvent via AuditEventEmitter."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory

        user = self._make_user()
        project = ProjectFactory(status="borrador")

        with patch("apps.projects.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            ProjectService.submit(project, user)

        mock_emitter.emit.assert_called_once()
        call_kwargs = mock_emitter.emit.call_args[1]
        assert call_kwargs["event_type"] == "PROJECT_STATE_CHANGE"
        assert call_kwargs["user"] == user
        assert call_kwargs["institution_id"] == project.institution_id
        assert "from_state" in call_kwargs["details"]
        assert "to_state" in call_kwargs["details"]


# ──────────────────────────────────────────────
# ProjectService._log_transition()
# ──────────────────────────────────────────────


class TestLogTransition:
    """ProjectService._log_transition() — creates ProjectStateLog + emits AuditEvent."""

    def test_creates_state_log(self, db):
        """_log_transition() creates a ProjectStateLog row."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory, UserFactory

        user = UserFactory()
        project = ProjectFactory(status="borrador")

        with patch("apps.projects.services.AuditEventEmitter"):
            ProjectService._log_transition(
                project, "borrador", "enviado", user, reason="Submitted by PI"
            )

        log = ProjectStateLog.objects.get(project=project)
        assert log.from_state == "borrador"
        assert log.to_state == "enviado"
        assert log.triggered_by == user
        assert log.reason == "Submitted by PI"

    def test_emits_audit_event(self, db):
        """_log_transition() emits an AuditEvent."""
        from apps.projects.services import ProjectService
        from apps.projects.tests.conftest import ProjectFactory, UserFactory

        user = UserFactory()
        project = ProjectFactory()

        with patch("apps.projects.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            ProjectService._log_transition(
                project, "borrador", "enviado", user
            )

        mock_emitter.emit.assert_called_once_with(
            event_type="PROJECT_STATE_CHANGE",
            user=user,
            institution_id=project.institution_id,
            details={
                "project_id": str(project.pk),
                "from_state": "borrador",
                "to_state": "enviado",
                "triggered_by": user.email if user else None,
            },
        )


# ──────────────────────────────────────────────
# ProjectMemberService
# ──────────────────────────────────────────────


class TestProjectMemberService:
    """ProjectMemberService — add, update, remove with terminal-state guard."""

    def test_add_member_succeeds(self, db):
        """add() creates a ProjectMember for non-terminal project."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory(status="borrador")
        researcher = ResearcherFactory(institution=project.institution)

        member = ProjectMemberService.add(project, researcher, "co_investigator")

        assert member.pk is not None
        assert member.project == project
        assert member.researcher == researcher
        assert member.role == "co_investigator"

    def test_add_member_terminal_raises(self, db):
        """add() raises ValidationError when project is terminal (RN-011)."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory(status="cerrado")
        researcher = ResearcherFactory(institution=project.institution)

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectMemberService.add(project, researcher, "co_investigator")

    def test_add_duplicate_raises(self, db):
        """add() raises ValidationError for duplicate (project, researcher)."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory(status="borrador")
        researcher = ResearcherFactory(institution=project.institution)
        ProjectMemberService.add(project, researcher, "co_investigator")

        with pytest.raises(ValidationError, match=r"[Mm]ember"):
            ProjectMemberService.add(project, researcher, "student")

    def test_update_member_succeeds(self, db):
        """update() changes role for non-terminal parent project."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory(status="borrador")
        researcher = ResearcherFactory(institution=project.institution)
        member = ProjectMemberService.add(project, researcher, "co_investigator")

        updated = ProjectMemberService.update(member, role="student")
        assert updated.role == "student"

    def test_update_member_terminal_raises(self, db):
        """update() raises when parent project is terminal."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory, ProjectMemberFactory

        project = ProjectFactory(status="cerrado")
        member = ProjectMemberFactory(project=project, role="co_investigator")

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectMemberService.update(member, role="student")

    def test_remove_member_succeeds(self, db):
        """remove() deletes member for non-terminal parent."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory(status="borrador")
        researcher = ResearcherFactory(institution=project.institution)
        member = ProjectMemberService.add(project, researcher, "co_investigator")

        ProjectMemberService.remove(member)
        assert not ProjectMember.objects.filter(pk=member.pk).exists()

    def test_remove_member_terminal_raises(self, db):
        """remove() raises when parent project is terminal."""
        from apps.projects.services import ProjectMemberService
        from apps.projects.tests.conftest import ProjectFactory, ProjectMemberFactory

        project = ProjectFactory(status="cerrado")
        member = ProjectMemberFactory(project=project, role="co_investigator")

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectMemberService.remove(member)


# ──────────────────────────────────────────────
# ProjectDocumentService
# ──────────────────────────────────────────────


class TestProjectDocumentService:
    """ProjectDocumentService — add, update, remove with terminal-state guard."""

    def test_add_document_succeeds(self, db):
        """add() creates a ProjectDocument for non-terminal project."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(status="borrador")

        doc = ProjectDocumentService.add(
            project,
            name="Project Proposal",
            doc_type="proposal",
            external_url="https://example.com/doc.pdf",
        )

        assert doc.pk is not None
        assert doc.project == project
        assert doc.name == "Project Proposal"
        assert doc.doc_type == "proposal"

    def test_add_document_terminal_raises(self, db):
        """add() raises ValidationError when project is terminal (RN-011)."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(status="cerrado")

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectDocumentService.add(
                project,
                name="Doc",
                doc_type="other",
                external_url="https://example.com/doc.pdf",
            )

    def test_update_document_succeeds(self, db):
        """update() changes fields for non-terminal parent."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectDocumentFactory, ProjectFactory

        project = ProjectFactory(status="borrador")
        doc = ProjectDocumentFactory(project=project, name="Original")

        updated = ProjectDocumentService.update(doc, name="Updated")
        assert updated.name == "Updated"

    def test_update_document_terminal_raises(self, db):
        """update() raises when parent project is terminal."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectDocumentFactory, ProjectFactory

        project = ProjectFactory(status="cerrado")
        doc = ProjectDocumentFactory(project=project)

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectDocumentService.update(doc, name="Should fail")

    def test_remove_document_succeeds(self, db):
        """remove() deletes document for non-terminal parent."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectDocumentFactory, ProjectFactory

        project = ProjectFactory(status="borrador")
        doc = ProjectDocumentFactory(project=project)

        ProjectDocumentService.remove(doc)
        assert not ProjectDocument.objects.filter(pk=doc.pk).exists()

    def test_remove_document_terminal_raises(self, db):
        """remove() raises when parent project is terminal."""
        from apps.projects.services import ProjectDocumentService
        from apps.projects.tests.conftest import ProjectDocumentFactory, ProjectFactory

        project = ProjectFactory(status="cerrado")
        doc = ProjectDocumentFactory(project=project)

        with pytest.raises(ValidationError, match=r"[Tt]erminal"):
            ProjectDocumentService.remove(doc)
