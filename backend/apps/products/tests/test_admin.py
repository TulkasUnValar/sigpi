"""
Admin tests for products app — STRICT TDD.

Tests verify that all 3 product models are properly registered
in Django admin with appropriate list_display, search_fields,
list_filter, and raw_id_fields.

RED PHASE: Tests WILL fail if admin.py is incomplete.
"""
import pytest
from django.contrib.admin.sites import site as admin_site

from apps.products.models import ProductAttachment, ProductAuthor, ResearchProduct

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 3 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [ResearchProduct, ProductAuthor, ProductAttachment],
    )
    def test_model_is_registered(self, db, model):
        """Each product model is registered in admin site."""
        assert model in admin_site._registry, (
            f"{model.__name__} is not registered in admin site"
        )


# ──────────────────────────────────────────────
# ResearchProduct Admin Tests
# ──────────────────────────────────────────────


class TestResearchProductAdmin:
    """ResearchProductAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ResearchProductAdmin.list_display includes title, type,
        publication_year, project, institution, created_at."""
        admin_class = admin_site._registry[ResearchProduct]
        expected = [
            "title",
            "type",
            "publication_year",
            "project",
            "institution",
            "created_at",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ResearchProductAdmin.search_fields: title, description."""
        admin_class = admin_site._registry[ResearchProduct]
        expected = ["title", "description"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ResearchProductAdmin.list_filter: type, publication_year, institution."""
        admin_class = admin_site._registry[ResearchProduct]
        expected = ["type", "publication_year", "institution"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ResearchProductAdmin.raw_id_fields includes FK fields."""
        admin_class = admin_site._registry[ResearchProduct]
        expected = [
            "institution",
            "project",
            "created_by",
            "updated_by",
        ]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )

# ──────────────────────────────────────────────
# ProductAuthor Admin Tests
# ──────────────────────────────────────────────


class TestProductAuthorAdmin:
    """ProductAuthorAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ProductAuthorAdmin.list_display: product, researcher, is_principal, order."""
        admin_class = admin_site._registry[ProductAuthor]
        expected = ["product", "researcher", "is_principal", "order"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProductAuthorAdmin.search_fields: researcher__first_name, researcher__last_name."""
        admin_class = admin_site._registry[ProductAuthor]
        expected = ["researcher__first_name", "researcher__last_name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProductAuthorAdmin.list_filter: is_principal."""
        admin_class = admin_site._registry[ProductAuthor]
        expected = ["is_principal"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProductAuthorAdmin.raw_id_fields: product, researcher."""
        admin_class = admin_site._registry[ProductAuthor]
        expected = ["product", "researcher"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProductAttachment Admin Tests
# ──────────────────────────────────────────────


class TestProductAttachmentAdmin:
    """ProductAttachmentAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ProductAttachmentAdmin.list_display: product, name,
        doc_type, external_url, created_at."""
        admin_class = admin_site._registry[ProductAttachment]
        expected = ["product", "name", "doc_type", "external_url", "created_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProductAttachmentAdmin.search_fields: name."""
        admin_class = admin_site._registry[ProductAttachment]
        expected = ["name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProductAttachmentAdmin.list_filter: doc_type."""
        admin_class = admin_site._registry[ProductAttachment]
        expected = ["doc_type"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProductAttachmentAdmin.raw_id_fields: product."""
        admin_class = admin_site._registry[ProductAttachment]
        expected = ["product"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )
