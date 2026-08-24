"""
DRF URL routing for the budgets module.

Design decisions (from design.md):
- SimpleRouter for Budget ViewSet.
- Manual nested paths for sub-entities (avoids drf-nested-routers dependency).
- Prefix: /api/ (applied at config/urls.py level).

API contract (from spec.md):
  /budgets/                                       GET, POST
  /budgets/{id}/                                  GET, PATCH, DELETE
  /budgets/{id}/summary/                          GET
  /budgets/{id}/lines/                            GET, POST
  /budgets/{id}/lines/{lid}/                      GET, PATCH, DELETE
  /budgets/{id}/lines/{lid}/executions/           GET, POST
  /budgets/{id}/lines/{lid}/executions/{eid}/     GET, PATCH, DELETE
  /budgets/{id}/attachments/                      GET, POST
  /budgets/{id}/attachments/{aid}/                GET, PATCH, DELETE
  /projects/{pid}/funding-sources/                GET, POST
  /projects/{pid}/funding-sources/{fsid}/         GET, PATCH, DELETE

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — API Contract
Design reference: openspec/changes/budgets/design.md — URL Routing
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.budgets import views

# ──────────────────────────────────────────────────────────
# Router: Budget
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"budgets", views.BudgetViewSet, basename="budget")

# ──────────────────────────────────────────────────────────
# Budget-level nested routes (lines, attachments)
# ──────────────────────────────────────────────────────────

budget_nested = [
    path(
        "lines/",
        views.BudgetLineViewSet.as_view({"get": "list", "post": "create"}),
        name="budget-line-list",
    ),
    path(
        "lines/<uuid:pk>/",
        views.BudgetLineViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="budget-line-detail",
    ),
    path(
        "attachments/",
        views.BudgetAttachmentViewSet.as_view({"get": "list", "post": "create"}),
        name="budget-attachment-list",
    ),
    path(
        "attachments/<uuid:pk>/",
        views.BudgetAttachmentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="budget-attachment-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# Line-level nested routes (executions)
# ──────────────────────────────────────────────────────────

line_nested = [
    path(
        "executions/",
        views.BudgetExecutionViewSet.as_view({"get": "list", "post": "create"}),
        name="line-execution-list",
    ),
    path(
        "executions/<uuid:pk>/",
        views.BudgetExecutionViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="line-execution-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# Project-level nested routes (funding sources)
# ──────────────────────────────────────────────────────────

project_nested = [
    path(
        "funding-sources/",
        views.FundingSourceViewSet.as_view({"get": "list", "post": "create"}),
        name="funding-source-list",
    ),
    path(
        "funding-sources/<uuid:pk>/",
        views.FundingSourceViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="funding-source-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "budgets"

urlpatterns = (
    router.urls
    + [
        path(
            "budgets/<uuid:budget_pk>/",
            include(
                budget_nested
                + [
                    path(
                        "lines/<uuid:line_pk>/",
                        include(line_nested),
                    ),
                ]
            ),
        ),
        path(
            "projects/<uuid:project_pk>/",
            include(project_nested),
        ),
    ]
)
