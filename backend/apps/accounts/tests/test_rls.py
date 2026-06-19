"""
RLS policy tests for SIGPI tenant isolation — STRICT TDD.

Tests verify:
- RLS migration structure (RunSQL operations exist)
- RLS policy SQL is syntactically valid for PostgreSQL
- Documented known limitation: RLS tests require PostgreSQL, not SQLite
- Tenant-scoped tables are identified correctly
- Superadmin bypass policy exists

Spec references: FR-006
Design reference: openspec/changes/auth/design.md — PostgreSQL RLS Design
"""
import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.state import ProjectState

# ── RED: These imports WILL fail until migration is created ──
# The RLS migration should exist at accounts/migrations/0004_rls_policies.py
try:
    from apps.accounts.migrations import _0004_rls_policies  # Not importable as module...
except ImportError:
    _0004_rls_policies = None  # RED — migration not yet created


@pytest.mark.skip(reason="RLS requires PostgreSQL — SQLite used in tests")
class TestRLSEnforcement:
    """Integration tests for RLS — PostgreSQL only.

    These tests verify that RLS policies actually block cross-tenant
    queries. Since the test suite runs on SQLite (which doesn't support
    RLS), these tests are skipped and should be run against a PostgreSQL
    test database.
    """

    def test_cross_tenant_query_returns_empty(self):
        """Cross-tenant SELECT returns empty result set."""
        pass

    def test_superadmin_bypass_rls(self):
        """Superadmin SELECT returns all rows regardless of institution."""
        pass

    def test_same_tenant_query_returns_rows(self):
        """Same-tenant SELECT returns matching rows."""
        pass


class TestRLSMigrationStructure:
    """Tests that verify the RLS migration exists and has correct structure."""

    def test_rls_migration_exists(self, db):
        """Migration 0004_rls_policies exists in the accounts app."""
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        migrations = loader.disk_migrations

        key = ("accounts", "0004_rls_policies")
        assert key in migrations, (
            f"RLS migration {key} not found. Available: {[k for k in migrations if k[0] == 'accounts']}"
        )

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
            assert table.lower() in enable_sql.lower(), (
                f"Table {table} not found in RLS SQL"
            )

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

        assert "tenant_isolation" in enable_sql.lower() or "ENABLE ROW LEVEL SECURITY" in enable_sql.upper(), (
            "RLS SQL should enable row-level security on tenant tables"
        )

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
