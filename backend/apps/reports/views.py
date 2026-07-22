"""
DRF Views for the Reports / Informes module (§6.6).

Phase 2: ReportPreviewView — GET preview returns {"html": "..."}
with permission checks (CanGenerateReport, RN-015).

Spec reference:   sdd/reports/spec — RF-056, RN-015
Design reference: openspec/changes/reports/design.md
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.permissions import CanGenerateReport
from apps.reports.serializers import PreviewSerializer
from apps.reports.services import ReportRenderer

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# ReportPreviewView
# ──────────────────────────────────────────────

_VALID_PREVIEW_TYPES = frozenset({"project", "researcher", "center", "advances"})


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
        if report_type not in _VALID_PREVIEW_TYPES:
            return Response(
                {"error": f"Invalid report type: {report_type!r}"},
                status=400,
            )

        # RN-015: verify entity belongs to user's institution
        institution_id = self._get_entity_institution_id(report_type, entity_id)
        if institution_id is None:
            raise Http404("Entity not found.")

        user_institution_id = getattr(request, "institution_id", None)
        is_superadmin = request.user.is_superuser

        if not is_superadmin:
            if not user_institution_id or str(user_institution_id) != str(institution_id):
                # Also check via active_membership.institution_id
                membership = getattr(request, "active_membership", None)
                if membership and str(membership.institution_id) == str(institution_id):
                    pass  # OK
                else:
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

        serializer = PreviewSerializer({"html": html})
        return Response(serializer.data)

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _get_entity_institution_id(report_type: str, entity_id: str | UUID) -> UUID | None:
        """Look up the institution_id of the entity being previewed.

        Returns None if the entity does not exist or the UUID is invalid.
        """
        # Django URL converter <uuid:...> passes a UUID object directly.
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
                project = Project.objects.get(pk=entity_uuid)
                return project.institution_id
            except Project.DoesNotExist:
                return None
        elif report_type == "researcher":
            from apps.researchers.models import Researcher

            try:
                researcher = Researcher.objects.get(pk=entity_uuid)
                return researcher.institution_id
            except Researcher.DoesNotExist:
                return None
        elif report_type == "center":
            from apps.institutions.models import ResearchCenter

            try:
                center = ResearchCenter.objects.get(pk=entity_uuid)
                return center.institution_id
            except ResearchCenter.DoesNotExist:
                return None

        return None
