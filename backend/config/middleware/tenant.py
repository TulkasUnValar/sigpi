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
from config import tenant_context

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
        "/api/search/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.institution_id = request.session.get("institution_id")
        request.active_membership = None

        if request.user.is_authenticated and request.institution_id:
            request.active_membership = (
                InstitutionMembership.objects.select_related("role")
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
    """Establishes the PostgreSQL tenant context for every request.

    Ordering requirement: this middleware must run BEFORE ``TenantMiddleware``.
    ``TenantMiddleware`` reads the RLS-protected
    ``accounts_institutionmembership`` table to load ``active_membership``; if
    the tenant context is not already on the connection, that read runs under a
    least-privilege role with no GUC and returns nothing. Placing this class
    after ``TenantMiddleware`` would therefore silently break membership
    loading once the runtime switches to ``sigpi_app``.

    Design decisions:
    - Reads ``institution_id`` from the session itself, so it does not depend
      on ``TenantMiddleware`` having run
    - ``bypass`` is granted only to an authenticated superuser
    - The context is connection-scoped (see ``config.tenant_context``), not
      ``SET LOCAL``, because there is no request-spanning transaction
    - Anonymous / institution-less requests still write both GUCs (empty
      tenant, no bypass), so a stale value can never leak into the request
    - No-op on SQLite: RLS is a PostgreSQL feature and the default local test
      engine has no GUCs
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if connection.vendor != "postgresql":
            return self.get_response(request)

        institution_id = request.session.get("institution_id")
        bypass = bool(
            getattr(request.user, "is_authenticated", False) and request.user.is_superuser
        )

        try:
            tenant_context.activate(connection, institution_id, bypass)
        except Exception:
            # Deliberate tradeoff: a failure to establish the tenant context is
            # logged and the request continues instead of being rejected. The
            # runtime still connects as a superuser, so rejecting here would be
            # a production regression today; failing the request is deferred to
            # the change that switches the runtime role, when enforcement
            # actually matters. It is never silent — the traceback is logged.
            logger.exception(
                "Failed to establish the PostgreSQL tenant context; serving the request without it."
            )
            tenant_context.clear(connection)
            return self.get_response(request)

        try:
            return self.get_response(request)
        finally:
            tenant_context.clear(connection)
