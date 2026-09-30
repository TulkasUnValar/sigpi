"""
RLS policy tests for SIGPI tenant isolation — STRICT TDD.

Two groups of tests live here:

- The enforcement tests run on a real PostgreSQL connection assumed as the
  least-privilege ``sigpi_app`` role (via the ``postgres_app_role`` fixture),
  so row-level security genuinely applies. They prove the membership self-read
  policy is load-bearing: under ``sigpi_app`` a locally authenticated user can
  read their OWN membership rows, which is what lets login establish the
  primary institution and lets a session switch to another institution the
  user belongs to.
- The migration-structure tests assert the shape of the RLS migrations without
  needing PostgreSQL; they run on the default SQLite engine.

Spec references: FR-006, FR-004
Design reference: openspec/changes/auth/design.md — PostgreSQL RLS Design
"""

import uuid as uuid_module

from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.accounts.audit import AuditEventEmitter, AuditEventType
from apps.accounts.backends import SIGPIOIDCBackend
from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution, ResearchCenter
from config import tenant_context

TENANT_GUC = "sigpi.institution_id"
USER_GUC = "sigpi.user_id"
BYPASS_GUC = "sigpi.bypass_rls"


def _set_rls(conn, institution_id, bypass, user_id=None):
    """Write the three RLS GUCs at connection scope, exactly like production does.

    ``user_id`` is part of the write so a test can seed protected rows under
    bypass and then deny the connection with no stale value left behind: a
    connection-scoped value outlives the statement that set it.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [USER_GUC, "" if user_id is None else str(user_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


def _make_institution(code):
    return Institution.objects.create(name=f"Institution {code}", code=code)


def _make_user(email, password="testpass123"):
    return User.objects.create_user(email=email, auth_source="local", password=password)


def _make_membership(user, institution, role, *, is_primary=False):
    return InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=role,
        is_primary=is_primary,
        is_active=True,
    )


class TestMembershipSelfReadUnderAppRole:
    """A signed-in user may read their own memberships under ``sigpi_app``."""

    def test_local_login_sets_primary_institution_and_memberships(self, postgres_app_role):
        """Login as ``sigpi_app`` adopts the primary institution and lists memberships.

        Without the ``sigpi.user_id`` GUC and the ``own_memberships`` policy the
        primary-membership read is denied, so the session ends with no active
        institution and an empty ``memberships`` list even though the request
        is a 200.
        """
        conn = postgres_app_role
        role = get_role("Investigador")
        institution = _make_institution("RSR1")
        user = _make_user("rls-selfread-login@test.edu")

        _set_rls(conn, None, bypass=True)
        _make_membership(user, institution, role, is_primary=True)
        _set_rls(conn, None, bypass=False)

        client = Client()
        response = client.post(
            reverse("local_login"),
            data={"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )

        assert response.status_code == 200
        payload = response.json()["user"]
        assert payload["active_institution_id"] == str(institution.pk), (
            "Login did not adopt the primary institution: its RLS-protected "
            "membership row was invisible to the app role."
        )
        assert payload["memberships"], (
            "Login returned an empty memberships list: the app role could not "
            "read the user's own membership rows."
        )
        assert payload["memberships"][0]["institution"]["id"] == str(institution.pk)

    def test_switch_institution_adopts_the_target(self, postgres_app_role):
        """A→B switch returns 200, adopts B, and lists B's centers.

        The target membership row can only be found through the self-read
        policy: the tenant-only policy scopes to the currently active
        institution A, so B stays invisible without it.

        ``institutions_researchcenter`` is RLS-protected too, so the response's
        ``centers`` is only populated when it is read after the connection has
        been re-scoped to B: a prefetch issued under the old institution A
        caches an empty center list.
        """
        conn = postgres_app_role
        role = get_role("Investigador")
        institution_a = _make_institution("RSR2A")
        institution_b = _make_institution("RSR2B")
        user = _make_user("rls-selfread-switch@test.edu")

        _set_rls(conn, None, bypass=True)
        _make_membership(user, institution_a, role, is_primary=True)
        membership_b = _make_membership(user, institution_b, role)
        center = ResearchCenter.objects.create(
            institution=institution_b, code="RSR2BC", name="Adopted Center"
        )
        membership_b.centers.add(center)
        _set_rls(conn, None, bypass=False)

        client = Client()
        client.login(username=user.email, password="testpass123")
        session = client.session
        session["institution_id"] = str(institution_a.pk)
        session.save()

        response = client.post(
            reverse("switch_institution"),
            data={"institution_id": str(institution_b.pk)},
            content_type="application/json",
        )

        assert response.status_code == 200, response.content
        me = client.get(reverse("auth_me"))
        assert me.json()["active_institution_id"] == str(institution_b.pk)
        centers = response.json()["centers"]
        assert any(c["id"] == str(center.pk) for c in centers), (
            "The switch response did not list the adopted institution's center: "
            f"got {centers!r}. The lookup read centers before the connection was "
            "re-scoped from the old institution to the adopted one."
        )

    def test_user_guc_exposes_only_the_users_own_rows(self, postgres_app_role):
        """With user X's GUC set, X's rows are visible and Y's are not."""
        conn = postgres_app_role
        role = get_role("Investigador")
        institution = _make_institution("RSR3")
        user_x = _make_user("rls-selfread-x@test.edu")
        user_y = _make_user("rls-selfread-y@test.edu")

        _set_rls(conn, None, bypass=True)
        membership_x = _make_membership(user_x, institution, role)
        membership_y = _make_membership(user_y, institution, role)
        _set_rls(conn, None, bypass=False, user_id=user_x.pk)

        visible = set(InstitutionMembership.objects.values_list("pk", flat=True))

        assert membership_x.pk in visible, (
            "The user's own membership row was not visible with their user GUC set."
        )
        assert membership_y.pk not in visible, (
            "Another user's membership row was visible: the self-read policy "
            "widens access beyond the row owner."
        )

    def test_empty_user_guc_hides_the_users_own_rows(self, postgres_app_role):
        """Non-vacuity control: with no user GUC, the user's own rows are denied.

        If X's row were visible here, the positive assertion in the previous
        test would prove nothing about the policy.
        """
        conn = postgres_app_role
        role = get_role("Investigador")
        institution = _make_institution("RSR4")
        user_x = _make_user("rls-selfread-vac@test.edu")

        _set_rls(conn, None, bypass=True)
        membership_x = _make_membership(user_x, institution, role)
        _set_rls(conn, None, bypass=False)

        visible = set(InstitutionMembership.objects.values_list("pk", flat=True))

        assert membership_x.pk not in visible, (
            "The membership row was visible with an empty sigpi.user_id: the "
            "policy is not load-bearing."
        )


class TestOIDCMembershipSyncUnderAppRole:
    """The OIDC callback syncs membership under ``sigpi_app``.

    The ``mozilla_django_oidc`` callback runs while the request is still
    anonymous at middleware time, so the connection carries an empty context
    (``sigpi.institution_id = ''``, ``sigpi.user_id = ''``, ``bypass = false``).
    The membership write only succeeds once ``_sync_membership`` re-establishes
    a tenant context from the institution it resolved from the claims.
    """

    def test_create_user_creates_membership_under_app_role(self, postgres_app_role):
        """create_user with a ``sigpi_institution_id`` claim persists the membership.

        Without the tenant context the membership INSERT violates
        ``tenant_isolation`` (``institution_id = NULL``) and the primary
        Keycloak login path fails with an RLS policy violation.
        """
        conn = postgres_app_role
        institution = _make_institution("RSR5")

        # Simulate the anonymous callback: both GUCs are empty, no bypass.
        _set_rls(conn, None, bypass=False)

        backend = SIGPIOIDCBackend()
        claims = {
            "sub": str(uuid_module.uuid4()),
            "email": "rls-oidc-create@test.edu",
            "email_verified": True,
            "sigpi_institution_id": str(institution.pk),
            "sigpi_role": "researcher",
        }

        user = backend.create_user(claims)

        # Read the row back through the legitimate self-read scope.
        _set_rls(conn, institution.pk, bypass=False, user_id=user.pk)
        membership = InstitutionMembership.objects.filter(
            user=user, institution=institution
        ).first()

        assert membership is not None, (
            "create_user did not persist the InstitutionMembership: the OIDC "
            "callback's empty RLS context denied the membership write."
        )
        assert membership.is_primary is True
        assert membership.role.name == "Investigador"

    def test_update_user_updates_membership_under_app_role(self, postgres_app_role):
        """update_user re-syncs an existing membership without an RLS violation.

        The existing row must be found through the tenant context so the role
        update runs; without it the denied SELECT falls through to a blind
        INSERT that fails on the existing row.
        """
        conn = postgres_app_role
        role = get_role("Investigador")
        institution = _make_institution("RSR6")
        user = _make_user("rls-oidc-update@test.edu")

        _set_rls(conn, None, bypass=True)
        _make_membership(user, institution, role, is_primary=True)
        _set_rls(conn, None, bypass=False)

        backend = SIGPIOIDCBackend()
        claims = {
            "sub": str(uuid_module.uuid4()),
            "email": user.email,
            "sigpi_institution_id": str(institution.pk),
            "sigpi_role": "center_director",
        }

        backend.update_user(user, claims)

        _set_rls(conn, institution.pk, bypass=False, user_id=user.pk)
        membership = InstitutionMembership.objects.get(user=user, institution=institution)
        assert membership.role.name == "Director de Centro", (
            "update_user did not re-sync the membership role: the tenant context "
            "was missing, so the existing row was never found."
        )


class TestNestedTenantContext:
    """A nested context restores the enclosing one instead of clobbering it."""

    def test_nested_context_restores_the_enclosing_tenant(self, postgres_app_role):
        """Exiting a nested context leaves the outer tenant scope intact.

        The OIDC membership sync enters a nested ``tenant_context`` inside an
        authenticated request. Before the context manager was reentrant, its
        ``clear`` in ``finally`` dropped the request's own context, so the
        login audit event that follows ran without a GUC and was denied.
        """
        conn = postgres_app_role
        role = get_role("Investigador")
        institution = _make_institution("NST1")
        other = _make_institution("NST2")
        user = _make_user("rls-nested@test.edu")

        _set_rls(conn, None, bypass=True)
        _make_membership(user, institution, role, is_primary=True)
        _set_rls(conn, None, bypass=False)

        # The middleware establishes the request context for the active tenant.
        tenant_context.activate(conn, institution.pk, False, user.pk)
        try:
            with tenant_context.tenant_context(conn, other.pk, False, user.pk):
                assert tenant_context.get_context() == (other.pk, user.pk, False)

            # Non-vacuity: the enclosing scope is back, so a write scoped to the
            # request's own institution is authorized again.
            assert tenant_context.get_context() == (institution.pk, user.pk, False)
            event = AuditEventEmitter().emit(
                event_type=AuditEventType.LOGIN,
                user=user,
                institution_id=institution.pk,
            )
            assert event.pk is not None
        finally:
            tenant_context.clear(conn)


class TestRLSMigrationStructure:
    """Tests that verify the RLS migration exists and has correct structure."""

    def test_rls_migration_exists(self, db):
        """Migration 0004_rls_policies exists in the accounts app."""
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        migrations = loader.disk_migrations

        key = ("accounts", "0004_rls_policies")
        available = [k for k in migrations if k[0] == "accounts"]
        assert key in migrations, f"RLS migration {key} not found. Available: {available}"

    def test_rls_migration_has_operations(self, db):
        """RLS migration has RunPython operations (SQLite-safe)."""
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        migration = loader.disk_migrations[("accounts", "0004_rls_policies")]

        assert len(migration.operations) > 0, "RLS migration should have operations"
        # At least one operation should be RunPython (which conditionally runs SQL)
        from django.db.migrations import RunPython

        has_runpython = any(isinstance(op, RunPython) for op in migration.operations)
        assert has_runpython, "RLS migration should contain RunPython operations"

    def test_rls_migration_depends_on_initial(self, db):
        """RLS migration depends on the initial accounts migration."""
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        migration = loader.disk_migrations[("accounts", "0004_rls_policies")]

        deps = [(d[0], d[1]) for d in migration.dependencies]
        assert ("accounts", "0003_audit_event") in deps, (
            f"RLS migration should depend on audit_event migration. Got: {deps}"
        )

    def test_rls_sql_contains_expected_tables(self):
        """RLS SQL references tenant-scoped tables from the design."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "0004_rls_policies.py"
        )
        spec = importlib.util.spec_from_file_location(
            "rls_migration", os.path.abspath(migration_path)
        )
        rls_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rls_module)

        enable_sql = rls_module.ENABLE_RLS_SQL

        tenant_tables = [
            "institutions_researchcenter",
            "accounts_institutionmembership",
        ]

        for table in tenant_tables:
            assert table.lower() in enable_sql.lower(), f"Table {table} not found in RLS SQL"

    def test_rls_sql_has_tenant_isolation_policy(self):
        """RLS SQL includes the tenant_isolation policy pattern."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "0004_rls_policies.py"
        )
        spec = importlib.util.spec_from_file_location(
            "rls_migration", os.path.abspath(migration_path)
        )
        rls_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rls_module)

        enable_sql = rls_module.ENABLE_RLS_SQL

        assert (
            "tenant_isolation" in enable_sql.lower()
            or "ENABLE ROW LEVEL SECURITY" in enable_sql.upper()
        ), "RLS SQL should enable row-level security on tenant tables"

    def test_rls_sql_has_superadmin_bypass_policy(self):
        """RLS SQL includes the superadmin_bypass policy."""
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__), "..", "migrations", "0004_rls_policies.py"
        )
        spec = importlib.util.spec_from_file_location(
            "rls_migration", os.path.abspath(migration_path)
        )
        rls_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rls_module)

        enable_sql = rls_module.ENABLE_RLS_SQL

        assert "superadmin_bypass" in enable_sql.lower() or "bypass_rls" in enable_sql.lower(), (
            "RLS SQL should include superadmin bypass policy"
        )


class TestRLSPostgreSQLOnlyNote:
    """Documentation: RLS tests require PostgreSQL."""

    def test_rls_is_postgresql_only(self):
        """This test documents that RLS enforcement requires PostgreSQL.

        RLS (Row-Level Security) is a PostgreSQL feature. SQLite does not
        support RLS policies. The TenantRLSMiddleware gracefully handles
        this by wrapping cursor operations in try/except blocks.

        To run actual RLS tests:
        1. Set up a PostgreSQL test database
        2. Run: PYTEST_RUNNING=false pytest apps/accounts/tests/test_rls.py
        3. Ensure the migration 0004_rls_policies has been applied
        """
        assert True  # Documentation marker
