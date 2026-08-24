"""
Integration tests: project report budget summary (RN-022).

Covers the reports delta spec (RF-050):
- report context includes budget_summary when the project has a registered Budget
- report context excludes/None budget_summary when no Budget exists
- template renders approved, executed and balance from the budgets summary

STRICT TDD (RED phase): tests written BEFORE services/template wiring.
The summary endpoint (RF-B07) was verified in apps/budgets/tests before
this template wiring (contract stability NFR).
"""

from decimal import Decimal

from apps.reports.services import ReportRenderer
from apps.reports.tests.test_services import _make_center, _make_project, _make_researcher


class TestProjectReportBudgetSummary:
    """ReportRenderer project context + template — budget_summary (RN-022)."""

    def _project(self):
        from apps.institutions.models import Institution

        inst = Institution.objects.create(name="U-BS", code="UBS")
        center = _make_center(inst)
        researcher = _make_researcher(inst)
        return _make_project(inst, center, researcher)

    def test_context_includes_budget_summary_when_budget_exists(self, db):
        """Context carries approved/executed/balance from BudgetSummaryService."""
        from apps.budgets.tests.conftest import (
            BudgetExecutionFactory,
            BudgetFactory,
            BudgetLineFactory,
        )

        project = self._project()
        budget = BudgetFactory(
            project=project,
            institution=project.institution,
            approved_amount=Decimal("1000.00"),
        )
        line = BudgetLineFactory(budget=budget, approved_amount=Decimal("1000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("250.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("150.00"))

        context = ReportRenderer()._build_context("project", project.pk)
        summary = context["budget_summary"]
        assert summary is not None
        assert summary["approved"] == Decimal("1000.00")
        assert summary["executed"] == Decimal("400.00")
        assert summary["balance"] == Decimal("600.00")

    def test_context_budget_summary_none_when_no_budget(self, db):
        """Project without a Budget yields budget_summary=None (absent/empty)."""
        project = self._project()

        context = ReportRenderer()._build_context("project", project.pk)
        assert context["budget_summary"] is None

    def test_template_renders_budget_summary_values(self, db):
        """Rendered HTML shows approved, executed and balance amounts."""
        from django.template import Context, Template

        from apps.budgets.tests.conftest import (
            BudgetExecutionFactory,
            BudgetFactory,
            BudgetLineFactory,
        )

        project = self._project()
        budget = BudgetFactory(
            project=project,
            institution=project.institution,
            approved_amount=Decimal("3000.00"),
        )
        line = BudgetLineFactory(budget=budget, approved_amount=Decimal("3000.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("750.00"))
        BudgetExecutionFactory(line=line, amount=Decimal("250.00"))

        html = ReportRenderer().render_html("project", str(project.pk), None)

        # floatformat:2 is locale-aware (comma vs dot separator), so compare
        # against the same filter output rather than hardcoding a separator.
        fmt = Template("{{ v|floatformat:2 }}")
        assert fmt.render(Context({"v": Decimal("3000.00")})) in html  # approved
        assert fmt.render(Context({"v": Decimal("1000.00")})) in html  # executed
        assert fmt.render(Context({"v": Decimal("2000.00")})) in html  # balance

    def test_template_empty_state_when_no_budget(self, db):
        """Project without a Budget renders the empty-state section."""
        project = self._project()

        html = ReportRenderer().render_html("project", str(project.pk), None)
        assert "Budget data not available" in html