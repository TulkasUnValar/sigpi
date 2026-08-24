"""
DRF Permission classes for the budgets module.

Provides:
- CanManageBudget: role level ≤3 (Superadmin, Admin, Director de Centro)
  for mutations, with project-center membership on object permission
  (Directors only; Admin+ and superadmin bypass).
- CanAuthorizeExecution: role level ≤3, used to authorize execution
  overruns (RN-020).
- IsSameInstitution: re-exported from accounts for tenant object scoping.

Researchers and below (level ≥4) are read-only.

Design reference: openspec/changes/budgets/design.md — API and Permissions
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md — Security
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher, IsSameInstitution

__all__ = ["CanManageBudget", "CanAuthorizeExecution", "IsSameInstitution"]


# ──────────────────────────────────────────────────────────
# CanManageBudget
# ──────────────────────────────────────────────────────────


class CanManageBudget(BasePermission):
    """Permission for managing budgets: create, update, delete.

    has_permission: checks role level ≤ 3 (Director de Centro or higher).
    has_object_permission: for Center Directors (level 3), validates that
    the user's membership includes the project's center. Superadmin and
    Admin+ (level ≤ 2) bypass the center check.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        return HasRoleLevelOrHigher.has_level(request, 3)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not HasRoleLevelOrHigher.has_level(request, 3):
            return False

        # Superadmin and Admin+ (level ≤ 2) bypass center check
        if request.user.is_superuser or HasRoleLevelOrHigher.has_level(request, 2):
            return True

        membership = getattr(request, "active_membership", None)
        if membership is None:
            return False

        obj_center_id = getattr(obj, "center_id", None)
        if obj_center_id is None:
            return False

        user_center_ids = set(membership.centers.values_list("id", flat=True))
        return obj_center_id in user_center_ids


# ──────────────────────────────────────────────────────────
# CanAuthorizeExecution
# ──────────────────────────────────────────────────────────


class CanAuthorizeExecution(BasePermission):
    """Permission for authorizing execution overruns (RN-020).

    Only Superadmin, Institution Admin, and Center Director (level ≤ 3)
    may authorize an execution whose cumulative sum exceeds the line's
    approved amount.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        return HasRoleLevelOrHigher.has_level(request, 3)
