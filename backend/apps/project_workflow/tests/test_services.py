"""
Service layer tests for project_workflow app — STRICT TDD (RED phase).

Tests define expected behavior of:
- WorkflowService: create_instance, advance_step, complete_workflow,
  record_action, check_minimum_data, annotate_overdue, get_current_step
- WorkflowTemplateService: get_default_template, validate_step_order

Spec reference:  openspec/changes/project_workflow/spec.md
Design reference: openspec/changes/project_workflow/design.md

RED PHASE: Tests fail because services.py does not exist yet.
"""
import datetime
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    StepRole,
    WorkflowTemplate,
)


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


# ──────────────────────────────────────────────
# WorkflowService.create_instance
# ──────────────────────────────────────────────


class TestWorkflowServiceCreateInstance:
    """WorkflowService.create_instance — idempotent, deadline, action."""

    def test_create_instance_success(self, db):
        """Creates WorkflowInstance + first WorkflowAction with deadline."""
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        instance = WorkflowService.create_instance(project.id, template.id, triggered_by=user)

        assert instance.project_id == project.id
        assert instance.template == template
        assert instance.current_step == step
        assert instance.status == WorkflowInstanceStatus.PENDING
        assert instance.deadline_date is not None
        # deadline_date ≈ now + 7 days
        delta = instance.deadline_date - timezone.now()
        assert datetime.timedelta(hours=23) < delta < datetime.timedelta(days=8)

        actions = list(instance.actions.all())
        assert len(actions) == 1
        assert actions[0].action == WorkflowActionType.CREATE
        assert actions[0].acted_by == user

    def test_create_instance_idempotent(self, db):
        """WR-001: second call returns existing instance, no duplicate."""
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        first = WorkflowService.create_instance(project.id, template.id, triggered_by=user)
        second = WorkflowService.create_instance(project.id, template.id, triggered_by=user)

        assert first.id == second.id
        assert first.actions.count() == 1  # still only the create action

    def test_create_instance_no_steps_raises(self, db):
        """Raises ValidationError if template has no steps."""
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")

        with pytest.raises(ValidationError, match="no steps"):
            WorkflowService.create_instance(project.id, template.id, triggered_by=user)

    def test_create_instance_minimum_data_guard(self, db):
        """Raises ValidationError if project data is incomplete."""
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        # Clear methodology via ORM update to bypass full_clean
        WorkflowInstance._meta.model  # noqa: B018
        from apps.projects.models import Project

        Project.objects.filter(pk=project.pk).update(methodology="")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        with pytest.raises(ValidationError, match="(?i)minimum data"):
            WorkflowService.create_instance(project.id, template.id, triggered_by=user)


# ──────────────────────────────────────────────
# WorkflowService.check_minimum_data
# ──────────────────────────────────────────────


class TestWorkflowServiceCheckMinimumData:
    """WorkflowService.check_minimum_data — CA-005 guard."""

    def test_all_fields_present_passes(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)

        # should not raise
        WorkflowService.check_minimum_data(project.id)

    def test_missing_methodology_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(methodology="")

        with pytest.raises(ValidationError, match="methodology"):
            WorkflowService.check_minimum_data(project.id)

    def test_missing_objectives_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(objectives="")

        with pytest.raises(ValidationError, match="objectives"):
            WorkflowService.check_minimum_data(project.id)

    def test_missing_expected_results_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(expected_results="")

        with pytest.raises(ValidationError, match="expected_results"):
            WorkflowService.check_minimum_data(project.id)

    def test_missing_title_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(title="")

        with pytest.raises(ValidationError, match="title"):
            WorkflowService.check_minimum_data(project.id)

    def test_missing_abstract_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(abstract="")

        with pytest.raises(ValidationError, match="abstract"):
            WorkflowService.check_minimum_data(project.id)

    def test_missing_keywords_raises(self, db):
        from apps.project_workflow.services import WorkflowService
        from apps.projects.models import Project

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("pi@test.edu")
        from apps.researchers.models import Researcher

        pi = Researcher.objects.create(user=user, institution=inst)
        project = _make_project(inst, center, pi)
        Project.objects.filter(pk=project.pk).update(keywords="")

        with pytest.raises(ValidationError, match="keywords"):
            WorkflowService.check_minimum_data(project.id)

# ──────────────────────────────────────────────
# WorkflowService.advance_step
# ──────────────────────────────────────────────


class TestWorkflowServiceAdvanceStep:
    """WorkflowService.advance_step — move to next step or complete."""

    def test_advance_step_moves_to_next_step(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        step2 = WorkflowStep.objects.create(template=template, order=2, name="S2", deadline_days=5)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        result = WorkflowService.advance_step(instance.id, triggered_by=user)

        assert result.current_step == step2
        assert result.status == WorkflowInstanceStatus.PENDING
        actions = list(result.actions.all())
        assert len(actions) == 1
        assert actions[0].action == WorkflowActionType.APPROVE
        assert actions[0].acted_by == user
        assert actions[0].step == step1

    def test_advance_step_completes_when_last(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        result = WorkflowService.advance_step(instance.id, triggered_by=user)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert result.completed_at is not None
        actions = list(result.actions.all())
        assert any(a.action == WorkflowActionType.APPROVE for a in actions)

    def test_advance_step_no_current_step_raises(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=None,
            status=WorkflowInstanceStatus.PENDING,
        )

        with pytest.raises(ValidationError, match="current step"):
            WorkflowService.advance_step(instance.id, triggered_by=user)


# ──────────────────────────────────────────────
# WorkflowService.complete_workflow
# ──────────────────────────────────────────────


class TestWorkflowServiceCompleteWorkflow:
    """WorkflowService.complete_workflow — mark completed, create action."""

    def test_complete_workflow_sets_status_and_action(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step1 = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step1,
            status=WorkflowInstanceStatus.PENDING,
        )

        result = WorkflowService.complete_workflow(instance.id, triggered_by=user)

        assert result.status == WorkflowInstanceStatus.COMPLETED
        assert result.completed_at is not None
        actions = list(result.actions.all())
        assert len(actions) == 1
        assert actions[0].action == WorkflowActionType.APPROVE
        assert actions[0].acted_by == user
        assert actions[0].step == step1


# ──────────────────────────────────────────────
# WorkflowService.record_action
# ──────────────────────────────────────────────


class TestWorkflowServiceRecordAction:
    """WorkflowService.record_action — append-only generic action log."""

    def test_record_action_creates_action(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        center = _make_center(inst)
        user = _make_user("dir@test.edu")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        action = WorkflowService.record_action(
            instance.id, WorkflowActionType.OBSERVE, user, notes="Need changes."
        )

        assert action.instance == instance
        assert action.action == WorkflowActionType.OBSERVE
        assert action.acted_by == user
        assert action.observation_text == "Need changes."
        assert action.step == step


# ──────────────────────────────────────────────
# WorkflowService.annotate_overdue
# ──────────────────────────────────────────────


class TestWorkflowServiceAnnotateOverdue:
    """WorkflowService.annotate_overdue — is_overdue bool annotation."""

    def test_overdue_pending_instance(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )

        qs = WorkflowService.annotate_overdue(WorkflowInstance.objects.filter(pk=instance.pk))
        annotated = qs.first()
        assert annotated.is_overdue is True

    def test_not_overdue_future_deadline(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=timezone.now() + datetime.timedelta(days=1),
        )

        qs = WorkflowService.annotate_overdue(WorkflowInstance.objects.filter(pk=instance.pk))
        annotated = qs.first()
        assert annotated.is_overdue is False

    def test_completed_instance_not_overdue(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.COMPLETED,
            deadline_date=timezone.now() - datetime.timedelta(days=1),
        )

        qs = WorkflowService.annotate_overdue(WorkflowInstance.objects.filter(pk=instance.pk))
        annotated = qs.first()
        assert annotated.is_overdue is False

    def test_null_deadline_not_overdue(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            status=WorkflowInstanceStatus.PENDING,
            deadline_date=None,
        )

        qs = WorkflowService.annotate_overdue(WorkflowInstance.objects.filter(pk=instance.pk))
        annotated = qs.first()
        assert annotated.is_overdue is False


# ──────────────────────────────────────────────
# WorkflowService.get_current_step
# ──────────────────────────────────────────────


class TestWorkflowServiceGetCurrentStep:
    """WorkflowService.get_current_step — returns current WorkflowStep."""

    def test_get_current_step_returns_step(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        step = WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=step,
            status=WorkflowInstanceStatus.PENDING,
        )

        result = WorkflowService.get_current_step(instance)
        assert result == step

    def test_get_current_step_none(self, db):
        from apps.project_workflow.services import WorkflowService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        instance = WorkflowInstance.objects.create(
            project_id=uuid.uuid4(),
            institution=inst,
            template=template,
            current_step=None,
            status=WorkflowInstanceStatus.PENDING,
        )

        result = WorkflowService.get_current_step(instance)
        assert result is None


# ──────────────────────────────────────────────
# WorkflowTemplateService.get_default_template
# ──────────────────────────────────────────────


class TestWorkflowTemplateServiceGetDefaultTemplate:
    """WorkflowTemplateService.get_default_template — active, fewest steps."""

    def test_returns_template_with_fewest_steps(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        t1 = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=t1, order=1, name="S1", deadline_days=7)
        WorkflowStep.objects.create(template=t1, order=2, name="S2", deadline_days=7)
        t2 = WorkflowTemplate.objects.create(institution=inst, name="T2")
        WorkflowStep.objects.create(template=t2, order=1, name="S1", deadline_days=7)

        result = WorkflowTemplateService.get_default_template(inst.id)
        assert result == t2

    def test_prefers_center_specific(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        center = _make_center(inst)
        t_center = WorkflowTemplate.objects.create(institution=inst, center=center, name="Center")
        WorkflowStep.objects.create(template=t_center, order=1, name="S1", deadline_days=7)
        t_inst = WorkflowTemplate.objects.create(institution=inst, name="Inst")
        WorkflowStep.objects.create(template=t_inst, order=1, name="S1", deadline_days=7)

        result = WorkflowTemplateService.get_default_template(inst.id, center_id=center.id)
        assert result == t_center

    def test_returns_none_when_no_templates(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        result = WorkflowTemplateService.get_default_template(inst.id)
        assert result is None

    def test_ignores_inactive_templates(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        t1 = WorkflowTemplate.objects.create(institution=inst, name="T1", is_active=False)
        WorkflowStep.objects.create(template=t1, order=1, name="S1", deadline_days=7)
        t2 = WorkflowTemplate.objects.create(institution=inst, name="T2")
        WorkflowStep.objects.create(template=t2, order=1, name="S1", deadline_days=7)

        result = WorkflowTemplateService.get_default_template(inst.id)
        assert result == t2


# ──────────────────────────────────────────────
# WorkflowTemplateService.validate_step_order
# ──────────────────────────────────────────────


class TestWorkflowTemplateServiceValidateStepOrder:
    """WorkflowTemplateService.validate_step_order — sequential check."""

    def test_valid_sequential_order(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        WorkflowStep.objects.create(template=template, order=2, name="S2", deadline_days=7)
        WorkflowStep.objects.create(template=template, order=3, name="S3", deadline_days=7)

        assert WorkflowTemplateService.validate_step_order(template.id) is True

    def test_invalid_with_gap(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)
        WorkflowStep.objects.create(template=template, order=3, name="S3", deadline_days=7)

        assert WorkflowTemplateService.validate_step_order(template.id) is False

    def test_invalid_starts_not_at_one(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=2, name="S2", deadline_days=7)

        assert WorkflowTemplateService.validate_step_order(template.id) is False

    def test_valid_single_step(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")
        WorkflowStep.objects.create(template=template, order=1, name="S1", deadline_days=7)

        assert WorkflowTemplateService.validate_step_order(template.id) is True

    def test_invalid_empty(self, db):
        from apps.project_workflow.services import WorkflowTemplateService

        inst = _make_institution("TU")
        template = WorkflowTemplate.objects.create(institution=inst, name="T1")

        assert WorkflowTemplateService.validate_step_order(template.id) is False
