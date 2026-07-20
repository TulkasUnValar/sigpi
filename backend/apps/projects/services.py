"""
Service layer for projects — business logic + FSM orchestration.

ProjectService: CRUD + 15 FSM transition methods + _log_transition.
ProjectMemberService: member management with terminal-state guard.
ProjectDocumentService: document management with terminal-state guard.

All state transitions are centralized here — views never call
django-fsm @transition methods directly.

Design reference: openspec/changes/projects/design.md — Service Layer
Spec reference:   openspec/changes/projects/spec.md — RF-027 through RF-039
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.audit import AuditEventEmitter
from apps.projects.models import (
    TERMINAL_STATES,
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)

# ── Terminal-state validation helper ───────────────────────


def _validate_not_terminal(project):
    """Reject mutations if the project is in a terminal state (RN-011)."""
    if project.status in TERMINAL_STATES:
        raise ValidationError(
            "Project is in a terminal state and cannot be modified."
        )


# ──────────────────────────────────────────────
# ProjectService
# ──────────────────────────────────────────────


class ProjectService:
    """CRUD and FSM orchestration for the Project model.

    All methods are static — this is a plain Python class, not a
    Django model. Service signatures accept model instances and
    raw values, not ORM primitives.
    """

    # ── CRUD ───────────────────────────────────────────

    @staticmethod
    def create(institution, center, principal_investigator, user, **data):
        """Create a Project with status='borrador'.

        Validates:
        - RN-007: principal_investigator non-null.
        - RN-008: center non-null.
        - RN-009: PI must be affiliated with the target center.
        - RN-013: estimated_end_date >= start_date.
        """
        # RN-008: center non-null
        if center is None:
            raise ValidationError({"center": "Center is required."})

        # RN-007: principal_investigator non-null
        if principal_investigator is None:
            raise ValidationError({"principal_investigator": "Principal investigator is required."})

        # RN-009: PI must be affiliated with the target center
        from apps.researchers.models import ResearcherAffiliation

        affiliated = ResearcherAffiliation.objects.filter(
            researcher=principal_investigator,
            center=center,
        ).exists()
        if not affiliated:
            raise ValidationError(
                "PI must be affiliated with the target center."
            )

        # RN-013: date validation
        start_date = data.get("start_date")
        estimated_end_date = data.get("estimated_end_date")
        if start_date and estimated_end_date and estimated_end_date < start_date:
            raise ValidationError(
                {"estimated_end_date": "Estimated end date must be on or after start date."}
            )

        project = Project(
            institution=institution or center.institution,
            center=center,
            principal_investigator=principal_investigator,
            status="borrador",
            **data,
        )
        project.full_clean()
        project.save()
        return project

    @staticmethod
    def update(project, **data):
        """Update a Project — rejected if terminal (RN-011).

        Delegates to model full_clean() + save() for validation.
        Only fields present in data are updated.
        """
        _validate_not_terminal(project)

        for field, value in data.items():
            setattr(project, field, value)
        project.full_clean()
        project.save()
        return project

    # ── FSM Orchestration ──────────────────────────────

    @staticmethod
    def submit(project, user):
        """borrador → enviado."""
        from_state = project.status
        project.submit()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def accept_review(project, user):
        """enviado → en_revision."""
        from_state = project.status
        project.accept_review()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def approve(project, user):
        """en_revision → aprobado."""
        from_state = project.status
        project.approve()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def observe(project, user, observation_text):
        """en_revision → observado + create ProjectObservation."""
        from_state = project.status
        project.observe()
        project.save()
        ProjectObservation.objects.create(
            project=project,
            observed_by=user,
            observation_text=observation_text,
        )
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def return_to_draft(project, user):
        """en_revision | observado → borrador WITHOUT observation."""
        from_state = project.status
        project.return_to_draft()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def reject(project, user):
        """en_revision → rechazado (terminal)."""
        from_state = project.status
        project.reject()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def resubmit(project, user):
        """observado → enviado."""
        from_state = project.status
        project.resubmit()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def start_execution(project, user):
        """aprobado → en_ejecucion."""
        from_state = project.status
        project.start_execution()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def suspend(project, user, reason=""):
        """en_ejecucion → suspendido."""
        from_state = project.status
        project.suspend()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user, reason=reason)
        return project

    @staticmethod
    def resume(project, user):
        """suspendido → en_ejecucion."""
        from_state = project.status
        project.resume()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def finalize(project, user, actual_end_date):
        """en_ejecucion → finalizado with actual_end_date."""
        from_state = project.status
        project.finalize()
        project.actual_end_date = actual_end_date
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def initiate_closure(project, user):
        """finalizado → en_cierre."""
        from_state = project.status
        project.initiate_closure()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def close(project, user):
        """en_cierre → cerrado (terminal)."""
        from_state = project.status
        project.close()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user)
        return project

    @staticmethod
    def cancel(project, user, reason=""):
        """Any non-terminal → cancelado (terminal).

        Rejects if the project is already in a terminal state.
        """
        _validate_not_terminal(project)
        from_state = project.status
        project.cancel()
        project.save()
        ProjectService._log_transition(project, from_state, project.status, user, reason=reason)
        return project

    # ── Audit / Logging ────────────────────────────────

    @staticmethod
    def _log_transition(project, from_state, to_state, user, reason=""):
        """Create ProjectStateLog + emit AuditEvent.

        Private helper called by every FSM orchestration method.
        Two side-effects per RN-012:
        1. Write a ProjectStateLog row (domain audit).
        2. Emit an AuditEvent via AuditEventEmitter (global audit).
        """
        ProjectStateLog.objects.create(
            project=project,
            from_state=from_state,
            to_state=to_state,
            triggered_by=user,
            reason=reason,
        )
        AuditEventEmitter().emit(
            event_type="PROJECT_STATE_CHANGE",
            user=user,
            institution_id=project.institution_id,
            details={
                "project_id": str(project.pk),
                "from_state": from_state,
                "to_state": to_state,
                "triggered_by": user.email if user else None,
            },
        )


# ──────────────────────────────────────────────
# ProjectMemberService
# ──────────────────────────────────────────────


class ProjectMemberService:
    """Member management with terminal-state guard (RN-011)."""

    @staticmethod
    def add(project, researcher, role):
        """Add a researcher to the project with a role.

        Validates:
        - Project not terminal (RN-011).
        - Unique (project, researcher) constraint enforced via DB.
        """
        _validate_not_terminal(project)

        member = ProjectMember(project=project, researcher=researcher, role=role)
        try:
            member.full_clean()
            member.save()
        except IntegrityError:
            raise ValidationError("Researcher is already a member of this project.")
        return member

    @staticmethod
    def update(member, role):
        """Update a member's role — rejected if parent project is terminal."""
        _validate_not_terminal(member.project)
        member.role = role
        member.full_clean()
        member.save()
        return member

    @staticmethod
    def remove(member):
        """Remove a member — rejected if parent project is terminal."""
        _validate_not_terminal(member.project)
        member.delete()


# ──────────────────────────────────────────────
# ProjectDocumentService
# ──────────────────────────────────────────────


class ProjectDocumentService:
    """Document management with terminal-state guard (RN-011)."""

    @staticmethod
    def add(project, name, doc_type, external_url):
        """Add a document metadata record — rejected if project is terminal."""
        _validate_not_terminal(project)

        doc = ProjectDocument(
            project=project,
            name=name,
            doc_type=doc_type,
            external_url=external_url,
        )
        doc.full_clean()
        doc.save()
        return doc

    @staticmethod
    def update(document, **data):
        """Update document fields — rejected if parent project is terminal."""
        _validate_not_terminal(document.project)

        for field, value in data.items():
            setattr(document, field, value)
        document.full_clean()
        document.save()
        return document

    @staticmethod
    def remove(document):
        """Delete a document — rejected if parent project is terminal."""
        _validate_not_terminal(document.project)
        document.delete()
