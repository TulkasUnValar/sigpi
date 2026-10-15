"""
Permissions for dashboard endpoints.

Role-based access control for the dashboard summary endpoint.
Only users with specific role levels can access dashboard metrics.

Allowed levels:
- Level 1 (superadmin): Full access to all metrics
- Level 2 (admin): Institution-scoped metrics
- Level 3 (director): Institution and center-scoped metrics
- Level 4 (researcher): Own projects metrics
- Level 7 (auditor): Read-only access

Denied:
- Level 5 (evaluador): No dashboard access
- Level 6 (asistente): No dashboard access
"""

from rest_framework import permissions


class IsDashboardAuthorized(permissions.BasePermission):
    """
    Allow access only to users with specific role levels.

    Superadmin (level 1), Admin (level 2), Director (level 3),
    Researcher (level 4), and Auditor (level 7) can access.
    Evaluador (level 5) and Asistente (level 6) are denied.
    """

    ALLOWED_LEVELS = {1, 2, 3, 4, 7}

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers always have access
        if request.user.is_superuser:
            return True

        # Check if user has an active membership with allowed role level
        membership = getattr(request, "active_membership", None)
        if not membership:
            return False

        # Check role level
        role_level = membership.role.level
        return role_level in self.ALLOWED_LEVELS
