"""
DRF Permission classes for the calls module.

Provides:
- CanManageCall: director_centro (level <= 3) + institution match.

Admin+ (level <= 2) and superadmin bypass institution checks.
Researchers and below are denied mutations.

Design reference: openspec/changes/calls/design.md — Permission Classes
Spec reference:   openspec/changes/calls/spec.md — Permission Matrix
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher

__all__ = ["CanManageCall"]


# ──────────────────────────────────────────────────────────
# CanManageCall
# ──────────────────────────────────────────────────────────


class CanManageCall(BasePermission):
    """Permission for managing Calls: create, update, delete, FSM transitions.

    has_permission: checks role level <= 3 (Director de Centro or higher).
    has_object_permission: validates that the user's active institution
    matches the call's institution_id. Superadmin bypasses.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        return HasRoleLevelOrHigher.has_level(request, 3)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not HasRoleLevelOrHigher.has_level(request, 3):
            return False

        # Superadmin and Admin+ (level <= 2) bypass institution check
        if request.user.is_superuser or HasRoleLevelOrHigher.has_level(request, 2):
            return True

        membership = getattr(request, "active_membership", None)
        if membership is None:
            return False

        obj_inst_id = getattr(obj, "institution_id", None)
        if obj_inst_id is None:
            return False

        return str(membership.institution_id) == str(obj_inst_id)
