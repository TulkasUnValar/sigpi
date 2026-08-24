"""
Integration tests for budgets ViewSets — STRICT TDD (RED phase).

Covers per spec/design:
- BudgetViewSet: list/create/retrieve/update/delete + summary @action
- BudgetLineViewSet: nested under /budgets/{id}/lines/
- BudgetExecutionViewSet: nested under lines/executions/ (RN-020)
- BudgetAttachmentViewSet: nested under /budgets/{id}/attachments/
- FundingSourceViewSet: nested under /projects/{pid}/funding-sources/

Error cases: duplicate budget 409, over-execution 400, cross-institution 404,
researcher mutation 403, unauthenticated 403.

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — API Contract
Design reference: openspec/changes/budgets/design.md — API and Permissions
"""

import datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
    FundingSource,
)
from apps.institutions.models import Institution

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def other_institution(db):
    return Institution.objects.create(name="Other University", code="OU001")


@pytest.fixture
def admin_role(db):
    return get_role("Admin Institucional")


@pytest.fixture
def director_role(db):
    return get_role("Director de Centro")


@pytest.fixture
def researcher_role(db):
    return get_role("Investigador")


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(email="admin@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(email="res@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def director_user(db, institution, director_role):
    user = User.objects.create_user(email="dir@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    return user


@pytest.fixture
def project(institution):
    from apps.projects.tests.conftest import ProjectFactory

    return ProjectFactory(institution=institution)


# ════════════════════════════════════════════════════════
# BudgetViewSet — CRUD
# ════════════════════════════════════════════════════════


class TestBudgetCRUD:
    def test_create_budget_as_admin(self, api_client, institution, admin_user, project):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:budget-list"),
            {"name": "Project Budget", "approved_amount": "10000.00", "project": str(project.id)},
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Project Budget"
        assert data["status"] == BudgetStatus.DRAFT
        assert data["institution"] == str(institution.id)

    def test_create_denied_for_researcher(
        self, api_client, institution, researcher_user, project
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("budgets:budget-list"),
            {"name": "Denied", "approved_amount": "100.00", "project": str(project.id)},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("budgets:budget-list"))
        assert r.status_code == 403

    def test_duplicate_budget_returns_409(self, api_client, institution, admin_user, project):
        _login(api_client, admin_user, institution)
        Budget.objects.create(
            project=project, institution=institution, name="Existing", approved_amount="100.00"
        )
        r = api_client.post(
            reverse("budgets:budget-list"),
            {"name": "Duplicate", "approved_amount": "100.00", "project": str(project.id)},
            content_type="application/json",
        )
        assert r.status_code == 409

    def test_retrieve_budget_as_researcher(
        self, api_client, institution, researcher_user, project
    ):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="500.00"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("budgets:budget-detail", kwargs={"pk": str(budget.pk)}))
        assert r.status_code == 200
        assert r.json()["name"] == "Budget"

    def test_update_budget_as_admin(self, api_client, institution, admin_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Old", approved_amount="500.00"
        )
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse("budgets:budget-detail", kwargs={"pk": str(budget.pk)}),
            {"name": "New Name"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_delete_budget_as_admin(self, api_client, institution, admin_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="ToDelete", approved_amount="100.00"
        )
        _login(api_client, admin_user, institution)
        r = api_client.delete(reverse("budgets:budget-detail", kwargs={"pk": str(budget.pk)}))
        assert r.status_code == 204
        assert not Budget.objects.filter(pk=budget.pk).exists()

    def test_cross_institution_budget_404(self, api_client, institution, researcher_user):
        other = Institution.objects.create(name="Other", code="OU002")
        from apps.projects.tests.conftest import ProjectFactory

        other_project = ProjectFactory(institution=other)
        other_budget = Budget.objects.create(
            project=other_project, institution=other, name="Other", approved_amount="10.00"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("budgets:budget-detail", kwargs={"pk": str(other_budget.pk)}))
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# BudgetViewSet — summary action
# ════════════════════════════════════════════════════════


class TestBudgetSummary:
    def test_summary_totals(self, api_client, institution, researcher_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        line = BudgetLine.objects.create(budget=budget, name="Rubro", approved_amount="1000.00")
        BudgetExecution.objects.create(
            line=line, amount="250.00", executed_at=datetime.date(2026, 5, 1)
        )
        BudgetExecution.objects.create(
            line=line, amount="150.00", executed_at=datetime.date(2026, 6, 1)
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("budgets:budget-summary", kwargs={"pk": str(budget.pk)}))
        assert r.status_code == 200
        data = r.json()
        assert data["approved"] == "1000.00"
        assert data["executed"] == "400.00"
        assert data["balance"] == "600.00"


# ════════════════════════════════════════════════════════
# BudgetLineViewSet — nested under budget
# ════════════════════════════════════════════════════════


class TestBudgetLineViewSet:
    def test_create_line_as_admin(self, api_client, institution, admin_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:budget-line-list", kwargs={"budget_pk": str(budget.pk)}),
            {"name": "Equipment", "approved_amount": "400.00"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Equipment"
        assert r.json()["budget"] == str(budget.pk)

    def test_list_lines(self, api_client, institution, researcher_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        BudgetLine.objects.create(budget=budget, name="A", approved_amount="100.00")
        BudgetLine.objects.create(budget=budget, name="B", approved_amount="200.00")
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("budgets:budget-line-list", kwargs={"budget_pk": str(budget.pk)}))
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    def test_create_line_denied_for_researcher(
        self, api_client, institution, researcher_user, project
    ):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("budgets:budget-line-list", kwargs={"budget_pk": str(budget.pk)}),
            {"name": "Denied", "approved_amount": "100.00"},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_update_line_as_admin(self, api_client, institution, admin_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        line = BudgetLine.objects.create(budget=budget, name="Old", approved_amount="100.00")
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse(
                "budgets:budget-line-detail",
                kwargs={"budget_pk": str(budget.pk), "pk": str(line.pk)},
            ),
            {"name": "New"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New"

    def test_delete_line_as_admin(self, api_client, institution, admin_user, project):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        line = BudgetLine.objects.create(budget=budget, name="Del", approved_amount="100.00")
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "budgets:budget-line-detail",
                kwargs={"budget_pk": str(budget.pk), "pk": str(line.pk)},
            )
        )
        assert r.status_code == 204
        assert not BudgetLine.objects.filter(pk=line.pk).exists()

    def test_list_lines_cross_institution_empty(
        self, api_client, institution, researcher_user, other_institution
    ):
        """Lines of a foreign budget are hidden (empty result, not leaked)."""
        from apps.projects.tests.conftest import ProjectFactory

        other_project = ProjectFactory(institution=other_institution)
        other_budget = Budget.objects.create(
            project=other_project,
            institution=other_institution,
            name="Foreign",
            approved_amount="100.00",
        )
        BudgetLine.objects.create(
            budget=other_budget, name="Secret Line", approved_amount="10.00"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("budgets:budget-line-list", kwargs={"budget_pk": str(other_budget.pk)})
        )
        assert r.status_code == 200
        assert r.json()["results"] == []


# ════════════════════════════════════════════════════════
# BudgetExecutionViewSet — nested under line
# ════════════════════════════════════════════════════════


class TestBudgetExecutionViewSet:
    def _make_budget_and_line(self, institution, project, amount="1000.00"):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount=amount
        )
        line = BudgetLine.objects.create(
            budget=budget, name="Rubro", approved_amount=amount
        )
        return budget, line

    def test_create_execution_within_limit(
        self, api_client, institution, admin_user, project
    ):
        budget, line = self._make_budget_and_line(institution, project)
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "budgets:line-execution-list",
                kwargs={"budget_pk": str(budget.pk), "line_pk": str(line.pk)},
            ),
            {"amount": "400.00", "executed_at": "2026-05-01"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["amount"] == "400.00"

    def test_execution_overrun_without_auth_400(
        self, api_client, institution, admin_user, project
    ):
        budget, line = self._make_budget_and_line(institution, project)
        BudgetExecution.objects.create(
            line=line, amount="900.00", executed_at=datetime.date(2026, 4, 1)
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "budgets:line-execution-list",
                kwargs={"budget_pk": str(budget.pk), "line_pk": str(line.pk)},
            ),
            {"amount": "200.00", "executed_at": "2026-05-01"},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_execution_overrun_with_auth_201(
        self, api_client, institution, admin_user, project
    ):
        budget, line = self._make_budget_and_line(institution, project)
        BudgetExecution.objects.create(
            line=line, amount="900.00", executed_at=datetime.date(2026, 4, 1)
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "budgets:line-execution-list",
                kwargs={"budget_pk": str(budget.pk), "line_pk": str(line.pk)},
            ),
            {
                "amount": "200.00",
                "executed_at": "2026-05-01",
                "authorized_by": str(admin_user.pk),
                "authorized_at": "2026-05-02",
            },
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_execution_denied_for_researcher(
        self, api_client, institution, researcher_user, project
    ):
        budget, line = self._make_budget_and_line(institution, project)
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "budgets:line-execution-list",
                kwargs={"budget_pk": str(budget.pk), "line_pk": str(line.pk)},
            ),
            {"amount": "100.00", "executed_at": "2026-05-01"},
            content_type="application/json",
        )
        assert r.status_code == 403

    def test_list_executions(self, api_client, institution, researcher_user, project):
        budget, line = self._make_budget_and_line(institution, project)
        BudgetExecution.objects.create(
            line=line, amount="100.00", executed_at=datetime.date(2026, 5, 1)
        )
        BudgetExecution.objects.create(
            line=line, amount="200.00", executed_at=datetime.date(2026, 6, 1)
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "budgets:line-execution-list",
                kwargs={"budget_pk": str(budget.pk), "line_pk": str(line.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2


# ════════════════════════════════════════════════════════
# BudgetAttachmentViewSet — nested under budget
# ════════════════════════════════════════════════════════


class TestBudgetAttachmentViewSet:
    def test_create_attachment_as_admin(
        self, api_client, institution, admin_user, project
    ):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:budget-attachment-list", kwargs={"budget_pk": str(budget.pk)}),
            {
                "name": "Plan.pdf",
                "doc_type": "soporte",
                "external_url": "https://example.com/plan.pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Plan.pdf"

    def test_attachment_missing_external_url_400(
        self, api_client, institution, admin_user, project
    ):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:budget-attachment-list", kwargs={"budget_pk": str(budget.pk)}),
            {"name": "Plan.pdf", "doc_type": "soporte", "external_url": ""},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_delete_attachment_as_admin(
        self, api_client, institution, admin_user, project
    ):
        budget = Budget.objects.create(
            project=project, institution=institution, name="Budget", approved_amount="1000.00"
        )
        att = BudgetAttachment.objects.create(
            budget=budget, name="Del.pdf", doc_type="soporte", external_url="https://a.com"
        )
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "budgets:budget-attachment-detail",
                kwargs={"budget_pk": str(budget.pk), "pk": str(att.pk)},
            )
        )
        assert r.status_code == 204
        assert not BudgetAttachment.objects.filter(pk=att.pk).exists()


# ════════════════════════════════════════════════════════
# FundingSourceViewSet — nested under project
# ════════════════════════════════════════════════════════


class TestFundingSourceViewSet:
    def test_add_funding_source_as_admin(
        self, api_client, institution, admin_user, project
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:funding-source-list", kwargs={"project_pk": str(project.id)}),
            {"name": "Gov Grant", "amount": "5000.00"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Gov Grant"

    def test_add_second_source_allowed(
        self, api_client, institution, admin_user, project
    ):
        FundingSource.objects.create(project=project, name="First", amount="1000.00")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("budgets:funding-source-list", kwargs={"project_pk": str(project.id)}),
            {"name": "Second", "amount": "2000.00"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert FundingSource.objects.filter(project=project).count() == 2

    def test_list_funding_sources(
        self, api_client, institution, researcher_user, project
    ):
        FundingSource.objects.create(project=project, name="A", amount="1000.00")
        FundingSource.objects.create(project=project, name="B", amount="2000.00")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("budgets:funding-source-list", kwargs={"project_pk": str(project.id)})
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2

    def test_delete_funding_source_as_admin(
        self, api_client, institution, admin_user, project
    ):
        source = FundingSource.objects.create(project=project, name="A", amount="1000.00")
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "budgets:funding-source-detail",
                kwargs={"project_pk": str(project.id), "pk": str(source.pk)},
            )
        )
        assert r.status_code == 204
        assert not FundingSource.objects.filter(pk=source.pk).exists()

    def test_update_funding_source_as_admin(
        self, api_client, institution, admin_user, project
    ):
        source = FundingSource.objects.create(project=project, name="A", amount="1000.00")
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse(
                "budgets:funding-source-detail",
                kwargs={"project_pk": str(project.id), "pk": str(source.pk)},
            ),
            {"name": "Renamed"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

    def test_list_sources_cross_institution_empty(
        self, api_client, institution, researcher_user, other_institution
    ):
        from apps.projects.tests.conftest import ProjectFactory

        other_project = ProjectFactory(institution=other_institution)
        FundingSource.objects.create(project=other_project, name="Secret", amount="10.00")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "budgets:funding-source-list", kwargs={"project_pk": str(other_project.id)}
            )
        )
        assert r.status_code == 200
        assert r.json()["results"] == []
