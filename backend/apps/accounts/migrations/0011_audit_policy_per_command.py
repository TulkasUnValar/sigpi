"""
Per-command RLS policies for the audit traceability table.

Migration ``0009_audit_rls`` declared a single ``ALL``/``USING`` pair. PostgreSQL
uses a policy's ``USING`` expression as its ``WITH CHECK`` for INSERT when none is
declared, so appending a system event with ``institution_id = NULL`` — a failed
login, a logout without a session institution, an OIDC login — raised
``new row violates row-level security policy`` and turned the request into a 500.

This migration splits the policy by command:

  - ``tenant_isolation`` (SELECT): a row with no institution is never visible to a
    tenant. The name is kept from ``0009_audit_rls`` because
    ``apps/audit/tests/test_rls.py`` pins ``CREATE POLICY tenant_isolation``
    against the schema contract.
  - ``tenant_insert`` (INSERT): appends also accept system events that carry no
    tenant, so traceability is not lost.
  - ``superadmin_bypass`` (ALL): applies to reads and writes alike.

After this migration UPDATE and DELETE have no applicable policy for a tenant
session, which under RLS means deny — the table is append-only.

Note: RLS is a PostgreSQL feature. On SQLite (test environment) these operations
are wrapped in a conditional that checks the DB engine.
"""

from django.db import migrations

TABLE = "accounts_auditevent"

TENANT_CAST = "NULLIF(current_setting('sigpi.institution_id', true), '')::uuid"
BYPASS_CAST = "NULLIF(current_setting('sigpi.bypass_rls', true), '')::bool = true"

ENABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};

-- Reads stay tenant-scoped: a row with no institution is never visible to a tenant.
CREATE POLICY tenant_isolation ON {TABLE}
    FOR SELECT
    USING (institution_id = {TENANT_CAST});

-- Appends also accept system events that carry no tenant, so a failed login or a
-- logout can be recorded instead of aborting the request with a policy violation.
CREATE POLICY tenant_insert ON {TABLE}
    FOR INSERT
    WITH CHECK (
        institution_id IS NULL
        OR institution_id = {TENANT_CAST}
    );

-- Superadmin bypass applies to reads and writes alike.
CREATE POLICY superadmin_bypass ON {TABLE}
    FOR ALL
    USING ({BYPASS_CAST})
    WITH CHECK ({BYPASS_CAST});
"""

# Restore the state left by 0009_audit_rls: drop the per-command policies and
# recreate the original ALL/USING-only pair. RLS itself stays enabled — 0009
# enabled it, and this migration's reverse must not disable what it did not enable.
DISABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
DROP POLICY IF EXISTS tenant_insert ON {TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};

CREATE POLICY tenant_isolation ON {TABLE}
    USING (institution_id = {TENANT_CAST});

CREATE POLICY superadmin_bypass ON {TABLE}
    USING ({BYPASS_CAST});
"""


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


def apply_rls(apps, schema_editor):
    """Apply per-command RLS policies — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(ENABLE_RLS_SQL)


def remove_rls(apps, schema_editor):
    """Restore the 0009 policies — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(DISABLE_RLS_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_least_privilege_app_role"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
