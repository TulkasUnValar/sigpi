"""
Admin tests for the Reports / Informes module (§6.6).

Covers: Django admin registration for Report, ReportTemplate, and ReportApproval
models with correct list_display, search_fields, list_filter, and readonly_fields.

RED PHASE: Tests written BEFORE production implementation.
"""

import pytest
from django.contrib.admin.sites import site as admin_site

from apps.reports.models import Report, ReportApproval, ReportTemplate

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 3 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [Report, ReportTemplate, ReportApproval],
    )
    def test_model_is_registered(self, db, model):
        """Each reports model is registered in admin site."""
        assert model in admin_site._registry, (
            f"{model.__name__} is not registered in admin site"
        )


# ──────────────────────────────────────────────
# Report Admin Tests
# ──────────────────────────────────────────────


class TestReportAdmin:
    """ReportAdmin — list_display, search_fields, list_filter, readonly_fields."""

    def test_list_display(self, db):
        """ReportAdmin.list_display: id, title, report_type, status, institution,
        created_by, created_at."""
        admin_class = admin_site._registry[Report]
        expected = [
            "id",
            "title",
            "report_type",
            "status",
            "institution",
            "created_by",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ReportAdmin.search_fields: title."""
        admin_class = admin_site._registry[Report]
        expected = ["title"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ReportAdmin.list_filter: report_type, status, institution."""
        admin_class = admin_site._registry[Report]
        expected = ["report_type", "status", "institution"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_readonly_fields(self, db):
        """ReportAdmin.readonly_fields: created_at, updated_at."""
        admin_class = admin_site._registry[Report]
        expected = ["created_at", "updated_at"]
        for field in expected:
            assert field in admin_class.readonly_fields, (
                f"Expected {field!r} in readonly_fields, got {admin_class.readonly_fields}"
            )


# ──────────────────────────────────────────────
# ReportTemplate Admin Tests
# ──────────────────────────────────────────────


class TestReportTemplateAdmin:
    """ReportTemplateAdmin — list_display, search_fields, list_filter."""

    def test_list_display(self, db):
        """ReportTemplateAdmin.list_display: id, name, report_type, institution,
        is_active."""
        admin_class = admin_site._registry[ReportTemplate]
        expected = ["id", "name", "report_type", "institution", "is_active"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ReportTemplateAdmin.search_fields: name."""
        admin_class = admin_site._registry[ReportTemplate]
        expected = ["name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ReportTemplateAdmin.list_filter: report_type, is_active."""
        admin_class = admin_site._registry[ReportTemplate]
        expected = ["report_type", "is_active"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )


# ──────────────────────────────────────────────
# ReportApproval Admin Tests
# ──────────────────────────────────────────────


class TestReportApprovalAdmin:
    """ReportApprovalAdmin — list_display, list_filter, readonly_fields."""

    def test_list_display(self, db):
        """ReportApprovalAdmin.list_display: id, report, approved_by, status,
        approved_at."""
        admin_class = admin_site._registry[ReportApproval]
        expected = ["id", "report", "approved_by", "status", "approved_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_list_filter(self, db):
        """ReportApprovalAdmin.list_filter: status."""
        admin_class = admin_site._registry[ReportApproval]
        expected = ["status"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_readonly_fields(self, db):
        """ReportApprovalAdmin.readonly_fields: approved_at."""
        admin_class = admin_site._registry[ReportApproval]
        expected = ["approved_at"]
        for field in expected:
            assert field in admin_class.readonly_fields, (
                f"Expected {field!r} in readonly_fields, got {admin_class.readonly_fields}"
            )
