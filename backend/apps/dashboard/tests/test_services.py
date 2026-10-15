"""
Service layer tests for dashboard — 14 indicators coverage.

Tests all dashboard indicators with controlled data:
- IND-001: Total proyectos activos
- IND-002: Proyectos por centro
- IND-003: Proyectos por estado
- IND-004: Avances pendientes (en_revision)
- IND-005: Avances observados
- IND-006: Cumplimiento de reportes (%)
- IND-007: Presupuesto aprobado
- IND-008: Presupuesto ejecutado
- IND-009: Saldo presupuestal
- IND-010: Productos por proyecto (top 10)
- IND-011: Productos por investigador (top 10)
- IND-012: Perfiles completos {total, complete, rate}
- IND-013: Convocatorias abiertas
- IND-014: Proyectos en convocatorias externas
"""

import datetime
from decimal import Decimal

from apps.dashboard.services import DashboardSummaryService


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(
        email=f"dash_{User.objects.count()}@test.edu", auth_source="local"
    )


class TestDashboardIndicators:
    """Test all 14 dashboard indicators."""

    def test_ind_001_active_projects_count(self, db):
        """IND-001: Counts only active projects."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        # 3 active projects
        ProjectFactory(institution=institution, is_active=True)
        ProjectFactory(institution=institution, is_active=True)
        ProjectFactory(institution=institution, is_active=True)
        # 2 inactive projects (should not count)
        ProjectFactory(institution=institution, is_active=False)
        ProjectFactory(institution=institution, is_active=False)

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-001"] == 3

    def test_ind_002_projects_by_center(self, db):
        """IND-002: Groups active projects by research center."""
        from apps.institutions.tests.conftest import InstitutionFactory, ResearchCenterFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        center1 = ResearchCenterFactory(institution=institution, name="Center Alpha")
        center2 = ResearchCenterFactory(institution=institution, name="Center Beta")

        ProjectFactory(institution=institution, center=center1, is_active=True)
        ProjectFactory(institution=institution, center=center1, is_active=True)
        ProjectFactory(institution=institution, center=center2, is_active=True)

        result = DashboardSummaryService.summary(institution.id)
        projects_by_center = result["indicators"]["IND-002"]
        assert len(projects_by_center) == 2
        assert any(p["center_id"] == center1.id and p["count"] == 2 for p in projects_by_center)
        assert any(p["center_id"] == center2.id and p["count"] == 1 for p in projects_by_center)

    def test_ind_003_projects_by_status(self, db):
        """IND-003: Groups all projects by status."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        ProjectFactory(institution=institution, status="borrador")
        ProjectFactory(institution=institution, status="aprobado")
        ProjectFactory(institution=institution, status="aprobado")
        ProjectFactory(institution=institution, status="en_ejecucion")

        result = DashboardSummaryService.summary(institution.id)
        projects_by_status = result["indicators"]["IND-003"]
        assert len(projects_by_status) == 3
        assert any(p["status"] == "borrador" and p["count"] == 1 for p in projects_by_status)
        assert any(p["status"] == "aprobado" and p["count"] == 2 for p in projects_by_status)
        assert any(p["status"] == "en_ejecucion" and p["count"] == 1 for p in projects_by_status)

    def test_ind_004_pending_advances(self, db):
        """IND-004: Counts progress reports in en_revision status."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.progress.tests.conftest import ProgressReportFactory

        institution = InstitutionFactory()
        ProgressReportFactory(institution=institution, status="en_revision")
        ProgressReportFactory(institution=institution, status="en_revision")
        ProgressReportFactory(institution=institution, status="aprobado")

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-004"] == 2

    def test_ind_005_observed_advances(self, db):
        """IND-005: Counts progress reports in observado status."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.progress.tests.conftest import ProgressReportFactory

        institution = InstitutionFactory()
        ProgressReportFactory(institution=institution, status="observado")
        ProgressReportFactory(institution=institution, status="observado")
        ProgressReportFactory(institution=institution, status="observado")
        ProgressReportFactory(institution=institution, status="aprobado")

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-005"] == 3

    def test_ind_006_compliance_rate(self, db):
        """IND-006: Calculates approved reports / expected periods."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.progress.tests.conftest import ProgressReportFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        # 1 active project spanning 2 years (2024-2025)
        project = ProjectFactory(
            institution=institution,
            is_active=True,
            start_date=datetime.date(2024, 1, 1),
            estimated_end_date=datetime.date(2025, 12, 31),
        )
        # 2 approved reports for this project
        ProgressReportFactory(institution=institution, project=project, status="aprobado")
        ProgressReportFactory(institution=institution, project=project, status="aprobado")

        result = DashboardSummaryService.summary(institution.id)
        # Expected: 2 years, Approved: 2, Rate: 100%
        assert result["indicators"]["IND-006"] == 100.0

    def test_ind_006_compliance_rate_zero_projects(self, db):
        """IND-006: Returns 0% when no expected periods."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-006"] == 0.0

    def test_ind_007_approved_budget(self, db):
        """IND-007: Sums approved budget amounts."""
        from apps.budgets.tests.conftest import BudgetFactory
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        BudgetFactory(institution=institution, approved_amount=Decimal("10000.00"))
        BudgetFactory(institution=institution, approved_amount=Decimal("5000.00"))

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-007"] == "15000.00"

    def test_ind_008_executed_budget(self, db):
        """IND-008: Sums all budget executions."""
        from apps.budgets.tests.conftest import (
            BudgetExecutionFactory,
            BudgetFactory,
            BudgetLineFactory,
        )
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        budget = BudgetFactory(institution=institution)
        # Create executions via lines
        line1 = BudgetLineFactory(budget=budget)
        line2 = BudgetLineFactory(budget=budget)
        BudgetExecutionFactory(line=line1, amount=Decimal("3000.00"))
        BudgetExecutionFactory(line=line2, amount=Decimal("2000.00"))

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-008"] == "5000.00"

    def test_ind_009_budget_balance(self, db):
        """IND-009: Calculates approved - executed."""
        from apps.budgets.tests.conftest import (
            BudgetExecutionFactory,
            BudgetFactory,
            BudgetLineFactory,
        )
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        budget = BudgetFactory(institution=institution, approved_amount=Decimal("10000.00"))
        line = BudgetLineFactory(budget=budget)
        BudgetExecutionFactory(line=line, amount=Decimal("3000.00"))

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-009"] == "7000.00"

    def test_ind_010_products_by_project(self, db):
        """IND-010: Returns top 10 projects by product count."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.products.tests.conftest import ProductFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        project1 = ProjectFactory(institution=institution)
        project2 = ProjectFactory(institution=institution)

        # project1: 3 products
        ProductFactory(institution=institution, project=project1)
        ProductFactory(institution=institution, project=project1)
        ProductFactory(institution=institution, project=project1)
        # project2: 1 product
        ProductFactory(institution=institution, project=project2)

        result = DashboardSummaryService.summary(institution.id)
        products_by_project = result["indicators"]["IND-010"]
        assert len(products_by_project) == 2
        assert products_by_project[0]["project_id"] == project1.id
        assert products_by_project[0]["count"] == 3
        assert products_by_project[1]["project_id"] == project2.id
        assert products_by_project[1]["count"] == 1

    def test_ind_011_products_by_researcher(self, db):
        """IND-011: Returns top 10 researchers by product authorship count."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.products.tests.conftest import ProductAuthorFactory, ProductFactory
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        institution = InstitutionFactory()
        researcher1 = ResearcherFactory(institution=institution)
        researcher2 = ResearcherFactory(institution=institution)
        project = ProjectFactory(institution=institution)

        product1 = ProductFactory(institution=institution, project=project)
        product2 = ProductFactory(institution=institution, project=project)
        product3 = ProductFactory(institution=institution, project=project)

        # researcher1: 2 products
        ProductAuthorFactory(product=product1, researcher=researcher1)
        ProductAuthorFactory(product=product2, researcher=researcher1)
        # researcher2: 1 product
        ProductAuthorFactory(product=product3, researcher=researcher2)

        result = DashboardSummaryService.summary(institution.id)
        products_by_researcher = result["indicators"]["IND-011"]
        assert len(products_by_researcher) == 2
        assert products_by_researcher[0]["researcher_id"] == researcher1.id
        assert products_by_researcher[0]["count"] == 2
        assert products_by_researcher[1]["researcher_id"] == researcher2.id
        assert products_by_researcher[1]["count"] == 1

    def test_ind_012_profile_completeness(self, db):
        """IND-012: Calculates profile completeness rate."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.researchers.tests.conftest import (
            ExternalProfileFactory,
            ResearcherAffiliationFactory,
            ResearcherFactory,
        )

        institution = InstitutionFactory()

        # Complete profile: primary affiliation + external profile + academic_formation
        r1 = ResearcherFactory(institution=institution, academic_formation="PhD")
        ResearcherAffiliationFactory(researcher=r1, is_primary=True)
        ExternalProfileFactory(researcher=r1)

        # Incomplete: missing academic_formation
        r2 = ResearcherFactory(institution=institution, academic_formation="")
        ResearcherAffiliationFactory(researcher=r2, is_primary=True)
        ExternalProfileFactory(researcher=r2)

        # Incomplete: missing external profile
        r3 = ResearcherFactory(institution=institution, academic_formation="Master")
        ResearcherAffiliationFactory(researcher=r3, is_primary=True)

        # Incomplete: no primary affiliation
        r4 = ResearcherFactory(institution=institution, academic_formation="PhD")
        ExternalProfileFactory(researcher=r4)
        ResearcherAffiliationFactory(researcher=r4, is_primary=False)

        result = DashboardSummaryService.summary(institution.id)
        profile_data = result["indicators"]["IND-012"]
        assert profile_data["total"] == 4
        assert profile_data["complete"] == 1
        assert profile_data["rate"] == 25.0

    def test_ind_012_profile_completeness_zero_researchers(self, db):
        """IND-012: Returns 0% when no researchers."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-012"]["total"] == 0
        assert result["indicators"]["IND-012"]["complete"] == 0
        assert result["indicators"]["IND-012"]["rate"] == 0.0

    def test_ind_013_open_calls(self, db):
        """IND-013: Counts calls with status 'abierta'."""
        from apps.calls.tests.conftest import CallFactory
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        CallFactory(institution=institution, status="abierta")
        CallFactory(institution=institution, status="abierta")
        CallFactory(institution=institution, status="cerrada")

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-013"] == 2

    def test_ind_014_projects_in_external_calls(self, db):
        """IND-014: Counts projects linked to external calls."""
        from apps.calls.tests.conftest import CallFactory, CallProjectFactory
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution = InstitutionFactory()
        external_call = CallFactory(
            institution=institution, call_type="external", external_entity="External Org"
        )
        internal_call = CallFactory(institution=institution, call_type="internal")

        project1 = ProjectFactory(institution=institution)
        project2 = ProjectFactory(institution=institution)
        project3 = ProjectFactory(institution=institution)

        CallProjectFactory(call=external_call, project=project1)
        CallProjectFactory(call=external_call, project=project2)
        CallProjectFactory(call=internal_call, project=project3)

        result = DashboardSummaryService.summary(institution.id)
        assert result["indicators"]["IND-014"] == 2

    def test_charts_data_structure(self, db):
        """Verify charts section contains expected data."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        result = DashboardSummaryService.summary(institution.id)

        assert "charts" in result
        assert "projects_by_status" in result["charts"]
        assert "projects_by_center" in result["charts"]
        assert "budget" in result["charts"]
        assert "progress_reports" in result["charts"]

        # Budget chart should have approved, executed, balance
        budget_chart = result["charts"]["budget"]
        assert "approved" in budget_chart
        assert "executed" in budget_chart
        assert "balance" in budget_chart

        # Progress reports chart should have pending, observed, approved
        progress_chart = result["charts"]["progress_reports"]
        assert "pending" in progress_chart
        assert "observed" in progress_chart
        assert "approved" in progress_chart

    def test_institution_scoping(self, db):
        """Verify data is scoped to institution."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.projects.tests.conftest import ProjectFactory

        institution1 = InstitutionFactory()
        institution2 = InstitutionFactory()

        # Institution 1: 2 active projects
        ProjectFactory(institution=institution1, is_active=True)
        ProjectFactory(institution=institution1, is_active=True)

        # Institution 2: 3 active projects
        ProjectFactory(institution=institution2, is_active=True)
        ProjectFactory(institution=institution2, is_active=True)
        ProjectFactory(institution=institution2, is_active=True)

        result1 = DashboardSummaryService.summary(institution1.id)
        result2 = DashboardSummaryService.summary(institution2.id)

        assert result1["indicators"]["IND-001"] == 2
        assert result2["indicators"]["IND-001"] == 3
