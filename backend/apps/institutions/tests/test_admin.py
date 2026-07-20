"""
Admin tests for institutions app — STRICT TDD.

Tests verify that all 6 models are properly registered in the Django admin
with appropriate list_display, search_fields, list_filter, and raw_id_fields.

RED PHASE: Tests will fail because admin.py only registers Institution
and ResearchCenter (missing Sede, Facultad, ResearchGroup, ResearchLine)
and doesn't yet include status/description in existing admins.
"""

import pytest
from django.contrib.admin.sites import site as admin_site

from apps.institutions.models import (
    Facultad,
    Institution,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
    Sede,
)

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 6 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [Institution, Sede, Facultad, ResearchCenter, ResearchGroup, ResearchLine],
    )
    def test_model_is_registered(self, db, model):
        """Each model is registered in admin site."""
        assert model in admin_site._registry, f"{model.__name__} is not registered in admin site"


# ──────────────────────────────────────────────
# Institution Admin Tests
# ──────────────────────────────────────────────


class TestInstitutionAdmin:
    """Institution admin configuration — expanded with status + description."""

    def test_list_display_includes_new_fields(self, db):
        """InstitutionAdmin.list_display includes status and description."""
        admin_class = admin_site._registry[Institution]
        assert "status" in admin_class.list_display
        assert "description" in admin_class.list_display

    def test_list_display_keeps_core_fields(self, db):
        """InstitutionAdmin.list_display keeps name, code, is_active."""
        admin_class = admin_site._registry[Institution]
        for field in ["name", "code", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """InstitutionAdmin.search_fields includes name, code."""
        admin_class = admin_site._registry[Institution]
        assert "name" in admin_class.search_fields
        assert "code" in admin_class.search_fields

    def test_list_filter(self, db):
        """InstitutionAdmin.list_filter includes is_active."""
        admin_class = admin_site._registry[Institution]
        assert "is_active" in admin_class.list_filter


# ──────────────────────────────────────────────
# ResearchCenter Admin Tests
# ──────────────────────────────────────────────


class TestResearchCenterAdmin:
    """ResearchCenter admin — expanded with status + description."""

    def test_list_display_includes_new_fields(self, db):
        """ResearchCenterAdmin.list_display includes status and description."""
        admin_class = admin_site._registry[ResearchCenter]
        assert "status" in admin_class.list_display
        assert "description" in admin_class.list_display

    def test_list_display_keeps_core_fields(self, db):
        """ResearchCenterAdmin.list_display keeps name, institution, code, is_active."""
        admin_class = admin_site._registry[ResearchCenter]
        for field in ["name", "institution", "code", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """ResearchCenterAdmin.search_fields includes name, code, institution__name."""
        admin_class = admin_site._registry[ResearchCenter]
        for field in ["name", "code"]:
            assert field in admin_class.search_fields

    def test_list_filter(self, db):
        """ResearchCenterAdmin.list_filter includes is_active, institution."""
        admin_class = admin_site._registry[ResearchCenter]
        for field in ["is_active", "institution"]:
            assert field in admin_class.list_filter

    def test_raw_id_fields(self, db):
        """ResearchCenterAdmin.raw_id_fields includes institution."""
        admin_class = admin_site._registry[ResearchCenter]
        assert "institution" in admin_class.raw_id_fields


# ──────────────────────────────────────────────
# Sede Admin Tests
# ──────────────────────────────────────────────


class TestSedeAdmin:
    """Sede admin — newly registered."""

    def test_list_display(self, db):
        """SedeAdmin.list_display: name, institution, code, status, is_active."""
        admin_class = admin_site._registry[Sede]
        for field in ["name", "institution", "code", "status", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """SedeAdmin.search_fields: name, code, institution__name."""
        admin_class = admin_site._registry[Sede]
        for field in ["name", "code", "institution__name"]:
            assert field in admin_class.search_fields

    def test_list_filter(self, db):
        """SedeAdmin.list_filter: status, is_active, institution."""
        admin_class = admin_site._registry[Sede]
        for field in ["status", "is_active", "institution"]:
            assert field in admin_class.list_filter

    def test_raw_id_fields(self, db):
        """SedeAdmin.raw_id_fields includes institution."""
        admin_class = admin_site._registry[Sede]
        assert "institution" in admin_class.raw_id_fields


# ──────────────────────────────────────────────
# Facultad Admin Tests
# ──────────────────────────────────────────────


class TestFacultadAdmin:
    """Facultad admin — newly registered."""

    def test_list_display(self, db):
        """FacultadAdmin.list_display: name, institution, sede, code, status, is_active."""
        admin_class = admin_site._registry[Facultad]
        for field in ["name", "institution", "sede", "code", "status", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """FacultadAdmin.search_fields: name, code, institution__name."""
        admin_class = admin_site._registry[Facultad]
        for field in ["name", "code", "institution__name"]:
            assert field in admin_class.search_fields

    def test_list_filter(self, db):
        """FacultadAdmin.list_filter: status, is_active, institution."""
        admin_class = admin_site._registry[Facultad]
        for field in ["status", "is_active", "institution"]:
            assert field in admin_class.list_filter

    def test_raw_id_fields(self, db):
        """FacultadAdmin.raw_id_fields: institution, sede."""
        admin_class = admin_site._registry[Facultad]
        for field in ["institution", "sede"]:
            assert field in admin_class.raw_id_fields


# ──────────────────────────────────────────────
# ResearchGroup Admin Tests
# ──────────────────────────────────────────────


class TestResearchGroupAdmin:
    """ResearchGroup admin — newly registered."""

    def test_list_display(self, db):
        """ResearchGroupAdmin.list_display: name, institution, center, code, status, is_active."""
        admin_class = admin_site._registry[ResearchGroup]
        for field in ["name", "institution", "center", "code", "status", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """ResearchGroupAdmin.search_fields: name, code, institution__name, center__name."""
        admin_class = admin_site._registry[ResearchGroup]
        for field in ["name", "code", "institution__name", "center__name"]:
            assert field in admin_class.search_fields

    def test_list_filter(self, db):
        """ResearchGroupAdmin.list_filter: status, is_active, institution, center."""
        admin_class = admin_site._registry[ResearchGroup]
        for field in ["status", "is_active", "institution", "center"]:
            assert field in admin_class.list_filter

    def test_raw_id_fields(self, db):
        """ResearchGroupAdmin.raw_id_fields: institution, center."""
        admin_class = admin_site._registry[ResearchGroup]
        for field in ["institution", "center"]:
            assert field in admin_class.raw_id_fields


# ──────────────────────────────────────────────
# ResearchLine Admin Tests
# ──────────────────────────────────────────────


class TestResearchLineAdmin:
    """ResearchLine admin — newly registered."""

    def test_list_display(self, db):
        """ResearchLineAdmin.list_display: name, institution, group, code, status, is_active."""
        admin_class = admin_site._registry[ResearchLine]
        for field in ["name", "institution", "group", "code", "status", "is_active"]:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        """ResearchLineAdmin.search_fields: name, code, institution__name, group__name."""
        admin_class = admin_site._registry[ResearchLine]
        for field in ["name", "code", "institution__name", "group__name"]:
            assert field in admin_class.search_fields

    def test_list_filter(self, db):
        """ResearchLineAdmin.list_filter: status, is_active, institution, group."""
        admin_class = admin_site._registry[ResearchLine]
        for field in ["status", "is_active", "institution", "group"]:
            assert field in admin_class.list_filter

    def test_raw_id_fields(self, db):
        """ResearchLineAdmin.raw_id_fields: institution, group."""
        admin_class = admin_site._registry[ResearchLine]
        for field in ["institution", "group"]:
            assert field in admin_class.raw_id_fields
