"""
URL routing tests for budgets — STRICT TDD (RED phase).

Verifies the URL patterns exposed by apps/budgets/urls.py:
- /api/budgets/ and /api/budgets/{id}/ (Budget ViewSet + summary)
- /api/budgets/{id}/lines/ and lines/{lid}/executions/
- /api/budgets/{id}/attachments/
- /api/projects/{pid}/funding-sources/

Strict TDD: written BEFORE urls.py is filled in (currently empty).
Expected failure: reverse() raises NoReverseMatch.

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — API Contract
"""

from django.urls import reverse


class TestBudgetUrls:
    def test_budget_list_url(self):
        url = reverse("budgets:budget-list")
        assert url == "/api/budgets/"

    def test_budget_detail_url(self):
        pk = "00000000-0000-0000-0000-000000000001"
        url = reverse("budgets:budget-detail", kwargs={"pk": pk})
        assert url == f"/api/budgets/{pk}/"

    def test_budget_summary_url(self):
        pk = "00000000-0000-0000-0000-000000000001"
        url = reverse("budgets:budget-summary", kwargs={"pk": pk})
        assert url == f"/api/budgets/{pk}/summary/"

    def test_budget_lines_list_url(self):
        pk = "00000000-0000-0000-0000-000000000001"
        url = reverse("budgets:budget-line-list", kwargs={"budget_pk": pk})
        assert url == f"/api/budgets/{pk}/lines/"

    def test_budget_line_detail_url(self):
        bpk = "00000000-0000-0000-0000-000000000001"
        lpk = "00000000-0000-0000-0000-000000000002"
        url = reverse("budgets:budget-line-detail", kwargs={"budget_pk": bpk, "pk": lpk})
        assert url == f"/api/budgets/{bpk}/lines/{lpk}/"

    def test_line_executions_list_url(self):
        bpk = "00000000-0000-0000-0000-000000000001"
        lpk = "00000000-0000-0000-0000-000000000002"
        url = reverse("budgets:line-execution-list", kwargs={"budget_pk": bpk, "line_pk": lpk})
        assert url == f"/api/budgets/{bpk}/lines/{lpk}/executions/"

    def test_budget_attachments_list_url(self):
        pk = "00000000-0000-0000-0000-000000000001"
        url = reverse("budgets:budget-attachment-list", kwargs={"budget_pk": pk})
        assert url == f"/api/budgets/{pk}/attachments/"

    def test_funding_source_list_url(self):
        pid = "00000000-0000-0000-0000-000000000003"
        url = reverse("budgets:funding-source-list", kwargs={"project_pk": pid})
        assert url == f"/api/projects/{pid}/funding-sources/"

    def test_funding_source_detail_url(self):
        pid = "00000000-0000-0000-0000-000000000003"
        fsid = "00000000-0000-0000-0000-000000000004"
        url = reverse("budgets:funding-source-detail", kwargs={"project_pk": pid, "pk": fsid})
        assert url == f"/api/projects/{pid}/funding-sources/{fsid}/"
