"""
DRF serializers for the notifications module (PR 4).

Provides the API contract serializers from design.md / orchestrator spec:
- NotificationSerializer — full read-only view of a Notification row
- NotificationSummarySerializer — lightweight list payload
- UserPreferenceSerializer — per-user channel opt-out (channel/enabled writable)

Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
Spec reference:   openspec/changes/notifications/spec.md — Data Model
"""

from rest_framework import serializers

from apps.notifications.models import Notification, UserPreference

# ──────────────────────────────────────────────
# NotificationSerializer
# ──────────────────────────────────────────────


class NotificationSerializer(serializers.ModelSerializer):
    """Full read-only Notification payload.

    Notification rows are created ONLY by signal receivers — the API never
    writes them (spec API Contract: write endpoints limited to read-state
    mutations).
    """

    class Meta:
        model = Notification
        fields = [
            "id",
            "institution",
            "recipient",
            "event_type",
            "template",
            "title",
            "body",
            "context",
            "entity_type",
            "entity_id",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────
# NotificationSummarySerializer
# ──────────────────────────────────────────────


class NotificationSummarySerializer(serializers.ModelSerializer):
    """Lightweight list payload for the notifications list endpoint."""

    class Meta:
        model = Notification
        fields = ["id", "title", "is_read", "created_at", "entity_type"]
        read_only_fields = fields


# ──────────────────────────────────────────────
# UserPreferenceSerializer
# ──────────────────────────────────────────────


class UserPreferenceSerializer(serializers.ModelSerializer):
    """User channel preference — channel/enabled are the only writable fields.

    The user FK is locked to the caller by the viewset queryset
    (user == request.user), so it is exposed read-only.
    """

    class Meta:
        model = UserPreference
        fields = ["id", "user", "channel", "enabled", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
