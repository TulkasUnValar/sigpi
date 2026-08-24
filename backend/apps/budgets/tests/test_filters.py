"""
Unit tests for budgets filters — STRICT TDD (RED phase).

Covers BudgetFilter per design.md:
- project (exact UUID filter)
- institution (exact UUID filter)
- status (ChoiceFilter)
- name (icontains search)

Strict TDD: written BEFORE filters.py exists.
Expected failure: ImportError.

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — RF-B06
Design reference: openspec/changes/budgets/design.md — Filtering
"""

import pytest


class TestBudgetFilter:
    """BudgetFilter: filter by project, institution, status, name."""

    @pytest.mark.django_db
    def test_filter_by_project(self):
        from apps.budgets.filters import BudgetFilter
        from apps.budgets.tests.conftest import BudgetFactory

        b1 = BudgetFactory(name="Budget A")
        b2 = BudgetFactory(name="Budget B")

        f = BudgetFilter(
            data={"project": str(b1.project_id)},
            queryset=__import__("apps.budgets.models", fromlist=["Budget"]).Budget.objects.all(),
        )
        qs = f.qs
        assert b1 in qs
        assert b2 not in qs

    @pytest.mark.django_db
    def test_filter_by_institution(self):
        from apps.budgets.filters import BudgetFilter
        from apps.budgets.tests.conftest import BudgetFactory
        from apps.institutions.tests.conftest import InstitutionFactory

        inst1 = InstitutionFactory()
        inst2 = InstitutionFactory()
        b1 = BudgetFactory(institution=inst1)
        b2 = BudgetFactory(institution=inst2)

        f = BudgetFilter(
            data={"institution": str(inst1.id)},
            queryset=__import__("apps.budgets.models", fromlist=["Budget"]).Budget.objects.all(),
        )
        qs = f.qs
        assert b1 in qs
        assert b2 not in qs

    @pytest.mark.django_db
    def test_filter_by_status(self):
        from apps.budgets.filters import BudgetFilter
        from apps.budgets.models import Budget, BudgetStatus
        from apps.budgets.tests.conftest import BudgetFactory

        draft = BudgetFactory(status=BudgetStatus.DRAFT)
        approved = BudgetFactory(status=BudgetStatus.APPROVED)

        f = BudgetFilter(data={"status": BudgetStatus.APPROVED}, queryset=Budget.objects.all())
        qs = f.qs
        assert approved in qs
        assert draft not in qs

    @pytest.mark.django_db
    def test_filter_by_name_icontains(self):
        from apps.budgets.filters import BudgetFilter
        from apps.budgets.models import Budget
        from apps.budgets.tests.conftest import BudgetFactory

        BudgetFactory(name="Research Infrastructure")
        BudgetFactory(name="Lab Equipment")

        f = BudgetFilter(data={"name": "research"}, queryset=Budget.objects.all())
        qs = f.qs
        assert qs.count() == 1
        assert qs.first().name == "Research Infrastructure"

    @pytest.mark.django_db
    def test_no_filters_returns_all(self):
        from apps.budgets.filters import BudgetFilter
        from apps.budgets.models import Budget
        from apps.budgets.tests.conftest import BudgetFactory

        BudgetFactory()
        BudgetFactory()

        f = BudgetFilter(data={}, queryset=Budget.objects.all())
        assert f.qs.count() == Budget.objects.count()
