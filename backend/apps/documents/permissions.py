"""
DRF Permission classes for the documents module.

Provides:
- CanWriteDocuments: write actions (presign, confirm, sign, minutes-create)
  require role level ≤ 6 (all roles except Auditor, per SPEC §6.7
  permissions table); SAFE_METHODS are allowed for any authenticated member.
  Institution scoping is delegated to IsSameInstitution.
- IsSameInstitution: re-exported from accounts for tenant object scoping.
- IsAuditor: re-exported from accounts — auditors are read-only.

Design reference: openspec/changes/attachments/design.md — API and Permissions
Spec reference:   openspec/changes/attachments/specs/documents/spec.md — Authorization
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.permissions import HasRoleLevelOrHigher, IsAuditor, IsSameInstitution

__all__ = ["CanWriteDocuments", "IsSameInstitution", "IsAuditor"]


# ──────────────────────────────────────────────
# CanWriteDocuments
# ──────────────────────────────────────────────


class CanWriteDocuments(BasePermission):
    """Write access for document upload/sign/minutes actions.

    has_permission: SAFE_METHODS require authentication only; unsafe
    methods require role level ≤ 6 (all roles except Auditor).
    has_object_permission mirrors has_permission — the institution check
    is delegated to IsSameInstitution.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return HasRoleLevelOrHigher.has_level(request, 6)

    def has_object_permission(self, request: Request, view, obj) -> bool:
        return self.has_permission(request, view)
