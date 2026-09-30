"""
Membership self-read RLS policy.

``accounts_institutionmembership`` is scoped by ``institution_id`` only
(``0004_rls_policies``). Under the least-privilege ``sigpi_app`` role that
makes "which institutions does this authenticated user belong to?" — an
inherently cross-tenant question — unanswerable, so local login cannot adopt
the primary institution and institution switching is denied.

This migration adds a third, permissive ``FOR SELECT`` policy that lets a
session read membership rows whose ``user_id`` is its own. PostgreSQL ORs
permissive policies, so ``tenant_isolation`` and ``superadmin_bypass`` are left
untouched and tenant isolation is unchanged for every row that is not the
session user's own.

The policy matches the ``NULLIF(current_setting(..., true), '')`` hardening
used by the other policies: an empty GUC (anonymous or user-less request)
casts to NULL and matches no row, rather than falling back to a stale value.

Note: RLS is a PostgreSQL feature. On SQLite (test environment) these
operations are wrapped in a conditional that checks the DB engine.
"""

from django.db import migrations

TABLE = "accounts_institutionmembership"
POLICY = "own_memberships"
USER_CAST = "NULLIF(current_setting('sigpi.user_id', true), '')::uuid"

ENABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS {POLICY} ON {TABLE};
CREATE POLICY {POLICY} ON {TABLE}
    FOR SELECT
    USING (user_id = {USER_CAST});
"""

DISABLE_RLS_SQL = f"""
DROP POLICY IF EXISTS {POLICY} ON {TABLE};
"""


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


def apply_rls(apps, schema_editor):
    """Add the membership self-read policy — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(ENABLE_RLS_SQL)


def remove_rls(apps, schema_editor):
    """Drop the membership self-read policy — PostgreSQL only, no-op on SQLite.

    Reversing removes only the policy this migration added: RLS stays enabled
    and the other policies on the table are untouched.
    """
    if _is_postgresql(schema_editor):
        schema_editor.execute(DISABLE_RLS_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_app_role_login"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_rls,
            reverse_code=remove_rls,
        ),
    ]
