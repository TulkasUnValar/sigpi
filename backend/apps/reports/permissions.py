"""
DRF Permission classes for the reports (informes) module.

Provides:
- CanGenerateReport: HasRoleLevelOrHigher(4) + IsSameInstitution
- Re-export: IsCenterDirectorForProject from projects (for CanApproveReport)

Design reference: openspec/changes/reports/design.md — Permission Classes
Spec reference:   sdd/reports/spec — RN-015, RN-016
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher, IsSameInstitution
from apps.projects.permissions import IsCenterDirectorForProject  # noqa: F401 — re-export

__all__ = [
    "CanGenerateReport",
    "IsCenterDirectorForProject",
]


class CanGenerateReport(BasePermission):
    """User has Researcher role (level ≤ 4) AND belongs to the same institution.

    Admin+ (level ≤ 2) bypasses all checks.
    SAFE_METHODS pass at the view level.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # SAFE_METHODS always pass at view level
        if request.method in SAFE_METHODS:
            return True

        # Non-admin must have Researcher role (≤ 4)
        return HasRoleLevelOrHigher.has_level(request, 4)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # Same-institution check (RN-015)
        return IsSameInstitution().has_object_permission(request, view, obj)
