"""
RLS (Row-Level Security) policies for reports_reporttemplate.

``ReportTemplate`` is institution-scoped (``institution`` FK,
``backend/apps/reports/models.py:202``; table declared at :212). It was created
in ``reports/0003``, after ``reports/0002`` applied the app's policies, so no
migration ever covered it — a multi-tenant isolation gap. This migration closes
it with the standard policy pair used by every other app.

Policies applied to ``reports_reporttemplate``:
  - tenant_isolation: restrict rows to the session's sigpi.institution_id
  - superadmin_bypass: allow when sigpi.bypass_rls = true

Note: RLS is a PostgreSQL feature. On SQLite (test environment), these
operations are wrapped in a conditional that checks the DB engine.
"""

from django.db import migrations

TABLE = "reports_reporttemplate"


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


ENABLE_RLS_SQL = f"""
-- Enable RLS on the report template table
ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their institution's rows
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
CREATE POLICY tenant_isolation ON {TABLE}
    USING (institution_id = NULLIF(current_setting('sigpi.institution_id', true), '')::uuid);

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};
CREATE POLICY superadmin_bypass ON {TABLE}
    USING (NULLIF(current_setting('sigpi.bypass_rls', true), '')::bool = true);
"""

DISABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {TABLE};
ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
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
        ("reports", "0003_report_title_report_updated_at_reportapproval_status_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
