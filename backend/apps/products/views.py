"""
DRF ViewSets for the products module.

Implements 3 ViewSets per design.md:
- ResearchProductViewSet: CRUD, institution-scoped queryset, django-filter
- ProductAuthorViewSet: nested under product, CRUD
- ProductAttachmentViewSet: nested under product, CRUD

Institution scoping via request.active_membership.
Project FK validated in perform_create (404 if foreign).

Design reference: openspec/changes/products/design.md
Spec reference: openspec/changes/products/specs/products/spec.md
"""
from django.db.models import QuerySet
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from apps.products.filters import ResearchProductFilter
from apps.products.models import (
    ProductAttachment,
    ProductAuthor,
    ResearchProduct,
)
from apps.products.serializers import (
    ProductAttachmentSerializer,
    ProductAuthorSerializer,
    ResearchProductSerializer,
)
from apps.projects.models import Project

# ──────────────────────────────────────────────────────────
# ResearchProductViewSet
# ──────────────────────────────────────────────────────────


class ResearchProductViewSet(viewsets.ModelViewSet):
    """CRUD for ResearchProduct. Institution-scoped with filtering.

    - list: any authenticated user in the institution
    - create: any authenticated user (institution injected)
    - retrieve/update/destroy: any authenticated user (institution-scoped)
    """

    queryset = ResearchProduct.objects.all()
    serializer_class = ResearchProductSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ResearchProductFilter
    ordering_fields = ["title", "publication_year", "created_at"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter products by the user's active institution."""
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return ResearchProduct.objects.all()

        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            return ResearchProduct.objects.none()

        return ResearchProduct.objects.filter(institution=membership.institution)

    def perform_create(self, serializer):
        """Inject institution from active membership and validate project."""
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        institution = membership.institution
        project = serializer.validated_data.get("project")

        # RF-080: validate project belongs to the same institution (404 if foreign)
        if project is not None and project.institution_id != institution.id:
            raise Http404("Project not found.")

        serializer.save(
            institution=institution,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        """Set updated_by on save."""
        serializer.save(updated_by=self.request.user)


# ──────────────────────────────────────────────────────────
# ProductAuthorViewSet — nested under /products/{product_pk}/authors/
# ──────────────────────────────────────────────────────────


class ProductAuthorViewSet(viewsets.ModelViewSet):
    """Nested CRUD for ProductAuthor.

    - list: any authenticated user
    - create/update/destroy: any authenticated user
    """

    serializer_class = ProductAuthorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter authors by parent product from URL."""
        product_pk = self.kwargs.get("product_pk")
        if product_pk:
            return ProductAuthor.objects.filter(product_id=product_pk)
        return ProductAuthor.objects.none()

    def perform_create(self, serializer):
        """Inject product FK from URL."""
        product_pk = self.kwargs.get("product_pk")
        try:
            product = ResearchProduct.objects.get(pk=product_pk)
        except ResearchProduct.DoesNotExist:
            raise Http404("Product not found.")
        try:
            serializer.save(product=product)
        except Exception as exc:
            from django.db import IntegrityError
            if isinstance(exc, IntegrityError):
                raise DRFValidationError(
                    {"researcher": "Researcher already associated with this product."}
                )
            raise


# ──────────────────────────────────────────────────────────
# ProductAttachmentViewSet — nested under /products/{product_pk}/attachments/
# ──────────────────────────────────────────────────────────


class ProductAttachmentViewSet(viewsets.ModelViewSet):
    """Nested CRUD for ProductAttachment.

    - list: any authenticated user
    - create/update/destroy: any authenticated user
    """

    serializer_class = ProductAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter attachments by parent product from URL."""
        product_pk = self.kwargs.get("product_pk")
        if product_pk:
            return ProductAttachment.objects.filter(product_id=product_pk)
        return ProductAttachment.objects.none()

    def perform_create(self, serializer):
        """Inject product FK from URL."""
        product_pk = self.kwargs.get("product_pk")
        try:
            product = ResearchProduct.objects.get(pk=product_pk)
        except ResearchProduct.DoesNotExist:
            raise Http404("Product not found.")
        serializer.save(product=product)
