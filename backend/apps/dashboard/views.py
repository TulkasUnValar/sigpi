"""
ViewSets for dashboard endpoints.

DashboardViewSet exposes the /api/dashboard/summary/ endpoint with 14 indicators.
Institution-scoped via request.institution_id (set by TenantMiddleware).

SupersetEmbedView provides embed configuration for Apache Superset dashboards.
"""

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.permissions import IsDashboardAuthorized
from apps.dashboard.serializers import DashboardSummarySerializer
from apps.dashboard.services import DashboardSummaryService


class DashboardViewSet(viewsets.ViewSet):
    """
    Dashboard endpoints for institutional metrics.

    Provides:
    - GET /api/dashboard/summary/: 14 indicators + chart data

    Permissions: IsDashboardAuthorized (role-based)
    - Superadmin (level 1): full access
    - Admin (level 2): institution-scoped
    - Director (level 3): institution/center-scoped
    - Researcher (level 4): own projects only
    - Auditor (level 7): read-only
    """

    permission_classes = [IsAuthenticated, IsDashboardAuthorized]

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """
        GET /api/dashboard/summary/

        Returns aggregated metrics for the authenticated user's institution.

        Response shape:
        {
            'indicators': {
                'IND-001': int,      # Total proyectos activos
                'IND-002': list,     # Proyectos por centro
                'IND-003': list,     # Proyectos por estado
                'IND-004': int,      # Avances pendientes
                'IND-005': int,      # Avances observados
                'IND-006': float,    # Cumplimiento %
                'IND-007': str,      # Presupuesto aprobado
                'IND-008': str,      # Presupuesto ejecutado
                'IND-009': str,      # Saldo presupuestal
                'IND-010': list,     # Productos por proyecto (top 10)
                'IND-011': list,     # Productos por investigador (top 10)
                'IND-012': dict,     # {total, complete, rate}
                'IND-013': int,      # Convocatorias abiertas
                'IND-014': int,      # Proyectos en convocatorias externas
            },
            'charts': {
                'projects_by_status': list,
                'projects_by_center': list,
                'budget': {approved, executed, balance},
                'progress_reports': {pending, observed, approved}
            }
        }
        """
        institution_id = request.institution_id

        if not institution_id:
            return Response(
                {"detail": "Institution context required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Compute summary via service
        summary_data = DashboardSummaryService.summary(
            institution_id=institution_id, user=request.user
        )

        # Serialize response
        serializer = DashboardSummarySerializer(summary_data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class SupersetEmbedView(APIView):
    """
    Get Superset embed configuration for dashboards.

    Returns the Superset URL and dashboard ID for iframe integration.
    Requires authentication. Future: generate guest tokens for embedded analytics.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """
        GET /api/dashboard/superset-embed/

        Returns Superset embed configuration.

        Query params:
            dashboard_id: Superset dashboard ID (default: "1")

        Response shape:
        {
            'superset_url': str,
            'dashboard_id': str,
            'embed_url': str,
        }
        """
        dashboard_id = request.query_params.get("dashboard_id", "1")

        return Response(
            {
                "superset_url": settings.SUPERSET_URL,
                "dashboard_id": dashboard_id,
                "embed_url": f"{settings.SUPERSET_URL}/superset/dashboard/{dashboard_id}/",
            },
            status=status.HTTP_200_OK,
        )
