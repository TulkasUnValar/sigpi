"""
django-filter FilterSet for the audit read API (PR 3).

Implements the API Contract query params from spec.md:
project_id, user_id, entity_type, entity_id, action, event_type,
date_from, date_to, institution_id.

Design reference: openspec/changes/audit/design.md — Interfaces/Contracts
Spec reference:   openspec/changes/audit/specs/audit/spec.md — API Contract
"""

import django_filters

from apps.accounts.audit import AuditEvent, AuditEventType


class AuditLogFilter(django_filters.FilterSet):
    """FilterSet for the audit list endpoint.

    - project_id: exact UUID of the related project (RA-3 / RF-102).
    - user_id: exact actor user UUID (RA-4 / RF-103).
    - entity_type + entity_id: exact entity pair (RA-5 / RF-104).
    - action / event_type: exact match.
    - date_from / date_to: timestamp range (inclusive bounds).
    - institution_id: exact institution UUID (superuser convenience).
    """

    project_id = django_filters.UUIDFilter(field_name="project_id", lookup_expr="exact")
    user_id = django_filters.UUIDFilter(field_name="user_id", lookup_expr="exact")
    entity_type = django_filters.CharFilter(field_name="entity_type", lookup_expr="exact")
    entity_id = django_filters.UUIDFilter(field_name="entity_id", lookup_expr="exact")
    action = django_filters.CharFilter(field_name="action", lookup_expr="exact")
    event_type = django_filters.ChoiceFilter(
        field_name="event_type", choices=AuditEventType.choices
    )
    date_from = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")
    institution_id = django_filters.UUIDFilter(field_name="institution_id", lookup_expr="exact")

    class Meta:
        model = AuditEvent
        fields = [
            "project_id",
            "user_id",
            "entity_type",
            "entity_id",
            "action",
            "event_type",
            "date_from",
            "date_to",
            "institution_id",
        ]
