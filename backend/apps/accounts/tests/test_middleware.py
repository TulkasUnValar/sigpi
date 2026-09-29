"""
Middleware tests for SIGPI TenantMiddleware and TenantRLSMiddleware — STRICT TDD.

Tests define the expected behavior of:
- TenantMiddleware: inject institution_id, load active_membership, enforce tenant requirement
- TenantRLSMiddleware: set PostgreSQL RLS context per request

Spec references: FR-004, FR-006
Design reference: openspec/changes/auth/design.md — TenantMiddleware, PostgreSQL RLS Design
"""

import uuid
from unittest import mock
from unittest.mock import MagicMock

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution
from config import tenant_context
from config.tenant_context import BYPASS_GUC, TENANT_GUC

# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(name="Otra Universidad", code="OTRA")


@pytest.fixture
def researcher_role(db):
    return get_role("Investigador")


@pytest.fixture
def user_with_membership(db, institution, researcher_role) -> User:
    """User with an active membership in 'Universidad Test'."""
    user = User.objects.create_user(
        email="member@example.com",
        auth_source="local",
        password="testpass123",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=researcher_role,
        is_active=True,
    )
    return user


@pytest.fixture
def user_without_membership(db) -> User:
    """User with no institution memberships."""
    return User.objects.create_user(
        email="nomembership@example.com",
        auth_source="local",
        password="testpass123",
    )


@pytest.fixture
def user_multi_institution(db, institution, other_institution, researcher_role) -> User:
    """User with memberships in two institutions."""
    user = User.objects.create_user(
        email="multi@example.com",
        auth_source="local",
        password="testpass123",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=researcher_role,
        is_active=True,
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=other_institution,
        role=researcher_role,
        is_active=True,
    )
    return user


# ──────────────────────────────────────────────────────────
# TenantMiddleware Tests
# ──────────────────────────────────────────────────────────


# Dummy get_response for middleware testing
def dummy_get_response(request):
    return HttpResponse("OK")


class TestTenantMiddleware:
    """TenantMiddleware: injects institution_id and active_membership."""

    def _build_middleware_request(self, factory, user=None, session_data=None):
        """Build a request through Session+Auth middleware, ready for TenantMiddleware."""
        request = factory.get("/api/test/")
        # Session middleware sets up the session engine
        SessionMiddleware(dummy_get_response).process_request(request)
        if session_data:
            request.session.update(session_data)
        if user is not None:
            request.user = user
        return request

    def test_injects_institution_id_from_session(self, db, institution, user_with_membership):
        """Session's institution_id is injected into request.institution_id."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={"institution_id": str(institution.id)},
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.institution_id == str(institution.id)

    def test_institution_id_none_when_not_in_session(self, db, user_with_membership):
        """request.institution_id is None when no institution_id in session."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={},  # no institution_id
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.institution_id is None

    def test_loads_active_membership(self, db, institution, user_with_membership, researcher_role):
        """Active membership is loaded from DB when institution_id matches."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={"institution_id": str(institution.id)},
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.active_membership is not None
        assert request.active_membership.user == user_with_membership
        assert request.active_membership.institution == institution

    def test_active_membership_selects_related_role(
        self, db, institution, user_with_membership, researcher_role
    ):
        """Active membership includes the role via select_related."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={"institution_id": str(institution.id)},
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.active_membership.role == researcher_role
        assert request.active_membership.role.name == "Investigador"

    def test_active_membership_none_for_wrong_institution(
        self, db, institution, user_with_membership
    ):
        """active_membership is None when institution_id doesn't match a membership."""
        from config.middleware.tenant import TenantMiddleware

        fake_id = str(uuid.uuid4())
        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={"institution_id": fake_id},
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.active_membership is None

    def test_active_membership_none_for_inactive_membership(self, db, institution, researcher_role):
        """active_membership is None when membership is not active."""
        from config.middleware.tenant import TenantMiddleware

        user = User.objects.create_user(
            email="inactive@example.com", auth_source="local", password="pass123"
        )
        InstitutionMembership.objects.create(
            user=user,
            institution=institution,
            role=researcher_role,
            is_active=False,
        )

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user,
            session_data={"institution_id": str(institution.id)},
        )

        middleware = TenantMiddleware(dummy_get_response)
        middleware(request)

        assert request.active_membership is None

    def test_middleware_passes_through_to_view(self, db, user_with_membership, institution):
        """Middleware calls get_response and returns its result."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={"institution_id": str(institution.id)},
        )

        response = HttpResponse("View Response")
        middleware = TenantMiddleware(lambda r: response)
        result = middleware(request)

        assert result.status_code == 200
        assert result.content == b"View Response"

    def test_returns_400_when_tenant_required_but_no_institution(self, db, user_with_membership):
        """Tenant-required endpoint with no institution returns 400."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        # Use a path that requires tenant
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={},  # no institution_id
        )
        # Override path to a tenant-required prefix
        request.path = "/api/projects/"

        middleware = TenantMiddleware(dummy_get_response)
        response = middleware(request)

        assert response.status_code == 400
        assert "institution" in response.content.decode().lower()

    def test_anonymous_user_bypasses_tenant_check(self, db):
        """Anonymous users don't trigger the 400 tenant check."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(factory, user=None, session_data={})
        request.user = MagicMock()
        request.user.is_authenticated = False
        request.path = "/api/projects/"

        middleware = TenantMiddleware(dummy_get_response)
        response = middleware(request)

        assert response.status_code == 200  # Passes through

    def test_public_endpoint_bypasses_tenant_check(self, db, user_with_membership):
        """Non-tenant endpoints don't require institution_id."""
        from config.middleware.tenant import TenantMiddleware

        factory = RequestFactory()
        request = self._build_middleware_request(
            factory,
            user=user_with_membership,
            session_data={},  # no institution_id
        )
        request.path = "/auth/me/"  # public/auth endpoint — not tenant-scoped

        middleware = TenantMiddleware(dummy_get_response)
        response = middleware(request)

        assert response.status_code == 200


# ──────────────────────────────────────────────────────────
# TenantRLSMiddleware Tests
# ──────────────────────────────────────────────────────────


class TestTenantRLSMiddleware:
    """TenantRLSMiddleware: sets PostgreSQL RLS session context."""

    def _build_request(self, factory, user=None, institution_id=None):
        request = factory.get("/api/test/")
        SessionMiddleware(dummy_get_response).process_request(request)
        if institution_id:
            request.session["institution_id"] = institution_id
        request.institution_id = institution_id
        if user is not None:
            request.user = user
        return request

    def _capturing_view(self, captured):
        """A view that records the GUC values present while it runs.

        The GUCs only exist on PostgreSQL, so on SQLite the view records the
        call and asserts the documented no-op instead.
        """

        def view(request):
            captured["called"] = True
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_setting(%s, true)", [TENANT_GUC])
                    captured["institution_id"] = cursor.fetchone()[0]
                    cursor.execute("SELECT current_setting(%s, true)", [BYPASS_GUC])
                    captured["bypass"] = cursor.fetchone()[0]
            return HttpResponse("OK")

        return view

    def test_institution_present_reaches_the_connection(
        self, db, institution, user_with_membership
    ):
        """When an institution is in the session, its GUC reaches the connection.

        PostgreSQL-only effect: on SQLite the middleware is a documented no-op.
        """
        from config.middleware.tenant import TenantRLSMiddleware

        captured = {}
        request = self._build_request(
            RequestFactory(),
            user=user_with_membership,
            institution_id=str(institution.id),
        )

        result = TenantRLSMiddleware(self._capturing_view(captured))(request)

        assert result.status_code == 200
        assert captured["called"] is True
        if connection.vendor == "postgresql":
            assert captured["institution_id"] == str(institution.id)
            assert captured["bypass"] == "false"
        else:
            assert tenant_context.get_context() is None

    def test_institution_absent_writes_the_deny_context(self, db, user_with_membership):
        """Without an institution the GUC is written empty, never left stale.

        PostgreSQL-only effect: on SQLite the middleware is a documented no-op.
        """
        from config.middleware.tenant import TenantRLSMiddleware

        captured = {}
        request = self._build_request(
            RequestFactory(),
            user=user_with_membership,
            institution_id=None,
        )

        TenantRLSMiddleware(self._capturing_view(captured))(request)

        assert captured["called"] is True
        if connection.vendor == "postgresql":
            assert captured["institution_id"] == ""
            assert captured["bypass"] == "false"
        else:
            assert tenant_context.get_context() is None

    def test_superuser_gets_bypass(self, db, institution):
        """An authenticated superuser gets bypass_rls = 'true' on the connection.

        PostgreSQL-only effect: on SQLite the middleware is a documented no-op.
        """
        from config.middleware.tenant import TenantRLSMiddleware

        user = User.objects.create_superuser(email="super@example.com", password="superpass123")

        captured = {}
        request = self._build_request(
            RequestFactory(),
            user=user,
            institution_id=str(institution.id),
        )

        TenantRLSMiddleware(self._capturing_view(captured))(request)

        if connection.vendor == "postgresql":
            assert captured["institution_id"] == str(institution.id)
            assert captured["bypass"] == "true"
        else:
            assert tenant_context.get_context() is None

    def test_non_superuser_has_no_bypass(self, db, institution, user_with_membership):
        """A non-superuser never gets bypass_rls.

        PostgreSQL-only effect: on SQLite the middleware is a documented no-op.
        """
        from config.middleware.tenant import TenantRLSMiddleware

        captured = {}
        request = self._build_request(
            RequestFactory(),
            user=user_with_membership,
            institution_id=str(institution.id),
        )

        TenantRLSMiddleware(self._capturing_view(captured))(request)

        if connection.vendor == "postgresql":
            assert captured["bypass"] == "false"
        else:
            assert tenant_context.get_context() is None

    def test_passes_through_to_view(self, db, institution, user_with_membership):
        """The middleware calls get_response, returns its result and clears up."""
        from config.middleware.tenant import TenantRLSMiddleware

        request = self._build_request(
            RequestFactory(),
            user=user_with_membership,
            institution_id=str(institution.id),
        )

        response = HttpResponse("After RLS")
        result = TenantRLSMiddleware(lambda r: response)(request)

        assert result.status_code == 200
        assert result.content == b"After RLS"
        assert tenant_context.get_context() is None

    def test_activation_failure_is_not_served(self, db, institution, user_with_membership):
        """An activation failure rejects the request instead of serving it.

        ``vendor`` is forced to ``postgresql`` so the middleware reaches the
        activation path on SQLite too; ``activate`` is patched to raise. The
        view must never run, and the exception must propagate so Django's
        error handling responds and records the traceback (fail closed).
        """
        from config.middleware.tenant import TenantRLSMiddleware

        served = []
        request = self._build_request(
            RequestFactory(),
            user=user_with_membership,
            institution_id=str(institution.id),
        )

        def view(request):
            served.append(True)
            return HttpResponse("OK")

        with (
            mock.patch.object(connection, "vendor", "postgresql"),
            mock.patch.object(
                tenant_context,
                "activate",
                side_effect=RuntimeError("tenant context down"),
            ),
        ):
            with pytest.raises(RuntimeError, match="tenant context down"):
                TenantRLSMiddleware(view)(request)

        assert served == [], "The request was served despite a failed tenant context."
