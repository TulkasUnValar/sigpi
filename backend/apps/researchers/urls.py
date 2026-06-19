"""
DRF URL routing for the researchers module.

Design decisions (from design.md):
- SimpleRouter for Researcher ViewSet
- Manual nested paths for sub-entities (avoids drf-nested-routers dependency)
- Prefix: /api/v1/ (applied at config/urls.py level)

API contract (from spec.md):
  /researchers/                                 GET, POST
  /researchers/{id}/                            GET, PATCH, DELETE
  /researchers/{id}/affiliations/               GET, POST
  /researchers/{id}/affiliations/{aff_id}/      PATCH, DELETE
  /researchers/{id}/profiles/                   GET, POST
  /researchers/{id}/profiles/{prof_id}/         PATCH, DELETE
  /researchers/{id}/attachments/                GET, POST
  /researchers/{id}/attachments/{att_id}/       PATCH, DELETE

Spec reference: openspec/changes/researchers/spec.md — API Contract
Design reference: openspec/changes/researchers/design.md — URL Routing
"""
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.researchers import views

# ──────────────────────────────────────────────────────────
# Router: Researcher
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"researchers", views.ResearcherViewSet, basename="researcher")

# ──────────────────────────────────────────────────────────
# Nested routes under /researchers/{researcher_pk}/
# ──────────────────────────────────────────────────────────

researcher_nested = [
    # Affiliations
    path(
        "affiliations/",
        views.ResearcherAffiliationViewSet.as_view({"get": "list", "post": "create"}),
        name="researcher-affiliation-list",
    ),
    path(
        "affiliations/<uuid:pk>/",
        views.ResearcherAffiliationViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="researcher-affiliation-detail",
    ),
    path(
        "affiliations/<uuid:pk>/set_primary/",
        views.ResearcherAffiliationViewSet.as_view({"post": "set_primary"}),
        name="researcher-affiliation-set-primary",
    ),
    # External Profiles
    path(
        "profiles/",
        views.ExternalProfileViewSet.as_view({"get": "list", "post": "create"}),
        name="researcher-profile-list",
    ),
    path(
        "profiles/<uuid:pk>/",
        views.ExternalProfileViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="researcher-profile-detail",
    ),
    # Attachments
    path(
        "attachments/",
        views.ResearcherAttachmentViewSet.as_view({"get": "list", "post": "create"}),
        name="researcher-attachment-list",
    ),
    path(
        "attachments/<uuid:pk>/",
        views.ResearcherAttachmentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="researcher-attachment-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "researchers"

urlpatterns = router.urls + [
    # Nested sub-entity routes under researchers
    path(
        "researchers/<uuid:researcher_pk>/",
        include(researcher_nested),
    ),
]
