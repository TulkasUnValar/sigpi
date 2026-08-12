"""
DRF URL routing for the project_workflow module.

Uses DefaultRouter for WorkflowTemplate and WorkflowInstance ViewSets,
which automatically generates CRUD URLs plus @action endpoints
(approve, observe, reject).

Manual nested paths for WorkflowAction under /instances/{instance_pk}/actions/
because DefaultRouter does not support nested resources.

API contract (from spec.md):
  /workflows/templates/                              GET, POST
  /workflows/templates/{id}/                         GET, PATCH, DELETE
  /workflows/instances/                              GET
  /workflows/instances/{id}/                         GET
  /workflows/instances/{id}/approve/                 POST
  /workflows/instances/{id}/observe/                 POST
  /workflows/instances/{id}/reject/                  POST
  /workflows/instances/{id}/actions/                 GET, POST
  /workflows/instances/{id}/actions/{id}/            GET

Design reference: openspec/changes/project_workflow/design.md — URL Routing
Spec reference:   openspec/changes/project_workflow/spec.md — API Contract
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.project_workflow import views

# ──────────────────────────────────────────────────────────
# DefaultRouter: Template + Instance
# ──────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r"templates", views.WorkflowTemplateViewSet, basename="workflowtemplate")
router.register(r"instances", views.WorkflowInstanceViewSet, basename="workflowinstance")

# ──────────────────────────────────────────────────────────
# Nested action routes under /instances/{instance_pk}/
# ──────────────────────────────────────────────────────────

instance_nested = [
    # WorkflowAction nested under instance
    path(
        "actions/",
        views.WorkflowActionViewSet.as_view({"get": "list", "post": "create"}),
        name="workflowaction-list",
    ),
    path(
        "actions/<uuid:pk>/",
        views.WorkflowActionViewSet.as_view({"get": "retrieve"}),
        name="workflowaction-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "project_workflow"

urlpatterns = router.urls + [
    path("instances/<uuid:instance_pk>/", include(instance_nested)),
]
