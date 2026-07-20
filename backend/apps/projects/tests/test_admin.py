"""
Admin tests for projects app — STRICT TDD.

Tests verify that all 5 project models are properly registered
in Django admin with appropriate list_display, search_fields,
list_filter, and raw_id_fields.

RED PHASE: Tests WILL fail — admin.py does not exist yet.
"""
import pytest
from django.contrib.admin.sites import site as admin_site

from apps.projects.models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)

# ──────────────────────────────────────────────
# Registration Tests
# ──────────────────────────────────────────────


class TestAdminRegistration:
    """All 5 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [Project, ProjectMember, ProjectDocument, ProjectObservation, ProjectStateLog],
    )
    def test_model_is_registered(self, db, model):
        """Each project model is registered in admin site."""
        assert model in admin_site._registry, (
            f"{model.__name__} is not registered in admin site"
        )


# ──────────────────────────────────────────────
# Project Admin Tests
# ──────────────────────────────────────────────


class TestProjectAdmin:
    """ProjectAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ProjectAdmin.list_display includes title, status, center,
        institution, principal_investigator, start_date, is_active."""
        admin_class = admin_site._registry[Project]
        expected = [
            "title",
            "status",
            "center",
            "institution",
            "principal_investigator",
            "start_date",
            "is_active",
        ]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProjectAdmin.search_fields: title, keywords."""
        admin_class = admin_site._registry[Project]
        expected = ["title", "keywords"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProjectAdmin.list_filter: status, center, institution."""
        admin_class = admin_site._registry[Project]
        expected = ["status", "center", "institution"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProjectAdmin.raw_id_fields includes FK fields."""
        admin_class = admin_site._registry[Project]
        expected = [
            "institution",
            "center",
            "group",
            "line",
            "principal_investigator",
        ]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProjectMember Admin Tests
# ──────────────────────────────────────────────


class TestProjectMemberAdmin:
    """ProjectMemberAdmin — list_display, search_fields, list_filter, raw_id_fields."""

    def test_list_display(self, db):
        """ProjectMemberAdmin.list_display: project, researcher, role, joined_at."""
        admin_class = admin_site._registry[ProjectMember]
        expected = ["project", "researcher", "role", "joined_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProjectMemberAdmin.search_fields: researcher__first_name,
        researcher__last_name."""
        admin_class = admin_site._registry[ProjectMember]
        expected = ["researcher__first_name", "researcher__last_name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProjectMemberAdmin.list_filter: role."""
        admin_class = admin_site._registry[ProjectMember]
        expected = ["role"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProjectMemberAdmin.raw_id_fields: project, researcher."""
        admin_class = admin_site._registry[ProjectMember]
        expected = ["project", "researcher"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProjectDocument Admin Tests
# ──────────────────────────────────────────────


class TestProjectDocumentAdmin:
    """ProjectDocumentAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProjectDocumentAdmin.list_display: project, name, doc_type,
        uploaded_at."""
        admin_class = admin_site._registry[ProjectDocument]
        expected = ["project", "name", "doc_type", "uploaded_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProjectDocumentAdmin.search_fields: name."""
        admin_class = admin_site._registry[ProjectDocument]
        expected = ["name"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_list_filter(self, db):
        """ProjectDocumentAdmin.list_filter: doc_type."""
        admin_class = admin_site._registry[ProjectDocument]
        expected = ["doc_type"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProjectDocumentAdmin.raw_id_fields: project."""
        admin_class = admin_site._registry[ProjectDocument]
        expected = ["project"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProjectObservation Admin Tests
# ──────────────────────────────────────────────


class TestProjectObservationAdmin:
    """ProjectObservationAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProjectObservationAdmin.list_display: project, observed_by,
        created_at."""
        admin_class = admin_site._registry[ProjectObservation]
        expected = ["project", "observed_by", "created_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_search_fields(self, db):
        """ProjectObservationAdmin.search_fields: observation_text."""
        admin_class = admin_site._registry[ProjectObservation]
        expected = ["observation_text"]
        for field in expected:
            assert field in admin_class.search_fields, (
                f"Expected {field!r} in search_fields, got {admin_class.search_fields}"
            )

    def test_raw_id_fields(self, db):
        """ProjectObservationAdmin.raw_id_fields: project, observed_by."""
        admin_class = admin_site._registry[ProjectObservation]
        expected = ["project", "observed_by"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )


# ──────────────────────────────────────────────
# ProjectStateLog Admin Tests
# ──────────────────────────────────────────────


class TestProjectStateLogAdmin:
    """ProjectStateLogAdmin — list_display, search_fields, list_filter,
    raw_id_fields."""

    def test_list_display(self, db):
        """ProjectStateLogAdmin.list_display: project, from_state, to_state,
        triggered_by, created_at."""
        admin_class = admin_site._registry[ProjectStateLog]
        expected = ["project", "from_state", "to_state", "triggered_by", "created_at"]
        for field in expected:
            assert field in admin_class.list_display, (
                f"Expected {field!r} in list_display, got {admin_class.list_display}"
            )

    def test_list_filter(self, db):
        """ProjectStateLogAdmin.list_filter: from_state, to_state."""
        admin_class = admin_site._registry[ProjectStateLog]
        expected = ["from_state", "to_state"]
        for field in expected:
            assert field in admin_class.list_filter, (
                f"Expected {field!r} in list_filter, got {admin_class.list_filter}"
            )

    def test_raw_id_fields(self, db):
        """ProjectStateLogAdmin.raw_id_fields: project, triggered_by."""
        admin_class = admin_site._registry[ProjectStateLog]
        expected = ["project", "triggered_by"]
        for field in expected:
            assert field in admin_class.raw_id_fields, (
                f"Expected {field!r} in raw_id_fields, got {admin_class.raw_id_fields}"
            )
