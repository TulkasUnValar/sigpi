"""
django-filter FilterSet for the notifications module (PR 4).

NotificationFilter supports:
- is_read: boolean flag
- event_type: exact event-type code (e.g. PROJECT_SUBMITTED)
- entity_type: exact entity-type code (e.g. project, document)
- entity_id: exact linked-entity UUID
- date_from / date_to: created_at range (inclusive bounds)

Design reference: openspec/changes/notifications/design.md — Filters
Spec reference:   openspec/changes/notifications/spec.md — API Contract
"""

import django_filters

from apps.notifications.models import Notification


class NotificationFilter(django_filters.FilterSet):
    """FilterSet for the Notification list endpoint (own notifications only)."""

    is_read = django_filters.BooleanFilter()
    event_type = django_filters.CharFilter(field_name="event_type", lookup_expr="exact")
    entity_type = django_filters.CharFilter(field_name="entity_type", lookup_expr="exact")
    entity_id = django_filters.UUIDFilter(field_name="entity_id")
    date_from = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Notification
        fields = [
            "is_read",
            "event_type",
            "entity_type",
            "entity_id",
            "date_from",
            "date_to",
        ]
