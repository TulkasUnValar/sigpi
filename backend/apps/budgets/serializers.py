"""
DRF ModelSerializers for the budgets module (Phase 2.1).

Provides 6 serializers implementing the API contract from spec.md:
- BudgetSerializer — full detail with read-only parent/tenant + nested
  read-only lines and attachments.
- BudgetLineSerializer — name, approved_amount; budget FK read-only.
- FundingSourceSerializer — name, amount; project FK read-only.
- BudgetExecutionSerializer — amount, executed_at + authorization fields;
  line FK read-only.
- BudgetAttachmentSerializer — name, doc_type, required external_url;
  budget FK read-only.

Design decisions (from design.md):
- Parent (project/budget/line) and tenant (institution) FKs are read-only
  and set by the view from the URL path or active membership.
- BudgetSerializer nests lines and attachments as read-only.
- Money fields remain Decimal(14,2); negative values are rejected at the API
  boundary via each serializer's min_value=Decimal("0.00").

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — API Contract
Design reference: openspec/changes/budgets/design.md — Serializer Mapping
"""

from decimal import Decimal

from rest_framework import serializers

from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    FundingSource,
)
from apps.projects.models import Project

# ──────────────────────────────────────────────────────────
# BudgetAttachmentSerializer (referenced by BudgetSerializer)
# ──────────────────────────────────────────────────────────


class BudgetAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for BudgetAttachment CRUD.

    budget FK is read-only — set by the view from the URL path.
    external_url is required (RF-B05 metadata-only attachment).
    """

    class Meta:
        model = BudgetAttachment
        fields = [
            "id",
            "budget",
            "name",
            "doc_type",
            "external_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "budget",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# BudgetLineSerializer (referenced by BudgetSerializer)
# ──────────────────────────────────────────────────────────


class BudgetLineSerializer(serializers.ModelSerializer):
    """Serializer for BudgetLine CRUD.

    budget FK is read-only — set by the view from the URL path.
    """

    approved_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00")
    )

    class Meta:
        model = BudgetLine
        fields = [
            "id",
            "budget",
            "name",
            "approved_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "budget",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# FundingSourceSerializer
# ──────────────────────────────────────────────────────────


class FundingSourceSerializer(serializers.ModelSerializer):
    """Serializer for FundingSource CRUD.

    project FK is read-only — set by the view from the URL path.
    """

    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))

    class Meta:
        model = FundingSource
        fields = [
            "id",
            "project",
            "name",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# BudgetExecutionSerializer
# ──────────────────────────────────────────────────────────


class BudgetExecutionSerializer(serializers.ModelSerializer):
    """Serializer for BudgetExecution.

    line FK is read-only — set by the view from the URL path.
    authorized_by / authorized_at are writable for authorized over-execution
    (RN-020); validation of the authorization pair happens in the service.
    """

    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.00"))

    class Meta:
        model = BudgetExecution
        fields = [
            "id",
            "line",
            "amount",
            "executed_at",
            "authorized_by",
            "authorized_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "line",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# BudgetSerializer
# ──────────────────────────────────────────────────────────


class BudgetSerializer(serializers.ModelSerializer):
    """Full-detail serializer for Budget.

    project (parent) and institution (tenant) are read-only — set by the
    view from the active membership / resolved parent. Nested lines and
    attachments are read-only collections.
    """

    lines = BudgetLineSerializer(many=True, read_only=True)
    attachments = BudgetAttachmentSerializer(many=True, read_only=True)

    approved_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00")
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "project",
            "institution",
            "name",
            "approved_amount",
            "status",
            "lines",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]


class BudgetCreateSerializer(serializers.ModelSerializer):
    """Writable serializer for creating a Budget.

    project (parent) is writable here — the client selects which project
    the budget belongs to. institution and status remain read-only and are
    set by the service (institution from active membership; status=draft).

    The project field is declared explicitly so DRF does NOT auto-add a
    UniqueValidator (OneToOne unique constraint). Duplicate detection is
    handled by BudgetService → HTTP 409 (RF-B01), not a serializer 400.
    """

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    approved_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.00")
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "project",
            "institution",
            "name",
            "approved_amount",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]
