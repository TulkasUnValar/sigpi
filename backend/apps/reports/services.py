"""
Report Services — Renderer, Generator, and Approval logic (§6.6).

Phase 2: ReportRenderer builds context dicts per report type and
renders Django templates to HTML strings.
Phase 3: ReportGenerator (WeasyPrint HTML→PDF, RF-057) and
ReportApprovalService (RN-017 guard, audit, RN-018 metadata).

Spec reference:   sdd/reports/spec — RF-050–RF-053, RF-056, RF-057, RF-058
Design reference: openspec/changes/reports/design.md
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.core.exceptions import ValidationError
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


# ──────────────────────────────────────────────
# ReportGenerator (Phase 3)
# ──────────────────────────────────────────────


class ReportGenerator:
    """Convert rendered HTML to PDF bytes via WeasyPrint (RF-057).

    Usage:
        generator = ReportGenerator()
        pdf_bytes = generator.generate_pdf(html)
        pdf_bytes, _ = generator.generate_report("project", uuid, user)
    """

    def generate_pdf(self, html: str) -> bytes:
        """Convert an HTML string to PDF bytes using WeasyPrint.

        Args:
            html: Rendered Django template HTML string.

        Returns:
            PDF content as bytes.
        """
        import weasyprint

        return weasyprint.HTML(string=html).write_pdf()

    def generate_report(
        self,
        report_type: str,
        entity_id: str | UUID,
        user,
    ) -> tuple[bytes, str]:
        """Render a report to HTML and convert to PDF.

        Args:
            report_type: One of "project", "researcher", "center", "advances".
            entity_id: UUID string or UUID object of the target entity.
            user: Django User for context rendering.

        Returns:
            Tuple of (pdf_bytes, html_string).
        """
        renderer = ReportRenderer()
        html = renderer.render_html(report_type, entity_id, user)
        pdf = self.generate_pdf(html)
        return pdf, html


# ──────────────────────────────────────────────
# ReportApprovalService (Phase 3)
# ──────────────────────────────────────────────


class ReportApprovalService:
    """Manage report approvals with RN-017 guard, audit, and metadata (RN-018).

    Usage:
        service = ReportApprovalService()
        approval = service.approve(report, user)
    """

    @staticmethod
    def has_pending_progress_reports(project) -> bool:
        """Check RN-017: project has pending (enviado/en_revision/observado) progress reports.

        Delegates to ProjectService for the actual query.
        """
        from apps.projects.services import ProjectService

        return ProjectService.has_pending_progress_reports(project)

    def approve(self, report, user):
        """Approve a report — guards, creates approval record, emits audit.

        Args:
            report: Report instance to approve.
            user: Django User performing the approval.

        Returns:
            The created ReportApproval instance.

        Raises:
            ValidationError: If RN-017 guard blocks (pending progress reports).
        """
        from apps.accounts.audit import AuditEventEmitter, AuditEventType
        from apps.reports.models import ReportApproval, ReportStatus, ReportType

        # ── RN-017: pending progress guard (project type only) ──
        if report.report_type == ReportType.PROJECT:
            from apps.projects.models import Project

            try:
                project = Project.objects.only("pk").get(pk=report.entity_id)
            except Project.DoesNotExist:
                raise ValidationError(
                    "Project not found for this report's entity_id."
                )

            if self.has_pending_progress_reports(project):
                raise ValidationError("Pending progress reports must be reviewed")

        # ── Create approval record (RN-018: metadata) ──
        approval = ReportApproval.objects.create(
            report=report,
            approved_by=user,
            report_version=report.version,
        )

        # ── Update report status ──
        report.status = ReportStatus.APPROVED
        report.save(update_fields=["status"])

        # ── Audit: REPORT_APPROVED (FR-007, RF-058) ──
        AuditEventEmitter().emit(
            event_type=AuditEventType.REPORT_APPROVED,
            user=user,
            institution_id=report.institution_id,
            details={
                "report_type": report.report_type,
                "entity_id": str(report.entity_id),
                "report_id": str(report.pk),
                "approval_id": str(approval.pk),
                "version": report.version,
            },
        )

        logger.info(
            "Report %s (%s) approved by %s (version %d)",
            report.pk,
            report.report_type,
            user.email,
            report.version,
        )

        return approval
