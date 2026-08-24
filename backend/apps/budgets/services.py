"""
Service layer for budgets — business logic + audit orchestration.

BudgetService: atomic create/update/delete and execution writes, with
RN-020 enforcement (sum of executions per line ≤ approved unless authorized)
and BUDGET_* audit events via AuditEventEmitter.
BudgetSummaryService: aggregates approved/executed/balance per budget.

Views never bypass this service — all mutations go through it inside a
transaction, locking/rechecking the line before summing executions.

Design reference: openspec/changes/budgets/design.md — Services, Audit and Reports
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md — RF-B01/B04/B07
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum

from apps.accounts.audit import AuditEventEmitter
from apps.budgets.models import (
    Budget,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
)

ZERO = Decimal("0.00")


class DuplicateBudgetError(ValidationError):
    """Raised when a project already has a budget (RF-B01 → HTTP 409)."""


# ──────────────────────────────────────────────
# BudgetService
# ──────────────────────────────────────────────


class BudgetService:
    """Owns budget mutation, authorization, and audit inside transactions."""

    @staticmethod
    def create(institution, user, project, name, approved_amount, status=None, **kwargs):
        """Create a Budget (OneToOne per project).

        Raises ValidationError if the project already has a budget.
        Emits BUDGET_CREATED.
        """
        with transaction.atomic():
            if Budget.objects.filter(project=project).exists():
                raise DuplicateBudgetError("Project already has a budget.")

            budget = Budget(
                institution=institution,
                project=project,
                name=name,
                approved_amount=approved_amount,
                status=status or BudgetStatus.DRAFT,
            )
            try:
                budget.full_clean()
                budget.save()
            except IntegrityError:
                raise DuplicateBudgetError("Project already has a budget.")

            AuditEventEmitter().emit(
                event_type="BUDGET_CREATED",
                user=user,
                institution_id=institution.id,
                details={
                    "budget_id": str(budget.pk),
                    "project_id": str(project.pk),
                    "name": name,
                    "approved_amount": str(approved_amount),
                },
            )
            return budget

    @staticmethod
    def update(budget, user, **data):
        """Update budget fields. Emits BUDGET_UPDATED."""
        with transaction.atomic():
            for field, value in data.items():
                setattr(budget, field, value)
            budget.full_clean()
            budget.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_UPDATED",
                user=user,
                institution_id=budget.institution_id,
                details={
                    "budget_id": str(budget.pk),
                    "name": budget.name,
                    "approved_amount": str(budget.approved_amount),
                },
            )
            return budget

    @staticmethod
    def delete(budget, user):
        """Delete a budget. Parent cascade removes lines, executions, attachments."""
        with transaction.atomic():
            budget.delete()

    @staticmethod
    def add_execution(
        line,
        amount,
        executed_at,
        user=None,
        authorized_by=None,
        authorized_at=None,
    ):
        """Record a line-level execution enforcing RN-020.

        Locks the line (select_for_update), rechecks the cumulative sum,
        and rejects over-execution unless both authorization fields are set.
        Emits BUDGET_EXECUTION_ADDED.
        """
        with transaction.atomic():
            locked_line = BudgetLine.objects.select_for_update().get(pk=line.pk)
            current_sum = (
                BudgetExecution.objects.filter(line=locked_line).aggregate(
                    total=Sum("amount")
                )["total"]
                or ZERO
            )

            overrun = (current_sum + amount) > locked_line.approved_amount
            if overrun:
                if not (authorized_by and authorized_at):
                    raise ValidationError(
                        "Execution exceeds the line's approved amount and requires authorization."
                    )

            execution = BudgetExecution(
                line=locked_line,
                amount=amount,
                executed_at=executed_at,
                authorized_by=authorized_by,
                authorized_at=authorized_at,
            )
            execution.full_clean()
            execution.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_EXECUTION_ADDED",
                user=user,
                institution_id=locked_line.budget.institution_id,
                details={
                    "line_id": str(locked_line.pk),
                    "line_name": locked_line.name,
                    "budget_id": str(locked_line.budget_id),
                    "amount": str(amount),
                    "executed_at": executed_at.isoformat(),
                    "authorized_by": (
                        str(authorized_by.pk) if authorized_by else None
                    ),
                },
            )
            return execution


# ──────────────────────────────────────────────
# BudgetSummaryService
# ──────────────────────────────────────────────


class BudgetSummaryService:
    """Aggregates approved/executed/balance for a budget or project."""

    @staticmethod
    def for_budget(project):
        """Return {approved, executed, balance} for a project's budget.

        Returns None when the project has no registered budget.
        executed is the aggregate of all line executions; balance is
        approved minus executed.
        """
        try:
            budget = Budget.objects.select_related("project").get(project=project)
        except Budget.DoesNotExist:
            return None

        executed = (
            BudgetExecution.objects.filter(line__budget=budget).aggregate(
                total=Sum("amount")
            )["total"]
            or ZERO
        )
        balance = budget.approved_amount - executed

        return {
            "approved": budget.approved_amount,
            "executed": executed,
            "balance": balance,
        }
