"""
DRF ModelSerializers for the calls module (Phase 3.1).

Provides 6 serializers implementing the API contract from spec.md:
- CallListSerializer — lightweight list (5 fields)
- CallSerializer — full detail with nested dates validation (read + write)
- CallDocumentSerializer — name, doc_type, external_url; call read-only
- CallProjectSerializer — read-only list of linked projects
- CallProjectCreateSerializer — writable, project FK only, call read-only
- CallStateLogSerializer — read-only state history data

Design decisions (from design.md):
- Nested serializers on CallSerializer are read-only
- institution is read-only on CallSerializer (set by view)
- call FK is read-only on child serializers (set by view from URL)
- State logs are append-only — no update/delete (mirrors projects)

Spec reference: openspec/changes/calls/spec.md — API Contract
Design reference: openspec/changes/calls/design.md — Serializer Mapping
"""

from rest_framework import serializers

from apps.calls.models import (
    Call,
    CallDocument,
    CallProject,
    CallStateLog,
    CallType,
)

# ──────────────────────────────────────────────────────────
# CallListSerializer
# ──────────────────────────────────────────────────────────


class CallListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for call list views.

    Exposes only 5 fields: id, title, status, call_type, created_at.
    """

    class Meta:
        model = Call
        fields = [
            "id",
            "title",
            "status",
            "call_type",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# CallSerializer (full detail + write)
# ──────────────────────────────────────────────────────────


class CallSerializer(serializers.ModelSerializer):
    """Full-detail serializer for Call with nested dates validation.

    Handles both read and write operations. Validates type/entity
    rules and date ordering at the serializer level so that
    `is_valid()` catches violations before save().
    """

    class Meta:
        model = Call
        fields = [
            "id",
            "institution",
            "title",
            "description",
            "call_type",
            "external_entity",
            "submission_start",
            "submission_end",
            "evaluation_start",
            "evaluation_end",
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

    def validate(self, data):
        """Cross-field validation: type/entity rules and date ordering."""
        call_type = data.get("call_type")
        external_entity = data.get("external_entity", "")

        if call_type == CallType.INTERNAL and external_entity:
            raise serializers.ValidationError(
                {"external_entity": ["Internal calls must not have an external entity."]}
            )
        if call_type == CallType.EXTERNAL and not external_entity:
            raise serializers.ValidationError(
                {"external_entity": ["External entity is required for external calls."]}
            )

        submission_start = data.get("submission_start")
        submission_end = data.get("submission_end")
        if submission_start and submission_end and submission_end < submission_start:
            raise serializers.ValidationError(
                {"submission_end": ["Submission end must be on or after submission start."]}
            )

        evaluation_start = data.get("evaluation_start")
        evaluation_end = data.get("evaluation_end")
        if evaluation_start and evaluation_end and evaluation_end < evaluation_start:
            raise serializers.ValidationError(
                {"evaluation_end": ["Evaluation end must be on or after evaluation start."]}
            )

        return data


# ──────────────────────────────────────────────────────────
# CallDocumentSerializer
# ──────────────────────────────────────────────────────────


class CallDocumentSerializer(serializers.ModelSerializer):
    """Serializer for CallDocument CRUD.

    call FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = CallDocument
        fields = [
            "id",
            "call",
            "name",
            "doc_type",
            "external_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "call",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# CallProjectSerializer
# ──────────────────────────────────────────────────────────


class CallProjectSerializer(serializers.ModelSerializer):
    """Read-only serializer for CallProject list views."""

    class Meta:
        model = CallProject
        fields = [
            "id",
            "call",
            "project",
            "linked_at",
        ]
        read_only_fields = [
            "id",
            "call",
            "project",
            "linked_at",
        ]


# ──────────────────────────────────────────────────────────
# CallProjectCreateSerializer
# ──────────────────────────────────────────────────────────


class CallProjectCreateSerializer(serializers.ModelSerializer):
    """Writable serializer for creating CallProject links.

    call FK is read-only — set by the view from the URL path.
    project FK is writable.
    """

    class Meta:
        model = CallProject
        fields = [
            "id",
            "call",
            "project",
            "linked_at",
        ]
        read_only_fields = [
            "id",
            "call",
            "linked_at",
        ]


# ──────────────────────────────────────────────────────────
# CallStateLogSerializer
# ──────────────────────────────────────────────────────────


class CallStateLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for CallStateLog.

    All fields are read-only — state logs are append-only,
    created via the _log_transition() private method in CallService.
    No create/update/delete endpoints exposed.
    """

    class Meta:
        model = CallStateLog
        fields = [
            "id",
            "call",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "call",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
