"""
SIGPI DRF Permission Classes.

Implements the authorization layer defined in design.md:
- Role-based permission classes for each of the 7 roles
- Role hierarchy: higher roles inherit lower permissions
- IsSameInstitution: tenant-scoping at the object level

Spec references: FR-005
Design reference: openspec/changes/auth/design.md — Custom DRF Permission Classes
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Role Hierarchy Utility
# ──────────────────────────────────────────────────────────


class HasRoleLevelOrHigher:
    """Static utility to check if the request user has a sufficient role level.

    Level 1 = Superadmin (highest privilege)
    Level 7 = Auditor (lowest privilege)

    A user with a LOWER level number has MORE privilege.
    has_level(request, 3) returns True for users with level 1, 2, or 3.
    """

    @staticmethod
    def has_level(request: Request, required_level: int) -> bool:
        """Check if the user has role level <= required_level.

        Args:
            request: DRF request with user and active_membership attributes.
            required_level: The minimum level needed (lower = more privilege).

        Returns:
            True if the user's role level is <= required_level.
        """
        if not request.user.is_authenticated:
            return False

        # Superadmin (Django is_superuser) bypasses all checks
        if request.user.is_superuser:
            return True

        # Must have an active institution
        institution_id = getattr(request, "institution_id", None)
        if not institution_id:
            return False

        # Must have an active membership
        membership = getattr(request, "active_membership", None)
        if membership is None:
            return False

        role = membership.role
        if role is None:
            return False

        return role.level <= required_level


# ──────────────────────────────────────────────────────────
# Role-Based Permission Classes
# ──────────────────────────────────────────────────────────


class IsSuperAdmin(BasePermission):
    """Only Django superuser or Superadmin role.

    Checks:
    1. user.is_superuser (local-only superadmin)
    2. active_membership.role.level <= 1 (Superadmin role from Keycloak)
    """

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 1)


class IsInstitutionAdmin(BasePermission):
    """Admin Institucional role or higher (level <= 2).

    Allows: Superadmin, Admin Institucional
    Denies: Director de Centro and below
    """

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 2)


class IsCenterDirector(BasePermission):
    """Director de Centro role or higher (level <= 3).

    has_permission: checks role level only.
    has_object_permission: also validates center membership.
    """

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 3)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not HasRoleLevelOrHigher.has_level(request, 3):
            return False

        # Superadmins bypass center check
        if request.user.is_superuser:
            return True

        membership = getattr(request, "active_membership", None)
        if membership is None:
            return False

        # Check if the object's center is in the user's center list
        obj_center_id = getattr(obj, "center_id", None)
        if obj_center_id is None:
            return False

        user_center_ids = set(membership.centers.values_list("id", flat=True))
        return obj_center_id in user_center_ids


class IsResearcher(BasePermission):
    """Investigador role or higher (level <= 4)."""

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 4)


class IsEvaluador(BasePermission):
    """Evaluador role or higher (level <= 5)."""

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 5)


class IsAssistant(BasePermission):
    """Asistente role or higher (level <= 6)."""

    def has_permission(self, request: Request, view) -> bool:
        return HasRoleLevelOrHigher.has_level(request, 6)


class IsAuditor(BasePermission):
    """Auditor role or higher (level <= 7) — READ-ONLY.

    Auditors can only use SAFE_METHODS (GET, HEAD, OPTIONS).
    Higher roles (Researcher, etc.) also pass this check.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not HasRoleLevelOrHigher.has_level(request, 7):
            return False
        return request.method in SAFE_METHODS


# ──────────────────────────────────────────────────────────
# Object-Level Tenant Permissions
# ──────────────────────────────────────────────────────────


class IsSameInstitution(BasePermission):
    """Object must belong to the user's active institution.

    has_permission: always True (defer to object-level check).
    has_object_permission: checks obj.institution_id == request.institution_id.
    Superadmin bypasses the check.
    """

    def has_permission(self, request: Request, view) -> bool:
        return True

    def has_object_permission(self, request: Request, view, obj) -> bool:
        # Superadmin bypasses institution check
        if request.user.is_authenticated and request.user.is_superuser:
            return True

        institution_id = getattr(request, "institution_id", None)
        if not institution_id:
            return False

        obj_inst_id = getattr(obj, "institution_id", None)
        if obj_inst_id is None:
            return False

        return str(institution_id) == str(obj_inst_id)
