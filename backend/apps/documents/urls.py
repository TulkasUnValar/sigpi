"""DRF URL routing for the documents module — Phase 5.

Implements the API Contract routes from spec.md:
  /documents/types/                                GET
  /documents/presign/                              POST
  /documents/                                      GET, POST
  /documents/{id}/                                 GET, PATCH, DELETE
  /documents/{id}/confirm/                         POST
  /documents/{id}/versions/                        GET, POST
  /documents/{id}/versions/{v}/                    GET
  /documents/{id}/versions/{v}/sign/               POST
  /documents/{id}/download/                        GET
  /documents/{id}/signatures/                      GET (read-only, RF-D05)
  /documents/{id}/signatures/{signature_id}/       GET (read-only)
  /minutes/                                        GET, POST
  /minutes/{id}/                                   GET, PATCH, DELETE

Routing decisions (design.md): SimpleRouter for the two top-level ViewSets
(matches budgets); manual nested paths for the read-only signatures viewset
(avoids drf-nested-routers dependency). Prefix /api/ applied in config/urls.py.

Spec reference: openspec/changes/attachments/specs/documents/spec.md — API Contract
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.documents import views

app_name = "documents"

router = SimpleRouter()
router.register(r"documents", views.DocumentViewSet, basename="document")
router.register(r"minutes", views.MinutesViewSet, basename="minutes")

urlpatterns = router.urls + [
    path(
        "documents/<uuid:pk>/signatures/",
        views.DigitalSignatureViewSet.as_view({"get": "list"}),
        name="document-signatures",
    ),
    path(
        "documents/<uuid:pk>/signatures/<uuid:signature_pk>/",
        views.DigitalSignatureViewSet.as_view({"get": "retrieve"}),
        name="document-signature-detail",
    ),
]
