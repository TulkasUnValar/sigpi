"""
Dashboard summary service — aggregates 14 indicators for institutional metrics.

Provides computed metrics across projects, budgets, researchers, products,
calls, and progress reports. All queries are institution-scoped.

Design reference: dashboard metrics spec (14 indicators IND-001 to IND-014)
"""

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.budgets.models import Budget, BudgetExecution
from apps.calls.models import Call, CallProject, CallStatus
from apps.products.models import ProductAuthor, ResearchProduct
from apps.progress.models import ProgressReport, ProgressStatus
from apps.projects.models import Project
from apps.researchers.models import Researcher


class DashboardSummaryService:
    """
    Aggregates 14 dashboard indicators for an institution.

    IND-001: Total proyectos activos
    IND-002: Proyectos por centro de investigación
    IND-003: Proyectos por estado
    IND-004: Avances pendientes (en_revision)
    IND-005: Avances observados
    IND-006: Cumplimiento de reportes (%)
    IND-007: Presupuesto aprobado total
    IND-008: Presupuesto ejecutado
    IND-009: Saldo presupuestal
    IND-010: Productos por proyecto (top 10)
    IND-011: Productos por investigador (top 10)
    IND-012: Perfiles de investigadores completos
    IND-013: Convocatorias abiertas
    IND-014: Proyectos en convocatorias externas
    """

    @staticmethod
    def summary(institution_id, user=None):
        """
        Compute all 14 indicators for the given institution.

        Args:
            institution_id: UUID of the institution
            user: Optional user for future scoping (not used in current implementation)

        Returns:
            dict with 'indicators' and 'charts' sections
        """
        indicators = {}
        charts = {}

        # Base querysets scoped to institution
        projects_qs = Project.objects.filter(institution_id=institution_id)
        active_projects_qs = projects_qs.filter(is_active=True)
        progress_reports_qs = ProgressReport.objects.filter(institution_id=institution_id)
        budgets_qs = Budget.objects.filter(institution_id=institution_id)
        researchers_qs = Researcher.objects.filter(institution_id=institution_id)
        products_qs = ResearchProduct.objects.filter(institution_id=institution_id)
        calls_qs = Call.objects.filter(institution_id=institution_id)

        # ──────────────────────────────────────────────
        # IND-001: Total proyectos activos
        # ──────────────────────────────────────────────
        indicators["IND-001"] = active_projects_qs.count()

        # ──────────────────────────────────────────────
        # IND-002: Proyectos por centro de investigación
        # ──────────────────────────────────────────────
        projects_by_center = (
            active_projects_qs.values("center__id", "center__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Transform to expected format: [{center_id, name, count}]
        indicators["IND-002"] = [
            {"center_id": item["center__id"], "name": item["center__name"], "count": item["count"]}
            for item in projects_by_center
        ]

        # ──────────────────────────────────────────────
        # IND-003: Proyectos por estado
        # ──────────────────────────────────────────────
        projects_by_status = (
            projects_qs.values("status").annotate(count=Count("id")).order_by("-count")
        )
        indicators["IND-003"] = list(projects_by_status)

        # ──────────────────────────────────────────────
        # IND-004: Avances pendientes (en_revision)
        # ──────────────────────────────────────────────
        indicators["IND-004"] = progress_reports_qs.filter(
            status=ProgressStatus.EN_REVISION
        ).count()

        # ──────────────────────────────────────────────
        # IND-005: Avances observados
        # ──────────────────────────────────────────────
        indicators["IND-005"] = progress_reports_qs.filter(status=ProgressStatus.OBSERVADO).count()

        # ──────────────────────────────────────────────
        # IND-006: Cumplimiento de reportes (%)
        # Regla: approved_progress_reports / expected_periods * 100
        # Expected periods = simplified calculation based on active projects and years span
        # ──────────────────────────────────────────────
        approved_reports = progress_reports_qs.filter(status=ProgressStatus.APROBADO).count()

        # Calculate expected periods: sum of years each active project has been running
        from django.utils import timezone

        current_year = timezone.now().year

        expected_periods = 0
        for project in active_projects_qs.values("start_date", "estimated_end_date"):
            if project["start_date"]:
                start_year = project["start_date"].year
                end_year = (
                    project["estimated_end_date"].year
                    if project["estimated_end_date"]
                    else current_year
                )
                # Years span = end_year - start_year + 1 (inclusive)
                years_span = max(1, end_year - start_year + 1)
                expected_periods += years_span

        # Compliance rate: approved / expected * 100
        if expected_periods > 0:
            compliance_rate = (Decimal(approved_reports) / Decimal(expected_periods)) * Decimal(
                "100"
            )
        else:
            compliance_rate = Decimal("0.00")

        indicators["IND-006"] = float(compliance_rate)

        # ──────────────────────────────────────────────
        # IND-007: Presupuesto aprobado total
        # ──────────────────────────────────────────────
        approved_budget = budgets_qs.aggregate(
            total=Coalesce(Sum("approved_amount"), Decimal("0.00"))
        )["total"]
        indicators["IND-007"] = f"{approved_budget:.2f}"

        # ──────────────────────────────────────────────
        # IND-008: Presupuesto ejecutado
        # ──────────────────────────────────────────────
        executed_budget = BudgetExecution.objects.filter(
            line__budget__institution_id=institution_id
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        indicators["IND-008"] = f"{executed_budget:.2f}"

        # ──────────────────────────────────────────────
        # IND-009: Saldo presupuestal
        # ──────────────────────────────────────────────
        balance = approved_budget - executed_budget
        indicators["IND-009"] = f"{balance:.2f}"

        # ──────────────────────────────────────────────
        # IND-010: Productos por proyecto (top 10)
        # ──────────────────────────────────────────────
        products_by_project = (
            products_qs.values("project__id", "project__title")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        # Transform to expected format: [{project_id, project_title, count}]
        indicators["IND-010"] = [
            {
                "project_id": item["project__id"],
                "project_title": item["project__title"],
                "count": item["count"],
            }
            for item in products_by_project
        ]

        # ──────────────────────────────────────────────
        # IND-011: Productos por investigador (top 10)
        # Count products where researcher is an author (via ProductAuthor)
        # ──────────────────────────────────────────────
        products_by_researcher = (
            ProductAuthor.objects.filter(product__institution_id=institution_id)
            .values("researcher__id", "researcher__first_name", "researcher__last_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        # Transform to expected format: [{researcher_id, researcher_name, count}]
        indicators["IND-011"] = [
            {
                "researcher_id": item["researcher__id"],
                "researcher_name": (
                    f"{item['researcher__first_name']} {item['researcher__last_name']}"
                ),
                "count": item["count"],
            }
            for item in products_by_researcher
        ]

        # ──────────────────────────────────────────────
        # IND-012: Perfiles de investigadores completos
        # Perfil completo si tiene:
        # - Al menos una afiliación (ResearcherAffiliation with is_primary=True)
        # - Al menos un perfil externo (ExternalProfile)
        # - academic_formation not empty
        # Return: {total: N, complete: N, rate: percentage}
        # ──────────────────────────────────────────────
        total_researchers = researchers_qs.count()

        # Researchers with at least one primary affiliation
        researchers_with_primary_affiliation = researchers_qs.filter(
            affiliations__is_primary=True
        ).distinct()

        # Researchers with at least one external profile
        researchers_with_external_profile = researchers_qs.filter(
            external_profiles__isnull=False
        ).distinct()

        # Researchers with academic_formation not empty
        researchers_with_formation = researchers_qs.exclude(
            Q(academic_formation="") | Q(academic_formation__isnull=True)
        )

        # Complete profile: intersection of all three conditions
        complete_researchers = (
            researchers_with_primary_affiliation.filter(
                id__in=researchers_with_external_profile.values("id")
            )
            .filter(id__in=researchers_with_formation.values("id"))
            .count()
        )

        if total_researchers > 0:
            completeness_rate = (
                Decimal(complete_researchers) / Decimal(total_researchers)
            ) * Decimal("100")
        else:
            completeness_rate = Decimal("0.00")

        indicators["IND-012"] = {
            "total": total_researchers,
            "complete": complete_researchers,
            "rate": float(completeness_rate),
        }

        # ──────────────────────────────────────────────
        # IND-013: Convocatorias abiertas
        # ──────────────────────────────────────────────
        indicators["IND-013"] = calls_qs.filter(status=CallStatus.ABIERTA).count()

        # ──────────────────────────────────────────────
        # IND-014: Proyectos en convocatorias externas
        # Projects linked to external calls (CallProject with call.call_type='external')
        # ──────────────────────────────────────────────
        projects_in_external_calls = (
            CallProject.objects.filter(
                call__institution_id=institution_id, call__call_type="external"
            )
            .values("project__id")
            .distinct()
            .count()
        )
        indicators["IND-014"] = projects_in_external_calls

        # ──────────────────────────────────────────────
        # CHARTS DATA
        # ──────────────────────────────────────────────

        # projects_by_status (reuse IND-003 data)
        charts["projects_by_status"] = indicators["IND-003"]

        # projects_by_center (reuse IND-002 data)
        charts["projects_by_center"] = indicators["IND-002"]

        # budget: {approved, executed, balance}
        charts["budget"] = {
            "approved": indicators["IND-007"],
            "executed": indicators["IND-008"],
            "balance": indicators["IND-009"],
        }

        # progress_reports: {pending, observed, approved}
        approved_count = progress_reports_qs.filter(status=ProgressStatus.APROBADO).count()
        charts["progress_reports"] = {
            "pending": indicators["IND-004"],
            "observed": indicators["IND-005"],
            "approved": approved_count,
        }

        return {"indicators": indicators, "charts": charts}
