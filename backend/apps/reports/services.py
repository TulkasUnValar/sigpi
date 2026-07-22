"""
Report Services — Renderer, Generator, and Approval logic (§6.6).

Phase 2: ReportRenderer builds context dicts per report type and
renders Django templates to HTML strings.

Spec reference:   sdd/reports/spec — RF-050–RF-053, RF-056
Design reference: openspec/changes/reports/design.md
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# ReportRenderer
# ──────────────────────────────────────────────

_VALID_TYPES = frozenset({"project", "researcher", "center", "advances"})


class ReportRenderer:
    """Build context and render Django templates to HTML for all 4 report types.

    Usage:
        renderer = ReportRenderer()
        html = renderer.render_html("project", project_uuid, user)
    """

    # ── Public API ──────────────────────────────────────────────

    def render_html(
        self,
        report_type: str,
        entity_id: str | UUID,
        user,  # User | None — None ok for preview rendering tests
    ) -> str:
        """Render a report to an HTML string via Django templates.

        Args:
            report_type: One of "project", "researcher", "center", "advances".
            entity_id: UUID string or UUID object of the target entity.
            user: Django User (or None for test convenience).

        Returns:
            Rendered HTML string.

        Raises:
            ValueError: Unknown report_type or entity not found.
        """
        if report_type not in _VALID_TYPES:
            raise ValueError(f"Unknown report type: {report_type!r}")

        context = self._build_context(report_type, entity_id)
        template_name = f"reports/{report_type}_report.html"
        return render_to_string(template_name, context)

    # ── Context Builders (per-type, private) ───────────────────

    def _build_context(self, report_type: str, entity_id: str | UUID) -> dict:
        """Dispatch to the correct context builder based on type."""
        if isinstance(entity_id, UUID):
            entity_uuid = entity_id
        else:
            try:
                entity_uuid = UUID(entity_id)
            except (ValueError, AttributeError):
                raise ValueError(f"Invalid entity_id: {entity_id!r}")

        builders = {
            "project": self._project_context,
            "researcher": self._researcher_context,
            "center": self._center_context,
            "advances": self._advances_context,
        }
        return builders[report_type](entity_uuid)

    # ── Project (RF-050) ───────────────────────────────────────

    def _project_context(self, entity_uuid: UUID) -> dict:
        """Build context for a project report.

        Sections: general data, objectives, team, budget summary,
        results, progress.
        """
        from apps.projects.models import Project

        try:
            project = (
                Project.objects.select_related("institution", "center", "principal_investigator")
                .prefetch_related("members__researcher", "progress_reports")
                .get(pk=entity_uuid)
            )
        except Project.DoesNotExist:
            raise ValueError(f"Project not found: {entity_uuid}")

        members = project.members.all()
        progress_reports = project.progress_reports.order_by("-created_at")

        return {
            "institution": project.institution,
            "report_title": f"Project Report: {project.title}",
            "project": project,
            "members": members,
            "progress_reports": progress_reports,
            "generated_at": None,  # filled by caller in Phase 3
        }

    # ── Researcher (RF-051) ────────────────────────────────────

    def _researcher_context(self, entity_uuid: UUID) -> dict:
        """Build context for a researcher report.

        Sections: profile, projects, production summary.
        """
        from apps.researchers.models import Researcher

        try:
            researcher = (
                Researcher.objects.select_related("institution", "user")
                .prefetch_related(
                    "affiliations__center",
                    "affiliations__group",
                    "affiliations__line",
                    "led_projects",
                    "project_memberships__project",
                )
                .get(pk=entity_uuid)
            )
        except Researcher.DoesNotExist:
            raise ValueError(f"Researcher not found: {entity_uuid}")

        affiliations = researcher.affiliations.all()
        led_projects = researcher.led_projects.all()
        member_projects = [m.project for m in researcher.project_memberships.all()]

        return {
            "institution": researcher.institution,
            "report_title": f"Researcher Report: {researcher}",
            "researcher": researcher,
            "affiliations": affiliations,
            "led_projects": led_projects,
            "member_projects": member_projects,
            "generated_at": None,
        }

    # ── Center (RF-052) ────────────────────────────────────────

    def _center_context(self, entity_uuid: UUID) -> dict:
        """Build context for a center report.

        Sections: center data, project list, aggregate statistics.
        """
        from apps.institutions.models import ResearchCenter
        from apps.projects.models import Project

        try:
            center = ResearchCenter.objects.select_related("institution").get(pk=entity_uuid)
        except ResearchCenter.DoesNotExist:
            raise ValueError(f"Center not found: {entity_uuid}")

        projects = Project.objects.filter(center=center).order_by("-created_at")
        project_count = projects.count()
        active_count = projects.filter(is_active=True).count()

        return {
            "institution": center.institution,
            "report_title": f"Center Report: {center.name}",
            "center": center,
            "projects": projects,
            "project_count": project_count,
            "active_count": active_count,
            "generated_at": None,
        }

    # ── Advances (RF-053) ──────────────────────────────────────

    def _advances_context(self, entity_uuid: UUID) -> dict:
        """Build context for an advances (progress) report.

        Sections: activities, completion %, documents, reviews.
        """
        from apps.projects.models import Project

        try:
            project = (
                Project.objects.select_related("institution")
                .prefetch_related("progress_reports__documents")
                .get(pk=entity_uuid)
            )
        except Project.DoesNotExist:
            raise ValueError(f"Project not found: {entity_uuid}")

        progress_reports = project.progress_reports.order_by("-created_at")

        return {
            "institution": project.institution,
            "report_title": f"Advances Report: {project.title}",
            "project": project,
            "progress_reports": progress_reports,
            "generated_at": None,
        }
