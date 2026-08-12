"""
RLS (Row-Level Security) policies for workflow-scoped tables.

Implements tenant isolation for all 4 workflow tables:
- project_workflow_workflowtemplate (parent: direct institution_id)
- project_workflow_workflowinstance (parent: direct institution_id)
- project_workflow_workflowstep (child: subquery via template_id)
- project_workflow_workflowaction (child: subquery via instance_id)

Design reference: openspec/changes/project_workflow/design.md — RLS Policies
Pattern reference: apps/projects/migrations/0002_rls_policies.py

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


# ── Parent tables (direct institution_id column) ──────────────────────

PARENT_TABLES = [
    "project_workflow_workflowtemplate",
    "project_workflow_workflowinstance",
]

# ── Child tables (no institution_id — reach via FK) ─────────────────────

CHILD_TABLES_SQL = {
    "project_workflow_workflowstep": """
        template_id IN (
            SELECT id FROM project_workflow_workflowtemplate
            WHERE institution_id = current_setting('sigpi.institution_id')::uuid
        )
    """,
    "project_workflow_workflowaction": """
        instance_id IN (
            SELECT id FROM project_workflow_workflowinstance
            WHERE institution_id = current_setting('sigpi.institution_id')::uuid
        )
    """,
}

ENABLE_RLS_SQL = ""
DISABLE_RLS_SQL = ""

# ── Parent table policies ──────────────────────────────────────────────

for table in PARENT_TABLES:
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

# ── Child table policies (subquery via FK) ─────────────────────────────

for table, subquery in CHILD_TABLES_SQL.items():
    ENABLE_RLS_SQL += f"""
-- Enable RLS on {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only rows linked to parents in their institution
DROP POLICY IF EXISTS tenant_isolation ON {table};
CREATE POLICY tenant_isolation ON {table}
    USING ({subquery.strip()});

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
        ("project_workflow", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
