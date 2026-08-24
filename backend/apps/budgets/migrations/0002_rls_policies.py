"""
RLS (Row-Level Security) policies for budgets-scoped tables.

Implements tenant isolation for all 5 budget tables:
- budgets_budget (parent: direct institution_id)
- budgets_budgetline (child: subquery via budget_id)
- budgets_budgetexecution (child: subquery via line_id → budget_id)
- budgets_budgetattachment (child: subquery via budget_id)
- budgets_fundingsource (child: subquery via project_id)

Design reference: openspec/changes/budgets/design.md — RLS Policies
Pattern reference: apps/calls/migrations/0002_rls_policies.py

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

PARENT_TABLE = "budgets_budget"

# ── Child tables (no institution_id — reach via parent FKs) ──────────────

CHILD_TABLES = [
    "budgets_budgetline",
    "budgets_budgetexecution",
    "budgets_budgetattachment",
    "budgets_fundingsource",
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

# ── Child table policies ────────────────────────────────────────────────

# budgets_budgetline, budgets_budgetattachment: reach Budget directly.
ENABLE_RLS_SQL += """
-- Enable RLS on budgets_budgetline
ALTER TABLE budgets_budgetline ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetline;
CREATE POLICY tenant_isolation ON budgets_budgetline
    USING (budget_id IN (
        SELECT id FROM budgets_budget
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetline;
CREATE POLICY superadmin_bypass ON budgets_budgetline
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);

-- Enable RLS on budgets_budgetattachment
ALTER TABLE budgets_budgetattachment ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetattachment;
CREATE POLICY tenant_isolation ON budgets_budgetattachment
    USING (budget_id IN (
        SELECT id FROM budgets_budget
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetattachment;
CREATE POLICY superadmin_bypass ON budgets_budgetattachment
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

# budgets_budgetexecution: reach Budget via line_id → budget_id.
ENABLE_RLS_SQL += """
-- Enable RLS on budgets_budgetexecution
ALTER TABLE budgets_budgetexecution ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetexecution;
CREATE POLICY tenant_isolation ON budgets_budgetexecution
    USING (line_id IN (
        SELECT id FROM budgets_budgetline
        WHERE budget_id IN (
            SELECT id FROM budgets_budget
            WHERE institution_id = current_setting('sigpi.institution_id')::uuid
        )
    ));

DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetexecution;
CREATE POLICY superadmin_bypass ON budgets_budgetexecution
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

# budgets_fundingsource: reach institution via project_id → project.institution_id.
ENABLE_RLS_SQL += """
-- Enable RLS on budgets_fundingsource
ALTER TABLE budgets_fundingsource ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_fundingsource;
CREATE POLICY tenant_isolation ON budgets_fundingsource
    USING (project_id IN (
        SELECT id FROM projects_project
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

DROP POLICY IF EXISTS superadmin_bypass ON budgets_fundingsource;
CREATE POLICY superadmin_bypass ON budgets_fundingsource
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += """
DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetline;
DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetline;
ALTER TABLE budgets_budgetline DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetattachment;
DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetattachment;
ALTER TABLE budgets_budgetattachment DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_budgetexecution;
DROP POLICY IF EXISTS superadmin_bypass ON budgets_budgetexecution;
ALTER TABLE budgets_budgetexecution DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON budgets_fundingsource;
DROP POLICY IF EXISTS superadmin_bypass ON budgets_fundingsource;
ALTER TABLE budgets_fundingsource DISABLE ROW LEVEL SECURITY;
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
        ("budgets", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
