"""
RLS (Row-Level Security) policies for documents-scoped tables.

Implements tenant isolation for all 4 documents tables:
- documents_document (parent: direct institution_id)
- documents_minutes (parent: direct institution_id)
- documents_documentversion (child: subquery via document_id)
- documents_digitalsignature (child: subquery via document_version_id
  → documents_documentversion → documents_document)

Design reference: openspec/changes/attachments/design.md — RLS Policies
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


# ── Parent tables (direct institution_id column) ──────────────────────

PARENT_TABLES = [
    "documents_document",
    "documents_minutes",
]

# ── Child tables (no institution_id — reach via FK subqueries) ─────────

ENABLE_RLS_SQL = ""
DISABLE_RLS_SQL = ""

# ── Parent table policies ────────────────────────────────────────────

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

# ── Child table policies ─────────────────────────────────────────────

# documents_documentversion: reach institution via document_id → documents_document.
ENABLE_RLS_SQL += """
-- Enable RLS on documents_documentversion
ALTER TABLE documents_documentversion ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON documents_documentversion;
CREATE POLICY tenant_isolation ON documents_documentversion
    USING (document_id IN (
        SELECT id FROM documents_document
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

DROP POLICY IF EXISTS superadmin_bypass ON documents_documentversion;
CREATE POLICY superadmin_bypass ON documents_documentversion
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

# documents_digitalsignature: reach institution via document_version_id
# → documents_documentversion → documents_document.
ENABLE_RLS_SQL += """
-- Enable RLS on documents_digitalsignature
ALTER TABLE documents_digitalsignature ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON documents_digitalsignature;
CREATE POLICY tenant_isolation ON documents_digitalsignature
    USING (document_version_id IN (
        SELECT id FROM documents_documentversion
        WHERE document_id IN (
            SELECT id FROM documents_document
            WHERE institution_id = current_setting('sigpi.institution_id')::uuid
        )
    ));

DROP POLICY IF EXISTS superadmin_bypass ON documents_digitalsignature;
CREATE POLICY superadmin_bypass ON documents_digitalsignature
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += """
DROP POLICY IF EXISTS tenant_isolation ON documents_documentversion;
DROP POLICY IF EXISTS superadmin_bypass ON documents_documentversion;
ALTER TABLE documents_documentversion DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON documents_digitalsignature;
DROP POLICY IF EXISTS superadmin_bypass ON documents_digitalsignature;
ALTER TABLE documents_digitalsignature DISABLE ROW LEVEL SECURITY;
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
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
