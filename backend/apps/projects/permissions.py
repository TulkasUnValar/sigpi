"""
DRF Permission classes for the projects module.

Provides 4 permission classes defined in design.md:
- IsProjectOwnerOrCoInvestigator: PI or co_investigator member; Admin+ bypasses
- IsCenterDirectorForProject: user's membership includes project's center with Director role
- CanCreateProjectInCenter: Researcher level ≤ 4 AND affiliation with target center (RN-009)
- IsProjectEditable: object-level; False if terminal AND user not Admin+ (RN-011)

Design reference: openspec/changes/projects/design.md — Permission Classes
Spec reference:   openspec/changes/projects/spec.md — Permission Matrix
"""
from django.contrib.auth import get_user_model
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher
from apps.projects.models import TERMINAL_STATES

User = get_user_model()

__all__ = [
    "IsProjectOwnerOrCoInvestigator",
    "IsCenterDirectorForProject",
    "CanCreateProjectInCenter",
    "IsProjectEditable",
]


# ──────────────────────────────────────────────────────────
# IsProjectOwnerOrCoInvestigator
# ──────────────────────────────────────────────────────────


class IsProjectOwnerOrCoInvestigator(BasePermission):
    """User is PI (principal_investigator.user == request.user)
    OR co_investigator member (members.filter(researcher__user=user, role='co_investigator')).
    Admin+ (level ≤ 2) bypasses.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        # Admin+ (level ≤ 2) bypasses all checks
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True
        # For non-admin users: check at object level only
        # SAFE_METHODS always pass at view level
        if request.method in SAFE_METHODS:
            return True
        return HasRoleLevelOrHigher.has_level(request, 4)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # Check if user is PI via principal_investigator.user
        pi = getattr(obj, "principal_investigator", None)
        if pi is not None and getattr(pi, "user_id", None) == request.user.id:
            return True

        # Check if user is a co_investigator member
        members = getattr(obj, "members", None)
        if members is not None and hasattr(members, "filter"):
            return members.filter(
                researcher__user_id=request.user.id,
                role="co_investigator",
            ).exists()

        return False


# ──────────────────────────────────────────────────────────
# IsCenterDirectorForProject
# ──────────────────────────────────────────────────────────


class IsCenterDirectorForProject(BasePermission):
    """User's membership includes the project's center with Director role (level ≤ 3).

    has_permission: checks role level ≤ 3.
    has_object_permission: validates that the user's membership.centers
                           includes the project's center_id.
    Superadmin bypasses the center list check.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
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

        # Check if the project's center is in the user's center list
        obj_center_id = getattr(obj, "center_id", None)
        if obj_center_id is None:
            return False

        user_center_ids = set(
            membership.centers.values_list("id", flat=True)
        )
        return obj_center_id in user_center_ids


# ──────────────────────────────────────────────────────────
# CanCreateProjectInCenter
# ──────────────────────────────────────────────────────────


class CanCreateProjectInCenter(BasePermission):
    """User has Researcher role (level ≤ 4) AND ResearcherAffiliation
    with the target center (RN-009).

    The target center is determined from:
    1. request.data["center"] (for POST /projects/).
    2. URL kwargs (for nested creation within a center context).
    Admin+ (level ≤ 2) bypasses.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # Must be at least Researcher level (≤ 4)
        if not HasRoleLevelOrHigher.has_level(request, 4):
            return False

        # Determine the target center
        center_id = None
        if hasattr(request, "data") and isinstance(request.data, dict):
            center_id = request.data.get("center")
        if not center_id and hasattr(view, "kwargs"):
            center_id = view.kwargs.get("center_pk")

        if not center_id:
            # Can't determine center — defer to object-level check
            return True

        # Check ResearcherAffiliation for the user's researcher profile
        from apps.researchers.models import Researcher, ResearcherAffiliation

        try:
            researcher = Researcher.objects.get(user=request.user)
        except Researcher.DoesNotExist:
            return False

        return ResearcherAffiliation.objects.filter(
            researcher=researcher,
            center_id=center_id,
        ).exists()


# ──────────────────────────────────────────────────────────
# IsProjectEditable
# ──────────────────────────────────────────────────────────


class IsProjectEditable(BasePermission):
    """Object-level permission: returns False if the project is in a terminal
    state AND the user is not Admin+ (level ≤ 2).

    Enforces RN-011: terminal projects reject mutations by non-admin users.
    Applied to ProjectMemberViewSet and ProjectDocumentViewSet, which check
    the PARENT project's status.

    has_permission: always True (defers to object-level).
    """

    def has_permission(self, request: Request, view) -> bool:
        return True

    def has_object_permission(self, request: Request, view, obj) -> bool:
        status = getattr(obj, "status", None)

        # Non-terminal projects are always editable
        if status not in TERMINAL_STATES:
            return True

        # Terminal projects: only Admin+ (level ≤ 2) can mutate
        return HasRoleLevelOrHigher.has_level(request, 2)
