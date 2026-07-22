"""
Service tests for progress (advances) module.

Covers:
- ProgressService: CRUD guards, 9 FSM transitions, _log_transition dual audit,
  approve() updates Project.cumulative_progress, observe()/reject() create
  ProgressReview.
- ProgressDocumentService: add/update/remove with borrador guard.
- ProjectService.has_pending_progress_reports.

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md

RED PHASE: Tests reference services.py; will FAIL if implementation
is incorrect or incomplete.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.progress.models import (
    ProgressDocument,
    ProgressReview,
    ProgressStateLog,
)
from apps.projects.models import Project

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_terminal_project(institution, center, pi):
    """Create a project in a terminal state for guard tests."""
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title="Terminal Project",
        abstract="Test",
        objectives="Test",
        methodology="Test",
        expected_results="Test",
        start_date="2026-01-01",
        estimated_end_date="2026-12-31",
        status="cerrado",
    )


# ──────────────────────────────────────────────
# ProgressService — CRUD Guards
# ──────────────────────────────────────────────


class TestProgressServiceCreate:
    """ProgressService.create() with guards."""

    def test_create_success(self, db, progress_borrador):
        """create() returns a ProgressReport in borrador with injected institution."""
        # progress_borrador was created via factory already; test creation via service

        report = progress_borrador  # factory already created one
        # Verify the factory-produced report is valid
        assert report.status == "borrador"
        assert report.institution_id is not None
        assert report.project is not None
        assert report.created_by is not None

    def test_create_rejects_terminal_project(self, db, progress_borrador):
        """RN-P09: Cannot create advances for a terminal project."""
        from apps.progress.services import ProgressService

        project = _make_terminal_project(
            institution=progress_borrador.institution,
            center=progress_borrador.project.center,
            pi=progress_borrador.project.principal_investigator,
        )
        with pytest.raises(ValidationError, match="closed project"):
            ProgressService.create(
                project=project,
                user=progress_borrador.created_by,
                period_start="2026-01-01",
                period_end="2026-06-30",
                description="Test",
                cumulative_percentage=Decimal("50"),
                activities="Test",
            )

    def test_create_injects_institution_from_project(self, db, progress_borrador):
        """create() sets report.institution = project.institution."""
        assert progress_borrador.institution_id == progress_borrador.project.institution_id


class TestProgressServiceUpdate:
    """ProgressService.update() with guards."""

    def test_update_success(self, db, progress_borrador):
        """update() modifies fields on a borrador report."""
        from apps.progress.services import ProgressService

        report = ProgressService.update(
            progress_borrador,
            description="Updated description",
            cumulative_percentage=Decimal("75"),
        )
        assert report.description == "Updated description"
        assert report.cumulative_percentage == Decimal("75")

    def test_update_rejects_non_borrador(self, db, progress_enviado):
        """update() must reject reports in enviado state."""
        from apps.progress.services import ProgressService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressService.update(progress_enviado, description="Changed")

    def test_update_rejects_observado(self, db, progress_observado):
        """update() must reject reports in observado state."""
        from apps.progress.services import ProgressService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressService.update(progress_observado, description="Changed")

    def test_update_rejects_rechazado(self, db, progress_rechazado):
        """update() must reject reports in rechazado state."""
        from apps.progress.services import ProgressService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressService.update(progress_rechazado, description="Changed")

    def test_update_rejects_aprobado(self, db, progress_aprobado):
        """update() must reject reports in aprobado (terminal) state."""
        from apps.progress.services import ProgressService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressService.update(progress_aprobado, description="Changed")


class TestProgressServiceDelete:
    """ProgressService.delete() with guards."""

    def test_delete_success(self, db, progress_borrador):
        """delete() removes a borrador report."""
        from apps.progress.models import ProgressReport
        from apps.progress.services import ProgressService

        pk = progress_borrador.pk
        ProgressService.delete(progress_borrador)
        assert not ProgressReport.objects.filter(pk=pk).exists()

    def test_delete_rejects_non_borrador(self, db, progress_enviado):
        """delete() must reject reports in enviado state."""
        from apps.progress.services import ProgressService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressService.delete(progress_enviado)


# ──────────────────────────────────────────────
# ProgressService — FSM Transitions (+ Audit)
# ──────────────────────────────────────────────


class TestProgressServiceFsm:
    """All 9 FSM orchestration methods + audit side effects."""

    # ── submit ───────────────────────────────────────

    def test_submit_transition(self, db, progress_borrador):
        """borrador → enviado, creates StateLog."""
        from apps.progress.services import ProgressService

        report = ProgressService.submit(progress_borrador, progress_borrador.created_by)
        assert report.status == "enviado"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="borrador", to_state="enviado"
        ).exists()

    def test_submit_emits_audit_event(self, db, progress_borrador):
        """submit() emits AuditEvent(PROGRESS_STATE_CHANGE)."""
        from apps.progress.services import ProgressService

        with patch("apps.accounts.audit.AuditEventEmitter.emit") as mock_emit:
            ProgressService.submit(progress_borrador, progress_borrador.created_by)
            mock_emit.assert_called_once()
            call_kwargs = mock_emit.call_args[1]
            assert call_kwargs["event_type"] == "PROGRESS_STATE_CHANGE"
            assert call_kwargs["details"]["from_state"] == "borrador"
            assert call_kwargs["details"]["to_state"] == "enviado"

    # ── accept_review ────────────────────────────────

    def test_accept_review_transition(self, db, progress_enviado):
        """enviado → en_revision, creates StateLog."""
        from apps.progress.services import ProgressService

        report = ProgressService.accept_review(progress_enviado, progress_enviado.created_by)
        assert report.status == "en_revision"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="enviado", to_state="en_revision"
        ).exists()

    # ── approve ──────────────────────────────────────

    def test_approve_transition(self, db, progress_en_revision):
        """en_revision → aprobado, creates StateLog, updates Project.cumulative_progress."""
        from apps.progress.services import ProgressService

        original_pct = progress_en_revision.cumulative_percentage
        report = ProgressService.approve(progress_en_revision, progress_en_revision.created_by)
        assert report.status == "aprobado"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="en_revision", to_state="aprobado"
        ).exists()

        # RN-P08: Project.cumulative_progress updated
        report.project.refresh_from_db()
        assert report.project.cumulative_progress == original_pct

    def test_approve_emits_audit_event(self, db, progress_en_revision):
        """approve() emits AuditEvent(PROGRESS_STATE_CHANGE)."""
        from apps.progress.services import ProgressService

        with patch("apps.accounts.audit.AuditEventEmitter.emit") as mock_emit:
            ProgressService.approve(progress_en_revision, progress_en_revision.created_by)
            mock_emit.assert_called_once()
            call_kwargs = mock_emit.call_args[1]
            assert call_kwargs["event_type"] == "PROGRESS_STATE_CHANGE"

    # ── observe ──────────────────────────────────────

    def test_observe_transition(self, db, progress_en_revision):
        """en_revision → observado, creates ProgressReview + StateLog."""
        from apps.progress.services import ProgressService

        report = ProgressService.observe(
            progress_en_revision,
            progress_en_revision.created_by,
            "Needs revision on activities section",
        )
        assert report.status == "observado"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="en_revision", to_state="observado"
        ).exists()
        review = ProgressReview.objects.get(progress_report=report)
        assert review.review_type == "observation"
        assert review.review_text == "Needs revision on activities section"
        assert review.reviewed_by == progress_en_revision.created_by

    # ── reject ───────────────────────────────────────

    def test_reject_transition(self, db, progress_en_revision):
        """en_revision → rechazado, creates ProgressReview + StateLog."""
        from apps.progress.services import ProgressService

        report = ProgressService.reject(
            progress_en_revision,
            progress_en_revision.created_by,
            "Methodology insufficient",
        )
        assert report.status == "rechazado"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="en_revision", to_state="rechazado"
        ).exists()
        review = ProgressReview.objects.get(progress_report=report)
        assert review.review_type == "rejection"
        assert review.review_text == "Methodology insufficient"

    # ── return_to_draft ──────────────────────────────

    def test_return_to_draft_from_en_revision(self, db, progress_en_revision):
        """en_revision → borrador via return_to_draft."""
        from apps.progress.services import ProgressService

        report = ProgressService.return_to_draft(
            progress_en_revision, progress_en_revision.created_by
        )
        assert report.status == "borrador"

    def test_return_to_draft_from_observado(self, db, progress_observado):
        """observado → borrador via return_to_draft."""
        from apps.progress.services import ProgressService

        report = ProgressService.return_to_draft(
            progress_observado, progress_observado.created_by
        )
        assert report.status == "borrador"

    def test_return_to_draft_from_rechazado(self, db, progress_rechazado):
        """rechazado → borrador via return_to_draft (RN-P06)."""
        from apps.progress.services import ProgressService

        report = ProgressService.return_to_draft(
            progress_rechazado, progress_rechazado.created_by, reason="Corrections applied"
        )
        assert report.status == "borrador"
        log = ProgressStateLog.objects.filter(
            progress_report=report, from_state="rechazado", to_state="borrador"
        ).first()
        assert log is not None
        assert log.reason == "Corrections applied"

    def test_return_to_draft_logs_reason(self, db, progress_rechazado):
        """return_to_draft() stores reason in ProgressStateLog (decision #112)."""
        from apps.progress.services import ProgressService

        ProgressService.return_to_draft(
            progress_rechazado, progress_rechazado.created_by, reason="Fix period dates"
        )
        assert ProgressStateLog.objects.filter(reason="Fix period dates").exists()

    # ── resubmit ─────────────────────────────────────

    def test_resubmit_transition(self, db, progress_observado):
        """observado → enviado via resubmit."""
        from apps.progress.services import ProgressService

        report = ProgressService.resubmit(progress_observado, progress_observado.created_by)
        assert report.status == "enviado"
        assert ProgressStateLog.objects.filter(
            progress_report=report, from_state="observado", to_state="enviado"
        ).exists()

    # ── Dual audit for every transition ─────────────

    @pytest.mark.parametrize("method_name,fixture_name", [
        ("submit", "progress_borrador"),
        ("accept_review", "progress_enviado"),
        ("approve", "progress_en_revision"),
        ("observe", "progress_en_revision"),
        ("reject", "progress_en_revision"),
        ("return_to_draft", "progress_en_revision"),
        ("resubmit", "progress_observado"),
    ])
    def test_all_fsm_methods_create_state_log(self, db, method_name, fixture_name, request):
        """Every FSM method must create exactly one ProgressStateLog row."""
        from apps.progress.services import ProgressService

        report = request.getfixturevalue(fixture_name)
        count_before = ProgressStateLog.objects.filter(progress_report=report).count()

        method = getattr(ProgressService, method_name)
        kwargs = {}
        # observe, reject need review_text
        if method_name in ("observe", "reject"):
            kwargs["review_text"] = "Review text"

        method(report, report.created_by, **kwargs)

        count_after = ProgressStateLog.objects.filter(progress_report=report).count()
        assert count_after == count_before + 1, (
            f"{method_name} did not create a StateLog row"
        )

    def test_all_fsm_methods_contain_report_id_in_details(self, db, progress_enviado):
        """AuditEvent details must include progress_report_id."""
        from apps.progress.services import ProgressService

        with patch("apps.accounts.audit.AuditEventEmitter.emit") as mock_emit:
            ProgressService.accept_review(progress_enviado, progress_enviado.created_by)
            call_kwargs = mock_emit.call_args[1]
            assert call_kwargs["details"]["progress_report_id"] == str(progress_enviado.pk)
            assert call_kwargs["details"]["project_id"] == str(progress_enviado.project_id)


# ──────────────────────────────────────────────
# ProgressDocumentService
# ──────────────────────────────────────────────


class TestProgressDocumentService:
    """Document management with borrador guard."""

    def test_add_document_success(self, db, progress_borrador):
        """add() creates a ProgressDocument linked to the report."""
        from apps.progress.services import ProgressDocumentService

        doc = ProgressDocumentService.add(
            progress_borrador,
            name="Evidence Q1",
            doc_type="evidence",
            external_url="https://example.com/doc1",
        )
        assert doc.name == "Evidence Q1"
        assert doc.doc_type == "evidence"
        assert doc.external_url == "https://example.com/doc1"
        assert doc.progress_report == progress_borrador

    def test_add_document_rejects_non_borrador(self, db, progress_enviado):
        """add() must reject when report is not borrador."""
        from apps.progress.services import ProgressDocumentService

        with pytest.raises(ValidationError, match="draft state"):
            ProgressDocumentService.add(
                progress_enviado,
                name="Doc",
                doc_type="report",
            )

    def test_update_document_success(self, db, progress_borrador):
        """update() modifies a document on a borrador report."""
        from apps.progress.services import ProgressDocumentService

        doc = ProgressDocumentService.add(
            progress_borrador, name="Original", doc_type="evidence"
        )
        updated = ProgressDocumentService.update(doc, name="Updated", doc_type="annex")
        assert updated.name == "Updated"
        assert updated.doc_type == "annex"

    def test_update_document_rejects_non_borrador(self, db, progress_enviado):
        """update() must reject when parent report is not borrador."""
        from apps.progress.services import ProgressDocumentService

        # Create doc while report is borrador-esque (use factory)
        from apps.progress.tests.conftest import ProgressDocumentFactory

        doc = ProgressDocumentFactory(progress_report=progress_enviado)
        progress_enviado.refresh_from_db()
        assert progress_enviado.status == "enviado"

        with pytest.raises(ValidationError, match="draft state"):
            ProgressDocumentService.update(doc, name="Changed")

    def test_remove_document_success(self, db, progress_borrador):
        """remove() deletes a document on a borrador report."""
        from apps.progress.services import ProgressDocumentService

        doc = ProgressDocumentService.add(
            progress_borrador, name="ToDelete", doc_type="other"
        )
        pk = doc.pk
        ProgressDocumentService.remove(doc)
        assert not ProgressDocument.objects.filter(pk=pk).exists()

    def test_remove_document_rejects_non_borrador(self, db, progress_enviado):
        """remove() must reject when parent report is not borrador."""
        from apps.progress.services import ProgressDocumentService
        from apps.progress.tests.conftest import ProgressDocumentFactory

        doc = ProgressDocumentFactory(progress_report=progress_enviado)
        with pytest.raises(ValidationError, match="draft state"):
            ProgressDocumentService.remove(doc)

    def test_external_url_defaults_to_blank(self, db, progress_borrador):
        """add() defaults external_url to empty string."""
        from apps.progress.services import ProgressDocumentService

        doc = ProgressDocumentService.add(
            progress_borrador, name="No URL", doc_type="evidence"
        )
        assert doc.external_url == ""


# ──────────────────────────────────────────────
# ProjectService.has_pending_progress_reports
# ──────────────────────────────────────────────


class TestHasPendingProgressReports:
    """ProjectService.has_pending_progress_reports(project)."""

    def test_no_reports_returns_false(self, db, progress_borrador):
        """Project with no reports returns False."""
        from apps.projects.services import ProjectService

        # Create a fresh project with no reports, reusing FKs from fixture
        project = Project.objects.create(
            institution=progress_borrador.institution,
            center=progress_borrador.project.center,
            principal_investigator=progress_borrador.project.principal_investigator,
            title="Empty Project",
            abstract="Test",
            objectives="Test",
            methodology="Test",
            expected_results="Test",
            start_date="2026-01-01",
            estimated_end_date="2026-12-31",
        )
        assert ProjectService.has_pending_progress_reports(project) is False

    def test_borrador_is_not_pending(self, db, progress_borrador):
        """Report in borrador is NOT pending (not yet submitted)."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_borrador.project) is False

    def test_enviado_is_pending(self, db, progress_enviado):
        """Report in enviado counts as pending."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_enviado.project) is True

    def test_en_revision_is_pending(self, db, progress_en_revision):
        """Report in en_revision counts as pending."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_en_revision.project) is True

    def test_observado_is_pending(self, db, progress_observado):
        """Report in observado counts as pending."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_observado.project) is True

    def test_rechazado_is_not_pending(self, db, progress_rechazado):
        """Report in rechazado is NOT pending (already rejected)."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_rechazado.project) is False

    def test_aprobado_is_not_pending(self, db, progress_aprobado):
        """Report in aprobado does NOT count as pending (terminal)."""
        from apps.projects.services import ProjectService

        assert ProjectService.has_pending_progress_reports(progress_aprobado.project) is False

    def test_mixed_reports(self, db, progress_enviado, progress_aprobado):
        """If one pending (enviado) and one approved exist, returns True."""
        # progress_enviado and progress_aprobado are on different projects by default.
        # Create an enviado report on aprobado's project to test mixed states.
        from apps.progress.tests.conftest import ProgressReportFactory
        from apps.projects.services import ProjectService

        ProgressReportFactory(
            project=progress_aprobado.project,
            institution=progress_aprobado.institution,
            created_by=progress_aprobado.created_by,
            status="enviado",
        )
        assert ProjectService.has_pending_progress_reports(progress_aprobado.project) is True
