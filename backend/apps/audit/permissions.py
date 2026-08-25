"""
Read authorization for the audit module.

Implements the spec Permissions Matrix (RA-8) and the design decision on
read authorization: a dedicated ``IsAuditReader`` permission that allows
only audit-relevant roles — Auditor, Director de Centro, Admin
Institucional, and Superadmin — while explicitly denying researchers
(Investigador), coinvestigators (Evaluador), assistants, and anonymous
users. Django superusers bypass every check, which enables cross-
institution reads.

The existing ``accounts.IsAuditor`` intentionally permits higher roles
(including researchers); a dedicated permission prevents researcher
audit reads while preserving that existing behavior.

Design reference: openspec/changes/audit/design.md — Read authorization
Spec reference:   openspec/changes/audit/specs/audit/spec.md — Permissions Matrix (RA-8)
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

# Seeded hierarchy (migration 0002_seed_roles):
# 1 Superadmin · 2 Admin Institucional · 3 Director de Centro
# 4 Investigador · 5 Evaluador (Coinvestigador) · 6 Asistente · 7 Auditor
AUDIT_READER_ROLE_LEVELS = frozenset({1, 2, 3, 7})


class IsAuditReader(BasePermission):
    """Allow read-only audit access to audit-relevant roles.

    Allowed: Auditor (7), Director de Centro (3), Admin Institucional (2),
    Superadmin (1), and Django superusers (bypass).
    Denied: Investigador (4), Evaluador/Coinvestigador (5), Asistente (6),
    users without an active membership, anonymous users, and any
    non-safe HTTP method.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        # The audit API is read-only (RA-8).
        if request.method not in SAFE_METHODS:
            return False

        # Superadmin bypasses institution scope (cross-institution read).
        if request.user.is_superuser:
            return True

        membership = getattr(request, "active_membership", None)
        if membership is None or not getattr(membership, "is_active", False):
            return False

        role = getattr(membership, "role", None)
        if role is None:
            return False

        return role.level in AUDIT_READER_ROLE_LEVELS
