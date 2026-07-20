"""
DRF Permission classes for the institutions module.

Provides role-based write access with read fallback:
- IsInstitutionAdminOrReadOnly: writes require level≤2 (Institution Admin+),
  reads require IsAuthenticated
- IsCenterDirectorOrReadOnly: writes require level≤3 (Center Director+),
  reads require IsAuthenticated

Re-exports from apps.accounts.permissions:
- IsSuperAdmin — for Institution CRUD (superadmin-only)
- IsSameInstitution — for object-level tenant scoping

Design reference: openspec/changes/institutions/design.md — Permission Matrix
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import (
    HasRoleLevelOrHigher,
    IsSameInstitution,  # noqa: F401 — re-exported
    IsSuperAdmin,  # noqa: F401 — re-exported
)

__all__ = [
    "IsInstitutionAdminOrReadOnly",
    "IsCenterDirectorOrReadOnly",
    "IsSuperAdmin",
    "IsSameInstitution",
]


# ──────────────────────────────────────────────────────────
# IsInstitutionAdminOrReadOnly
# ──────────────────────────────────────────────────────────


class IsInstitutionAdminOrReadOnly(BasePermission):
    """Write: requires Institution Admin role (level ≤ 2).
    Read: requires authentication (any role).
    """

    def has_permission(self, request: Request, view) -> bool:
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return HasRoleLevelOrHigher.has_level(request, 2)


# ──────────────────────────────────────────────────────────
# IsCenterDirectorOrReadOnly
# ──────────────────────────────────────────────────────────


class IsCenterDirectorOrReadOnly(BasePermission):
    """Write: requires Center Director role (level ≤ 3).
    Read: requires authentication (any role).
    """

    def has_permission(self, request: Request, view) -> bool:
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return HasRoleLevelOrHigher.has_level(request, 3)
