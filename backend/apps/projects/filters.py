"""
django-filter FilterSet for the projects module.

Provides ProjectFilter with:
- status (ChoiceFilter) — filter by ProjectStatus
- center (UUIDFilter) — filter by center_id
- start_date_after (DateFilter gte) — filter start_date >= value
- start_date_before (DateFilter lte) — filter start_date <= value
- keywords (CharFilter icontains) — search in keywords field

Used by ProjectViewSet.filter_backends = [DjangoFilterBackend, ...]
together with SearchFilter and OrderingFilter (configured in views.py).

Design reference: openspec/changes/projects/design.md — Filtering (RF-039)
Spec reference:   openspec/changes/projects/spec.md — RF-039
"""
import django_filters

from apps.projects.models import Project, ProjectStatus


class ProjectFilter(django_filters.FilterSet):
    """FilterSet for Project list endpoint.

    Supports filtering by status, center, date range, and keyword search.
    """

    status = django_filters.ChoiceFilter(choices=ProjectStatus.choices)
    center = django_filters.UUIDFilter(field_name="center_id")
    start_date_after = django_filters.DateFilter(
        field_name="start_date", lookup_expr="gte"
    )
    start_date_before = django_filters.DateFilter(
        field_name="start_date", lookup_expr="lte"
    )
    keywords = django_filters.CharFilter(
        field_name="keywords", lookup_expr="icontains"
    )

    class Meta:
        model = Project
        fields = [
            "status",
            "center",
            "start_date_after",
            "start_date_before",
            "keywords",
        ]
