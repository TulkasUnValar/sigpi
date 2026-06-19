"""
Admin tests for researchers app — STRICT TDD.

Tests verify that all 4 researcher models are properly registered
in Django admin with appropriate list_display, search_fields,
list_filter, and raw_id_fields.

RED PHASE: Tests WILL fail — admin.py does not exist yet.
"""
import pytest
from django.contrib.admin.sites import site as admin_site

from apps.researchers.models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 4 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [Researcher, ResearcherAffiliation, ExternalProfile, ResearcherAttachment],
    )
    def test_model_is_registered(self, db, model):
        """Each model is registered in admin site."""
        assert model in admin_site._registry, (
            f"{model.__name__} is not registered in admin site"
        )


# ──────────────────────────────────────────────
# Researcher Admin Tests
# ──────────────────────────────────────────────


class TestResearcherAdmin:
    """ResearcherAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ResearcherAdmin.list_display includes full_name, document_number,
        institution, is_active, completeness_score, created_at."""
        admin_class = admin_site._registry[Researcher]
        expected = [
            "full_name",
            "document_number",
            "institution",
            "is_active",
            "completeness_score",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ResearcherAdmin.search_fields: first_name, last_name,
        document_number, primary_email."""
        admin_class = admin_site._registry[Researcher]
        expected = ["first_name", "last_name", "document_number", "primary_email"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ResearcherAdmin.list_filter: is_active, institution."""
        admin_class = admin_site._registry[Researcher]
        expected = ["is_active", "institution"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ResearcherAdmin.raw_id_fields: user, institution."""
        admin_class = admin_site._registry[Researcher]
        expected = ["user", "institution"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ResearcherAffiliation Admin Tests
# ──────────────────────────────────────────────


class TestResearcherAffiliationAdmin:
    """ResearcherAffiliationAdmin — list_display, search_fields,
    list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ResearcherAffiliationAdmin.list_display: researcher, center,
        group, line, is_primary."""
        admin_class = admin_site._registry[ResearcherAffiliation]
        expected = ["researcher", "center", "group", "line", "is_primary"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ResearcherAffiliationAdmin.search_fields: researcher__first_name,
        researcher__last_name."""
        admin_class = admin_site._registry[ResearcherAffiliation]
        expected = ["researcher__first_name", "researcher__last_name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ResearcherAffiliationAdmin.list_filter: is_primary."""
        admin_class = admin_site._registry[ResearcherAffiliation]
        expected = ["is_primary"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ResearcherAffiliationAdmin.raw_id_fields: researcher, center,
        group, line."""
        admin_class = admin_site._registry[ResearcherAffiliation]
        expected = ["researcher", "center", "group", "line"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ExternalProfile Admin Tests
# ──────────────────────────────────────────────


class TestExternalProfileAdmin:
    """ExternalProfileAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ExternalProfileAdmin.list_display: researcher, provider, url."""
        admin_class = admin_site._registry[ExternalProfile]
        expected = ["researcher", "provider", "url"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ExternalProfileAdmin.search_fields: researcher__first_name,
        researcher__last_name."""
        admin_class = admin_site._registry[ExternalProfile]
        expected = ["researcher__first_name", "researcher__last_name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ExternalProfileAdmin.list_filter: provider."""
        admin_class = admin_site._registry[ExternalProfile]
        expected = ["provider"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ExternalProfileAdmin.raw_id_fields: researcher."""
        admin_class = admin_site._registry[ExternalProfile]
        expected = ["researcher"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ResearcherAttachment Admin Tests
# ──────────────────────────────────────────────


class TestResearcherAttachmentAdmin:
    """ResearcherAttachmentAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ResearcherAttachmentAdmin.list_display: researcher, name,
        attachment_type, external_url."""
        admin_class = admin_site._registry[ResearcherAttachment]
        expected = ["researcher", "name", "attachment_type", "external_url"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ResearcherAttachmentAdmin.search_fields: researcher__first_name,
        name."""
        admin_class = admin_site._registry[ResearcherAttachment]
        expected = ["researcher__first_name", "name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ResearcherAttachmentAdmin.list_filter: type."""
        admin_class = admin_site._registry[ResearcherAttachment]
        expected = ["type"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ResearcherAttachmentAdmin.raw_id_fields: researcher."""
        admin_class = admin_site._registry[ResearcherAttachment]
        expected = ["researcher"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )
