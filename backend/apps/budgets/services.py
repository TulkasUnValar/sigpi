"""
Service layer for budgets — business logic + audit orchestration.

BudgetService: atomic create/update/delete and execution writes, with
RN-020 enforcement (sum of executions per line ≤ approved unless authorized)
and BUDGET_* audit events via AuditEventEmitter.
BudgetLineService: atomic CRUD for BudgetLine with BUDGET_LINE_* audit events.
BudgetAttachmentService: atomic CRUD for BudgetAttachment (metadata-only)
with BUDGET_ATTACHMENT_* audit events.
FundingSourceService: atomic CRUD for FundingSource with FUNDING_SOURCE_*
audit events.
BudgetSummaryService: aggregates approved/executed/balance per budget.

Views never bypass this service — all mutations go through it inside a
transaction, locking/rechecking the line before summing executions.

Design reference: openspec/changes/budgets/design.md — Services, Audit and Reports
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md — RF-B01/B04/B07
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum

from apps.accounts.audit import AuditEventEmitter
from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
    FundingSource,
)
from apps.budgets.signals import budget_overrun_attempted

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")


class DuplicateBudgetError(ValidationError):
    """Raised when a project already has a budget (RF-B01 → HTTP 409)."""


class _UnauthorizedOverrunError(ValidationError):
    """Internal marker: over-limit execution rejected without authorization.

    Carries the rejected attempt out of the atomic block so the
    budget_overrun_attempted signal (RN-4) can be emitted AFTER the
    block — a Notification insert inside the block would be rolled
    back together with the rejected execution.
    """

    def __init__(self, line, amount, user):
        self.line = line
        self.amount = amount
        self.user = user
        super().__init__("Execution exceeds the line's approved amount and requires authorization.")


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
        Emits BUDGET_EXECUTION_ADDED; a rejected unauthorized overrun also
        emits budget_overrun_attempted (RN-4) before re-raising.
        """
        try:
            with transaction.atomic():
                locked_line = BudgetLine.objects.select_for_update().get(pk=line.pk)
                current_sum = (
                    BudgetExecution.objects.filter(line=locked_line).aggregate(total=Sum("amount"))[
                        "total"
                    ]
                    or ZERO
                )

                overrun = (current_sum + amount) > locked_line.approved_amount
                if overrun:
                    if not (authorized_by and authorized_at):
                        raise _UnauthorizedOverrunError(locked_line, amount, user)

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
                        "authorized_by": (str(authorized_by.pk) if authorized_by else None),
                    },
                )
                return execution
        except _UnauthorizedOverrunError as exc:
            try:
                budget_overrun_attempted.send(
                    sender=BudgetExecution,
                    instance=exc.line,
                    budget_line=exc.line,
                    attempted_amount=exc.amount,
                    approved_amount=exc.line.approved_amount,
                    requested_by=exc.user,
                    institution=exc.line.budget.institution,
                )
            except Exception:  # pragma: no cover — receivers must never raise
                logger.exception("budget_overrun_attempted receiver failed")
            raise


# ──────────────────────────────────────────────
# BudgetLineService
# ──────────────────────────────────────────────


class BudgetLineService:
    """Owns BudgetLine mutation and audit inside transactions."""

    @staticmethod
    def create(budget, user, name, approved_amount):
        """Create a BudgetLine under a budget. Emits BUDGET_LINE_CREATED."""
        with transaction.atomic():
            line = BudgetLine(
                budget=budget,
                name=name,
                approved_amount=approved_amount,
            )
            line.full_clean()
            line.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_LINE_CREATED",
                user=user,
                institution_id=budget.institution_id,
                details={
                    "line_id": str(line.pk),
                    "budget_id": str(budget.pk),
                    "name": name,
                    "approved_amount": str(approved_amount),
                },
            )
            return line

    @staticmethod
    def update(line, user, **data):
        """Update line fields. Emits BUDGET_LINE_UPDATED."""
        with transaction.atomic():
            for field, value in data.items():
                setattr(line, field, value)
            line.full_clean()
            line.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_LINE_UPDATED",
                user=user,
                institution_id=line.budget.institution_id,
                details={
                    "line_id": str(line.pk),
                    "budget_id": str(line.budget_id),
                    "name": line.name,
                    "approved_amount": str(line.approved_amount),
                },
            )
            return line

    @staticmethod
    def delete(line, user):
        """Delete a line (cascade removes its executions). Emits BUDGET_LINE_DELETED."""
        with transaction.atomic():
            line_id = str(line.pk)
            budget_id = str(line.budget_id)
            institution_id = line.budget.institution_id
            name = line.name
            line.delete()

            AuditEventEmitter().emit(
                event_type="BUDGET_LINE_DELETED",
                user=user,
                institution_id=institution_id,
                details={
                    "line_id": line_id,
                    "budget_id": budget_id,
                    "name": name,
                },
            )


# ──────────────────────────────────────────────
# BudgetAttachmentService
# ──────────────────────────────────────────────


class BudgetAttachmentService:
    """Owns BudgetAttachment (metadata-only) mutation and audit."""

    @staticmethod
    def create(budget, user, name, doc_type, external_url):
        """Create a metadata-only attachment. Emits BUDGET_ATTACHMENT_CREATED."""
        with transaction.atomic():
            attachment = BudgetAttachment(
                budget=budget,
                name=name,
                doc_type=doc_type,
                external_url=external_url,
            )
            attachment.full_clean()
            attachment.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_ATTACHMENT_CREATED",
                user=user,
                institution_id=budget.institution_id,
                details={
                    "attachment_id": str(attachment.pk),
                    "budget_id": str(budget.pk),
                    "name": name,
                    "doc_type": doc_type,
                },
            )
            return attachment

    @staticmethod
    def update(attachment, user, **data):
        """Update attachment fields. Emits BUDGET_ATTACHMENT_UPDATED."""
        with transaction.atomic():
            for field, value in data.items():
                setattr(attachment, field, value)
            attachment.full_clean()
            attachment.save()

            AuditEventEmitter().emit(
                event_type="BUDGET_ATTACHMENT_UPDATED",
                user=user,
                institution_id=attachment.budget.institution_id,
                details={
                    "attachment_id": str(attachment.pk),
                    "budget_id": str(attachment.budget_id),
                    "name": attachment.name,
                    "doc_type": attachment.doc_type,
                },
            )
            return attachment

    @staticmethod
    def delete(attachment, user):
        """Delete an attachment. Emits BUDGET_ATTACHMENT_DELETED."""
        with transaction.atomic():
            attachment_id = str(attachment.pk)
            budget_id = str(attachment.budget_id)
            institution_id = attachment.budget.institution_id
            name = attachment.name
            doc_type = attachment.doc_type
            attachment.delete()

            AuditEventEmitter().emit(
                event_type="BUDGET_ATTACHMENT_DELETED",
                user=user,
                institution_id=institution_id,
                details={
                    "attachment_id": attachment_id,
                    "budget_id": budget_id,
                    "name": name,
                    "doc_type": doc_type,
                },
            )


# ──────────────────────────────────────────────
# FundingSourceService
# ──────────────────────────────────────────────


class FundingSourceService:
    """Owns FundingSource mutation and audit inside transactions."""

    @staticmethod
    def create(project, user, name, amount):
        """Create a funding source (multiple per project, RN-019).

        Emits FUNDING_SOURCE_CREATED.
        """
        with transaction.atomic():
            source = FundingSource(
                project=project,
                name=name,
                amount=amount,
            )
            source.full_clean()
            source.save()

            AuditEventEmitter().emit(
                event_type="FUNDING_SOURCE_CREATED",
                user=user,
                institution_id=project.institution_id,
                details={
                    "source_id": str(source.pk),
                    "project_id": str(project.pk),
                    "name": name,
                    "amount": str(amount),
                },
            )
            return source

    @staticmethod
    def update(source, user, **data):
        """Update source fields. Emits FUNDING_SOURCE_UPDATED."""
        with transaction.atomic():
            for field, value in data.items():
                setattr(source, field, value)
            source.full_clean()
            source.save()

            AuditEventEmitter().emit(
                event_type="FUNDING_SOURCE_UPDATED",
                user=user,
                institution_id=source.project.institution_id,
                details={
                    "source_id": str(source.pk),
                    "project_id": str(source.project_id),
                    "name": source.name,
                    "amount": str(source.amount),
                },
            )
            return source

    @staticmethod
    def delete(source, user):
        """Delete a funding source. Emits FUNDING_SOURCE_DELETED."""
        with transaction.atomic():
            source_id = str(source.pk)
            project_id = str(source.project_id)
            institution_id = source.project.institution_id
            name = source.name
            amount = source.amount
            source.delete()

            AuditEventEmitter().emit(
                event_type="FUNDING_SOURCE_DELETED",
                user=user,
                institution_id=institution_id,
                details={
                    "source_id": source_id,
                    "project_id": project_id,
                    "name": name,
                    "amount": str(amount),
                },
            )


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
            BudgetExecution.objects.filter(line__budget=budget).aggregate(total=Sum("amount"))[
                "total"
            ]
            or ZERO
        )
        balance = budget.approved_amount - executed

        return {
            "approved": budget.approved_amount,
            "executed": executed,
            "balance": balance,
        }
