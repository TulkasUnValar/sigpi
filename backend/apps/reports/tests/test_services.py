"""
Service tests for the Reports / Informes module (§6.6) — ReportRenderer.

Covers: ReportRenderer.render_html() for all 4 report types,
context building, template rendering, and error handling.

Spec reference:   sdd/reports/spec — RF-050–RF-053, RF-056
Design reference: openspec/changes/reports/design.md

RED PHASE: Tests written BEFORE production implementation.
"""

import uuid

import pytest

from apps.reports.services import ReportRenderer  # noqa: F401 — RED: does not exist yet

# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════


def _make_project(institution, center, pi, **kwargs):
    """Create a project with minimal required fields."""
    import datetime

    from apps.projects.models import Project

    today = datetime.date.today()
    defaults = {
        "institution": institution,
        "center": center,
        "principal_investigator": pi,
        "title": f"Test Project {uuid.uuid4().hex[:8]}",
        "abstract": "This is a test abstract for verification.",
        "objectives": "Test objectives for the report.",
        "methodology": "Test methodology section.",
        "expected_results": "Expected results content.",
        "keywords": "test, project, report",
        "start_date": today,
        "estimated_end_date": today + datetime.timedelta(days=365),
        "status": "aprobado",
    }
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


def _make_researcher(institution, **kwargs):
    """Create a researcher with minimal required fields."""
    from apps.researchers.models import Researcher

    _counter = getattr(_make_researcher, "_counter", 0) + 1
    _make_researcher._counter = _counter

    defaults = {
        "first_name": f"Test{_counter}",
        "last_name": f"Researcher{_counter}",
        "document_type": "CC",
        "document_number": f"RPT-{_counter:06d}",
        "primary_email": f"r{_counter}@test.edu",
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


def _make_center(institution, **kwargs):
    """Create a research center with minimal required fields."""
    from apps.institutions.models import ResearchCenter

    _counter = getattr(_make_center, "_counter", 0) + 1
    _make_center._counter = _counter

    defaults = {
        "name": f"Report Center {_counter}",
        "code": f"RC{_counter:03d}",
    }
    defaults.update(kwargs)
    return ResearchCenter.objects.create(institution=institution, **defaults)


def _make_progress_report(institution, project, created_by, **kwargs):
    """Create a progress report with minimal required fields."""
    import datetime

    from apps.progress.models import ProgressReport

    today = datetime.date.today()
    defaults = {
        "institution": institution,
        "project": project,
        "created_by": created_by,
        "period_start": today - datetime.timedelta(days=30),
        "period_end": today,
        "description": "Progress report description.",
        "cumulative_percentage": 50.00,
        "activities": "Activities completed this period.",
        "status": "aprobado",
    }
    defaults.update(kwargs)
    return ProgressReport.objects.create(**defaults)


# ═══════════════════════════════════════════════════════
# Project Report Tests (RF-050)
# ═══════════════════════════════════════════════════════


class TestProjectReport:
    """ReportRenderer.render_html('project', entity_id, user) — project report."""

    def test_render_html_project_returns_string(self, db):
        """render_html('project', ...) returns a non-empty string."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U1", code="U1")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher)

        renderer = ReportRenderer()
        result = renderer.render_html("project", str(project.pk), None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_html_project_contains_title(self, db):
        """Rendered HTML contains the project title."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U2", code="U2")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher, title="My Research Project")

        renderer = ReportRenderer()
        result = renderer.render_html("project", str(project.pk), None)
        assert "My Research Project" in result

    def test_render_html_project_contains_abstract(self, db):
        """Rendered HTML contains the project abstract."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U3", code="U3")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher)

        renderer = ReportRenderer()
        result = renderer.render_html("project", str(project.pk), None)
        assert project.abstract[:30] in result

    def test_render_html_project_contains_institution_name(self, db):
        """Rendered HTML contains the institution name for header context."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="Universidad Nacional", code="UN")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher)

        renderer = ReportRenderer()
        result = renderer.render_html("project", str(project.pk), None)
        assert "Universidad Nacional" in result

    def test_render_html_project_contains_objectives(self, db):
        """Rendered HTML contains project objectives section."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U5", code="U5")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(
            inst, center, researcher, objectives="Objective A: Find X. Objective B: Build Y."
        )

        renderer = ReportRenderer()
        result = renderer.render_html("project", str(project.pk), None)
        assert "Objective A" in result

    def test_render_html_project_entity_not_found_raises(self, db):
        """render_html raises ValueError when the project entity_id does not exist."""
        renderer = ReportRenderer()
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            renderer.render_html("project", fake_id, None)


# ═══════════════════════════════════════════════════════
# Researcher Report Tests (RF-051)
# ═══════════════════════════════════════════════════════


class TestResearcherReport:
    """ReportRenderer.render_html('researcher', entity_id, user) — researcher report."""

    def test_render_html_researcher_returns_string(self, db):
        """render_html('researcher', ...) returns a non-empty string."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-R1", code="UR1")
        researcher = _make_researcher(inst, first_name="Alice", last_name="Smith")

        renderer = ReportRenderer()
        result = renderer.render_html("researcher", str(researcher.pk), None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_html_researcher_contains_full_name(self, db):
        """Rendered HTML contains the researcher's full name."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-R2", code="UR2")
        researcher = _make_researcher(inst, first_name="Carlos", last_name="García")

        renderer = ReportRenderer()
        result = renderer.render_html("researcher", str(researcher.pk), None)
        assert "Carlos" in result
        assert "García" in result

    def test_render_html_researcher_contains_email(self, db):
        """Rendered HTML contains the researcher's email."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-R3", code="UR3")
        researcher = _make_researcher(
            inst, first_name="Bob", last_name="Jones", primary_email="bjones@test.edu"
        )

        renderer = ReportRenderer()
        result = renderer.render_html("researcher", str(researcher.pk), None)
        assert "bjones@test.edu" in result

    def test_render_html_researcher_not_found_raises(self, db):
        """render_html raises ValueError when researcher entity_id does not exist."""
        renderer = ReportRenderer()
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            renderer.render_html("researcher", fake_id, None)


# ═══════════════════════════════════════════════════════
# Center Report Tests (RF-052)
# ═══════════════════════════════════════════════════════


class TestCenterReport:
    """ReportRenderer.render_html('center', entity_id, user) — center report."""

    def test_render_html_center_returns_string(self, db):
        """render_html('center', ...) returns a non-empty string."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-C1", code="UC1")
        center = _make_center(inst)

        renderer = ReportRenderer()
        result = renderer.render_html("center", str(center.pk), None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_html_center_contains_name(self, db):
        """Rendered HTML contains the center name."""
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-C2", code="UC2")
        center = _make_center(inst, name="Biotech Research Center")

        renderer = ReportRenderer()
        result = renderer.render_html("center", str(center.pk), None)
        assert "Biotech Research Center" in result

    def test_render_html_center_not_found_raises(self, db):
        """render_html raises ValueError when center entity_id does not exist."""
        renderer = ReportRenderer()
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            renderer.render_html("center", fake_id, None)


# ═══════════════════════════════════════════════════════
# Advances Report Tests (RF-053)
# ═══════════════════════════════════════════════════════


class TestAdvancesReport:
    """ReportRenderer.render_html('advances', project_id, user) — advances report."""

    def test_render_html_advances_returns_string(self, db):
        """render_html('advances', ...) returns a non-empty string."""
        from apps.accounts.models import User as UserModel
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-A1", code="UA1")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher)
        user = UserModel.objects.create_user(email="adv-user@test.edu", password="testpass")
        _make_progress_report(inst, project, user)

        renderer = ReportRenderer()
        result = renderer.render_html("advances", str(project.pk), None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_html_advances_contains_activities(self, db):
        """Rendered HTML contains progress activities text."""
        from apps.accounts.models import User as UserModel
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-A2", code="UA2")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher)
        user = UserModel.objects.create_user(email="adv2@test.edu", password="testpass")
        _make_progress_report(
            inst,
            project,
            user,
            activities="Collected samples and ran PCR analysis.",
        )

        renderer = ReportRenderer()
        result = renderer.render_html("advances", str(project.pk), None)
        assert "PCR analysis" in result

    def test_render_html_advances_contains_project_title(self, db):
        """Advances report HTML contains the project title as context."""
        from apps.accounts.models import User as UserModel
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-A3", code="UA3")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center, researcher, title="Advances Demo Project")
        user = UserModel.objects.create_user(email="adv3@test.edu", password="testpass")
        _make_progress_report(inst, project, user)

        renderer = ReportRenderer()
        result = renderer.render_html("advances", str(project.pk), None)
        assert "Advances Demo Project" in result

    def test_render_html_advances_project_not_found_raises(self, db):
        """render_html raises ValueError when project for advances does not exist."""
        renderer = ReportRenderer()
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            renderer.render_html("advances", fake_id, None)


# ═══════════════════════════════════════════════════════
# Invalid Type Error
# ═══════════════════════════════════════════════════════


class TestInvalidType:
    """ReportRenderer.render_html with invalid report_type."""

    def test_render_html_invalid_type_raises_valueerror(self, db):
        """render_html with an unsupported type raises ValueError."""
        renderer = ReportRenderer()
        with pytest.raises(ValueError, match="Unknown report type"):
            renderer.render_html("invalid_type", str(uuid.uuid4()), None)

    def test_render_html_empty_type_raises_valueerror(self, db):
        """render_html with empty string type raises ValueError."""
        renderer = ReportRenderer()
        with pytest.raises(ValueError, match="Unknown report type"):
            renderer.render_html("", str(uuid.uuid4()), None)
