"""
DRF ModelSerializers for the products module.

Provides 3 serializers implementing the API contract from spec.md:
- ResearchProductSerializer: full detail with project FK, institution read-only
- ProductAuthorSerializer: researcher FK, is_principal, order; product read-only
- ProductAttachmentSerializer: name, doc_type, external_url; product read-only

Validation:
- type must be a valid ProductType choice
- publication_year between 1900 and current_year+1
- project FK validated for existence (institution scoping in view)

Design reference: openspec/changes/products/design.md
Spec reference: openspec/changes/products/specs/products/spec.md
"""
import datetime

from rest_framework import serializers

from apps.products.models import (
    ProductAttachment,
    ProductAuthor,
    ProductType,
    ResearchProduct,
)


# ──────────────────────────────────────────────────────────
# ResearchProductSerializer
# ──────────────────────────────────────────────────────────


class ResearchProductSerializer(serializers.ModelSerializer):
    """Full-detail serializer for ResearchProduct.

    Institution is read-only — injected by the view from active_membership.
    Project is writable (UUID) but must belong to the user's institution
    (enforced in the view's perform_create).
    """

    class Meta:
        model = ResearchProduct
        fields = [
            "id",
            "institution",
            "project",
            "title",
            "description",
            "type",
            "publication_year",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = [
            "id",
            "institution",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate_type(self, value):
        """RF-081: type must be a valid ProductType choice."""
        valid = {choice[0] for choice in ProductType.choices}
        if value not in valid:
            raise serializers.ValidationError("Invalid product type.")
        return value

    def validate_publication_year(self, value):
        """RF-081: publication_year between 1900 and current_year+1."""
        if value is not None:
            current_year = datetime.date.today().year
            if value < 1900:
                raise serializers.ValidationError(
                    "Publication year must be 1900 or later."
                )
            if value > current_year + 1:
                raise serializers.ValidationError(
                    f"Publication year must not exceed {current_year + 1}."
                )
        return value


# ──────────────────────────────────────────────────────────
# ProductAuthorSerializer
# ──────────────────────────────────────────────────────────


class ProductAuthorSerializer(serializers.ModelSerializer):
    """Serializer for ProductAuthor CRUD.

    product FK is read-only — set by the view from the URL path.
    researcher FK is writable.
    """

    class Meta:
        model = ProductAuthor
        fields = [
            "id",
            "product",
            "researcher",
            "is_principal",
            "order",
        ]
        read_only_fields = [
            "id",
            "product",
        ]

    def validate(self, attrs):
        """Reject duplicate researcher for the same product."""
        researcher = attrs.get("researcher")
        if researcher is None:
            return attrs

        product_id = None
        if self.instance is not None:
            product_id = self.instance.product_id
        else:
            # product may come from initial data (serializer tests)
            # or be absent (view posts without product in body)
            product_id = self.initial_data.get("product")

        if product_id is not None:
            from apps.products.models import ProductAuthor
            qs = ProductAuthor.objects.filter(product_id=product_id, researcher=researcher)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"researcher": "Researcher already associated with this product."}
                )

        return attrs


# ──────────────────────────────────────────────────────────
# ProductAttachmentSerializer
# ──────────────────────────────────────────────────────────


class ProductAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ProductAttachment CRUD.

    product FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = ProductAttachment
        fields = [
            "id",
            "product",
            "name",
            "doc_type",
            "external_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "product",
            "created_at",
        ]
