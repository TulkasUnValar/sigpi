"""
DRF URL routing for the progress (advances) module.

Design decisions (from design.md):
- SimpleRouter for ProgressViewSet
- Manual nested paths for sub-entities (avoids drf-nested-routers dependency)
- 9 FSM action endpoints as @action decorators on ProgressViewSet
- Hybrid routing: top-level + nested shortcut /projects/{id}/progress/
- Prefix: /api/ (applied at config/urls.py level)

API contract (from spec.md):
  /progress/                                    GET, POST
  /progress/{id}/                               GET, PATCH, DELETE
  /progress/{id}/submit/                        POST
  /progress/{id}/accept_review/                 POST
  /progress/{id}/approve/                       POST
  /progress/{id}/observe/                       POST
  /progress/{id}/reject/                        POST
  /progress/{id}/return_to_draft/               POST
  /progress/{id}/resubmit/                      POST
  /progress/{id}/documents/                     GET, POST
  /progress/{id}/documents/{did}/               PATCH, DELETE
  /progress/{id}/reviews/                       GET
  /progress/{id}/state_history/                 GET
  /projects/{id}/progress/                      GET

Spec reference:   openspec/sdd/advances/spec.md — API Contract
Design reference: openspec/sdd/advances/design.md — URL Routing
"""
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.progress import views

# ──────────────────────────────────────────────────────────
# Router: Progress
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"progress", views.ProgressViewSet, basename="progressreport")

# ──────────────────────────────────────────────────────────
# Nested routes under /progress/{progressreport_pk}/
# ──────────────────────────────────────────────────────────

progress_nested = [
    # Documents
    path(
        "documents/",
        views.ProgressDocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="progressreport-documents-list",
    ),
    path(
        "documents/<uuid:pk>/",
        views.ProgressDocumentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="progressreport-documents-detail",
    ),
    # Reviews (read-only list)
    path(
        "reviews/",
        views.ProgressReviewViewSet.as_view({"get": "list"}),
        name="progressreport-reviews-list",
    ),
    path(
        "reviews/<uuid:pk>/",
        views.ProgressReviewViewSet.as_view({"get": "retrieve"}),
        name="progressreport-reviews-detail",
    ),
    # State history (read-only list)
    path(
        "state_history/",
        views.ProgressStateLogViewSet.as_view({"get": "list"}),
        name="progressreport-state-history-list",
    ),
    path(
        "state_history/<uuid:pk>/",
        views.ProgressStateLogViewSet.as_view({"get": "retrieve"}),
        name="progressreport-state-history-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# Projects nested shortcut: /projects/{project_pk}/progress/
# ──────────────────────────────────────────────────────────

project_nested = [
    path(
        "progress/",
        views.ProgressViewSet.as_view({"get": "list"}),
        name="project-progress-list",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

urlpatterns = router.urls + [
    path(
        "progress/<uuid:progressreport_pk>/",
        include(progress_nested),
    ),
    path(
        "projects/<uuid:project_pk>/",
        include(project_nested),
    ),
]
