"""
Cross-module integration tests: budgets + accounts audit + reports.

Covers the auth delta spec (FR-007 scenarios) and the budgets design
"Services, Audit and Reports" section:

- BudgetService mutations persist REAL AuditEvent rows via the real
  AuditEventEmitter (no mocks): BUDGET_CREATED, BUDGET_UPDATED,
  BUDGET_EXECUTION_ADDED — with user, institution and details.
- Execution audit details name the line (rubro) and the amount
  (auth delta: "details naming the line and amount").
- RN-020 authorized/unauthorized with real persistence + atomic
  rollback boundary (rejection persists nothing and emits nothing).
- RN-020 atomic concurrent boundary: two racing executions cannot
  push a line over its approved amount (PostgreSQL row locking;
  SQLite ignores select_for_update → skipped, repo RLS pattern).

STRICT TDD (RED phase): the line_name assertion fails until the
execution audit details include the line name.
"""

import datetime
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.models import Sum

from apps.accounts.audit import AuditEvent, AuditEventType


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(
        email=f"int_{User.objects.count()}@test.edu", auth_source="local"
    )


# ──────────────────────────────────────────────────────────
# Audit payloads — real persistence (no mocks)
# ──────────────────────────────────────────────────────────


class TestBudgetAuditPayloads:
    """BudgetService mutations persist real AuditEvent rows (RN-021)."""

    def test_create_persists_budget_created_audit(self, db):
        from apps.budgets.services import BudgetService
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        institution = project.institution
        user = _make_user()

        budget = BudgetService.create(
            institution=institution,
            user=user,
            project=project,
            name="Integration Budget",
            approved_amount=Decimal("5000.00"),
        )

        event = AuditEvent.objects.get(event_type=AuditEventType.BUDGET_CREATED)
        assert event.user == user
        assert event.institution_id == institution.id
        assert event.details["budget_id"] == str(budget.pk)
        assert event.details["project_id"] == str(project.pk)
        assert event.details["name"] == "Integration Budget"
        assert event.details["approved_amount"] == "5000.00"

    def test_update_persists_budget_updated_audit(self, db):
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetFactory

        budget = BudgetFactory(name="Before", approved_amount=Decimal("1000.00"))
        user = _make_user()

        BudgetService.update(
            budget, user, name="After", approved_amount=Decimal("2500.00")
        )

        event = AuditEvent.objects.get(event_type=AuditEventType.BUDGET_UPDATED)
        assert event.user == user
        assert event.details["budget_id"] == str(budget.pk)
        assert event.details["name"] == "After"
        assert event.details["approved_amount"] == "2500.00"

    def test_execution_persists_audit_naming_line_and_amount(self, db):
        """BUDGET_EXECUTION_ADDED details name the line (rubro) and amount."""
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory(name="Laboratorio", approved_amount=Decimal("1000.00"))
        user = _make_user()

        BudgetService.add_execution(
            line=line,
            amount=Decimal("300.00"),
            executed_at=datetime.date(2026, 5, 10),
            user=user,
        )

        event = AuditEvent.objects.get(event_type=AuditEventType.BUDGET_EXECUTION_ADDED)
        assert event.user == user
        assert event.details["line_id"] == str(line.pk)
        assert event.details["line_name"] == "Laboratorio"
        assert event.details["amount"] == "300.00"
        assert event.details["budget_id"] == str(line.budget_id)


# ──────────────────────────────────────────────────────────
# RN-020 — real persistence + atomic boundaries
# ──────────────────────────────────────────────────────────


class TestExecutionAtomicBoundaries:
    """RN-020 enforcement boundaries with real persistence."""

    def test_overrun_unauthorized_rejected_atomically(self, db):
        """Rejected overrun persists NO execution and NO audit event."""
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetExecutionFactory, BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("900.00"))
        user = _make_user()
        audit_before = AuditEvent.objects.count()

        with pytest.raises(ValidationError):
            BudgetService.add_execution(
                line=line,
                amount=Decimal("200.00"),
                executed_at=datetime.date(2026, 6, 1),
                user=user,
            )

        from apps.budgets.models import BudgetExecution

        assert BudgetExecution.objects.filter(line=line).count() == 1
        assert AuditEvent.objects.count() == audit_before

    def test_overrun_authorized_persists_execution_and_audit(self, db):
        """Authorized overrun persists the execution and its audit event."""
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetExecutionFactory, BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("900.00"))
        user = _make_user()
        authorizer = _make_user()

        execution = BudgetService.add_execution(
            line=line,
            amount=Decimal("200.00"),
            executed_at=datetime.date(2026, 6, 1),
            user=user,
            authorized_by=authorizer,
            authorized_at=datetime.date(2026, 6, 2),
        )

        assert execution.authorized_by == authorizer
        event = AuditEvent.objects.get(
            event_type=AuditEventType.BUDGET_EXECUTION_ADDED
        )
        assert event.details["authorized_by"] == str(authorizer.pk)


@pytest.mark.skip(reason="Requires PostgreSQL row locking; SQLite ignores select_for_update")
class TestExecutionConcurrentBoundary:
    """RN-020 concurrent boundary — PostgreSQL only (repo RLS pattern)."""

    def test_concurrent_executions_cannot_exceed_line_limit(self, db):
        """Two racing executions whose sum exceeds the limit: at most one wins."""
        from apps.budgets.services import BudgetService
        from apps.budgets.tests.conftest import BudgetLineFactory

        line = BudgetLineFactory(approved_amount=Decimal("1000.00"))
        user = _make_user()

        def _try_add(_):
            try:
                BudgetService.add_execution(
                    line=line,
                    amount=Decimal("700.00"),
                    executed_at=datetime.date(2026, 7, 1),
                    user=user,
                )
                return "ok"
            except ValidationError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(_try_add, range(2)))

        from apps.budgets.models import BudgetExecution

        total = (
            BudgetExecution.objects.filter(line=line).aggregate(total=Sum("amount"))[
                "total"
            ]
            or Decimal("0.00")
        )
        assert results.count("ok") <= 1
        assert total <= line.approved_amount