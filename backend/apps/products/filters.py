"""
django-filter FilterSet for the products module.

Provides ResearchProductFilter with:
- type (ChoiceFilter)
- year (NumberFilter exact)
- year__gte / year__lte (NumberFilter range)
- project (UUIDFilter)
- center / group / line (UUIDFilter via project FKs)
- researcher (UUIDFilter via authors__researcher_id)

Used by ResearchProductViewSet.filter_backends.

Design reference: openspec/changes/products/design.md
Spec reference: openspec/changes/products/specs/products/spec.md — RF-084
"""
import django_filters

from apps.products.models import ProductType, ResearchProduct


class ResearchProductFilter(django_filters.FilterSet):
    """FilterSet for ResearchProduct list endpoint.

    Supports filtering by type, publication year (exact/range),
    project, center, group, line, and researcher.
    """

    type = django_filters.ChoiceFilter(choices=ProductType.choices)
    year = django_filters.NumberFilter(field_name="publication_year")
    year__gte = django_filters.NumberFilter(
        field_name="publication_year", lookup_expr="gte"
    )
    year__lte = django_filters.NumberFilter(
        field_name="publication_year", lookup_expr="lte"
    )
    project = django_filters.UUIDFilter(field_name="project_id")
    center = django_filters.UUIDFilter(field_name="project__center_id")
    group = django_filters.UUIDFilter(field_name="project__group_id")
    line = django_filters.UUIDFilter(field_name="project__line_id")
    researcher = django_filters.UUIDFilter(field_name="authors__researcher_id")

    class Meta:
        model = ResearchProduct
        fields = [
            "type",
            "year",
            "year__gte",
            "year__lte",
            "project",
            "center",
            "group",
            "line",
            "researcher",
        ]
