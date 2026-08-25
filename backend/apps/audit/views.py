"""
Read-only audit API ViewSet (PR 3).

Implements the API Contract from spec.md (RA-3..RA-8):
- GET /api/audit/ and /api/audit/{id}/ — read-only.
- Filtering via AuditLogFilter (DjangoFilterBackend).
- PageNumberPagination: page_size 50, capped at 100.
- Ordered -timestamp by default.
- Queryset institution-filtered unless superuser (cross-institution read).

Design reference: openspec/changes/audit/design.md — Interfaces/Contracts
Spec reference:   openspec/changes/audit/specs/audit/spec.md — API Contract
"""

from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.audit import AuditEvent
from apps.audit.filters import AuditLogFilter
from apps.audit.permissions import IsAuditReader
from apps.audit.serializers import AuditLogSerializer


class AuditLogPagination(PageNumberPagination):
    """PageNumberPagination for audit rows — 50/page, hard cap 100."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditLogViewSet(ReadOnlyModelViewSet):
    """Read-only audit event list/retrieve.

    Access: IsAuthenticated + IsAuditReader (Auditor, Director, Admin
    Institucional, Superadmin). Queryset is scoped to the request's active
    institution unless the user is a superuser, who may read across
    institutions (RA-8).
    """

    queryset = AuditEvent.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAuditReader]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditLogFilter
    pagination_class = AuditLogPagination
    ordering = "-timestamp"

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset

        institution_id = getattr(self.request, "institution_id", None)
        if not institution_id:
            return queryset.none()
        return queryset.filter(institution_id=institution_id)
