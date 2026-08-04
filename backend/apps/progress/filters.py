"""
django-filter FilterSet for the progress (advances) module.

Provides ProgressReportFilter with:
- status (ChoiceFilter) — filter by ProgressStatus
- project (UUIDFilter) — filter by project_id
- period_start_after (DateFilter gte) — filter period_start >= value
- period_start_before (DateFilter lte) — filter period_start <= value

Used by ProgressViewSet.filter_backends = [DjangoFilterBackend, ...]
together with SearchFilter and OrderingFilter (configured in views.py).

Design reference: openspec/sdd/advances/design.md — Filtering
Spec reference:   openspec/sdd/advances/spec.md
"""
import django_filters

from apps.progress.models import ProgressReport, ProgressStatus


class ProgressReportFilter(django_filters.FilterSet):
    """FilterSet for ProgressReport list endpoint.

    Supports filtering by status, project, and period range.
    """

    status = django_filters.ChoiceFilter(choices=ProgressStatus.choices)
    project = django_filters.UUIDFilter(field_name="project_id")
    period_start_after = django_filters.DateFilter(
        field_name="period_start", lookup_expr="gte"
    )
    period_start_before = django_filters.DateFilter(
        field_name="period_start", lookup_expr="lte"
    )

    class Meta:
        model = ProgressReport
        fields = [
            "status",
            "project",
            "period_start_after",
            "period_start_before",
        ]
