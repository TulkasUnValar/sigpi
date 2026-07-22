"""
Service layer for progress (advances) — business logic + FSM orchestration.

ProgressService: CRUD + 9 FSM transition methods + _log_transition.
ProgressDocumentService: document management with borrador guard.

All state transitions are centralized here — views never call
django-fsm @transition methods directly.

Design reference: openspec/sdd/advances/design.md — Service Layer
Spec reference:   openspec/sdd/advances/spec.md — RF-041 through RF-049
"""
from django.core.exceptions import ValidationError

from apps.accounts.audit import AuditEventEmitter
from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressReviewType,
    ProgressStateLog,
    ProgressStatus,
)
from apps.projects.models import TERMINAL_STATES as PROJECT_TERMINAL_STATES

# ── Guard helpers ───────────────────────────────────────


def _validate_project_not_terminal(project):
    """Reject if the project is in a terminal state (RN-P09)."""
    if project.status in PROJECT_TERMINAL_STATES:
        raise ValidationError(
            "Cannot create advances for a closed project."
        )


def _validate_borrador(report):
    """Reject if the report is not in borrador state."""
    if report.status != ProgressStatus.BORRADOR:
        raise ValidationError(
            "Advance can only be edited in draft state."
        )


# ──────────────────────────────────────────────
# ProgressService
# ──────────────────────────────────────────────


class ProgressService:
    """CRUD and FSM orchestration for ProgressReport.

    All methods are static — plain Python class, not a Django model.
    Service signatures accept model instances and raw values.
    """

    # ── CRUD ───────────────────────────────────────────

    @staticmethod
    def create(project, user, **data) -> ProgressReport:
        """Create a ProgressReport with status='borrador'.

        Validates:
        - RN-P09: project not in a terminal state.
        - Injects institution from project.
        """
        _validate_project_not_terminal(project)

        report = ProgressReport(
            institution=project.institution,
            project=project,
            created_by=user,
            status=ProgressStatus.BORRADOR,
            **data,
        )
        report.full_clean()
        report.save()
        return report

    @staticmethod
    def update(report, **data) -> ProgressReport:
        """Update a ProgressReport — rejected if not borrador.

        Delegates to model full_clean() + save() for validation.
        Only fields present in data are updated.
        """
        _validate_borrador(report)

        for field, value in data.items():
            setattr(report, field, value)
        report.full_clean()
        report.save()
        return report

    @staticmethod
    def delete(report) -> None:
        """Delete a ProgressReport — rejected if not borrador."""
        _validate_borrador(report)
        report.delete()

    # ── FSM Orchestration (9 methods) ─────────────────

    @staticmethod
    def submit(report, user) -> ProgressReport:
        """borrador → enviado."""
        from_state = report.status
        report.submit()
        report.save()
        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    @staticmethod
    def accept_review(report, user) -> ProgressReport:
        """enviado → en_revision."""
        from_state = report.status
        report.accept_review()
        report.save()
        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    @staticmethod
    def approve(report, user) -> ProgressReport:
        """en_revision → aprobado (terminal).

        Side effects (RN-P08):
        - Updates Project.cumulative_progress to the report's
          cumulative_percentage (NOT summed — latest approved value).
        """
        from_state = report.status
        report.approve()
        report.save()

        # RN-P08: Update denormalized cumulative progress on Project
        project = report.project
        project.cumulative_progress = report.cumulative_percentage
        project.save(update_fields=["cumulative_progress"])

        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    @staticmethod
    def observe(report, user, review_text) -> ProgressReport:
        """en_revision → observado.

        Side effect: Creates a ProgressReview with review_type='observation'.
        """
        from_state = report.status
        report.observe()
        report.save()

        ProgressReview.objects.create(
            progress_report=report,
            reviewed_by=user,
            review_text=review_text,
            review_type=ProgressReviewType.OBSERVATION,
        )
        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    @staticmethod
    def reject(report, user, review_text) -> ProgressReport:
        """en_revision → rechazado.

        Side effect: Creates a ProgressReview with review_type='rejection'.
        rechazado is NOT terminal — can return_to_draft (RN-P06).
        """
        from_state = report.status
        report.reject()
        report.save()

        ProgressReview.objects.create(
            progress_report=report,
            reviewed_by=user,
            review_text=review_text,
            review_type=ProgressReviewType.REJECTION,
        )
        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    @staticmethod
    def return_to_draft(report, user, reason="") -> ProgressReport:
        """en_revision | observado | rechazado → borrador.

        Accepts optional reason (decision #112): return_to_draft from
        rechazado accepts a reason for the correction.
        """
        from_state = report.status
        report.return_to_draft()
        report.save()
        ProgressService._log_transition(
            report, from_state, report.status, user, reason=reason
        )
        return report

    @staticmethod
    def resubmit(report, user) -> ProgressReport:
        """observado → enviado."""
        from_state = report.status
        report.resubmit()
        report.save()
        ProgressService._log_transition(report, from_state, report.status, user)
        return report

    # ── Audit / Logging ────────────────────────────────

    @staticmethod
    def _log_transition(report, from_state, to_state, user, reason=""):
        """Create ProgressStateLog + emit AuditEvent(PROGRESS_STATE_CHANGE).

        Private helper called by every FSM orchestration method.
        Two side-effects per RN-P04:
        1. Write a ProgressStateLog row (domain audit).
        2. Emit an AuditEvent via AuditEventEmitter (global audit).
        """
        ProgressStateLog.objects.create(
            progress_report=report,
            from_state=from_state,
            to_state=to_state,
            triggered_by=user,
            reason=reason,
        )
        AuditEventEmitter().emit(
            event_type="PROGRESS_STATE_CHANGE",
            user=user,
            institution_id=report.institution_id,
            details={
                "progress_report_id": str(report.pk),
                "project_id": str(report.project_id),
                "from_state": from_state,
                "to_state": to_state,
                "triggered_by": user.email if user else None,
            },
        )


# ──────────────────────────────────────────────
# ProgressDocumentService
# ──────────────────────────────────────────────


class ProgressDocumentService:
    """Document management with borrador guard.

    Mutations (add, update, remove) are only allowed when the
    parent ProgressReport is in borrador state.
    """

    @staticmethod
    def add(report, name, doc_type, external_url="") -> ProgressDocument:
        """Add a document metadata record — rejected if report not borrador."""
        _validate_borrador(report)

        doc = ProgressDocument(
            progress_report=report,
            name=name,
            doc_type=doc_type,
            external_url=external_url,
        )
        doc.full_clean()
        doc.save()
        return doc

    @staticmethod
    def update(document, **data) -> ProgressDocument:
        """Update document fields — rejected if parent report not borrador."""
        _validate_borrador(document.progress_report)

        for field, value in data.items():
            setattr(document, field, value)
        document.full_clean()
        document.save()
        return document

    @staticmethod
    def remove(document) -> None:
        """Delete a document — rejected if parent report not borrador."""
        _validate_borrador(document.progress_report)
        document.delete()
