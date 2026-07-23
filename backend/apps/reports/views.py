"""
DRF Views for the Reports / Informes module (§6.6).

Phase 2: ReportPreviewView — GET preview returns {"html": "..."}
with permission checks (CanGenerateReport, RN-015).
Phase 3: ReportPDFView — GET PDF streams FileResponse (RF-057).
         ReportApprovalView — POST approve with RN-017 guard (RN-016, RN-017).

Spec reference:   sdd/reports/spec — RF-056, RF-057, RF-058, RN-015–RN-018
Design reference: openspec/changes/reports/design.md
"""

from __future__ import annotations

import logging
from io import BytesIO
from uuid import UUID

from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import AuditEventEmitter, AuditEventType
from apps.reports.models import Report, ReportStatus
from apps.reports.permissions import CanGenerateReport, IsCenterDirectorForProject
from apps.reports.serializers import PreviewSerializer
from apps.reports.services import ReportApprovalService, ReportGenerator, ReportRenderer

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Valid report types (shared across views)
# ──────────────────────────────────────────────

_VALID_REPORT_TYPES = frozenset({"project", "researcher", "center", "advances"})


# ──────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────


def _get_entity_institution_id(report_type: str, entity_id: str | UUID) -> UUID | None:
    """Look up the institution_id of the entity for scoping checks (RN-015).

    Returns None if the entity does not exist or the UUID is invalid.
    """
    if isinstance(entity_id, UUID):
        entity_uuid = entity_id
    else:
        try:
            entity_uuid = UUID(entity_id)
        except (ValueError, AttributeError):
            return None

    if report_type in ("project", "advances"):
        from apps.projects.models import Project

        try:
            project = Project.objects.only("institution_id").get(pk=entity_uuid)
            return project.institution_id
        except Project.DoesNotExist:
            return None
    elif report_type == "researcher":
        from apps.researchers.models import Researcher

        try:
            researcher = Researcher.objects.only("institution_id").get(pk=entity_uuid)
            return researcher.institution_id
        except Researcher.DoesNotExist:
            return None
    elif report_type == "center":
        from apps.institutions.models import ResearchCenter

        try:
            center = ResearchCenter.objects.only("institution_id").get(pk=entity_uuid)
            return center.institution_id
        except ResearchCenter.DoesNotExist:
            return None

    return None


def _check_institution_access(request, institution_id: UUID) -> bool:
    """Verify the user's active institution matches the entity (RN-015).

    Superadmins bypass. Returns True if access is allowed.
    """
    if request.user.is_superuser:
        return True

    user_institution_id = getattr(request, "institution_id", None)
    if user_institution_id and str(user_institution_id) == str(institution_id):
        return True

    membership = getattr(request, "active_membership", None)
    if membership and str(membership.institution_id) == str(institution_id):
        return True

    return False


# ──────────────────────────────────────────────
# ReportPreviewView (Phase 2)
# ──────────────────────────────────────────────


class ReportPreviewView(APIView):
    """GET /api/reports/{type}/{id}/preview/ → {"html": "..."}

    Permission: CanGenerateReport (role ≤ 4 + same-institution).
    Institution scoping (RN-015): the entity being previewed MUST
    belong to the user's active institution.
    """

    permission_classes = [IsAuthenticated, CanGenerateReport]

    def get(
        self,
        request: Request,
        report_type: str,
        entity_id: str,
    ) -> Response:
        # Validate report_type
        if report_type not in _VALID_REPORT_TYPES:
            return Response(
                {"error": f"Invalid report type: {report_type!r}"},
                status=400,
            )

        # RN-015: verify entity belongs to user's institution
        institution_id = _get_entity_institution_id(report_type, entity_id)
        if institution_id is None:
            raise Http404("Entity not found.")

        if not _check_institution_access(request, institution_id):
            return Response(
                {"error": "You do not have access to this entity."},
                status=403,
            )

        # Render
        try:
            renderer = ReportRenderer()
            html = renderer.render_html(report_type, entity_id, request.user)
        except ValueError as exc:
            raise Http404(str(exc)) from exc
        except Exception as exc:
            logger.exception("Preview rendering failed for %s/%s", report_type, entity_id)
            return Response(
                {"error": f"Preview rendering failed: {exc}"},
                status=500,
            )

        serializer = PreviewSerializer({"html": html})
        return Response(serializer.data)


# ──────────────────────────────────────────────
# ReportPDFView (Phase 3)
# ──────────────────────────────────────────────


class ReportPDFView(APIView):
    """GET /api/reports/{type}/{id}/pdf/ → FileResponse PDF (RF-050–RF-053, RF-057).

    Permission: CanGenerateReport (role ≤ 4 + same-institution).
    Emits REPORT_GENERATED audit event on success (RF-058).
    """

    permission_classes = [IsAuthenticated, CanGenerateReport]

    def get(
        self,
        request: Request,
        report_type: str,
        entity_id: str,
    ) -> FileResponse | Response:
        # Validate report_type
        if report_type not in _VALID_REPORT_TYPES:
            return Response(
                {"error": f"Invalid report type: {report_type!r}"},
                status=400,
            )

        # RN-015: verify entity belongs to user's institution
        institution_id = _get_entity_institution_id(report_type, entity_id)
        if institution_id is None:
            raise Http404("Entity not found.")

        if not _check_institution_access(request, institution_id):
            return Response(
                {"error": "You do not have access to this entity."},
                status=403,
            )

        # Generate PDF
        try:
            generator = ReportGenerator()
            pdf_bytes, _html = generator.generate_report(
                report_type, entity_id, request.user
            )
        except ValueError as exc:
            raise Http404(str(exc)) from exc
        except Exception as exc:
            logger.exception("PDF generation failed for %s/%s", report_type, entity_id)
            return Response(
                {"error": f"PDF generation failed: {exc}"},
                status=500,
            )

        # Create Report record for audit trail (RF-058)
        report = Report.objects.create(
            report_type=report_type,
            entity_id=entity_id,
            institution_id=institution_id,
            status=ReportStatus.GENERATED,
            version=1,
            created_by=request.user,
        )

        # Audit: REPORT_GENERATED (FR-007, RF-058)
        AuditEventEmitter().emit(
            event_type=AuditEventType.REPORT_GENERATED,
            user=request.user,
            institution_id=institution_id,
            details={
                "report_type": report_type,
                "entity_id": str(entity_id),
                "report_id": str(report.pk),
            },
        )

        logger.info(
            "PDF report generated: type=%s entity=%s by %s",
            report_type,
            entity_id,
            request.user.email,
        )

        return FileResponse(
            BytesIO(pdf_bytes),
            content_type="application/pdf",
            as_attachment=False,
            filename=f"{report_type}_report.pdf",
        )


# ──────────────────────────────────────────────
# ReportApprovalView (Phase 3)
# ──────────────────────────────────────────────


class ReportApprovalView(APIView):
    """POST /api/reports/{type}/{id}/approve/ → 200/409 (RN-016, RN-017).

    Permission: IsAuthenticated + center-director check (manual).
    RN-016: only center director can approve.
    RN-017: blocked if project has pending progress reports.
    """

    permission_classes = [IsAuthenticated]

    def post(
        self,
        request: Request,
        report_type: str,
        entity_id: str,
    ) -> Response:
        # Validate report_type
        if report_type not in _VALID_REPORT_TYPES:
            return Response(
                {"error": f"Invalid report type: {report_type!r}"},
                status=400,
            )

        # RN-016: director permission check
        if not self._user_is_entity_director(request, report_type, entity_id):
            return Response(
                {"error": "You must be a center director to approve reports."},
                status=403,
            )

        # Get or create Report record
        report = self._get_or_create_report(request, report_type, entity_id)

        # Approve via service (RN-017 guard, RN-018 metadata, audit)
        try:
            service = ReportApprovalService()
            approval = service.approve(report, request.user)
        except ValidationError as exc:
            error_msg = (
                exc.messages[0]
                if hasattr(exc, "messages") and exc.messages
                else str(exc)
            )
            return Response({"error": error_msg}, status=409)

        return Response(
            {
                "status": "approved",
                "report_id": str(report.pk),
                "approval_id": str(approval.pk),
            }
        )

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _user_is_entity_director(
        request: Request,
        report_type: str,
        entity_id: str | UUID,
    ) -> bool:
        """Check if the user has director authority over this entity (RN-016)."""
        if request.user.is_superuser:
            return True

        entity_uuid = entity_id if isinstance(entity_id, UUID) else UUID(entity_id)

        if report_type in ("project", "advances"):
            from apps.projects.models import Project

            try:
                project = Project.objects.only("center_id").get(pk=entity_uuid)
            except Project.DoesNotExist:
                raise Http404("Entity not found.")

            perm = IsCenterDirectorForProject()
            if not perm.has_permission(request, None):
                return False
            return perm.has_object_permission(request, None, project)

        elif report_type == "center":
            from apps.accounts.permissions import HasRoleLevelOrHigher

            membership = getattr(request, "active_membership", None)
            if not membership or not HasRoleLevelOrHigher.has_level(request, 3):
                return False
            return membership.centers.filter(pk=entity_uuid).exists()

        elif report_type == "researcher":
            from apps.accounts.permissions import HasRoleLevelOrHigher

            membership = getattr(request, "active_membership", None)
            if not membership or not HasRoleLevelOrHigher.has_level(request, 3):
                return False
            return membership.centers.exists()

        return False

    @staticmethod
    def _get_or_create_report(
        request: Request,
        report_type: str,
        entity_id: str | UUID,
    ) -> Report:
        """Find or create a Report record for the given type + entity."""
        entity_uuid = entity_id if isinstance(entity_id, UUID) else UUID(entity_id)

        report = Report.objects.filter(
            report_type=report_type,
            entity_id=entity_uuid,
        ).first()

        if report is not None:
            return report

        institution_id = _get_entity_institution_id(report_type, entity_uuid)
        if institution_id is None:
            raise Http404("Entity not found for report creation.")

        return Report.objects.create(
            report_type=report_type,
            entity_id=entity_uuid,
            institution_id=institution_id,
            status=ReportStatus.DRAFT,
            version=1,
            created_by=request.user,
        )
