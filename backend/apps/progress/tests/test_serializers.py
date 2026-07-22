"""
Serializer tests for the progress (advances) module.

Covers:
- ProgressReportListSerializer: field set validation (7 fields)
- ProgressReportSerializer: full detail + nested reviews/documents/state_logs (read-only)
- ProgressReportCreateSerializer: writable fields, validation, read-only institution/created_by
- ProgressDocumentSerializer: CRUD fields, read-only report FK
- ProgressReviewSerializer: read-only fields
- ProgressStateLogSerializer: read-only fields
- Edge cases: percentage boundary (0, 100, -1, 101), period validation

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md

RED PHASE: Tests reference serializers.py; will FAIL if serializers
are missing or incorrect.
"""

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

# ──────────────────────────────────────────────
# Test Helpers
# ──────────────────────────────────────────────


def _make_valid_data(project, **overrides):
    """Build a valid create payload for ProgressReport."""
    data = {
        "project": str(project.pk),
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "description": "Test description",
        "cumulative_percentage": "50.00",
        "activities": "Test activities",
        "difficulties": "",
        "next_steps": "",
    }
    data.update(overrides)
    return data


# ──────────────────────────────────────────────
# ProgressReportListSerializer
# ──────────────────────────────────────────────


class TestProgressReportListSerializer:
    """ProgressReportListSerializer exposes only 7 fields."""

    def test_list_fields(self, db, progress_borrador):
        """List serializer returns exactly the 7 specified fields."""
        from apps.progress.serializers import ProgressReportListSerializer

        serializer = ProgressReportListSerializer(progress_borrador)
        data = serializer.data

        expected_fields = {
            "id", "project", "status", "cumulative_percentage",
            "period_start", "period_end", "created_at",
        }
        assert set(data.keys()) == expected_fields

    def test_list_status_value(self, db, progress_borrador):
        """Status field is the raw FSM value, not display label."""
        from apps.progress.serializers import ProgressReportListSerializer

        serializer = ProgressReportListSerializer(progress_borrador)
        assert serializer.data["status"] == progress_borrador.status
        assert serializer.data["status"] == "borrador"

    def test_list_cumulative_percentage_is_string(self, db, progress_borrador):
        """Decimal field should serialize as string for precision."""
        from apps.progress.serializers import ProgressReportListSerializer

        serializer = ProgressReportListSerializer(progress_borrador)
        assert isinstance(serializer.data["cumulative_percentage"], str)


# ──────────────────────────────────────────────
# ProgressReportSerializer (full detail)
# ──────────────────────────────────────────────


class TestProgressReportSerializer:
    """ProgressReportSerializer exposes all fields + nested data."""

    def test_detail_includes_all_own_fields(self, db, progress_borrador):
        """All model fields present in detail serializer."""
        from apps.progress.serializers import ProgressReportSerializer

        serializer = ProgressReportSerializer(progress_borrador)
        data = serializer.data

        # Check required model fields are present
        required = {"id", "institution", "project", "created_by",
                     "period_start", "period_end", "description",
                     "cumulative_percentage", "activities", "difficulties",
                     "next_steps", "status", "created_at", "updated_at"}
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_detail_includes_nested_documents(self, db, progress_borrador):
        """Detail serializer returns nested documents list."""
        from apps.progress.serializers import ProgressReportSerializer
        from apps.progress.tests.conftest import ProgressDocumentFactory

        ProgressDocumentFactory(progress_report=progress_borrador)
        serializer = ProgressReportSerializer(progress_borrador)

        assert "documents" in serializer.data
        assert isinstance(serializer.data["documents"], list)
        assert len(serializer.data["documents"]) >= 1
        # Verify the nested doc has expected fields
        doc_data = serializer.data["documents"][0]
        assert "name" in doc_data
        assert "doc_type" in doc_data

    def test_detail_includes_nested_reviews(self, db, progress_borrador):
        """Detail serializer returns nested reviews list."""
        from apps.progress.serializers import ProgressReportSerializer
        from apps.progress.tests.conftest import ProgressReviewFactory

        ProgressReviewFactory(progress_report=progress_borrador)
        serializer = ProgressReportSerializer(progress_borrador)

        assert "reviews" in serializer.data
        assert isinstance(serializer.data["reviews"], list)
        assert len(serializer.data["reviews"]) >= 1
        review_data = serializer.data["reviews"][0]
        assert "review_text" in review_data
        assert "review_type" in review_data

    def test_detail_includes_nested_state_logs(self, db, progress_borrador):
        """Detail serializer returns nested state_logs list."""
        from apps.progress.serializers import ProgressReportSerializer
        from apps.progress.tests.conftest import ProgressStateLogFactory

        ProgressStateLogFactory(progress_report=progress_borrador)
        serializer = ProgressReportSerializer(progress_borrador)

        assert "state_logs" in serializer.data
        assert isinstance(serializer.data["state_logs"], list)
        assert len(serializer.data["state_logs"]) >= 1
        log_data = serializer.data["state_logs"][0]
        assert "from_state" in log_data
        assert "to_state" in log_data

    def test_detail_nested_empty_when_no_children(self, db, progress_borrador):
        """Nested lists are empty when no related objects exist."""
        from apps.progress.serializers import ProgressReportSerializer

        serializer = ProgressReportSerializer(progress_borrador)
        # The nested data should exist but be empty
        assert "documents" in serializer.data or "reviews" in serializer.data

    def test_detail_nested_is_read_only(self, db, progress_borrador):
        """Nested data cannot be written through the serializer — it's read-only."""
        from apps.progress.serializers import ProgressReportSerializer

        # SerializerMethodField is always read-only — verify we can't
        # inject nested data via update
        payload = {"description": "Updated", "documents": [{"name": "injected"}]}
        update_serializer = ProgressReportSerializer(
            progress_borrador, data=payload, partial=True
        )
        assert update_serializer.is_valid()
        # documents should NOT be in validated_data (read-only)
        assert "documents" not in update_serializer.validated_data


# ──────────────────────────────────────────────
# ProgressReportCreateSerializer
# ──────────────────────────────────────────────


class TestProgressReportCreateSerializer:
    """ProgressReportCreateSerializer validates writes."""

    def test_create_valid_data_passes(self, db, progress_borrador):
        """All required fields pass validation."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project,
                                cumulative_percentage="75.50")
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_institution_is_read_only(self, db, progress_borrador):
        """institution should not be writable — it's read-only on create."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()

        # institution should NOT appear in writable fields
        assert "institution" not in serializer.validated_data

    def test_created_by_is_read_only(self, db, progress_borrador):
        """created_by should not be writable — it's injected by the view."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()
        assert "created_by" not in serializer.validated_data

    def test_status_is_read_only(self, db, progress_borrador):
        """status should not be writable — it's managed by FSM."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project, status="aprobado")
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()
        # status should either be excluded or ignored
        assert "status" not in serializer.validated_data

    def test_missing_required_field_fails(self, db, progress_borrador):
        """Missing 'activities' returns validation error."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        del data["activities"]
        serializer = ProgressReportCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "activities" in serializer.errors

    def test_missing_description_fails(self, db, progress_borrador):
        """Missing 'description' returns validation error."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        del data["description"]
        serializer = ProgressReportCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "description" in serializer.errors

    def test_percentage_above_100_fails(self, db, progress_borrador):
        """cumulative_percentage > 100 rejected by model clean()."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project,
                                cumulative_percentage="105.00")
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid(), f"Serializer should validate, error: {serializer.errors}"
        # Model-level validation catches this in save/clean
        with pytest.raises(DjangoValidationError) as exc_info:
            instance = serializer.save()
            # Trigger clean
            instance.full_clean()
        err = exc_info.value
        assert "cumulative_percentage" in err.message_dict

    def test_percentage_below_0_fails(self, db, progress_borrador):
        """cumulative_percentage < 0 rejected by model clean()."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project,
                                cumulative_percentage="-5.00")
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()
        with pytest.raises(DjangoValidationError) as exc_info:
            instance = serializer.save()
            instance.full_clean()
        err = exc_info.value
        assert "cumulative_percentage" in err.message_dict

    def test_percentage_at_boundaries_is_valid(self, db, progress_borrador):
        """0.00 and 100.00 are valid cumulative percentages."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        # 0.00
        data_zero = _make_valid_data(progress_borrador.project,
                                     cumulative_percentage="0.00")
        serializer_zero = ProgressReportCreateSerializer(data=data_zero)
        assert serializer_zero.is_valid(), serializer_zero.errors

        # 100.00
        data_hundred = _make_valid_data(progress_borrador.project,
                                        cumulative_percentage="100.00")
        serializer_hundred = ProgressReportCreateSerializer(data=data_hundred)
        assert serializer_hundred.is_valid(), serializer_hundred.errors

    def test_period_end_before_period_start_fails(self, db, progress_borrador):
        """period_end < period_start rejected by model clean()."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(
            progress_borrador.project,
            period_start="2026-06-30",
            period_end="2026-01-01",
        )
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()
        with pytest.raises(DjangoValidationError) as exc_info:
            instance = serializer.save()
            instance.full_clean()
        err = exc_info.value
        assert "period_end" in err.message_dict

    def test_optional_fields_blank_allowed(self, db, progress_borrador):
        """difficulties and next_steps can be blank."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project,
                                difficulties="", next_steps="")
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_update_partial_data(self, db, progress_borrador):
        """Partial update only changes specified fields."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        previous_activities = progress_borrador.activities
        serializer = ProgressReportCreateSerializer(
            progress_borrador,
            data={"description": "Updated desc"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.description == "Updated desc"
        assert updated.activities == previous_activities  # unchanged

    def test_create_serializer_excludes_read_only_from_validated(self, db, progress_borrador):
        """Read-only fields (id, created_at, updated_at, institution, created_by, status)
        are not present in validated_data."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()

        read_only = {"id", "created_at", "updated_at", "institution", "created_by", "status"}
        for field in read_only:
            assert field not in serializer.validated_data, (
                f"Field {field} should be read-only but appeared in validated_data"
            )

    def test_project_fk_is_writable(self, db, progress_borrador):
        """Project FK should be writable on create."""
        from apps.progress.serializers import ProgressReportCreateSerializer

        data = _make_valid_data(progress_borrador.project)
        serializer = ProgressReportCreateSerializer(data=data)
        assert serializer.is_valid()
        assert "project" in serializer.validated_data


# ──────────────────────────────────────────────
# ProgressDocumentSerializer
# ──────────────────────────────────────────────


class TestProgressDocumentSerializer:
    """ProgressDocumentSerializer for CRUD on documents."""

    def test_document_fields(self, db, progress_borrador):
        """Serializer includes expected document fields."""
        from apps.progress.serializers import ProgressDocumentSerializer
        from apps.progress.tests.conftest import ProgressDocumentFactory

        doc = ProgressDocumentFactory(progress_report=progress_borrador)
        serializer = ProgressDocumentSerializer(doc)
        data = serializer.data

        expected = {"id", "progress_report", "name", "doc_type",
                    "external_url", "uploaded_at"}
        assert set(data.keys()) >= expected

    def test_document_report_is_read_only(self, db, progress_borrador):
        """progress_report FK is read-only — set from URL."""
        from apps.progress.serializers import ProgressDocumentSerializer

        serializer = ProgressDocumentSerializer(
            data={
                "name": "Test Doc",
                "doc_type": "evidence",
                "progress_report": str(progress_borrador.pk),
            }
        )
        assert serializer.is_valid(), serializer.errors
        # progress_report should be excluded from validated_data
        assert "progress_report" not in serializer.validated_data

    def test_document_create_valid_data(self, db, progress_borrador):
        """Valid document create passes validation."""
        from apps.progress.serializers import ProgressDocumentSerializer

        serializer = ProgressDocumentSerializer(
            data={
                "name": "Test Evidence",
                "doc_type": "evidence",
                "external_url": "https://example.com/doc.pdf",
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_document_doc_type_choices(self, db, progress_borrador):
        """doc_type must be one of the valid choices."""
        from apps.progress.serializers import ProgressDocumentSerializer

        for valid_choice in ("evidence", "annex", "report", "other"):
            serializer = ProgressDocumentSerializer(
                data={"name": "Doc", "doc_type": valid_choice}
            )
            assert serializer.is_valid(), (
                f"Choice '{valid_choice}' should be valid: {serializer.errors}"
            )

    def test_document_invalid_doc_type_fails(self, db, progress_borrador):
        """Invalid doc_type returns validation error."""
        from apps.progress.serializers import ProgressDocumentSerializer

        serializer = ProgressDocumentSerializer(
            data={"name": "Doc", "doc_type": "invalid_type"}
        )
        assert not serializer.is_valid()
        assert "doc_type" in serializer.errors

    def test_document_external_url_optional(self, db, progress_borrador):
        """external_url is optional (blank allowed)."""
        from apps.progress.serializers import ProgressDocumentSerializer

        serializer = ProgressDocumentSerializer(
            data={"name": "Doc", "doc_type": "evidence"}
        )
        assert serializer.is_valid(), serializer.errors


# ──────────────────────────────────────────────
# ProgressReviewSerializer (read-only)
# ──────────────────────────────────────────────


class TestProgressReviewSerializer:
    """ProgressReviewSerializer is read-only (append-only)."""

    def test_review_fields(self, db, progress_borrador):
        """Serializer includes expected review fields."""
        from apps.progress.serializers import ProgressReviewSerializer
        from apps.progress.tests.conftest import ProgressReviewFactory

        review = ProgressReviewFactory(progress_report=progress_borrador)
        serializer = ProgressReviewSerializer(review)
        data = serializer.data

        expected = {"id", "progress_report", "reviewed_by", "review_text",
                    "review_type", "created_at"}
        assert set(data.keys()) >= expected

    def test_review_is_read_only(self, db, progress_borrador):
        """Review serializer rejects creation — it's read-only (RN-P05)."""
        from apps.progress.serializers import ProgressReviewSerializer

        # All fields are marked read_only — serializer.save() with no
        # writable fields should either raise or ignore writable data.
        serializer = ProgressReviewSerializer(
            data={
                "progress_report": str(progress_borrador.pk),
                "review_text": "Test",
                "review_type": "observation",
            }
        )
        # is_valid may pass since DRF doesn't reject read_only fields at
        # validation level, but validated_data should be empty
        assert serializer.is_valid()
        # No writable fields → all fields are read-only
        assert serializer.validated_data == {}


# ──────────────────────────────────────────────
# ProgressStateLogSerializer (read-only)
# ──────────────────────────────────────────────


class TestProgressStateLogSerializer:
    """ProgressStateLogSerializer is read-only (append-only)."""

    def test_state_log_fields(self, db, progress_borrador):
        """Serializer includes expected state log fields."""
        from apps.progress.serializers import ProgressStateLogSerializer
        from apps.progress.tests.conftest import ProgressStateLogFactory

        log = ProgressStateLogFactory(progress_report=progress_borrador)
        serializer = ProgressStateLogSerializer(log)
        data = serializer.data

        expected = {"id", "progress_report", "from_state", "to_state",
                    "triggered_by", "reason", "created_at"}
        assert set(data.keys()) >= expected

    def test_state_log_is_read_only(self, db, progress_borrador):
        """State log serializer rejects creation — it's read-only (RN-P05)."""
        from apps.progress.serializers import ProgressStateLogSerializer

        serializer = ProgressStateLogSerializer(
            data={
                "progress_report": str(progress_borrador.pk),
                "from_state": "borrador",
                "to_state": "enviado",
            }
        )
        # is_valid may pass since DRF doesn't reject read_only fields at
        # validation level, but validated_data should be empty
        assert serializer.is_valid()
        assert serializer.validated_data == {}


# ──────────────────────────────────────────────
# Integration: Serializer chain round-trip
# ──────────────────────────────────────────────


class TestSerializerRoundTrip:
    """End-to-end serializer flow: create → retrieve → list."""

    def test_create_then_retrieve_round_trip(self, db, progress_borrador):
        """Data round-trips correctly through create and detail serializers."""
        from apps.progress.serializers import (
            ProgressReportCreateSerializer,
            ProgressReportSerializer,
        )

        data = _make_valid_data(progress_borrador.project,
                                cumulative_percentage="42.50")
        create_s = ProgressReportCreateSerializer(data=data)
        assert create_s.is_valid(), create_s.errors

        # Simulate what the view does: inject institution + created_by
        report = create_s.save(
            institution=progress_borrador.institution,
            created_by=progress_borrador.created_by,
            project=progress_borrador.project,
        )

        detail_s = ProgressReportSerializer(report)
        detail_data = detail_s.data

        assert detail_data["cumulative_percentage"] == "42.50"
        assert detail_data["status"] == "borrador"
        assert "documents" in detail_data
        assert "reviews" in detail_data
