"""
DRF serializers for the audit read API (PR 3).

Provides the API contract serializers from design.md:
- AuditLogSerializer — full read-only representation of an AuditEvent.
- AuditLogSummarySerializer — lightweight row (id, event_type, action,
  entity_type, timestamp, user) for compact list payloads.

Design reference: openspec/changes/audit/design.md — Interfaces/Contracts
Spec reference:   openspec/changes/audit/specs/audit/spec.md — API Contract
"""

from rest_framework import serializers

from apps.accounts.audit import AuditEvent
from apps.accounts.models import User

# ──────────────────────────────────────────────
# User (embedded actor)
# ──────────────────────────────────────────────


class AuditUserSerializer(serializers.ModelSerializer):
    """Minimal read-only actor representation embedded in audit rows."""

    class Meta:
        model = User
        fields = ["id", "email"]
        read_only_fields = ["id", "email"]


# ──────────────────────────────────────────────
# AuditEvent serializers
# ──────────────────────────────────────────────


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only, all AuditEvent fields."""

    user = AuditUserSerializer(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "user",
            "event_type",
            "timestamp",
            "ip_address",
            "institution_id",
            "details",
            "entity_type",
            "entity_id",
            "action",
            "old_values",
            "new_values",
            "project_id",
        ]
        read_only_fields = fields


class AuditLogSummarySerializer(serializers.ModelSerializer):
    """Lightweight read-only audit row."""

    user = AuditUserSerializer(read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "event_type",
            "action",
            "entity_type",
            "timestamp",
            "user",
        ]
        read_only_fields = fields
