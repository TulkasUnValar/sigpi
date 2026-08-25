"""
RLS (Row-Level Security) policies for notifications tables.

Implements tenant isolation for all 4 notifications tables:
- notifications_notification (parent: direct denormalized institution_id)
- notifications_notificationlog (child: subquery via notification_id)
- notifications_userpreference (user-global: subquery via active membership)
- notifications_notificationtemplate (catalog: explicit global policy)

Design reference: openspec/changes/notifications/design.md — RLS Policies
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
    return schema_editor.connection.vendor == "postgresql"


# ── Parent table (direct institution_id column) ─────────────────────────

PARENT_TABLE = "notifications_notification"

# ── Child table (reaches institution via notification_id FK) ─────────────

LOG_TABLE = "notifications_notificationlog"

# ── User-global table (scoped through active institution membership) ─────

PREFERENCE_TABLE = "notifications_userpreference"

# ── Catalog table (global policy — templates are catalog data) ───────────

TEMPLATE_TABLE = "notifications_notificationtemplate"

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

# ── Child table policies (subquery via notification_id) ────────────────

ENABLE_RLS_SQL += f"""
-- Enable RLS on {LOG_TABLE}
ALTER TABLE {LOG_TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: users see only logs linked to notifications in their institution
DROP POLICY IF EXISTS tenant_isolation ON {LOG_TABLE};
CREATE POLICY tenant_isolation ON {LOG_TABLE}
    USING (notification_id IN (
        SELECT id FROM notifications_notification
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
    ));

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {LOG_TABLE};
CREATE POLICY superadmin_bypass ON {LOG_TABLE}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += f"""
DROP POLICY IF EXISTS tenant_isolation ON {LOG_TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {LOG_TABLE};
ALTER TABLE {LOG_TABLE} DISABLE ROW LEVEL SECURITY;
"""

# ── UserPreference policies (scoped through caller's active membership) ──

ENABLE_RLS_SQL += f"""
-- Enable RLS on {PREFERENCE_TABLE}
ALTER TABLE {PREFERENCE_TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: preferences are user-global — visible when the user has an
-- active membership in the session's institution
DROP POLICY IF EXISTS tenant_isolation ON {PREFERENCE_TABLE};
CREATE POLICY tenant_isolation ON {PREFERENCE_TABLE}
    USING (user_id IN (
        SELECT user_id FROM accounts_institutionmembership
        WHERE institution_id = current_setting('sigpi.institution_id')::uuid
          AND is_active = true
    ));

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {PREFERENCE_TABLE};
CREATE POLICY superadmin_bypass ON {PREFERENCE_TABLE}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += f"""
DROP POLICY IF EXISTS tenant_isolation ON {PREFERENCE_TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {PREFERENCE_TABLE};
ALTER TABLE {PREFERENCE_TABLE} DISABLE ROW LEVEL SECURITY;
"""

# ── NotificationTemplate policies (explicit global catalog policy) ───────

ENABLE_RLS_SQL += f"""
-- Enable RLS on {TEMPLATE_TABLE}
ALTER TABLE {TEMPLATE_TABLE} ENABLE ROW LEVEL SECURITY;

-- Policy: templates are catalog data — globally visible to every tenant
DROP POLICY IF EXISTS tenant_isolation ON {TEMPLATE_TABLE};
CREATE POLICY tenant_isolation ON {TEMPLATE_TABLE}
    USING (true);

-- Policy: superadmin bypass
DROP POLICY IF EXISTS superadmin_bypass ON {TEMPLATE_TABLE};
CREATE POLICY superadmin_bypass ON {TEMPLATE_TABLE}
    USING (COALESCE(current_setting('sigpi.bypass_rls', true), 'false')::bool = true);
"""

DISABLE_RLS_SQL += f"""
DROP POLICY IF EXISTS tenant_isolation ON {TEMPLATE_TABLE};
DROP POLICY IF EXISTS superadmin_bypass ON {TEMPLATE_TABLE};
ALTER TABLE {TEMPLATE_TABLE} DISABLE ROW LEVEL SECURITY;
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
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]