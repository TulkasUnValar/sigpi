"""
Service layer tests for budgets — STRICT TDD (RED phase).

Covers:
- BudgetService: create/update/delete (atomic, audit), add_execution with
  RN-020 (sum ≤ approved unless authorized) + lock/recheck.
- BudgetSummaryService.for_budget(): approved/executed/balance or None.

Audit events (BUDGET_CREATED/UPDATED/EXECUTION_ADDED) are emitted via
AuditEventEmitter; the enum types are added in Phase 3 (task 3.1), but the
emitter persists any event_type string, so this is testable now.

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
    BudgetExecution,
    BudgetStatus,
)


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(email=f"svc_{User.objects.count()}@test.edu", auth_source="local")


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
            updated = BudgetService.update(budget, user, name="Updated", approved_amount=Decimal("2000.00"))

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
            BudgetService.add_execution(line=line, amount=Decimal("1000.00"), executed_at=datetime.date(2026, 5, 1), user=user)

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
