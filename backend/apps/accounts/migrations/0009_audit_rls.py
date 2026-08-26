"""
RLS (Row-Level Security) policies for the audit traceability table.

Adds PostgreSQL row-level security to `accounts_auditevent` as defense-in-depth
for the audit/traceability module (SIGPI §6.13).

Design reference: openspec/changes/audit/design.md — PostgreSQL RLS
Spec reference: openspec/changes/audit/specs/audit/spec.md

Policies applied to `accounts_auditevent`:
- tenant_isolation: restrict rows to the session's sigpi.institution_id
- superadmin_bypass: allow when sigpi.bypass_rls = true

Note: RLS is a PostgreSQL feature. On SQLite (test environment) these
operations are wrapped in a conditional that checks the DB engine.
"""

from django.db import migrations

TABLE = "accounts_auditevent"

ENABLE_RLS_SQL = f"""
-- Enable RLS on {TABLE}
ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their institution's rows
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
CREATE POLICY tenant_isolation ON {TABLE}
    USING (institution_id = current_setting('sigpi.institution_id')::uuid);

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};
CREATE POLICY superadmin_bypass ON {TABLE}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};
ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""


def apply_rls(apps, schema_editor):
    """Apply RLS policies — PostgreSQL only, no-op on SQLite."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(ENABLE_RLS_SQL)


def remove_rls(apps, schema_editor):
    """Remove RLS policies — PostgreSQL only, no-op on SQLite."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DISABLE_RLS_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_audit_traceability"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
