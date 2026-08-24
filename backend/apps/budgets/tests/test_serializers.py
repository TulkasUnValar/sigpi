"""
Unit tests for budgets serializers — STRICT TDD (RED phase).

Covers 6 serializers per design.md:
- BudgetSerializer: read-only parent/tenant (project, institution); nested
  lines/attachments read-only; status lifecycle.
- BudgetLineSerializer: budget FK read-only (set by view from URL).
- FundingSourceSerializer: project FK read-only.
- BudgetExecutionSerializer: line FK read-only; authorized_by/authorized_at
  writable for over-execution authorization.
- BudgetAttachmentSerializer: budget FK read-only; external_url required.

Strict TDD: this file is written BEFORE serializers.py exists.
Expected failure: ImportError (serializers.py not created yet).

Spec reference: openspec/changes/budgets/specs/budgets/spec.md
Design reference: openspec/changes/budgets/design.md — Serializer Mapping
"""

from uuid import uuid4

import pytest


class TestBudgetSerializer:
    """BudgetSerializer: parent/tenant read-only, nested lines/attachments."""

    @pytest.mark.django_db
    def test_serializes_core_fields(self):
        from apps.budgets.serializers import BudgetSerializer
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory(name="Project Budget", approved_amount="5000.00")
        data = BudgetSerializer(budget).data

        assert data["name"] == "Project Budget"
        assert data["approved_amount"] == "5000.00"
        assert data["status"] == "draft"
        assert data["institution"] == budget.institution_id
        assert data["project"] == budget.project_id
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.django_db
    def test_nested_lines_are_read_only_and_serialized(self):
        from apps.budgets.serializers import BudgetSerializer
        from apps.budgets.tests.conftest import BudgetFactory, BudgetLineFactory

        budget = BudgetFactory()
        BudgetLineFactory(budget=budget, name="Rubro A", approved_amount="100.00")
        BudgetLineFactory(budget=budget, name="Rubro B", approved_amount="200.00")

        data = BudgetSerializer(budget).data
        assert len(data["lines"]) == 2
        names = {line["name"] for line in data["lines"]}
        assert names == {"Rubro A", "Rubro B"}

    @pytest.mark.django_db
    def test_nested_attachments_serialized(self):
        from apps.budgets.serializers import BudgetSerializer
        from apps.budgets.tests.conftest import BudgetAttachmentFactory, BudgetFactory

        budget = BudgetFactory()
        BudgetAttachmentFactory(budget=budget, name="Plan.pdf")
        BudgetAttachmentFactory(budget=budget, name="Report.pdf")

        data = BudgetSerializer(budget).data
        assert len(data["attachments"]) == 2
        names = {a["name"] for a in data["attachments"]}
        assert names == {"Plan.pdf", "Report.pdf"}

    @pytest.mark.django_db
    def test_institution_read_only_on_deserialize(self):
        from apps.budgets.serializers import BudgetSerializer

        data = {
            "name": "New Budget",
            "approved_amount": "100.00",
            "project": str(uuid4()),
            "institution": str(uuid4()),
        }
        serializer = BudgetSerializer(data=data)
        # institution and project are read-only; they must not produce errors
        assert isinstance(serializer.is_valid(), bool)
        assert "institution" not in serializer.errors

    @pytest.mark.django_db
    def test_name_and_amount_required(self):
        from apps.budgets.serializers import BudgetSerializer

        serializer = BudgetSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "approved_amount" in serializer.errors


class TestBudgetLineSerializer:
    """BudgetLineSerializer: name, approved_amount; budget FK read-only."""

    @pytest.mark.django_db
    def test_serializes_fields(self):
        from apps.budgets.serializers import BudgetLineSerializer
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory(name="Equipment", approved_amount="1500.00")
        data = BudgetLineSerializer(line).data

        assert data["name"] == "Equipment"
        assert data["approved_amount"] == "1500.00"
        assert data["budget"] == line.budget_id

    @pytest.mark.django_db
    def test_budget_read_only(self):
        from apps.budgets.serializers import BudgetLineSerializer
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory()
        data = {"budget": str(uuid4()), "name": "Changed", "approved_amount": "10.00"}
        serializer = BudgetLineSerializer(instance=line, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "budget" not in serializer.errors

    @pytest.mark.django_db
    def test_name_and_amount_required(self):
        from apps.budgets.serializers import BudgetLineSerializer

        serializer = BudgetLineSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "approved_amount" in serializer.errors

    @pytest.mark.django_db
    def test_rejects_negative_amount(self):
        from apps.budgets.serializers import BudgetLineSerializer

        data = {"name": "Bad", "approved_amount": "-5.00"}
        serializer = BudgetLineSerializer(data=data)
        assert not serializer.is_valid()
        assert "approved_amount" in serializer.errors


class TestFundingSourceSerializer:
    """FundingSourceSerializer: name, amount; project FK read-only."""

    @pytest.mark.django_db
    def test_serializes_fields(self):
        from apps.budgets.serializers import FundingSourceSerializer
        from apps.budgets.tests.conftest import FundingSourceFactory

        source = FundingSourceFactory(name="Gov Grant", amount="3000.00")
        data = FundingSourceSerializer(source).data

        assert data["name"] == "Gov Grant"
        assert data["amount"] == "3000.00"
        assert data["project"] == source.project_id

    @pytest.mark.django_db
    def test_project_read_only(self):
        from apps.budgets.serializers import FundingSourceSerializer
        from apps.budgets.tests.conftest import FundingSourceFactory

        source = FundingSourceFactory()
        data = {"project": str(uuid4()), "name": "Changed", "amount": "1.00"}
        serializer = FundingSourceSerializer(instance=source, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "project" not in serializer.errors


class TestBudgetExecutionSerializer:
    """BudgetExecutionSerializer: line read-only; authorization fields writable."""

    @pytest.mark.django_db
    def test_serializes_fields(self):
        import datetime

        from apps.budgets.serializers import BudgetExecutionSerializer
        from apps.budgets.tests.conftest import BudgetExecutionFactory

        ex = BudgetExecutionFactory(
            amount="400.00", executed_at=datetime.date(2026, 5, 1)
        )
        data = BudgetExecutionSerializer(ex).data

        assert data["amount"] == "400.00"
        assert data["executed_at"] == "2026-05-01"
        assert data["line"] == ex.line_id
        assert data["authorized_by"] is None
        assert data["authorized_at"] is None

    @pytest.mark.django_db
    def test_line_read_only(self):
        from apps.budgets.serializers import BudgetExecutionSerializer
        from apps.budgets.tests.conftest import BudgetExecutionFactory

        ex = BudgetExecutionFactory()
        data = {"line": str(uuid4()), "amount": "10.00"}
        serializer = BudgetExecutionSerializer(instance=ex, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "line" not in serializer.errors

    @pytest.mark.django_db
    def test_authorized_fields_writable(self):
        from apps.accounts.models import User
        from apps.budgets.serializers import BudgetExecutionSerializer
        from apps.budgets.tests.conftest import BudgetExecutionFactory

        ex = BudgetExecutionFactory()
        user = User.objects.create_user(email="auth@test.edu", auth_source="local")
        data = {"authorized_by": user.pk, "authorized_at": "2026-05-01"}
        serializer = BudgetExecutionSerializer(instance=ex, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "authorized_by" not in serializer.errors
        assert "authorized_at" not in serializer.errors

    @pytest.mark.django_db
    def test_amount_required(self):
        from apps.budgets.serializers import BudgetExecutionSerializer

        serializer = BudgetExecutionSerializer(data={})
        assert not serializer.is_valid()
        assert "amount" in serializer.errors


class TestBudgetAttachmentSerializer:
    """BudgetAttachmentSerializer: name, doc_type, required external_url."""

    @pytest.mark.django_db
    def test_serializes_fields(self):
        from apps.budgets.serializers import BudgetAttachmentSerializer
        from apps.budgets.tests.conftest import BudgetAttachmentFactory

        att = BudgetAttachmentFactory(name="Plan.pdf", doc_type="soporte")
        data = BudgetAttachmentSerializer(att).data

        assert data["name"] == "Plan.pdf"
        assert data["doc_type"] == "soporte"
        assert data["external_url"]
        assert data["budget"] == att.budget_id

    @pytest.mark.django_db
    def test_budget_read_only(self):
        from apps.budgets.serializers import BudgetAttachmentSerializer
        from apps.budgets.tests.conftest import BudgetAttachmentFactory

        att = BudgetAttachmentFactory()
        data = {"budget": str(uuid4()), "name": "Changed"}
        serializer = BudgetAttachmentSerializer(instance=att, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "budget" not in serializer.errors

    @pytest.mark.django_db
    def test_external_url_required(self):
        from apps.budgets.serializers import BudgetAttachmentSerializer

        data = {"name": "Plan.pdf", "doc_type": "soporte", "external_url": ""}
        serializer = BudgetAttachmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "external_url" in serializer.errors

    @pytest.mark.django_db
    def test_name_required(self):
        from apps.budgets.serializers import BudgetAttachmentSerializer

        data = {"doc_type": "soporte", "external_url": "https://example.com/plan.pdf"}
        serializer = BudgetAttachmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors
