"""
Admin tests for progress app — STRICT TDD.

Tests verify that all 4 progress models are properly registered
in Django admin with appropriate list_display, search_fields,
list_filter, and raw_id_fields.

RED PHASE: Tests WILL fail — admin.py does not exist yet.
"""

import pytest
from django.contrib.admin.sites import site as admin_site

from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 4 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [
            ProgressReport,
            ProgressReview,
            ProgressDocument,
            ProgressStateLog,
        ],
    )
    def test_model_is_registered(self, db, model):
        """Each progress model is registered in admin site."""
        assert model in admin_site._registry, f"{model.__name__} is not registered in admin site"


# ──────────────────────────────────────────────
# ProgressReport Admin Tests
# ──────────────────────────────────────────────


class TestProgressReportAdmin:
    """ProgressReportAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProgressReportAdmin.list_display includes id, project, status,
        cumulative_percentage, period_start, period_end, created_by,
        created_at."""
        admin_class = admin_site._registry[ProgressReport]
        expected = [
            "id",
            "project",
            "status",
            "cumulative_percentage",
            "period_start",
            "period_end",
            "created_by",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProgressReportAdmin.search_fields: description, activities."""
        admin_class = admin_site._registry[ProgressReport]
        expected = ["description", "activities"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProgressReportAdmin.list_filter: status, institution."""
        admin_class = admin_site._registry[ProgressReport]
        expected = ["status", "institution"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProgressReportAdmin.raw_id_fields: institution, project, created_by."""
        admin_class = admin_site._registry[ProgressReport]
        expected = ["institution", "project", "created_by"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProgressReview Admin Tests
# ──────────────────────────────────────────────


class TestProgressReviewAdmin:
    """ProgressReviewAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProgressReviewAdmin.list_display: progress_report, reviewed_by,
        review_type, created_at."""
        admin_class = admin_site._registry[ProgressReview]
        expected = [
            "progress_report",
            "reviewed_by",
            "review_type",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProgressReviewAdmin.search_fields: review_text."""
        admin_class = admin_site._registry[ProgressReview]
        expected = ["review_text"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProgressReviewAdmin.list_filter: review_type."""
        admin_class = admin_site._registry[ProgressReview]
        expected = ["review_type"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProgressReviewAdmin.raw_id_fields: progress_report, reviewed_by."""
        admin_class = admin_site._registry[ProgressReview]
        expected = ["progress_report", "reviewed_by"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProgressDocument Admin Tests
# ──────────────────────────────────────────────


class TestProgressDocumentAdmin:
    """ProgressDocumentAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProgressDocumentAdmin.list_display: progress_report, name, doc_type,
        uploaded_at."""
        admin_class = admin_site._registry[ProgressDocument]
        expected = ["progress_report", "name", "doc_type", "uploaded_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProgressDocumentAdmin.search_fields: name."""
        admin_class = admin_site._registry[ProgressDocument]
        expected = ["name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProgressDocumentAdmin.list_filter: doc_type."""
        admin_class = admin_site._registry[ProgressDocument]
        expected = ["doc_type"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProgressDocumentAdmin.raw_id_fields: progress_report."""
        admin_class = admin_site._registry[ProgressDocument]
        expected = ["progress_report"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProgressStateLog Admin Tests
# ──────────────────────────────────────────────


class TestProgressStateLogAdmin:
    """ProgressStateLogAdmin — list_display, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ProgressStateLogAdmin.list_display: progress_report, from_state,
        to_state, triggered_by, created_at."""
        admin_class = admin_site._registry[ProgressStateLog]
        expected = [
            "progress_report",
            "from_state",
            "to_state",
            "triggered_by",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_list_filter(self, db):
        """ProgressStateLogAdmin.list_filter: from_state, to_state."""
        admin_class = admin_site._registry[ProgressStateLog]
        expected = ["from_state", "to_state"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProgressStateLogAdmin.raw_id_fields: progress_report, triggered_by."""
        admin_class = admin_site._registry[ProgressStateLog]
        expected = ["progress_report", "triggered_by"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )
