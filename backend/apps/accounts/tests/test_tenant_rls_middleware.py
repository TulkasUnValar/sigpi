"""
Real-PostgreSQL tests for ``TenantRLSMiddleware`` — STRICT TDD (RED phase).

These tests close the blind spot deliberately left by the connection-mocking
tests in ``test_middleware.py``. They run against a real PostgreSQL connection
assumed as the least-privilege role ``sigpi_app`` (via the ``postgres_app_role``
fixture), so row-level security actually applies, and they assert the observable
effect the mocked tests structurally cannot: a query issued by the view sees the
tenant's rows and nothing else.

The ``postgres_app_role`` fixture skips on SQLite (RLS needs PostgreSQL) and
fails loudly on PostgreSQL when the harness cannot guarantee enforcement, so
these tests can never be green by omission.

Design reference: ``odd/tasks/rls-runtime-enforcement.md`` — acceptance
criteria 1-3.

RED PHASE: against the current code (bare ``SET LOCAL`` with no transaction,
run after ``TenantMiddleware``) every test below must FAIL.
"""

import pytest
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils.module_loading import import_string

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution

RLS_PATH = "config.middleware.tenant.TenantRLSMiddleware"
TENANT_PATH = "config.middleware.tenant.TenantMiddleware"
TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def dummy_get_response(request):
    return HttpResponse("OK")


def _session_request(institution_id):
    """A RequestFactory request carrying ``institution_id`` in its session."""
    request = RequestFactory().get("/api/test/")
    SessionMiddleware(dummy_get_response).process_request(request)
    if institution_id is not None:
        request.session["institution_id"] = str(institution_id)
    return request


def _apply_rls(connection, institution_id, bypass):
    """Write both RLS GUCs at connection scope, exactly like production does.

    ``set_config(..., false)`` is the session-scoped primitive. It is used here
    (rather than in-test ``SET LOCAL``) so the setup can create RLS-protected
    membership rows under bypass and then deny before the middleware runs.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


def _read_guc(connection, name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [name])
        return cursor.fetchone()[0]


def _make_institution(code):
    return Institution.objects.create(name=f"Institution {code}", code=code)


def _make_user(email):
    return User.objects.create_user(email=email, auth_source="local")


class TestTenantRLSMiddlewareRealPostgres:
    """The view's queries must see the tenant's rows under ``sigpi_app``."""

    def _setup_two_tenants(self, connection):
        """Create two isolated tenants with one membership each.

        ``accounts_institutionmembership`` is RLS-protected, so the rows can
        only be inserted under the superadmin bypass. The context is denied
        again before the test body runs, so a middleware that does nothing
        cannot pass any assertion below by accident.
        """
        role = get_role("Investigador")
        inst_a = _make_institution("TRA")
        inst_b = _make_institution("TRB")
        user_a = _make_user("rls-a@example.com")
        user_b = _make_user("rls-b@example.com")

        _apply_rls(connection, None, bypass=True)
        membership_a = InstitutionMembership.objects.create(
            user=user_a, institution=inst_a, role=role, is_active=True
        )
        membership_b = InstitutionMembership.objects.create(
            user=user_b, institution=inst_b, role=role, is_active=True
        )
        _apply_rls(connection, None, bypass=False)

        return inst_a, inst_b, user_a, membership_a, membership_b

    def test_view_query_sees_tenant_rows_only(self, postgres_app_role):
        """A real ORM query inside the chain sees A's rows and not B's."""
        from config.middleware.tenant import TenantRLSMiddleware

        connection = postgres_app_role
        inst_a, _inst_b, user_a, membership_a, membership_b = self._setup_two_tenants(connection)

        observed = {}

        def view(request):
            observed["memberships"] = set(
                InstitutionMembership.objects.values_list("pk", flat=True)
            )
            return HttpResponse("OK")

        request = _session_request(inst_a.pk)
        request.user = user_a

        response = TenantRLSMiddleware(view)(request)

        assert response.status_code == 200
        assert membership_a.pk in observed["memberships"], (
            "The view's query did not see institution A's own membership: the "
            "tenant GUC never reached the connection, so RLS denied A's rows too."
        )
        assert membership_b.pk not in observed["memberships"], (
            "The view's query saw institution B's membership: tenant isolation failed."
        )

    def test_context_is_active_inside_and_cleared_after(self, postgres_app_role):
        """The context is active during the view and cleared after the response."""
        from config.middleware.tenant import TenantRLSMiddleware

        connection = postgres_app_role
        inst_a, _inst_b, user_a, membership_a, _membership_b = self._setup_two_tenants(connection)

        observed = {}

        def view(request):
            observed["memberships"] = set(
                InstitutionMembership.objects.values_list("pk", flat=True)
            )
            return HttpResponse("OK")

        request = _session_request(inst_a.pk)
        request.user = user_a

        TenantRLSMiddleware(view)(request)

        # Non-vacuous precondition: the context really was established first.
        assert membership_a.pk in observed["memberships"], (
            "The tenant context was never active inside the view."
        )

        assert _read_guc(connection, TENANT_GUC) == "", (
            "sigpi.institution_id was not reset after the response."
        )
        assert _read_guc(connection, BYPASS_GUC) == "false", (
            "sigpi.bypass_rls was not reset after the response."
        )

        rows_after = set(InstitutionMembership.objects.values_list("pk", flat=True))
        assert not rows_after, f"Rows were visible after the context was cleared: {rows_after}"

    def test_rls_context_set_before_tenant_middleware_read(self, postgres_app_role):
        """The real chain loads active_membership only if RLS runs first.

        The chain is composed from the order declared in ``settings.MIDDLEWARE``
        so this test pins the ordering fix: with ``TenantRLSMiddleware`` placed
        after ``TenantMiddleware``, ``TenantMiddleware`` reads the RLS-protected
        membership table before the GUC exists and ``active_membership`` is
        ``None``.
        """
        connection = postgres_app_role
        inst_a, _inst_b, user_a, membership_a, _membership_b = self._setup_two_tenants(connection)

        tenant_order = [path for path in settings.MIDDLEWARE if path in (RLS_PATH, TENANT_PATH)]

        response = HttpResponse("OK")

        def view(request):
            return response

        chain = view
        for path in reversed(tenant_order):
            chain = import_string(path)(chain)

        request = _session_request(inst_a.pk)
        request.user = user_a

        result = chain(request)

        assert result is response
        assert request.active_membership is not None, (
            "active_membership is None: TenantRLSMiddleware did not establish the "
            "tenant context before TenantMiddleware's RLS-protected membership read."
        )
        assert request.active_membership.pk == membership_a.pk

    @pytest.mark.django_db(transaction=True)
    def test_context_reapplied_on_new_connection(self, postgres_app_role):
        """A connection opened mid-request also receives the GUCs.

        ``transaction=True`` is required so ``connection.close()`` can be called
        without tearing down the per-test wrapping transaction. The test harness
        logs in as the superuser and assumes ``sigpi_app`` with ``SET ROLE``;
        that role is session state lost when the connection drops, so the view
        re-assumes it after reconnecting. Production logs in as the app role
        directly, so only the GUC — the middleware's concern — needs
        re-application here.
        """
        from config.middleware.tenant import TenantRLSMiddleware

        connection = postgres_app_role
        inst_a, _inst_b, user_a, membership_a, membership_b = self._setup_two_tenants(connection)

        observed = {}

        def view(request):
            connection.close()
            with connection.cursor() as cursor:
                cursor.execute('SET ROLE "sigpi_app"')
            observed["guc"] = _read_guc(connection, TENANT_GUC)
            observed["memberships"] = set(
                InstitutionMembership.objects.values_list("pk", flat=True)
            )
            return HttpResponse("OK")

        request = _session_request(inst_a.pk)
        request.user = user_a

        TenantRLSMiddleware(view)(request)

        assert observed["guc"] == str(inst_a.pk), (
            "The tenant GUC was not re-applied to the connection opened mid-request."
        )
        assert membership_a.pk in observed["memberships"], (
            "The reconnected session did not see institution A's membership."
        )
        assert membership_b.pk not in observed["memberships"], (
            "The reconnected session saw institution B's membership."
        )
