"""
RLS (Row-Level Security) policies for researcher-scoped tables.

Implements tenant isolation for all 4 researcher tables:
- researchers_researcher (parent: direct institution_id)
- researchers_researcheraffiliation (child: subquery via researcher_id)
- researchers_externalprofile (child: subquery via researcher_id)
- researchers_researcherattachment (child: subquery via researcher_id)

Design reference: openspec/changes/researchers/design.md — RLS Policies
Pattern reference: apps/institutions/migrations/0003_rls_policies.py

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


# ── Parent table (direct institution_id column) ─────────────────────────

PARENT_TABLE = "researchers_researcher"

# ── Child tables (no institution_id — reach via researcher_id FK) ───────

CHILD_TABLES = [
    "researchers_researcheraffiliation",
    "researchers_externalprofile",
    "researchers_researcherattachment",
]

ENABLE_RLS_SQL = ""
DISABLE_RLS_SQL = ""

# ── Parent table policies ──────────────────────────────────────────────

ENABLE_RLS_SQL += f"""
-- Enable RLS on parent table
ALTER TABLE {PARENT_TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their institution's rows
DROP POLICY IF EXISTS tenant_isolation ON {PARENT_TABLE};
CREATE POLICY tenant_isolation ON {PARENT_TABLE}
    USING (institution_id = current_setting('sigpi.institution_id')::uuid);

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {PARENT_TABLE};
CREATE POLICY superadmin_bypass ON {PARENT_TABLE}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += f"""
DROP POLICY IF EXISTS tenant_isolation ON {PARENT_TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {PARENT_TABLE};
ALTER TABLE {PARENT_TABLE} DISABLE ROW LEVEL SECURITY;
"""

# ── Child table policies (subquery via researcher_id) ──────────────────

for table in CHILD_TABLES:
    ENABLE_RLS_SQL += f"""
-- Enable RLS on {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only rows linked to researchers in their institution
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
    USING (researcher_id IN (
        SELECT id FROM researchers_researcher
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

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
        ("researchers", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
