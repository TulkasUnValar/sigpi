"""
RLS (Row-Level Security) policies for progress-scoped tables.

Implements tenant isolation for all 4 progress tables:
- progress_progressreport (parent: direct institution_id)
- progress_progressreview (child: subquery via progress_report_id)
- progress_progressdocument (child: subquery via progress_report_id)
- progress_progressstatelog (child: subquery via progress_report_id)

Design reference: openspec/sdd/advances/design.md — RLS Policies
Pattern reference: apps/projects/migrations/0002_rls_policies.py

Note: RLS is a PostgreSQL feature. On SQLite (test environment),
these operations are wrapped in a conditional that checks the DB engine.
"""
from django.db import migrations


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


# ── Parent table (direct institution_id column) ─────────────────────────

PARENT_TABLE = "progress_progressreport"

# ── Child tables (no institution_id — reach via progress_report_id FK) ───

CHILD_TABLES = [
    "progress_progressreview",
    "progress_progressdocument",
    "progress_progressstatelog",
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

# ── Child table policies (subquery via progress_report_id) ──────────────

for table in CHILD_TABLES:
    ENABLE_RLS_SQL += f"""
-- Enable RLS on {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only rows linked to progress reports in their institution
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
    USING (progress_report_id IN (
        SELECT id FROM progress_progressreport
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
        ("progress", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
