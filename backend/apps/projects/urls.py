"""
DRF URL routing for the projects module.

Design decisions (from design.md):
- SimpleRouter for Project ViewSet
- Manual nested paths for sub-entities (avoids drf-nested-routers dependency)
- 16 FSM action endpoints as @action decorators on ProjectViewSet
- Prefix: /api/ (applied at config/urls.py level)

API contract (from spec.md):
  /projects/                                    GET, POST
  /projects/{id}/                               GET, PATCH, DELETE
  /projects/{id}/submit/                        POST
  /projects/{id}/accept_review/                 POST
  /projects/{id}/approve/                       POST
  /projects/{id}/observe/                       POST
  /projects/{id}/return_to_draft/               POST
  /projects/{id}/reject/                        POST
  /projects/{id}/resubmit/                      POST
  /projects/{id}/start_execution/               POST
  /projects/{id}/suspend/                       POST
  /projects/{id}/resume/                        POST
  /projects/{id}/finalize/                      POST
  /projects/{id}/initiate_closure/              POST
  /projects/{id}/close/                         POST
  /projects/{id}/cancel/                        POST
  /projects/{id}/members/                       GET, POST
  /projects/{id}/members/{mid}/                 PATCH, DELETE
  /projects/{id}/documents/                     GET, POST
  /projects/{id}/documents/{did}/               PATCH, DELETE
  /projects/{id}/observations/                  GET
  /projects/{id}/state_history/                 GET

Spec reference: openspec/changes/projects/spec.md — API Contract
Design reference: openspec/changes/projects/design.md — URL Routing
"""
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.projects import views

# ──────────────────────────────────────────────────────────
# Router: Project
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"projects", views.ProjectViewSet, basename="project")

# ──────────────────────────────────────────────────────────
# FSM action endpoints (16)
# ──────────────────────────────────────────────────────────

fsm_actions = [
    path("submit/", views.ProjectViewSet.as_view({"post": "submit"}), name="project-submit"),
    path(
        "accept_review/",
        views.ProjectViewSet.as_view({"post": "accept_review"}),
        name="project-accept-review",
    ),
    path(
        "approve/",
        views.ProjectViewSet.as_view({"post": "approve"}),
        name="project-approve",
    ),
    path(
        "observe/",
        views.ProjectViewSet.as_view({"post": "observe"}),
        name="project-observe",
    ),
    path(
        "return_to_draft/",
        views.ProjectViewSet.as_view({"post": "return_to_draft"}),
        name="project-return-to-draft",
    ),
    path(
        "reject/",
        views.ProjectViewSet.as_view({"post": "reject"}),
        name="project-reject",
    ),
    path(
        "resubmit/",
        views.ProjectViewSet.as_view({"post": "resubmit"}),
        name="project-resubmit",
    ),
    path(
        "start_execution/",
        views.ProjectViewSet.as_view({"post": "start_execution"}),
        name="project-start-execution",
    ),
    path(
        "suspend/",
        views.ProjectViewSet.as_view({"post": "suspend"}),
        name="project-suspend",
    ),
    path(
        "resume/",
        views.ProjectViewSet.as_view({"post": "resume"}),
        name="project-resume",
    ),
    path(
        "finalize/",
        views.ProjectViewSet.as_view({"post": "finalize"}),
        name="project-finalize",
    ),
    path(
        "initiate_closure/",
        views.ProjectViewSet.as_view({"post": "initiate_closure"}),
        name="project-initiate-closure",
    ),
    path(
        "close/",
        views.ProjectViewSet.as_view({"post": "close"}),
        name="project-close",
    ),
    path(
        "cancel/",
        views.ProjectViewSet.as_view({"post": "cancel"}),
        name="project-cancel",
    ),
]

# ──────────────────────────────────────────────────────────
# Nested routes under /projects/{project_pk}/
# ──────────────────────────────────────────────────────────

project_nested = [
    # FSM actions
    *fsm_actions,
    # Members
    path(
        "members/",
        views.ProjectMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="project-member-list",
    ),
    path(
        "members/<uuid:pk>/",
        views.ProjectMemberViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="project-member-detail",
    ),
    # Documents
    path(
        "documents/",
        views.ProjectDocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="project-document-list",
    ),
    path(
        "documents/<uuid:pk>/",
        views.ProjectDocumentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="project-document-detail",
    ),
    # Observations (read-only list)
    path(
        "observations/",
        views.ProjectObservationViewSet.as_view({"get": "list"}),
        name="project-observation-list",
    ),
    # State history (read-only list)
    path(
        "state_history/",
        views.ProjectStateLogViewSet.as_view({"get": "list"}),
        name="project-state-log-list",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "projects"

urlpatterns = router.urls + [
    path(
        "projects/<uuid:project_pk>/",
        include(project_nested),
    ),
]
