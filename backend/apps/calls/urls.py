"""
DRF URL routing for the calls module.

Design decisions (from design.md):
- SimpleRouter for Call ViewSet
- Manual nested paths for sub-entities (avoids drf-nested-routers dependency)
- 5 FSM action endpoints as @action decorators on CallViewSet
- Prefix: /api/calls/ (applied at config/urls.py level)

API contract (from spec.md):
  /calls/                                    GET, POST
  /calls/{id}/                               GET, PATCH, DELETE
  /calls/{id}/open_call/                     POST
  /calls/{id}/close_call/                    POST
  /calls/{id}/start_evaluation/            POST
  /calls/{id}/publish_results/               POST
  /calls/{id}/archive/                      POST
  /calls/{id}/documents/                     GET, POST
  /calls/{id}/documents/{did}/              PATCH, DELETE
  /calls/{id}/projects/                      GET, POST
  /calls/{id}/projects/{pid}/                DELETE
  /calls/{id}/state_history/                 GET

Spec reference: openspec/changes/calls/spec.md — API Contract
Design reference: openspec/changes/calls/design.md — URL Routing
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.calls import views

# ──────────────────────────────────────────────────────────
# Router: Call
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"calls", views.CallViewSet, basename="call")

# ──────────────────────────────────────────────────────────
# FSM action endpoints (5)
# ──────────────────────────────────────────────────────────

fsm_actions = [
    path("open_call/", views.CallViewSet.as_view({"post": "open_call"}), name="call-open-call"),
    path("close_call/", views.CallViewSet.as_view({"post": "close_call"}), name="call-close-call"),
    path(
        "start_evaluation/",
        views.CallViewSet.as_view({"post": "start_evaluation"}),
        name="call-start-evaluation",
    ),
    path(
        "publish_results/",
        views.CallViewSet.as_view({"post": "publish_results"}),
        name="call-publish-results",
    ),
    path("archive/", views.CallViewSet.as_view({"post": "archive"}), name="call-archive"),
]

# ──────────────────────────────────────────────────────────
# Nested routes under /calls/{call_pk}/
# ──────────────────────────────────────────────────────────

call_nested = [
    # Documents
    path(
        "documents/",
        views.CallDocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="call-document-list",
    ),
    path(
        "documents/<uuid:pk>/",
        views.CallDocumentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="call-document-detail",
    ),
    # Projects
    path(
        "projects/",
        views.CallProjectViewSet.as_view({"get": "list", "post": "create"}),
        name="call-project-list",
    ),
    path(
        "projects/<uuid:pk>/",
        views.CallProjectViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="call-project-detail",
    ),
    # State history (read-only list)
    path(
        "state_history/",
        views.CallStateLogViewSet.as_view({"get": "list"}),
        name="call-state-log-list",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "calls"

urlpatterns = router.urls + [
    path(
        "calls/<uuid:call_pk>/",
        include(call_nested),
    ),
]
