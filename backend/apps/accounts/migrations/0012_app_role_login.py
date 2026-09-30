"""
Make the least-privilege application role login-capable.

Migration ``0010_least_privilege_app_role`` created ``sigpi_app`` with
``NOLOGIN`` and deliberately deferred the login-capable runtime role to the
runtime switch. This migration only flips the role to ``LOGIN``.

No password
-----------
A password is intentionally **not** set here. A password must never be
committed, and a migration must not read environment variables: a migration
that depends on the environment produces a different result on every machine
and cannot be replayed from the migration history. The password is provisioned
out of band, per environment, by whoever operates the cluster. The runtime
reads it from ``POSTGRES_APP_PASSWORD``.

A ``LOGIN`` role with no password still connects wherever the cluster trusts
the connection: the throwaway clusters used for verification and CI's
PostgreSQL service both accept the handshake (CI sets the password at runtime
with ``psql`` from the owner, so pg_hba's password method is satisfied too).

Safety
------
The ``ALTER`` is convergent: re-running it is a no-op. It is guarded for
PostgreSQL because roles are a PostgreSQL feature and the default local test
engine is SQLite. The reverse restores ``NOLOGIN`` so a rollback returns the
role to the state ``0010`` left it in; it never drops the role, because a role
is shared infrastructure and dropping it would be more destructive than
creating it.
"""

from django.db import migrations

APP_ROLE = "sigpi_app"

LOGIN_SQL = f"""
ALTER ROLE {APP_ROLE} LOGIN;
"""

NOLOGIN_SQL = f"""
ALTER ROLE {APP_ROLE} NOLOGIN;
"""


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


def enable_login(apps, schema_editor):
    """Let the least-privilege role log in — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(LOGIN_SQL)


def disable_login(apps, schema_editor):
    """Restore the ``NOLOGIN`` state left by 0010 — PostgreSQL only, no-op on SQLite.

    The role itself is not dropped: the migration only reverses the attribute
    this migration changed.
    """
    if _is_postgresql(schema_editor):
        schema_editor.execute(NOLOGIN_SQL)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_audit_policy_per_command"),
    ]

    operations = [
        migrations.RunPython(
            code=enable_login,
            reverse_code=disable_login,
        ),
    ]
