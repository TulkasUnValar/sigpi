"""
Model tests for budgets app — STRICT TDD (RED phase).

Tests define the expected behavior of the 5-entity budget module:
Budget, BudgetLine, FundingSource, BudgetExecution, BudgetAttachment.

Spec reference:  openspec/changes/budgets/specs/budgets/spec.md
Design reference: openspec/changes/budgets/design.md

RED PHASE: All tests fail because the models are not yet implemented.
"""

import datetime
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
    FundingSource,
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


def _make_budget(institution, project=None, **kwargs):
    if project is None:
        project = _make_project(institution)
    defaults = {
        "project": project,
        "institution": institution,
        "name": "Research Budget",
        "approved_amount": 100000.00,
        "status": BudgetStatus.DRAFT,
    }
    defaults.update(kwargs)
    return Budget.objects.create(**defaults)


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestBudgetStatusEnum:
    """BudgetStatus TextChoices has 4 states."""

    def test_all_four_states_defined(self):
        expected = {"draft", "approved", "executed", "closed"}
        actual = {choice[0] for choice in BudgetStatus.choices}
        assert actual == expected


# ──────────────────────────────────────────────
# Budget Model Tests
# ──────────────────────────────────────────────


class TestBudgetFields:
    """Budget model field behavior and defaults."""

    def test_create_budget_minimal(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        assert budget.id is not None
        assert isinstance(budget.id, uuid.UUID)
        assert budget.institution == inst
        assert budget.status == BudgetStatus.DRAFT
        assert budget.name == "Research Budget"
        assert budget.approved_amount == 100000.00

    def test_budget_project_one_to_one(self, db):
        """Only one Budget per project (OneToOne FK)."""
        inst = _make_institution("TU")
        project = _make_project(inst)
        _make_budget(inst, project=project)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_budget(inst, project=project)

    def test_budget_has_denormalized_institution_id(self, db):
        """Budget carries denormalized institution_id for RLS."""
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        assert budget.institution_id == inst.id

    def test_timestamps_auto_set(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        assert budget.created_at is not None
        assert budget.updated_at is not None

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        assert "Research Budget" in str(budget)

    def test_status_choices_valid(self, db):
        inst = _make_institution("TU")
        project = _make_project(inst)
        for status in ("draft", "approved", "executed", "closed"):
            b = Budget(
                project=project,
                institution=inst,
                name=f"B-{status}",
                approved_amount=1.00,
                status=status,
            )
            b.full_clean()  # should not raise

    def test_status_invalid_choice(self, db):
        inst = _make_institution("TU")
        project = _make_project(inst)
        b = Budget(
            project=project,
            institution=inst,
            name="Bad",
            approved_amount=1.00,
            status="invalid",
        )
        with pytest.raises(ValidationError):
            b.full_clean()


class TestBudgetConstraints:
    """Budget DB constraints and indexes."""

    def test_has_expected_constraints(self):
        constraint_names = {c.name for c in Budget._meta.constraints}
        assert "check_budget_amount_non_negative" in constraint_names
        assert "unique_budget_per_project" in constraint_names

    def test_has_expected_indexes(self):
        index_fields = {tuple(i.fields) for i in Budget._meta.indexes}
        assert ("institution", "status") in index_fields

    def test_non_negative_amount_constraint(self, db):
        """Negative approved_amount is rejected at the DB level."""
        inst = _make_institution("TU")
        project = _make_project(inst)
        b = Budget(
            project=project,
            institution=inst,
            name="Neg",
            approved_amount=-1.00,
        )
        with pytest.raises(ValidationError):
            b.full_clean()

    def test_amount_is_decimal_14_2(self):
        field = Budget._meta.get_field("approved_amount")
        assert field.max_digits == 14
        assert field.decimal_places == 2


# ──────────────────────────────────────────────
# BudgetLine Tests
# ──────────────────────────────────────────────


class TestBudgetLineFields:
    """BudgetLine model behavior."""

    def test_create_line(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        line = BudgetLine.objects.create(
            budget=budget,
            name="Personal",
            approved_amount=50000.00,
        )
        assert line.id is not None
        assert line.budget == budget
        assert line.name == "Personal"
        assert line.approved_amount == 50000.00
        assert line.created_at is not None
        assert line.updated_at is not None

    def test_line_cascades_on_budget_delete(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        BudgetLine.objects.create(budget=budget, name="Line", approved_amount=10.00)
        budget.delete()
        assert BudgetLine.objects.count() == 0

    def test_line_has_expected_indexes(self):
        index_fields = {tuple(i.fields) for i in BudgetLine._meta.indexes}
        assert ("budget",) in index_fields
        assert ("budget", "name") in index_fields

    def test_line_amount_is_decimal_14_2(self):
        field = BudgetLine._meta.get_field("approved_amount")
        assert field.max_digits == 14
        assert field.decimal_places == 2

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        line = BudgetLine.objects.create(budget=budget, name="Personal", approved_amount=1.00)
        assert "Personal" in str(line)


# ──────────────────────────────────────────────
# FundingSource Tests
# ──────────────────────────────────────────────


class TestFundingSourceFields:
    """FundingSource model behavior (RN-019 multiple sources allowed)."""

    def test_create_funding_source(self, db):
        inst = _make_institution("TU")
        project = _make_project(inst)
        src = FundingSource.objects.create(
            project=project,
            name="MinCiencias",
            amount=80000.00,
        )
        assert src.id is not None
        assert src.project == project
        assert src.name == "MinCiencias"
        assert src.amount == 80000.00

    def test_multiple_sources_allowed(self, db):
        """A project can have more than one FundingSource (RN-019)."""
        inst = _make_institution("TU")
        project = _make_project(inst)
        FundingSource.objects.create(project=project, name="MinCiencias", amount=50000.00)
        FundingSource.objects.create(project=project, name="University", amount=30000.00)
        assert FundingSource.objects.filter(project=project).count() == 2

    def test_source_has_index_on_project(self):
        index_fields = {tuple(i.fields) for i in FundingSource._meta.indexes}
        assert ("project",) in index_fields

    def test_source_amount_is_decimal_14_2(self):
        field = FundingSource._meta.get_field("amount")
        assert field.max_digits == 14
        assert field.decimal_places == 2

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        project = _make_project(inst)
        src = FundingSource.objects.create(project=project, name="MinCiencias", amount=1.00)
        assert "MinCiencias" in str(src)


# ──────────────────────────────────────────────
# BudgetExecution Tests
# ──────────────────────────────────────────────


class TestBudgetExecutionFields:
    """BudgetExecution model behavior."""

    def test_create_execution(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        line = BudgetLine.objects.create(budget=budget, name="Personal", approved_amount=1000.00)
        exec_ = BudgetExecution.objects.create(
            line=line,
            amount=400.00,
            executed_at=datetime.date(2026, 5, 1),
        )
        assert exec_.id is not None
        assert exec_.line == line
        assert exec_.amount == 400.00
        assert exec_.executed_at == datetime.date(2026, 5, 1)
        assert exec_.authorized_by is None
        assert exec_.authorized_at is None

    def test_authorized_fields_nullable(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        line = BudgetLine.objects.create(budget=budget, name="Personal", approved_amount=1000.00)
        user = _make_user()
        exec_ = BudgetExecution.objects.create(
            line=line,
            amount=500.00,
            executed_at=datetime.date(2026, 5, 1),
            authorized_by=user,
            authorized_at=datetime.date(2026, 5, 2),
        )
        assert exec_.authorized_by == user
        assert exec_.authorized_at == datetime.date(2026, 5, 2)

    def test_execution_cascades_on_line_delete(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        line = BudgetLine.objects.create(budget=budget, name="Personal", approved_amount=1000.00)
        BudgetExecution.objects.create(line=line, amount=100.00, executed_at=datetime.date(2026, 1, 1))
        line.delete()
        assert BudgetExecution.objects.count() == 0

    def test_execution_has_expected_index(self):
        index_fields = {tuple(i.fields) for i in BudgetExecution._meta.indexes}
        assert ("line", "executed_at") in index_fields

    def test_amount_is_decimal_14_2(self):
        field = BudgetExecution._meta.get_field("amount")
        assert field.max_digits == 14
        assert field.decimal_places == 2


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


# ──────────────────────────────────────────────
# BudgetAttachment Tests
# ──────────────────────────────────────────────


class TestBudgetAttachmentFields:
    """BudgetAttachment model behavior (RF-B05, metadata-only)."""

    def test_create_attachment(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        att = BudgetAttachment.objects.create(
            budget=budget,
            name="Presupuesto.pdf",
            doc_type="soporte",
            external_url="https://storage.example.com/presupuesto.pdf",
        )
        assert att.id is not None
        assert att.budget == budget
        assert att.name == "Presupuesto.pdf"
        assert att.doc_type == "soporte"
        assert att.external_url == "https://storage.example.com/presupuesto.pdf"
        assert att.created_at is not None

    def test_external_url_required(self, db):
        """external_url is required — missing raises ValidationError (RF-B05)."""
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        att = BudgetAttachment(
            budget=budget,
            name="NoUrl.pdf",
            doc_type="soporte",
            external_url="",
        )
        with pytest.raises(ValidationError):
            att.full_clean()

    def test_attachment_cascades_on_budget_delete(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        BudgetAttachment.objects.create(
            budget=budget, name="A.pdf", doc_type="soporte", external_url="https://x.com/a"
        )
        budget.delete()
        assert BudgetAttachment.objects.count() == 0

    def test_attachment_has_index_on_budget(self):
        index_fields = {tuple(i.fields) for i in BudgetAttachment._meta.indexes}
        assert ("budget",) in index_fields

    def test_str_representation(self, db):
        inst = _make_institution("TU")
        budget = _make_budget(inst)
        att = BudgetAttachment.objects.create(
            budget=budget, name="Presupuesto.pdf", doc_type="soporte", external_url="https://x.com"
        )
        assert "Presupuesto.pdf" in str(att)


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestBudgetFactories:
    """Factories produce valid instances."""

    def test_budget_factory(self, db):
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory()
        assert budget.id is not None
        assert budget.project is not None
        assert budget.institution == budget.project.institution

    def test_budget_line_factory(self, db):
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory()
        assert line.id is not None
        assert line.budget is not None
        assert line.name

    def test_funding_source_factory(self, db):
        from apps.budgets.tests.conftest import FundingSourceFactory

        src = FundingSourceFactory()
        assert src.id is not None
        assert src.project is not None

    def test_budget_execution_factory(self, db):
        from apps.budgets.tests.conftest import BudgetExecutionFactory

        exec_ = BudgetExecutionFactory()
        assert exec_.id is not None
        assert exec_.line is not None
        assert exec_.authorized_by is None

    def test_budget_attachment_factory(self, db):
        from apps.budgets.tests.conftest import BudgetAttachmentFactory

        att = BudgetAttachmentFactory()
        assert att.id is not None
        assert att.budget is not None
        assert att.external_url
