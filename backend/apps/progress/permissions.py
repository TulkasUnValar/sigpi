"""
DRF Permission classes for the progress (advances) module.

Provides:
- IsProgressCreatorOrProjectMember: user is created_by OR ProjectMember
- Re-export: IsCenterDirectorForProject from projects (accepted coupling)

Design reference: openspec/sdd/advances/design.md — Permission Classes
Spec reference:   openspec/sdd/advances/spec.md — Permission Matrix
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher
from apps.projects.permissions import IsCenterDirectorForProject  # noqa: F401 — re-export

__all__ = [
    "CanReturnToDraft",
    "IsCenterDirectorForProject",
    "IsProgressCreatorOrProjectMember",
]


class IsProgressCreatorOrProjectMember(BasePermission):
    """User is report.created_by OR is a ProjectMember of report.project.

    Admin+ (level ≤ 2) bypasses all checks.
    SAFE_METHODS pass at the view level.

    Used for: CRUD + submit/resubmit/create.
    Not used for: director-only actions (approve, observe, reject, accept_review).
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses all checks
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # SAFE_METHODS always pass at view level
        if request.method in SAFE_METHODS:
            return True

        # Non-admin must have Researcher role (≤ 4) for mutation
        return HasRoleLevelOrHigher.has_level(request, 4)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False

        # Admin+ (level ≤ 2) bypasses
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        # Check if user is the creator of this report
        if getattr(obj, "created_by_id", None) == request.user.id:
            return True

        # Check if user is a ProjectMember of the associated project
        project = getattr(obj, "project", None)
        if project is not None and hasattr(project, "members"):
            return project.members.filter(
                researcher__user_id=request.user.id,
            ).exists()

        return False


class CanReturnToDraft(BasePermission):
    """Permission for return_to_draft action.

    - From ``rechazado``: creator (PI) can trigger.
    - From ``en_revision`` / ``observado``: center director can trigger.

    Admin+ (level ≤ 2) bypasses all checks.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True
        return HasRoleLevelOrHigher.has_level(request, 4)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False
        if HasRoleLevelOrHigher.has_level(request, 2):
            return True

        status = getattr(obj, "status", None)

        # From rechazado → creator (PI) can trigger
        if status == "rechazado":
            if getattr(obj, "created_by_id", None) == request.user.id:
                return True
            project = getattr(obj, "project", None)
            if project is not None and hasattr(project, "members"):
                return project.members.filter(
                    researcher__user_id=request.user.id,
                ).exists()
            return False

        # From en_revision / observado → director can trigger
        project = getattr(obj, "project", None)
        if project is not None:
            from apps.projects.permissions import IsCenterDirectorForProject
            return IsCenterDirectorForProject().has_object_permission(
                request, view, project,
            )

        return False
