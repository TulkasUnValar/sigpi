"""
DRF URL routing for the products module.

Design decisions (from design.md):
- SimpleRouter for ResearchProduct ViewSet
- Manual nested paths for authors and attachments (avoids drf-nested-routers)
- Prefix: /api/ (applied at config/urls.py level)

API contract (from spec.md):
  /products/                                    GET, POST
  /products/{id}/                               GET, PATCH, DELETE
  /products/{id}/authors/                       GET, POST
  /products/{id}/authors/{pk}/                 GET, PATCH, DELETE
  /products/{id}/attachments/                   GET, POST
  /products/{id}/attachments/{pk}/              GET, PATCH, DELETE

Design reference: openspec/changes/products/design.md — URL Routing
Spec reference: openspec/changes/products/specs/products/spec.md — API Contract
"""
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.products import views

# ──────────────────────────────────────────────────────────
# Router: ResearchProduct
# ──────────────────────────────────────────────────────────

router = SimpleRouter()
router.register(r"products", views.ResearchProductViewSet, basename="product")

# ──────────────────────────────────────────────────────────
# Nested routes under /products/{product_pk}/
# ──────────────────────────────────────────────────────────

product_nested = [
    # Authors
    path(
        "authors/",
        views.ProductAuthorViewSet.as_view({"get": "list", "post": "create"}),
        name="author-list",
    ),
    path(
        "authors/<uuid:pk>/",
        views.ProductAuthorViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="author-detail",
    ),
    # Attachments
    path(
        "attachments/",
        views.ProductAttachmentViewSet.as_view({"get": "list", "post": "create"}),
        name="attachment-list",
    ),
    path(
        "attachments/<uuid:pk>/",
        views.ProductAttachmentViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="attachment-detail",
    ),
]

# ──────────────────────────────────────────────────────────
# urlpatterns assembly
# ──────────────────────────────────────────────────────────

app_name = "products"

urlpatterns = router.urls + [
    path(
        "products/<uuid:product_pk>/",
        include(product_nested),
    ),
]
