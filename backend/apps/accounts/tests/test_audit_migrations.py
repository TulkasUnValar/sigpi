"""
Audit traceability migration tests — STRICT TDD.

Tests verify the PR 1 migrations (0008_audit_traceability, 0009_audit_rls):
- New traceability fields exist on the AuditEvent model
- Composite indexes are declared on the model
- Migration 0008 contains AddField/AlterField/AddIndex operations
- Migration 0009 (PostgreSQL-only) contains the RLS policy SQL
- Both migrations are reversible

Design reference: openspec/changes/audit/design.md
Spec reference: openspec/changes/audit/specs/audit/spec.md (RA-1, RA-2)
"""

import importlib.util
import os

import pytest
from django.db import connection, models

from apps.accounts.audit import AuditEvent, AuditEventType

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


def _load_migration_module(name):
    """Load a migration module from disk by filename (without .py)."""
    path = os.path.join(MIGRATIONS_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ──────────────────────────────────────────────────────────
# Model field presence
# ──────────────────────────────────────────────────────────


class TestAuditEventTraceabilityFields:
    """New traceability fields exist on the AuditEvent model."""

    @pytest.fixture(autouse=True)
    def _ensure_fields(self):
        # Force field introspection to pick up the migrated schema.
        AuditEvent._meta.get_fields()

    def test_entity_type_field_exists(self):
        field = AuditEvent._meta.get_field("entity_type")
        assert isinstance(field, models.CharField)
        assert field.max_length == 50
        assert field.null is True
        assert field.blank is True
        assert field.db_index is True

    def test_entity_id_field_exists(self):
        field = AuditEvent._meta.get_field("entity_id")
        assert isinstance(field, models.UUIDField)
        assert field.null is True
        assert field.blank is True
        assert field.db_index is True

    def test_action_field_exists(self):
        field = AuditEvent._meta.get_field("action")
        assert isinstance(field, models.CharField)
        assert field.max_length == 20
        assert field.null is True
        assert field.blank is True
        assert field.db_index is True

    def test_old_values_field_exists(self):
        field = AuditEvent._meta.get_field("old_values")
        assert isinstance(field, models.JSONField)
        assert field.null is True
        assert field.blank is True
        assert field.default is dict

    def test_new_values_field_exists(self):
        field = AuditEvent._meta.get_field("new_values")
        assert isinstance(field, models.JSONField)
        assert field.null is True
        assert field.blank is True
        assert field.default is dict

    def test_project_id_field_exists(self):
        field = AuditEvent._meta.get_field("project_id")
        assert isinstance(field, models.UUIDField)
        assert field.null is True
        assert field.blank is True
        assert field.db_index is True


# ──────────────────────────────────────────────────────────
# Model indexes
# ──────────────────────────────────────────────────────────


class TestAuditEventIndexes:
    """Composite indexes are declared on the model."""

    def _index_fields(self):
        return {tuple(i.fields) for i in AuditEvent._meta.indexes}

    def test_entity_type_entity_id_index(self):
        assert ("entity_type", "entity_id") in self._index_fields()

    def test_project_id_timestamp_index(self):
        assert ("project_id", "-timestamp") in self._index_fields()

    def test_action_timestamp_index(self):
        assert ("action", "-timestamp") in self._index_fields()


# ──────────────────────────────────────────────────────────
# AuditEventType choices
# ──────────────────────────────────────────────────────────


class TestAuditEventTypeChoices:
    """New generic event types are registered."""

    @pytest.mark.parametrize(
        "value",
        ["CREATE", "UPDATE", "DELETE", "STATE_CHANGE", "DOCUMENT_DOWNLOADED"],
    )
    def test_new_event_type_registered(self, value):
        assert value in {v for v, _l in AuditEventType.choices}

    def test_generic_event_types_preserved(self):
        """The generic CRUD event types remain registered (RA-1)."""
        values = {v for v, _l in AuditEventType.choices}
        for value in ("CREATE", "UPDATE", "DELETE", "STATE_CHANGE", "DOCUMENT_DOWNLOADED"):
            assert value in values


# ──────────────────────────────────────────────────────────
# Migration 0008 structure
# ──────────────────────────────────────────────────────────


class TestMigration0008Structure:
    """Migration 0008 adds fields, updates choices, adds indexes."""

    def test_migration_exists_on_disk(self):
        assert os.path.exists(os.path.join(MIGRATIONS_DIR, "0008_audit_traceability.py"))

    def test_addfield_operations_present(self):
        from django.db.migrations import AddField

        module = _load_migration_module("0008_audit_traceability")
        addfields = [op for op in module.Migration.operations if isinstance(op, AddField)]
        names = {op.name for op in addfields}
        assert {
            "entity_type",
            "entity_id",
            "action",
            "old_values",
            "new_values",
            "project_id",
        } <= names

    def test_alterfield_event_type_present(self):
        module = _load_migration_module("0008_audit_traceability")
        from django.db.migrations import AlterField

        alters = [op for op in module.Migration.operations if isinstance(op, AlterField)]
        assert any(op.name == "event_type" for op in alters)

    def test_addindex_operations_present(self):
        module = _load_migration_module("0008_audit_traceability")
        from django.db.migrations import AddIndex

        addindexes = [op for op in module.Migration.operations if isinstance(op, AddIndex)]
        assert len(addindexes) >= 3


# ──────────────────────────────────────────────────────────
# Migration 0009 RLS structure (PostgreSQL-only)
# ──────────────────────────────────────────────────────────


class TestMigration0009RLSStructure:
    """Migration 0009 adds RLS policies on accounts_auditevent."""

    def test_migration_exists_on_disk(self):
        assert os.path.exists(os.path.join(MIGRATIONS_DIR, "0009_audit_rls.py"))

    def test_rls_sql_contains_enable_row_level_security(self):
        module = _load_migration_module("0009_audit_rls")
        sql = module.ENABLE_RLS_SQL.upper()
        assert "ENABLE ROW LEVEL SECURITY" in sql

    def test_rls_sql_contains_tenant_isolation_policy(self):
        module = _load_migration_module("0009_audit_rls")
        sql = module.ENABLE_RLS_SQL
        assert "tenant_isolation" in sql
        assert "accounts_auditevent" in sql

    def test_rls_sql_contains_superadmin_bypass_policy(self):
        module = _load_migration_module("0009_audit_rls")
        sql = module.ENABLE_RLS_SQL
        assert "superadmin_bypass" in sql
        assert "bypass_rls" in sql

    def test_reverse_sql_drops_policies(self):
        module = _load_migration_module("0009_audit_rls")
        sql = module.DISABLE_RLS_SQL
        assert "DROP POLICY IF EXISTS" in sql
        assert "tenant_isolation" in sql
        assert "superadmin_bypass" in sql


# ──────────────────────────────────────────────────────────
# RLS enforcement on PostgreSQL (skipped on SQLite)
# ──────────────────────────────────────────────────────────


@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="RLS requires PostgreSQL — SQLite in tests"
)
class TestRLSEnforcementPostgres:
    """Actual RLS enforcement — PostgreSQL only."""

    def test_rls_policy_exists(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT policyname FROM pg_policies WHERE tablename = 'accounts_auditevent'"
            )
            policies = {row[0] for row in cursor.fetchall()}
        assert "tenant_isolation" in policies
        assert "superadmin_bypass" in policies

    def test_rls_enabled_on_table(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = 'accounts_auditevent'"
            )
            row = cursor.fetchone()
        assert row is not None and row[0] is True


# ──────────────────────────────────────────────────────────
# Migration reversibility
# ──────────────────────────────────────────────────────────


class TestMigrationReversibility:
    """Both migrations are reversible without error."""

    def test_0008_reversible(self):
        """0008 operations are reversible Django schema operations."""
        from django.db.migrations import AddField, AddIndex, AlterField

        module = _load_migration_module("0008_audit_traceability")
        assert len(module.Migration.operations) > 0
        for op in module.Migration.operations:
            assert isinstance(op, (AddField, AlterField, AddIndex)), (
                f"Unexpected non-reversible operation: {type(op).__name__}"
            )

    def test_0009_reversible(self):
        module = _load_migration_module("0009_audit_rls")
        from django.db.migrations import RunPython

        for op in module.Migration.operations:
            if isinstance(op, RunPython):
                assert op.reverse_code is not None
