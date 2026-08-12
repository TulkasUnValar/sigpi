"""
django-filter FilterSet for the project_workflow module.

Provides WorkflowInstanceFilter with:
- project (UUIDFilter) — filter by project_id
- status (ChoiceFilter) — filter by WorkflowInstanceStatus
- center (UUIDFilter method) — filter via Project.center_id lookup
- overdue (BooleanFilter method) — deadline_date < now AND status=pending

Used by WorkflowInstanceViewSet.filter_backends.

Design reference: openspec/changes/project_workflow/design.md — Filtering
Spec reference:   openspec/changes/project_workflow/spec.md — WF-005, WF-007
"""

import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.project_workflow.models import WorkflowInstance, WorkflowInstanceStatus


class WorkflowInstanceFilter(django_filters.FilterSet):
    """FilterSet for WorkflowInstance list endpoint.

    Supports filtering by project, status, center, and overdue flag.
    """

    project = django_filters.UUIDFilter(field_name="project_id")
    status = django_filters.ChoiceFilter(choices=WorkflowInstanceStatus.choices)
    center = django_filters.UUIDFilter(method="filter_center")
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = WorkflowInstance
        fields = [
            "project",
            "status",
            "center",
            "overdue",
        ]

    def filter_center(self, queryset, name, value):
        """Filter instances whose project's center matches the given UUID.

        WorkflowInstance stores project_id as UUIDField (not FK),
        so we resolve via a Project subquery.
        """
        from apps.projects.models import Project

        project_ids = Project.objects.filter(center_id=value).values_list("id", flat=True)
        return queryset.filter(project_id__in=list(project_ids))

    def filter_overdue(self, queryset, name, value):
        """Filter instances that are overdue.

        Overdue = deadline_date < now AND status = pending.
        When value=False, return instances that are NOT overdue.
        """
        now = timezone.now()
        overdue_q = Q(
            status=WorkflowInstanceStatus.PENDING,
            deadline_date__lt=now,
        )
        if value:
            return queryset.filter(overdue_q)
        return queryset.exclude(overdue_q)
