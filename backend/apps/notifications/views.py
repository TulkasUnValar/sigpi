"""
DRF ViewSets for the notifications module — PR 4 (API layer).

Implements the API Contract from spec.md:
- NotificationViewSet: GET list/detail (own notifications only), plus the
  read-state mutation actions `read`, `read_all`, and `unread_count`.
- UserPreferenceViewSet: list/retrieve/update of the caller's own
  UserPreference (email opt-out).

Design invariants:
- queryset ALWAYS filters recipient == request.user, including for
  superusers (design: "Querysets additionally enforce recipient=request.user")
- cross-user access is therefore a 404 (RLS hides the row)
- Notification rows are created ONLY by receivers — no create/update/delete
- pagination 50/page; default ordering -created_at
- lookup regex is UUID-only so the nested `preferences` prefix and the
  list actions (unread_count, read_all) never collide with detail routing

Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
Spec reference:   openspec/changes/notifications/spec.md — API Contract
"""

from django.db.models import QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.notifications.filters import NotificationFilter
from apps.notifications.models import Notification, UserPreference
from apps.notifications.permissions import IsAdminOrOwner
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationSummarySerializer,
    UserPreferenceSerializer,
)


class NotificationPagination(PageNumberPagination):
    """50 notifications per page (orchestrator PR 4 contract)."""

    page_size = 50


# ──────────────────────────────────────────────
# NotificationViewSet
# ──────────────────────────────────────────────


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only own-notifications API + read-state mutations.

    - list: paginated (50/page), filterable (is_read, event_type,
      entity_type, entity_id, date_from, date_to), ordered -created_at
    - detail: full payload; cross-user access 404s (queryset-scoped)
    - read: POST /{id}/read/ — idempotent mark-read
    - read_all: POST /read_all/ — mark all own unread notifications read
    - unread_count: GET /unread_count/ — {"count": N}
    """

    queryset = Notification.objects.select_related("template").all()
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = NotificationFilter
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    lookup_value_regex = r"[0-9a-f-]{36}"

    def get_queryset(self) -> QuerySet:
        """Own notifications only — enforced for every user, incl. superusers."""
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "template"
        )

    def get_serializer_class(self):
        """List uses the summary payload; detail and actions use the full one."""
        if self.action == "list":
            return NotificationSummarySerializer
        return NotificationSerializer

    # ── Actions ─────────────────────────────────

    @action(detail=True, methods=["post"])
    def read(self, request: Request, pk=None) -> Response:
        """Mark one notification as read. Idempotent (spec API Contract)."""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request: Request) -> Response:
        """Mark all own unread notifications as read. Idempotent."""
        now = timezone.now()
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=now
        )
        return Response({"updated": updated})

    @action(detail=False, methods=["get"])
    def unread_count(self, request: Request) -> Response:
        """Unread count of own notifications (spec API Contract)."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})


# ──────────────────────────────────────────────
# UserPreferenceViewSet
# ──────────────────────────────────────────────


class UserPreferenceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Own UserPreference — list/retrieve/update only (no create/delete).

    Preferences are user-global; the queryset locks the row to the caller
    (user == request.user), so cross-user access 404s.
    """

    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9a-f-]{36}"

    def get_queryset(self) -> QuerySet:
        return UserPreference.objects.filter(user=self.request.user)
