"""
django-filter FilterSet for the budgets module.

Provides BudgetFilter with:
- project (UUIDFilter) — filter by exact project
- institution (UUIDFilter) — filter by exact institution
- status (ChoiceFilter) — filter by BudgetStatus
- name (CharFilter icontains) — search in budget name

Used by BudgetViewSet.filter_backends = [DjangoFilterBackend, ...]
(together with SearchFilter and OrderingFilter, configured in views.py).

Design reference: openspec/changes/budgets/design.md — Filtering (RF-B06)
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md — RF-B06
"""

import django_filters

from apps.budgets.models import Budget, BudgetStatus


class BudgetFilter(django_filters.FilterSet):
    """FilterSet for the Budget list endpoint.

    Supports filtering by project, institution, status, and name search.
    """

    project = django_filters.UUIDFilter(field_name="project")
    institution = django_filters.UUIDFilter(field_name="institution")
    status = django_filters.ChoiceFilter(choices=BudgetStatus.choices)
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Budget
        fields = [
            "project",
            "institution",
            "status",
            "name",
        ]
