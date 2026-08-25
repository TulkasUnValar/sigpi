"""
DRF permission classes for the notifications module (PR 4).

Provides:
- IsNotificationOwner: only the recipient may access a Notification row.
- IsAdminOrOwner: institution admin (level <= 2) or the notification
  recipient may access a row.

Note on tenancy: every read is additionally constrained by the viewset
queryset (recipient == request.user, including for superusers — design
invariant), so cross-user access is a 404 regardless of the permission
class outcome. The permission classes gate authentication and object-level
authorization for defense in depth.

Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
Spec reference:   openspec/changes/notifications/spec.md — Permissions Matrix
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher

__all__ = ["IsNotificationOwner", "IsAdminOrOwner"]


# ──────────────────────────────────────────────
# IsNotificationOwner
# ──────────────────────────────────────────────


class IsNotificationOwner(BasePermission):
    """Only the notification recipient may read or mutate the row."""

    def has_permission(self, request: Request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        return (
            request.user.is_authenticated
            and getattr(obj, "recipient_id", None) == request.user.id
        )


# ──────────────────────────────────────────────
# IsAdminOrOwner
# ──────────────────────────────────────────────


class IsAdminOrOwner(BasePermission):
    """Institution admin (role level <= 2) or the notification recipient.

    Superusers bypass the object check. The viewset queryset still scopes
    every read to recipient == request.user, so admins never see rows that
    belong to other users through the API (spec Permissions Matrix).
    """

    def has_permission(self, request: Request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if getattr(obj, "recipient_id", None) == request.user.id:
            return True
        return HasRoleLevelOrHigher.has_level(request, 2)
