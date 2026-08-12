"""
django-filter FilterSet for the calls module.

Provides CallFilter with:
- status (ChoiceFilter) — filter by CallStatus
- call_type (ChoiceFilter) — filter by CallType
- title (CharFilter icontains) — search in title field
- submission_start_after (DateFilter gte)
- submission_start_before (DateFilter lte)
- evaluation_start_after (DateFilter gte)
- evaluation_start_before (DateFilter lte)

Used by CallViewSet.filter_backends = [DjangoFilterBackend, ...]
together with SearchFilter and OrderingFilter (configured in views.py).

Design reference: openspec/changes/calls/design.md — Filtering (RF-071)
Spec reference:   openspec/changes/calls/spec.md — RF-071
"""

import django_filters

from apps.calls.models import Call, CallStatus, CallType


class CallFilter(django_filters.FilterSet):
    """FilterSet for Call list endpoint.

    Supports filtering by status, call_type, date range, and title search.
    """

    status = django_filters.ChoiceFilter(choices=CallStatus.choices)
    call_type = django_filters.ChoiceFilter(choices=CallType.choices)
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    submission_start_after = django_filters.DateFilter(
        field_name="submission_start", lookup_expr="gte"
    )
    submission_start_before = django_filters.DateFilter(
        field_name="submission_start", lookup_expr="lte"
    )
    evaluation_start_after = django_filters.DateFilter(
        field_name="evaluation_start", lookup_expr="gte"
    )
    evaluation_start_before = django_filters.DateFilter(
        field_name="evaluation_start", lookup_expr="lte"
    )

    class Meta:
        model = Call
        fields = [
            "status",
            "call_type",
            "title",
            "submission_start_after",
            "submission_start_before",
            "evaluation_start_after",
            "evaluation_start_before",
        ]
