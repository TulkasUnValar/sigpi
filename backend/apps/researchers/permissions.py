"""
DRF Permission classes for the researchers module.

Provides:
- IsResearcherOrReadOnly: write requires owning researcher or institution admin+,
  read requires authentication (same-institution filtering is handled by
  IsSameInstitution at the object level).

Re-exports from apps.accounts.permissions:
- IsInstitutionAdminOrReadOnly — for researcher write protection
- IsSameInstitution — for object-level tenant scoping

Design reference: openspec/changes/researchers/design.md — Permission Matrix
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import (
    HasRoleLevelOrHigher,
    IsSameInstitution,  # noqa: F401 — re-exported
)
from apps.institutions.permissions import (
    IsInstitutionAdminOrReadOnly,  # noqa: F401 — re-exported
)

__all__ = [
    "IsResearcherOrReadOnly",
    "IsInstitutionAdminOrReadOnly",
    "IsSameInstitution",
]


# ──────────────────────────────────────────────────────────
# IsResearcherOrReadOnly
# ──────────────────────────────────────────────────────────


class IsResearcherOrReadOnly(BasePermission):
    """Write: user is the owning researcher (self-profile) OR has role level ≤ 2 (admin+).
    Read: any authenticated user.

    Institution scoping is handled by IsSameInstitution at the object level.
    This permission only checks ownership and role privileges.
    """

    def has_permission(self, request: Request, view) -> bool:
        # Read: any authenticated user
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        # Write: researcher role or higher (level ≤ 4)
        return HasRoleLevelOrHigher.has_level(request, 4)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        # Read: any authenticated user (institution scoping is separate)
        if request.method in SAFE_METHODS:
            return True

        # Write: determine the researcher from the object.
        # For nested objects (affiliations, profiles, attachments), the parent
        # researcher is accessible via .researcher attribute.
        # For Researcher instances directly, use the object itself.
        researcher = getattr(obj, "researcher", None)
        if researcher is None:
            researcher = obj

        if researcher is None:
            return False

        # Self-edit: user is the owning researcher
        if researcher.user_id is not None and researcher.user_id == request.user.id:
            return True

        # Admin+ (level ≤ 2) can edit any researcher in their institution
        return HasRoleLevelOrHigher.has_level(request, 2)
