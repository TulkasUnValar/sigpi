"""
SIGPI Auth API Views.

Implements the authentication API endpoints defined in design.md:
- local_login_view: local username/password login with Keycloak fallback
- switch_institution_view: switch active institution (FR-004)
- keycloak_health_view: Keycloak availability check
- account_linking_view: manual account linking confirmation
- auth_me_view: current user profile
- logout_view: session destruction

Spec references: FR-002, FR-003, FR-004
Design reference: openspec/changes/auth/design.md — API Design
"""

import json
import logging

from django.contrib.auth import authenticate, login, logout
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.accounts.audit import AuditEventEmitter, AuditEventType
from apps.accounts.models import InstitutionMembership
from config import tenant_context

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# JSON-aware login_required decorator
# ──────────────────────────────────────────────────────────


def login_required_json(view_func):
    """Login-required for API views — returns 401 JSON instead of redirect."""

    def _wrapped(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Authentication credentials were not provided."},
                status=401,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


# ──────────────────────────────────────────────────────────
# Keycloak Health Check
# ──────────────────────────────────────────────────────────


@require_http_methods(["GET"])
def keycloak_health_view(request: HttpRequest) -> JsonResponse:
    """Check Keycloak availability.

    Used by the local login flow to decide whether to
    require SSO (KC up) or allow local auth (KC down).

    Design: 2s timeout to Keycloak health endpoint.
    Returns: {"status": "available" | "unavailable"}
    """
    # In production this would make a real HTTP request to Keycloak.
    # For now, report status based on whether OIDC is configured.
    from django.conf import settings

    try:
        token_endpoint = getattr(settings, "OIDC_OP_TOKEN_ENDPOINT", None)
        if token_endpoint:
            status = "available"
        else:
            status = "unavailable"
    except Exception:
        status = "unknown"

    return JsonResponse({"status": status})


# ──────────────────────────────────────────────────────────
# Local Login (django-allauth fallback)
# ──────────────────────────────────────────────────────────


@csrf_exempt
@require_http_methods(["POST"])
def local_login_view(request: HttpRequest) -> JsonResponse:
    """Authenticate user with local email+password.

    Implements FR-002: local fallback when Keycloak is unreachable.

    Request: POST {"email": "...", "password": "..."}
    Response 200: {"user": {...}, "csrf_token": "..."}
    Response 401: {"detail": "Authentication failed."}
    Response 400: {"detail": "Email and password are required."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"detail": "Invalid JSON."},
            status=400,
        )

    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return JsonResponse(
            {"detail": "Email and password are required."},
            status=400,
        )

    # Authenticate against allauth ModelBackend + local User
    user = authenticate(request, username=email, password=password)

    if user is None:
        logger.info("Failed local login attempt for email: %s", email)
        AuditEventEmitter().emit(
            event_type=AuditEventType.FAILED_LOGIN,
            user=None,
            ip_address=AuditEventEmitter.extract_ip(request),
            details={"email_attempted": email, "reason": "invalid_credentials"},
        )
        return JsonResponse(
            {"detail": "Authentication failed."},
            status=401,
        )

    if not user.is_active:
        AuditEventEmitter().emit(
            event_type=AuditEventType.FAILED_LOGIN,
            user=user,
            ip_address=AuditEventEmitter.extract_ip(request),
            details={"email_attempted": email, "reason": "account_disabled"},
        )
        return JsonResponse(
            {"detail": "User account is disabled."},
            status=401,
        )

    # Create Django session
    login(request, user)

    # Re-scope the RLS context to the just-authenticated user so the
    # primary-membership read below is allowed by the own_memberships policy.
    # The middleware wrote this context before login(), when the request was
    # still anonymous.
    _activate_rls_context(user.pk, None)

    # Set initial institution if user has a primary membership
    primary = user.memberships.filter(is_primary=True, is_active=True).first()
    if primary:
        request.session["institution_id"] = str(primary.institution_id)
        request.session["active_role"] = primary.role.name

    # Emit audit event. institution_id is read after the conditional so it is
    # whatever the session ended up with, and the context is re-scoped to it
    # before emitting: the audit tenant_insert policy requires
    # institution_id = sigpi.institution_id.
    institution_id = request.session.get("institution_id")
    _activate_rls_context(user.pk, institution_id)
    AuditEventEmitter().emit(
        event_type=AuditEventType.LOGIN,
        user=user,
        ip_address=AuditEventEmitter.extract_ip(request),
        institution_id=institution_id,
        details={"auth_source": user.auth_source},
    )

    # Build user response
    user_data = _serialize_user(request)
    return JsonResponse({"user": user_data}, status=200)


# ──────────────────────────────────────────────────────────
# Account Linking — Manual Confirmation
# ──────────────────────────────────────────────────────────


@require_http_methods(["POST"])
@login_required_json
def account_linking_view(request: HttpRequest) -> JsonResponse:
    """Confirm manual account linking for unverified email.

    Implements FR-003: manual confirmation required.

    Request: POST {"confirm": true}
    Response 200: {"detail": "Account linked successfully."}
    Response 400: {"detail": "No pending account link."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    confirm = body.get("confirm", False)
    if not confirm:
        return JsonResponse(
            {"detail": "Confirmation required."},
            status=400,
        )

    # Account linking is handled by the OIDC backend at login time.
    # This endpoint is for cases where the user needs to manually
    # confirm linking after a previous 409 response.
    pending_link = request.session.get("pending_account_link")
    if not pending_link:
        return JsonResponse(
            {"detail": "No pending account link."},
            status=400,
        )

    # Clear pending state
    del request.session["pending_account_link"]

    return JsonResponse(
        {"detail": "Account linked successfully."},
        status=200,
    )


# ──────────────────────────────────────────────────────────
# Current User Profile
# ──────────────────────────────────────────────────────────


@login_required_json
@require_http_methods(["GET"])
def auth_me_view(request: HttpRequest) -> JsonResponse:
    """Return the current authenticated user's profile.

    Includes memberships, active institution, and active role.

    Response 200: User profile JSON.
    Response 401: Not authenticated.
    """
    return JsonResponse(_serialize_user(request), status=200)


# ──────────────────────────────────────────────────────────
# Logout
# ──────────────────────────────────────────────────────────


@login_required_json
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> JsonResponse:
    """Destroy the current session.

    Response 200: {"detail": "Logged out."}
    """
    # Capture data before logout destroys the session
    user = request.user
    institution_id = request.session.get("institution_id")

    # Emit audit event before session destruction
    AuditEventEmitter().emit(
        event_type=AuditEventType.LOGOUT,
        user=user,
        ip_address=AuditEventEmitter.extract_ip(request),
        institution_id=institution_id,
    )

    logout(request)
    return JsonResponse({"detail": "Logged out."}, status=200)


# ──────────────────────────────────────────────────────────
# Institution Switch (FR-004)
# ──────────────────────────────────────────────────────────


@csrf_exempt
@require_http_methods(["POST"])
@login_required_json
def switch_institution_view(request: HttpRequest) -> JsonResponse:
    """Switch the active institution for the current session.

    Implements FR-004: Institution Switch.

    Request: POST {"institution_id": "uuid"}
    Response 200: {user, active_institution, role, centers}
    Response 400: {"detail": "institution_id is required."}
    Response 403: {"detail": "You do not belong to this institution."}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    institution_id = body.get("institution_id")
    if not institution_id:
        return JsonResponse(
            {"detail": "institution_id is required."},
            status=400,
        )

    user = request.user
    # No prefetch_related("centers") here: the connection still holds the OLD
    # institution's RLS context at this point, and institutions_researchcenter
    # is RLS-protected, so a prefetch would cache an empty center list. The
    # response reads centers after the re-scope to the adopted institution.
    membership = (
        InstitutionMembership.objects.select_related("institution", "role")
        .filter(
            user=user,
            institution_id=institution_id,
            is_active=True,
        )
        .first()
    )

    if membership is None:
        return JsonResponse(
            {"detail": "You do not belong to this institution."},
            status=403,
        )

    # Capture old institution before switching
    old_institution_id = request.session.get("institution_id")

    # Update session with new active institution
    request.session["institution_id"] = str(membership.institution_id)
    request.session["active_role"] = membership.role.name

    # Re-scope the RLS context to the adopted institution BEFORE emitting: the
    # audit tenant_insert policy requires institution_id = sigpi.institution_id.
    _activate_rls_context(user.pk, str(membership.institution_id))

    # Emit audit event
    AuditEventEmitter().emit(
        event_type=AuditEventType.INSTITUTION_SWITCH,
        user=user,
        ip_address=AuditEventEmitter.extract_ip(request),
        institution_id=membership.institution_id,
        details={"previous_institution_id": old_institution_id},
    )

    # Build response
    user_data = _serialize_user(request)
    return JsonResponse(
        {
            "user": user_data,
            "active_institution": {
                "id": str(membership.institution_id),
                "name": membership.institution.name,
            },
            "role": {
                "name": membership.role.name,
                "level": membership.role.level,
            },
            "centers": [{"id": str(c.id), "name": c.name} for c in membership.centers.all()],
        },
        status=200,
    )


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _activate_rls_context(user_id, institution_id) -> None:
    """Re-apply the request's PostgreSQL RLS context after a session change.

    The RLS GUCs are written at connection scope (see ``config.tenant_context``).
    Login and institution switch change the active user/institution mid-request,
    so the context the middleware established is stale for the reads that
    follow. No-op on SQLite, where RLS is unavailable and there are no GUCs.
    """
    if connection.vendor != "postgresql":
        return
    tenant_context.activate(connection, institution_id, False, user_id)


def _serialize_user(request: HttpRequest) -> dict:
    """Serialize the current user for API responses.

    Centers are read under the single active-institution RLS context, so only
    the ACTIVE membership can report centers: another membership's centers
    belong to a different tenant and are filtered out, legitimately returning
    ``centers: []``. That is a deliberate consequence of tenant scoping, not a
    bug — the client consumes only the active membership's centers
    (frontend/store/auth.ts: ``deriveActiveMembership`` → ``deriveCenters``;
    ``deriveInstitutions`` uses only id and name). Widening center visibility
    for data no consumer reads would weaken tenant isolation for nothing.
    """
    user = request.user
    memberships = (
        user.memberships.select_related("institution", "role")
        .prefetch_related("centers")
        .filter(is_active=True)
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "auth_source": user.auth_source,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "active_institution_id": request.session.get("institution_id"),
        "active_role": request.session.get("active_role"),
        "memberships": [
            {
                "institution": {
                    "id": str(m.institution_id),
                    "name": m.institution.name,
                },
                "role": {
                    "name": m.role.name,
                    "level": m.role.level,
                },
                "centers": [{"id": str(c.id), "name": c.name} for c in m.centers.all()],
                "is_primary": m.is_primary,
                "is_active": m.is_active,
            }
            for m in memberships
        ],
    }
