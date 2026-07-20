"""
SIGPI Tenant-Scoped Manager.

Implements the tenant isolation query filtering defined in design.md:
- TenantScopedQuerySet.for_tenant(): auto-filters by institution_id
- Superadmin bypass: returns unfiltered queryset
- No institution: returns unfiltered queryset (identity)

Design reference: openspec/changes/auth/design.md — TenantScopedQuerySet
"""

from django.db import models


class TenantScopedQuerySet(models.QuerySet):
    """QuerySet that can auto-filter by the request's active institution.

    Usage:
        MyModel.objects.for_tenant(request).all()

    Behavior:
        - If request.user.is_superuser → unfiltered (sees everything)
        - If request.institution_id is set → .filter(institution_id=...)
        - If request.institution_id is None or missing → unfiltered
    """

    def for_tenant(self, request):
        """Apply tenant-scoping to this queryset.

        Args:
            request: DRF Request or Django HttpRequest with:
                - user: Django User (checked for is_superuser)
                - institution_id: UUID string of active institution

        Returns:
            Filtered queryset if a non-superadmin user has an active institution,
            otherwise the original unfiltered queryset.
        """
        user = getattr(request, "user", None)
        institution_id = getattr(request, "institution_id", None)

        # Superadmin: return everything
        if user is not None and user.is_authenticated and user.is_superuser:
            return self

        # No institution context: return everything
        if not institution_id:
            return self

        # Apply tenant filter
        return self.filter(institution_id=institution_id)
