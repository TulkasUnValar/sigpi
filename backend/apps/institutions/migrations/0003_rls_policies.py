"""
RLS (Row-Level Security) policies for institution-scoped tables.

Implements tenant isolation for all 5 sub-institution entities.
Institution table is excluded — it has no institution_id column.

Design reference: openspec/changes/institutions/design.md — RLS Policies
Pattern reference: apps/accounts/migrations/0004_rls_policies.py

Policies applied:
  - tenant_isolation: restrict rows to session's sigpi.institution_id
  - superadmin_bypass: allow when sigpi.bypass_rls = true

Note: RLS is a PostgreSQL feature. On SQLite (test environment),
these operations are wrapped in a conditional that checks the DB engine.
"""
from django.db import migrations


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


# Tables scoped to an institution (all have institution_id column).
# Institution table excluded — it IS the tenant root, no institution_id FK.
TENANT_SCOPED_TABLES = [
    "institutions_sede",
    "institutions_facultad",
    "institutions_researchcenter",
    "institutions_researchgroup",
    "institutions_researchline",
]

ENABLE_RLS_SQL = ""
DISABLE_RLS_SQL = ""

for table in TENANT_SCOPED_TABLES:
    ENABLE_RLS_SQL += f"""
-- Enable RLS on {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their institution's rows
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
    USING (institution_id = current_setting('sigpi.institution_id')::uuid);

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {table};
CREATE POLICY superadmin_bypass ON {table}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

    DISABLE_RLS_SQL += f"""
DROP POLICY IF EXISTS tenant_isolation ON {table};
DROP POLICY IF EXISTS superadmin_bypass ON {table};
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def apply_rls(apps, schema_editor):
    """Apply RLS policies — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(ENABLE_RLS_SQL)


def remove_rls(apps, schema_editor):
    """Remove RLS policies — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(DISABLE_RLS_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("institutions", "0002_expand_hierarchy"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
