"""
Signal integration tests for project_workflow — STRICT TDD (RED phase).

Tests verify:
- on_project_state_change receiver creates/resets/cancels WorkflowInstance
- _log_transition in projects/services.py emits project_state_changed
- Atomic rollback when receiver fails

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md
"""
import datetime
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)
from apps.project_workflow.signals import project_state_changed

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(institution=institution, name=name, code=code)


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_project(institution, center, pi, **overrides):
    from apps.projects.models import Project

    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title=overrides.get("title", "Valid Title"),
        abstract=overrides.get("abstract", "Valid abstract."),
        objectives=overrides.get("objectives", "Valid objectives."),
        methodology=overrides.get("methodology", "Valid methodology."),
        expected_results=overrides.get("expected_results", "Valid expected results."),
        keywords=overrides.get("keywords", "ai, research"),
        start_date=overrides.get("start_date", datetime.date(2025, 1, 1)),
        estimated_end_date=overrides.get(
            "estimated_end_date", datetime.date(2025, 12, 31)
        ),
    )


def _make_template_with_step(institution, center=None, deadline_days=7):
    template = WorkflowTemplate.objects.create(
        institution=institution, center=center, name="Approval"
    )
    step = WorkflowStep.objects.create(
        template=template, order=1, name="Director Review", deadline_days=deadline_days
    )
    return template, step


# ──────────────────────────────────────────────
# Receiver: create instance on submit / review
# ──────────────────────────────────────────────


class TestSignalReceiverCreateInstance:
    """Receiver creates WorkflowInstance on enviado / en_revision."""

    def test_receiver_creates_instance_on_enviado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        _make_template_with_step(inst, center)

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="borrador",
            to_state="enviado",
            triggered_by=user,
        )

        instance = WorkflowInstance.objects.get(project_id=project.id)
        assert instance.status == WorkflowInstanceStatus.PENDING
        assert instance.current_step is not None
        assert instance.deadline_date is not None
        assert instance.actions.filter(action=WorkflowActionType.CREATE).exists()

    def test_receiver_creates_instance_on_en_revision(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        _make_template_with_step(inst, center)

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="enviado",
            to_state="en_revision",
            triggered_by=user,
        )

        assert WorkflowInstance.objects.filter(project_id=project.id).exists()

    def test_receiver_idempotent(self, db):
        """WR-001: second signal does not create duplicate."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        _make_template_with_step(inst, center)

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="borrador",
            to_state="enviado",
            triggered_by=user,
        )
        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="borrador",
            to_state="enviado",
            triggered_by=user,
        )

        assert WorkflowInstance.objects.filter(project_id=project.id).count() == 1


# ──────────────────────────────────────────────
# Receiver: approve / observe / reject
# ──────────────────────────────────────────────


class TestSignalReceiverActions:
    """Receiver handles approve, observe, reject transitions."""

    def test_receiver_completes_on_aprobado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_revision",
            to_state="aprobado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.COMPLETED
        assert instance.actions.filter(action=WorkflowActionType.APPROVE).exists()

    def test_receiver_observes_on_observado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_revision",
            to_state="observado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.OBSERVED
        assert instance.actions.filter(action=WorkflowActionType.OBSERVE).exists()

    def test_receiver_rejects_on_rechazado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_revision",
            to_state="rechazado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.REJECTED
        assert instance.actions.filter(action=WorkflowActionType.REJECT).exists()

    def test_receiver_resets_on_resubmit(self, db):
        """observado -> enviado resets instance to pending."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.OBSERVED,
        )
        WorkflowAction.objects.create(
            instance=instance, step=step, action=WorkflowActionType.OBSERVE, acted_by=user
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="observado",
            to_state="enviado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.PENDING
        assert instance.actions.filter(action=WorkflowActionType.RESUBMIT).exists()

    def test_receiver_cancels_on_cancelado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_ejecucion",
            to_state="cancelado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.CANCELLED
        assert instance.actions.filter(action=WorkflowActionType.CANCEL).exists()

    def test_receiver_cancels_on_cerrado(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template, step = _make_template_with_step(inst, center)
        instance = WorkflowInstance.objects.create(
            project_id=project.id,
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_cierre",
            to_state="cerrado",
            triggered_by=user,
        )

        instance.refresh_from_db()
        assert instance.status == WorkflowInstanceStatus.CANCELLED
        assert instance.actions.filter(action=WorkflowActionType.CANCEL).exists()

    def test_receiver_no_instance_noop(self, db):
        """If no active instance exists, approve/reject/observed are no-ops."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        # no instance created

        # should not raise
        project_state_changed.send(
            sender=type(project),
            project=project,
            from_state="en_revision",
            to_state="aprobado",
            triggered_by=user,
        )

        assert WorkflowInstance.objects.filter(project_id=project.id).count() == 0


# ──────────────────────────────────────────────
# Projects/services.py signal emission
# ──────────────────────────────────────────────


class TestProjectServiceSignalEmission:
    """_log_transition emits project_state_changed with correct kwargs."""

    def test_log_transition_emits_signal(self, db):
        from apps.projects.services import ProjectService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)

        received = {}

        def _receiver(sender, **kwargs):
            received.update(kwargs)

        project_state_changed.connect(_receiver)
        try:
            with patch("apps.projects.services.AuditEventEmitter"):
                ProjectService._log_transition(
                    project, "borrador", "enviado", user, reason=""
                )
        finally:
            project_state_changed.disconnect(_receiver)

        assert received.get("project") == project
        assert received.get("from_state") == "borrador"
        assert received.get("to_state") == "enviado"
        assert received.get("triggered_by") == user

    def test_submit_is_atomic(self, db):
        """If signal receiver raises, Project state transition rolls back."""
        from apps.projects.services import ProjectService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        _make_template_with_step(inst, center)

        def _bad_receiver(sender, **kwargs):
            raise RuntimeError("boom")

        project_state_changed.connect(_bad_receiver)
        try:
            with patch("apps.projects.services.AuditEventEmitter"):
                with pytest.raises(RuntimeError, match="boom"):
                    ProjectService.submit(project, user)
        finally:
            project_state_changed.disconnect(_bad_receiver)

        project.refresh_from_db()
        assert project.status == "borrador"
        assert not WorkflowInstance.objects.filter(project_id=project.id).exists()


# ──────────────────────────────────────────────
# Atomicity
# ──────────────────────────────────────────────


class TestSignalReceiverAtomicity:
    """Receiver failures roll back inside transaction.atomic()."""

    def test_receiver_rollback_on_create_failure(self, db):
        """If create_instance fails mid-transaction, no partial state left."""
        from apps.project_workflow.signals import on_project_state_change

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        WorkflowTemplate.objects.create(institution=inst, name="NoSteps")
        # intentionally no steps — will raise ValidationError

        with pytest.raises(ValidationError):
            on_project_state_change(
                sender=type(project),
                project=project,
                from_state="borrador",
                to_state="enviado",
                triggered_by=user,
            )

        assert WorkflowInstance.objects.filter(project_id=project.id).count() == 0
        assert WorkflowAction.objects.filter(
            instance__project_id=project.id
        ).count() == 0
