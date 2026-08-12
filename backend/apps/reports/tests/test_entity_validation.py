"""
Entity validation tests for reports module — STRICT TDD (RED phase).

Tests define expected behavior of `ReportRenderer.validate_entity()`:
- Resolves entity_id to an existing entity and returns its institution_id
- Raises Http404 for unresolvable UUID
- Raises PermissionDenied for cross-institution access

Spec reference:  openspec/changes/cross-module-integration/spec.md — FR-004, BR-003
Design reference: openspec/changes/cross-module-integration/design.md — IP-4
"""

import uuid

import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ── Helpers ────────────────────────────────────────────


def _make_researcher(institution, **kwargs):
    defaults = {
        "first_name": "Test",
        "last_name": "Researcher",
        "document_type": "CC",
        "document_number": f"RES-{uuid.uuid4().hex[:8]}",
        "primary_email": f"res-{uuid.uuid4().hex[:4]}@test.edu",
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


def _make_project(institution, center, pi, **kwargs):
    from datetime import date, timedelta

    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title="Report Test Project",
        abstract="Test abstract",
        objectives="Test objectives",
        methodology="Test methodology",
        expected_results="Test results",
        keywords="test, report",
        start_date=date.today(),
        estimated_end_date=date.today() + timedelta(days=365),
        status="aprobado",
    )


# ──────────────────────────────────────────────
# ReportRenderer.validate_entity (IP-4)
# ──────────────────────────────────────────────


class TestReportRendererValidateEntity:
    """ReportRenderer.validate_entity — resolve + institution scoping."""

    def _setup(self):
        institution = Institution.objects.create(name="Report Inst", code="RI001")
        center = ResearchCenter.objects.create(institution=institution, name="Lab", code="LAB")
        pi = _make_researcher(institution)
        return institution, center, pi

    def test_valid_project_entity(self, db):
        """validate_entity returns institution_id for a valid project entity."""
        from apps.reports.services import ReportRenderer

        institution, center, pi = self._setup()
        project = _make_project(institution, center, pi)
        renderer = ReportRenderer()

        result = renderer.validate_entity("project", str(project.pk), institution.id)
        assert result == institution.id

    def test_valid_researcher_entity(self, db):
        """validate_entity returns institution_id for a valid researcher entity."""
        from apps.reports.services import ReportRenderer

        institution = Institution.objects.create(name="R2", code="RI002")
        researcher = _make_researcher(institution)
        renderer = ReportRenderer()

        result = renderer.validate_entity("researcher", str(researcher.pk), institution.id)
        assert result == institution.id

    def test_valid_center_entity(self, db):
        """validate_entity returns institution_id for a valid center entity."""
        from apps.reports.services import ReportRenderer

        institution = Institution.objects.create(name="R3", code="RI003")
        center = ResearchCenter.objects.create(institution=institution, name="C3", code="C3")
        renderer = ReportRenderer()

        result = renderer.validate_entity("center", str(center.pk), institution.id)
        assert result == institution.id

    def test_unresolvable_project_raises_404(self, db):
        """validate_entity raises Http404 for unknown UUID."""
        from apps.reports.services import ReportRenderer

        renderer = ReportRenderer()
        fake_uuid = uuid.uuid4()

        with pytest.raises(Http404, match="Entity not found"):
            renderer.validate_entity("project", str(fake_uuid), uuid.uuid4())

    def test_cross_institution_project_raises_403(self, db):
        """validate_entity raises PermissionDenied for cross-institution entity."""
        from apps.reports.services import ReportRenderer

        institution_a, center_a, pi_a = self._setup()
        institution_b = Institution.objects.create(name="Other", code="OTH")
        center_b = ResearchCenter.objects.create(institution=institution_b, name="OB", code="OB")
        pi_b = _make_researcher(institution_b)
        project_b = _make_project(institution_b, center_b, pi_b)

        renderer = ReportRenderer()
        with pytest.raises(PermissionDenied, match="does not belong to your institution"):
            renderer.validate_entity("project", str(project_b.pk), institution_a.id)

    def test_cross_institution_researcher_raises_403(self, db):
        """validate_entity raises PermissionDenied for cross-institution researcher."""
        from apps.reports.services import ReportRenderer

        institution_a = Institution.objects.create(name="A", code="A")
        institution_b = Institution.objects.create(name="B", code="B")
        researcher_b = _make_researcher(institution_b)

        renderer = ReportRenderer()
        with pytest.raises(PermissionDenied, match="does not belong to your institution"):
            renderer.validate_entity("researcher", str(researcher_b.pk), institution_a.id)

    def test_superuser_bypasses_institution_check(self, db):
        """validate_entity allows any entity for superuser."""
        from apps.accounts.models import User
        from apps.reports.services import ReportRenderer

        institution_a = Institution.objects.create(name="A2", code="A2")
        institution_b = Institution.objects.create(name="B2", code="B2")
        center_b = ResearchCenter.objects.create(institution=institution_b, name="CB", code="CB")
        pi_b = _make_researcher(institution_b)
        project_b = _make_project(institution_b, center_b, pi_b)
        superuser = User.objects.create_superuser(email="su@test.edu", password="su123")

        renderer = ReportRenderer()
        result = renderer.validate_entity("project", str(project_b.pk), institution_a.id, user=superuser)
        assert result == institution_b.id
