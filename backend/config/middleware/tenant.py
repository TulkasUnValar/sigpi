"""
SIGPI Tenant Middleware.

Implements the tenant isolation layer defined in design.md:
- TenantMiddleware: injects institution_id from session, loads active_membership,
  enforces tenant requirement for protected endpoints, and populates the
  request-scoped audit context (actor, IP, institution) for signal capture.
- TenantRLSMiddleware: sets PostgreSQL RLS session variables per request.

Spec references: FR-004, FR-006
Design reference: openspec/changes/auth/design.md — TenantMiddleware, PostgreSQL RLS Design
"""
import logging

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.accounts.audit import AuditEventEmitter
from apps.accounts.models import InstitutionMembership
from apps.audit.context import reset_audit_context, set_audit_context

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# TenantMiddleware
# ──────────────────────────────────────────────────────────


class TenantMiddleware:
    """Injects institution_id from session into request context.

    Sets request.institution_id and request.active_membership.
    Returns 400 if endpoint requires tenant but none is active.

    Design decisions:
    - institution_id stored in Django session (soft reset per spec)
    - active_membership loaded from DB with select_related('role')
    - Tenant-required endpoints are prefix-matched against TENANT_REQUIRED_PREFIXES
    - Anonymous users bypass the tenant check
    """

    # Endpoints that require an active institution
    TENANT_REQUIRED_PREFIXES = [
        "/api/projects/",
        "/api/researchers/",
        "/api/progress/",
        "/api/budgets/",
        "/api/calls/",
        "/api/products/",
        "/api/documents/",
        "/api/minutes/",
        "/api/institutions/",
        "/api/centers/",
        "/api/groups/",
        "/api/lines/",
        "/api/workflows/",
        "/api/audit/",
        "/api/notifications/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.institution_id = request.session.get("institution_id")
        request.active_membership = None

        if request.user.is_authenticated and request.institution_id:
            request.active_membership = (
                InstitutionMembership.objects
                .select_related("role")
                .filter(
                    user=request.user,
                    institution_id=request.institution_id,
                    is_active=True,
                )
                .first()
            )

        # Populate the request-scoped audit context so signal receivers can
        # attribute actor/IP/institution (design: reset in middleware finally).
        set_audit_context(
            user=request.user if request.user.is_authenticated else None,
            ip_address=AuditEventEmitter.extract_ip(request),
            institution_id=request.institution_id,
        )

        try:
            # Enforce tenant requirement for protected endpoints.
            # Only applies to authenticated users — anonymous users are handled
            # by the authentication layer (Django auth middleware / DRF).
            # Superusers bypass: cross-institution reads (e.g. audit API) must
            # work without an active institution (spec Permissions Matrix).
            if (
                request.user.is_authenticated
                and not request.user.is_superuser
                and self._requires_tenant(request.path)
                and not request.institution_id
            ):
                return JsonResponse(
                    {"detail": "Active institution required."},
                    status=400,
                )

            return self.get_response(request)
        finally:
            reset_audit_context()

    def _requires_tenant(self, path: str) -> bool:
        """Check if the request path requires an active tenant."""
        return any(path.startswith(prefix) for prefix in self.TENANT_REQUIRED_PREFIXES)


# ──────────────────────────────────────────────────────────
# TenantRLSMiddleware
# ──────────────────────────────────────────────────────────


class TenantRLSMiddleware:
    """Sets PostgreSQL session variables for RLS on each request.

    Design decisions:
    - SET LOCAL scopes to the current transaction
    - institution_id: restricts row visibility per tenant
    - bypass_rls: superadmins skip RLS
    - Anonymous users (no institution) bypass RLS — no context to set
    - Runs AFTER TenantMiddleware (which sets request.institution_id)

    Note: SQLite does not support SET LOCAL. This middleware is designed
    for PostgreSQL. In test environments (SQLite), the cursor operations
    will be no-ops when the DB engine doesn't support them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if hasattr(request, "institution_id") and request.institution_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET LOCAL sigpi.institution_id = %s",
                        [str(request.institution_id)],
                    )
            except Exception:
                # Gracefully handle non-PostgreSQL backends (e.g., SQLite in tests)
                logger.debug(
                    "RLS session variable not set — non-PostgreSQL backend or "
                    "unsupported operation"
                )

        # Superadmin bypass
        if request.user.is_authenticated and request.user.is_superuser:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL sigpi.bypass_rls = true")
            except Exception:
                logger.debug("RLS bypass not set — unsupported backend")

        return self.get_response(request)
