"""
Permission classes for the project_workflow module.

IsWorkflowStepApprover: reuses IsCenterDirectorForProject logic.
Checks user's center membership against the project's center.
Admin+ (level ≤ 2) bypasses.

Design reference: openspec/changes/project_workflow/design.md
Spec reference:   openspec/changes/project_workflow/spec.md
"""
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher

__all__ = ["IsWorkflowStepApprover"]


class IsWorkflowStepApprover(BasePermission):
    """User's membership includes the project's center with Director role (level ≤ 3).

    has_permission: checks role level ≤ 3.
    has_object_permission: validates that the user's membership.centers
                           includes the project's center_id.
    Superadmin and Admin+ (level ≤ 2) bypass the center list check.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        return HasRoleLevelOrHigher.has_level(request, 3)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        if not HasRoleLevelOrHigher.has_level(request, 3):
            return False

        # Superadmins and Admin+ (level ≤ 2) bypass center check
        if request.user.is_superuser or HasRoleLevelOrHigher.has_level(request, 2):
            return True

        membership = getattr(request, "active_membership", None)
        if membership is None:
            return False

        # Resolve project's center_id from the workflow instance
        # WorkflowInstance stores project_id (UUID) without a FK to Project,
        # so we look up the Project lazily.
        obj_center_id = self._resolve_center_id(obj)
        if obj_center_id is None:
            return False

        user_center_ids = set(
            membership.centers.values_list("id", flat=True)
        )
        return obj_center_id in user_center_ids

    @staticmethod
    def _resolve_center_id(obj) -> str | None:
        """Return the center_id for the project linked to a workflow instance.

        Accepts WorkflowInstance or any object with a `project_id` attribute.
        """
        project_id = getattr(obj, "project_id", None)
        if project_id is None:
            return None

        # Lazy import to avoid circular dependency at module load time
        from apps.projects.models import Project

        try:
            project = Project.objects.only("center_id").get(pk=project_id)
            return project.center_id
        except Project.DoesNotExist:
            return None
