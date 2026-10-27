"""
Service layer tests for budgets — STRICT TDD (RED phase).

Covers:
- BudgetService: create/update/delete (atomic, audit), add_execution with
  RN-020 (sum ≤ approved unless authorized) + lock/recheck.
- BudgetLineService: create/update/delete (atomic, audit, full_clean).
- BudgetAttachmentService: create/update/delete (atomic, audit, full_clean).
- FundingSourceService: create/update/delete (atomic, audit, full_clean).
- BudgetSummaryService.for_budget(): approved/executed/balance or None.

Audit events (BUDGET_CREATED/UPDATED/EXECUTION_ADDED, BUDGET_LINE_*,
BUDGET_ATTACHMENT_*, FUNDING_SOURCE_*) are emitted via AuditEventEmitter;
the enum types are added in Phase 3 (task 3.1), but the emitter persists any
event_type string, so this is testable now.

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — RF-B01/B04/B07
Design reference: openspec/changes/budgets/design.md — Services, Audit and Reports
"""

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
    FundingSource,
)
from apps.budgets.services import (
    BudgetAttachmentService,
    BudgetLineService,
    FundingSourceService,
)
from apps.budgets.tests.conftest import (
    BudgetAttachmentFactory,
    BudgetFactory,
    BudgetLineFactory,
    FundingSourceFactory,
)
from apps.projects.tests.conftest import ProjectFactory


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(
        email=f"svc_{User.objects.count()}@test.edu", auth_source="local"
    )


# ──────────────────────────────────────────────────────────
# BudgetService.create()
# ──────────────────────────────────────────────────────────


class TestBudgetServiceCreate:
    def test_create_succeeds_and_audits(self, db):
        from apps.budgets.services import BudgetService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        institution = project.institution
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            budget = BudgetService.create(
                institution=institution,
                user=user,
                project=project,
                name="Project Budget",
                approved_amount=Decimal("10000.00"),
            )

        assert budget.pk is not None
        assert budget.institution == institution
        assert budget.project == project
        assert budget.status == BudgetStatus.DRAFT
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_CREATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == institution.id
        assert "budget_id" in kwargs["details"]

    def test_create_duplicate_raises(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory()
        institution = budget.institution
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter"):
            with pytest.raises((ValidationError, IntegrityError)):
                BudgetService.create(
                    institution=institution,
                    user=user,
                    project=budget.project,
                    name="Duplicate",
                    approved_amount=Decimal("100.00"),
                )


# ──────────────────────────────────────────────────────────
# BudgetService.update()
# ──────────────────────────────────────────────────────────


class TestBudgetServiceUpdate:
    def test_update_succeeds_and_audits(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory(name="Original", approved_amount=Decimal("1000.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            updated = BudgetService.update(
                budget, user, name="Updated", approved_amount=Decimal("2000.00")
            )

        assert updated.name == "Updated"
        assert updated.approved_amount == Decimal("2000.00")
        budget.refresh_from_db()
        assert budget.name == "Updated"
        mock_emitter.emit.assert_called_once()
        assert mock_emitter.emit.call_args[1]["event_type"] == "BUDGET_UPDATED"


# ──────────────────────────────────────────────────────────
# BudgetService.delete()
# ──────────────────────────────────────────────────────────


class TestBudgetServiceDelete:
    def test_delete_removes_budget(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory()
        user = _make_user()
        pk = budget.pk

        with patch("apps.budgets.services.AuditEventEmitter"):
            BudgetService.delete(budget, user)

        assert not Budget.objects.filter(pk=pk).exists()


# ──────────────────────────────────────────────────────────
# BudgetService.add_execution() — RN-020
# ──────────────────────────────────────────────────────────


class TestBudgetServiceAddExecution:
    def test_execution_within_limit_creates(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            ex = BudgetService.add_execution(
                line=line,
                amount=Decimal("400.00"),
                executed_at=datetime.date(2026, 5, 1),
                user=user,
            )

        assert ex.pk is not None
        assert ex.line == line
        assert ex.amount == Decimal("400.00")
        assert ex.authorized_by is None
        assert ex.authorized_at is None
        mock_emitter.emit.assert_called_once()
        assert mock_emitter.emit.call_args[1]["event_type"] == "BUDGET_EXECUTION_ADDED"

    def test_execution_at_exact_limit_allowed(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter"):
            BudgetService.add_execution(
                line=line,
                amount=Decimal("1000.00"),
                executed_at=datetime.date(2026, 5, 1),
                user=user,
            )

        assert BudgetExecution.objects.filter(line=line).count() == 1

    def test_execution_overrun_without_auth_rejected(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetExecutionFactory, BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("900.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter"):
            with pytest.raises(ValidationError, match=r"[Ee]xceed|approved|authorized"):
                BudgetService.add_execution(
                    line=line,
                    amount=Decimal("200.00"),
                    executed_at=datetime.date(2026, 6, 1),
                    user=user,
                )

    def test_execution_overrun_with_auth_allowed(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetExecutionFactory, BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("900.00"))
        user = _make_user()
        authorizer = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter"):
            ex = BudgetService.add_execution(
                line=line,
                amount=Decimal("200.00"),
                executed_at=datetime.date(2026, 6, 1),
                user=user,
                authorized_by=authorizer,
                authorized_at=datetime.date(2026, 6, 2),
            )

        assert ex.authorized_by == authorizer
        assert ex.authorized_at == datetime.date(2026, 6, 2)

    def test_execution_overrun_with_partial_auth_rejected(self, db):
        """authorized_by present but authorized_at missing → still rejected."""
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetExecutionFactory, BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("900.00"))
        user = _make_user()
        authorizer = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter"):
            with pytest.raises(ValidationError):
                BudgetService.add_execution(
                    line=line,
                    amount=Decimal("200.00"),
                    executed_at=datetime.date(2026, 6, 1),
                    user=user,
                    authorized_by=authorizer,
                    authorized_at=None,
                )


# ──────────────────────────────────────────────────────────
# BudgetSummaryService.for_budget()
# ──────────────────────────────────────────────────────────


class TestBudgetSummaryService:
    def test_summary_math(self, db):
        from apps.budgets.services import BudgetSummaryService
        from apps.budgets.tests.conftest import (
            BudgetExecutionFactory,
            BudgetFactory,
            BudgetLineFactory,
        )

        budget = BudgetFactory(approved_amount=Decimal("1000.00"))
        line = BudgetLineFactory(budget=budget, approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("250.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("150.00"))

        summary = BudgetSummaryService.for_budget(budget.project)
        assert summary is not None
        assert summary["approved"] == Decimal("1000.00")
        assert summary["executed"] == Decimal("400.00")
        assert summary["balance"] == Decimal("600.00")

    def test_summary_empty_executions(self, db):
        from apps.budgets.services import BudgetSummaryService
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory(approved_amount=Decimal("500.00"))

        summary = BudgetSummaryService.for_budget(budget.project)
        assert summary["approved"] == Decimal("500.00")
        assert summary["executed"] == Decimal("0.00")
        assert summary["balance"] == Decimal("500.00")

    def test_summary_missing_budget_returns_none(self, db):
        from apps.budgets.services import BudgetSummaryService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        assert BudgetSummaryService.for_budget(project) is None


# ──────────────────────────────────────────────────────────
# BudgetLineService.create()
# ──────────────────────────────────────────────────────────


class TestBudgetLineServiceCreate:
    def test_create_succeeds_and_audits(self, db):
        budget = BudgetFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            line = BudgetLineService.create(
                budget=budget,
                user=user,
                name="Equipment",
                approved_amount=Decimal("1500.00"),
            )

        assert line.pk is not None
        assert line.budget == budget
        assert line.name == "Equipment"
        assert line.approved_amount == Decimal("1500.00")
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_LINE_CREATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == budget.institution_id
        assert kwargs["details"]["line_id"] == str(line.pk)
        assert kwargs["details"]["budget_id"] == str(budget.pk)
        assert kwargs["details"]["name"] == "Equipment"
        assert kwargs["details"]["approved_amount"] == "1500.00"

    def test_create_negative_amount_rejected(self, db):
        budget = BudgetFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            with pytest.raises(ValidationError):
                BudgetLineService.create(
                    budget=budget,
                    user=user,
                    name="Invalid",
                    approved_amount=Decimal("-1.00"),
                )

        assert not BudgetLine.objects.filter(budget=budget, name="Invalid").exists()
        mock_class.return_value.emit.assert_not_called()


# ──────────────────────────────────────────────────────────
# BudgetLineService.update()
# ──────────────────────────────────────────────────────────


class TestBudgetLineServiceUpdate:
    def test_update_succeeds_and_audits(self, db):
        line = BudgetLineFactory(name="Original", approved_amount=Decimal("100.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            updated = BudgetLineService.update(
                line, user, name="Updated", approved_amount=Decimal("250.00")
            )

        assert updated.name == "Updated"
        assert updated.approved_amount == Decimal("250.00")
        line.refresh_from_db()
        assert line.name == "Updated"
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_LINE_UPDATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == line.budget.institution_id
        assert kwargs["details"]["line_id"] == str(line.pk)
        assert kwargs["details"]["approved_amount"] == "250.00"


# ──────────────────────────────────────────────────────────
# BudgetLineService.delete()
# ──────────────────────────────────────────────────────────


class TestBudgetLineServiceDelete:
    def test_delete_removes_line_and_audits(self, db):
        line = BudgetLineFactory(name="Delete me")
        user = _make_user()
        pk = line.pk

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            BudgetLineService.delete(line, user)

        assert not BudgetLine.objects.filter(pk=pk).exists()
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_LINE_DELETED"
        assert kwargs["user"] == user
        assert kwargs["details"]["line_id"] == str(pk)
        assert kwargs["details"]["name"] == "Delete me"


# ──────────────────────────────────────────────────────────
# BudgetAttachmentService.create()
# ──────────────────────────────────────────────────────────


class TestBudgetAttachmentServiceCreate:
    def test_create_succeeds_and_audits(self, db):
        budget = BudgetFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            attachment = BudgetAttachmentService.create(
                budget=budget,
                user=user,
                name="Plan.pdf",
                doc_type="soporte",
                external_url="https://example.com/plan.pdf",
            )

        assert attachment.pk is not None
        assert attachment.budget == budget
        assert attachment.name == "Plan.pdf"
        assert attachment.doc_type == "soporte"
        assert attachment.external_url == "https://example.com/plan.pdf"
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_ATTACHMENT_CREATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == budget.institution_id
        assert kwargs["details"]["attachment_id"] == str(attachment.pk)
        assert kwargs["details"]["budget_id"] == str(budget.pk)
        assert kwargs["details"]["doc_type"] == "soporte"

    def test_create_invalid_url_rejected(self, db):
        budget = BudgetFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            with pytest.raises(ValidationError):
                BudgetAttachmentService.create(
                    budget=budget,
                    user=user,
                    name="Broken.pdf",
                    doc_type="soporte",
                    external_url="not-a-url",
                )

        assert not BudgetAttachment.objects.filter(budget=budget, name="Broken.pdf").exists()
        mock_class.return_value.emit.assert_not_called()


# ──────────────────────────────────────────────────────────
# BudgetAttachmentService.update()
# ──────────────────────────────────────────────────────────


class TestBudgetAttachmentServiceUpdate:
    def test_update_succeeds_and_audits(self, db):
        attachment = BudgetAttachmentFactory(name="Old.pdf", doc_type="soporte")
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            updated = BudgetAttachmentService.update(
                attachment, user, name="New.pdf", doc_type="acta"
            )

        assert updated.name == "New.pdf"
        assert updated.doc_type == "acta"
        attachment.refresh_from_db()
        assert attachment.name == "New.pdf"
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_ATTACHMENT_UPDATED"
        assert kwargs["user"] == user
        assert kwargs["details"]["attachment_id"] == str(attachment.pk)
        assert kwargs["details"]["name"] == "New.pdf"
        assert kwargs["details"]["doc_type"] == "acta"


# ──────────────────────────────────────────────────────────
# BudgetAttachmentService.delete()
# ──────────────────────────────────────────────────────────


class TestBudgetAttachmentServiceDelete:
    def test_delete_removes_attachment_and_audits(self, db):
        attachment = BudgetAttachmentFactory(name="Delete me.pdf")
        user = _make_user()
        pk = attachment.pk

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            BudgetAttachmentService.delete(attachment, user)

        assert not BudgetAttachment.objects.filter(pk=pk).exists()
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "BUDGET_ATTACHMENT_DELETED"
        assert kwargs["user"] == user
        assert kwargs["details"]["attachment_id"] == str(pk)
        assert kwargs["details"]["name"] == "Delete me.pdf"


# ──────────────────────────────────────────────────────────
# FundingSourceService.create()
# ──────────────────────────────────────────────────────────


class TestFundingSourceServiceCreate:
    def test_create_succeeds_and_audits(self, db):
        project = ProjectFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            source = FundingSourceService.create(
                project=project,
                user=user,
                name="Gov Grant",
                amount=Decimal("5000.00"),
            )

        assert source.pk is not None
        assert source.project == project
        assert source.name == "Gov Grant"
        assert source.amount == Decimal("5000.00")
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "FUNDING_SOURCE_CREATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == project.institution_id
        assert kwargs["details"]["source_id"] == str(source.pk)
        assert kwargs["details"]["project_id"] == str(project.pk)
        assert kwargs["details"]["amount"] == "5000.00"

    def test_create_negative_amount_rejected(self, db):
        project = ProjectFactory()
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            with pytest.raises(ValidationError):
                FundingSourceService.create(
                    project=project,
                    user=user,
                    name="Invalid",
                    amount=Decimal("-1.00"),
                )

        assert not FundingSource.objects.filter(project=project, name="Invalid").exists()
        mock_class.return_value.emit.assert_not_called()


# ──────────────────────────────────────────────────────────
# FundingSourceService.update()
# ──────────────────────────────────────────────────────────


class TestFundingSourceServiceUpdate:
    def test_update_succeeds_and_audits(self, db):
        source = FundingSourceFactory(name="Original", amount=Decimal("1000.00"))
        user = _make_user()

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            updated = FundingSourceService.update(
                source, user, name="Updated", amount=Decimal("2000.00")
            )

        assert updated.name == "Updated"
        assert updated.amount == Decimal("2000.00")
        source.refresh_from_db()
        assert source.name == "Updated"
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "FUNDING_SOURCE_UPDATED"
        assert kwargs["user"] == user
        assert kwargs["institution_id"] == source.project.institution_id
        assert kwargs["details"]["source_id"] == str(source.pk)
        assert kwargs["details"]["amount"] == "2000.00"


# ──────────────────────────────────────────────────────────
# FundingSourceService.delete()
# ──────────────────────────────────────────────────────────


class TestFundingSourceServiceDelete:
    def test_delete_removes_source_and_audits(self, db):
        source = FundingSourceFactory(name="Delete me")
        user = _make_user()
        pk = source.pk

        with patch("apps.budgets.services.AuditEventEmitter") as mock_class:
            mock_emitter = mock_class.return_value
            FundingSourceService.delete(source, user)

        assert not FundingSource.objects.filter(pk=pk).exists()
        mock_emitter.emit.assert_called_once()
        kwargs = mock_emitter.emit.call_args[1]
        assert kwargs["event_type"] == "FUNDING_SOURCE_DELETED"
        assert kwargs["user"] == user
        assert kwargs["details"]["source_id"] == str(pk)
        assert kwargs["details"]["name"] == "Delete me"
