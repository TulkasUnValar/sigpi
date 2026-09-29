"""
Pytest configuration for SIGPI backend.

Sets PYTEST_RUNNING=true so settings use in-memory SQLite.
"""

import os

# Must be set at module level BEFORE Django settings are imported.
# pytest_configure() hook runs too late — settings already loaded.
os.environ["PYTEST_RUNNING"] = "true"

import logging

import pytest

logger = logging.getLogger(__name__)

# Name of the least-privilege role created by
# apps/accounts/migrations/0010_least_privilege_app_role.py.
APP_ROLE = "sigpi_app"


def pytest_configure():
    """Ensure PYTEST_RUNNING is set (belt-and-suspenders)."""
    os.environ["PYTEST_RUNNING"] = "true"


@pytest.fixture(autouse=True)
def _media_root(settings, tmpdir):
    """Ensure MEDIA_ROOT points to a temp directory during tests."""
    settings.MEDIA_ROOT = str(tmpdir.mkdir("media"))


@pytest.fixture
def postgres_app_role(db):
    """Run a test as a non-owner, non-BYPASSRLS role so RLS actually applies.

    Row-level security is enforced against the connected role: the default
    test connection is the PostgreSQL superuser (`sigpi`), which carries
    `BYPASSRLS` and skips every policy unconditionally. This fixture assumes
    the `sigpi_app` role with `SET ROLE`, so the enforcement suites exercise
    real RLS behaviour.

    On SQLite (the default local engine) the test is skipped, because SQLite
    has no row-level security. On PostgreSQL the fixture fails loudly — never
    skips — when the harness cannot guarantee enforcement, so CI cannot be
    green by omission.

    `SET ROLE` is session state that the test transaction's rollback does not
    undo, so the role is reset in a `finally` block to keep it from leaking
    into later tests.
    """
    from django.db import DatabaseError, connection

    if connection.vendor != "postgresql":
        pytest.skip("RLS enforcement requires PostgreSQL")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s",
            [APP_ROLE],
        )
        role_row = cursor.fetchone()

    if role_row is None:
        pytest.fail(
            f"PostgreSQL role '{APP_ROLE}' does not exist, so RLS enforcement "
            f"cannot run. Apply the migration that creates it: "
            f"'python manage.py migrate accounts' "
            f"(apps/accounts/migrations/0010_least_privilege_app_role.py)."
        )

    is_superuser, bypass_rls = role_row
    if is_superuser:
        pytest.fail(
            f"PostgreSQL role '{APP_ROLE}' is a superuser (rolsuper = true). "
            f"Superusers bypass RLS unconditionally, so the enforcement tests "
            f"would prove nothing. Fix the role definition: it must be created "
            f"NOSUPERUSER (see migration 0010_least_privilege_app_role)."
        )
    if bypass_rls:
        pytest.fail(
            f"PostgreSQL role '{APP_ROLE}' has BYPASSRLS (rolbypassrls = true). "
            f"A BYPASSRLS role skips RLS unconditionally, so the enforcement "
            f"tests would prove nothing. Fix the role definition: it must be "
            f"created NOBYPASSRLS (see migration 0010_least_privilege_app_role)."
        )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relrowsecurity = true
              AND n.nspname = 'public'
              AND pg_get_userbyid(c.relowner) = %s
            ORDER BY c.relname
            """,
            [APP_ROLE],
        )
        owned_rls_tables = [row[0] for row in cursor.fetchall()]

    if owned_rls_tables:
        pytest.fail(
            f"PostgreSQL role '{APP_ROLE}' owns RLS-protected table(s) "
            f"{owned_rls_tables}. A table owner bypasses its own RLS policies, "
            f"so the enforcement tests would prove nothing. The role must not "
            f"own any RLS table; tables must be owned by the migration user "
            f"(for example 'sigpi')."
        )

    try:
        with connection.cursor() as cursor:
            cursor.execute(f'SET ROLE "{APP_ROLE}"')
        yield connection
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")
        except DatabaseError:
            # A test that died mid-transaction leaves the connection aborted,
            # and an aborted transaction cannot execute RESET ROLE. Nothing
            # leaks: SET ROLE is transactional in PostgreSQL, so the rollback
            # that produced the abort already reverted the role. Log it so the
            # condition stays diagnosable instead of failing the teardown.
            logger.warning(
                "Could not RESET ROLE in teardown; the aborted test transaction "
                "already reverted the role."
            )
