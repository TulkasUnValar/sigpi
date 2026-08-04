"""
DRF ModelSerializers for the progress (advances) module.

Provides 6 serializers implementing the API contract from spec.md:
- ProgressReportListSerializer — lightweight list (7 fields)
- ProgressReportSerializer — full detail with nested documents, reviews,
  state_logs (read-only)
- ProgressReportCreateSerializer — writable fields; institution + created_by
  injected by view
- ProgressDocumentSerializer — document CRUD; progress_report read-only
- ProgressReviewSerializer — read-only review data (RN-P05)
- ProgressStateLogSerializer — read-only state history data (RN-P05)

Design decisions (from design.md):
- Nested serializers on ProgressReportSerializer are read-only
- institution is read-only on ProgressReportCreateSerializer (set by view)
- created_by is read-only on all serializers (set by view)
- progress_report FK is read-only on document/review/state_log serializers
- Reviews and state logs are append-only — no update/delete (RN-P05)

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md
"""
from rest_framework import serializers

from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)

# ──────────────────────────────────────────────────────────
# ProgressReportListSerializer
# ──────────────────────────────────────────────────────────


class ProgressReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for progress report list views.

    Exposes only 7 fields: id, project, status, cumulative_percentage,
    period_start, period_end, created_at.
    """

    class Meta:
        model = ProgressReport
        fields = [
            "id",
            "project",
            "status",
            "cumulative_percentage",
            "period_start",
            "period_end",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ProgressReportSerializer (full detail)
# ──────────────────────────────────────────────────────────


class ProgressReportSerializer(serializers.ModelSerializer):
    """Full-detail serializer with nested documents, reviews, and state_logs.

    Nested data is read-only — mutations go through dedicated
    nested endpoints (/documents/, /reviews/, /state_history/).
    """

    documents = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    state_logs = serializers.SerializerMethodField()

    class Meta:
        model = ProgressReport
        fields = [
            "id",
            "institution",
            "project",
            "created_by",
            "period_start",
            "period_end",
            "description",
            "cumulative_percentage",
            "activities",
            "difficulties",
            "next_steps",
            "status",
            "created_at",
            "updated_at",
            "documents",
            "reviews",
            "state_logs",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_documents(self, obj):
        """Return nested documents — read-only."""
        documents = obj.documents.all()
        return ProgressDocumentSerializer(documents, many=True).data

    def get_reviews(self, obj):
        """Return nested reviews — read-only."""
        reviews = obj.reviews.all()
        return ProgressReviewSerializer(reviews, many=True).data

    def get_state_logs(self, obj):
        """Return nested state logs — read-only."""
        logs = obj.state_logs.all()
        return ProgressStateLogSerializer(logs, many=True).data


# ──────────────────────────────────────────────────────────
# ProgressReportCreateSerializer
# ──────────────────────────────────────────────────────────


class ProgressReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating ProgressReport instances.

    Only writable fields are exposed. institution, created_by, and
    status are read-only (set by the view or FSM).
    No nested writes — documents are managed through dedicated
    nested endpoints.
    """

    class Meta:
        model = ProgressReport
        fields = [
            "id",
            "institution",
            "project",
            "created_by",
            "period_start",
            "period_end",
            "description",
            "cumulative_percentage",
            "activities",
            "difficulties",
            "next_steps",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "created_by",
            "status",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# ProgressDocumentSerializer
# ──────────────────────────────────────────────────────────


class ProgressDocumentSerializer(serializers.ModelSerializer):
    """Serializer for ProgressDocument CRUD.

    progress_report FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = ProgressDocument
        fields = [
            "id",
            "progress_report",
            "name",
            "doc_type",
            "external_url",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "progress_report",
            "uploaded_at",
        ]


# ──────────────────────────────────────────────────────────
# ProgressReviewSerializer (read-only — RN-P05)
# ──────────────────────────────────────────────────────────


class ProgressReviewSerializer(serializers.ModelSerializer):
    """Read-only serializer for ProgressReview (RN-P05).

    All fields are read-only — reviews are append-only,
    created via the observe()/reject() transitions in ProgressService.
    No create/update/delete endpoints exposed.
    """

    class Meta:
        model = ProgressReview
        fields = [
            "id",
            "progress_report",
            "reviewed_by",
            "review_text",
            "review_type",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "progress_report",
            "reviewed_by",
            "review_text",
            "review_type",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ProgressStateLogSerializer (read-only — RN-P04)
# ──────────────────────────────────────────────────────────


class ProgressStateLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for ProgressStateLog (RN-P04).

    All fields are read-only — state logs are append-only,
    created via the _log_transition() private method in ProgressService.
    No create/update/delete endpoints exposed.
    """

    class Meta:
        model = ProgressStateLog
        fields = [
            "id",
            "progress_report",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "progress_report",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
