"""
Least-privilege application role for SIGPI.

Creates the `sigpi_app` role and grants it the privileges the application
needs, so that a session can assume a non-owner, non-`BYPASSRLS` role that
row-level security actually restricts.

Why a migration owns this
-------------------------
The role must exist in every environment that runs the application:
CI, docker-compose, and local PostgreSQL. CI's postgres service declares no
`volumes:` mount, so `/docker-entrypoint-initdb.d` is not available there and
an init script cannot create the role. A versioned migration is the only
mechanism that makes the role exist in all three environments with no service
change, because every environment already applies migrations.

Least-privilege defect it addresses
-----------------------------------
The application currently connects as the `POSTGRES_USER` (for example the
CI/docker user `sigpi`), which is a superuser and therefore carries
`BYPASSRLS`. Superusers and `BYPASSRLS` roles skip row-level security
unconditionally, and `FORCE ROW LEVEL SECURITY` does not change that. As a
result RLS restricts nobody today. `sigpi_app` is deliberately `NOSUPERUSER`
and `NOBYPASSRLS` so the policies apply.

`NOLOGIN` is intentional least privilege: the role is only ever assumed with
`SET ROLE`. A login-capable runtime role arrives with the deferred runtime
switch (a separate change), together with `POSTGRES_APP_USER`/`POSTGRES_APP_PASSWORD`.

Safety
------
This migration is additive and convergent. It creates the role when it is
absent and otherwise re-applies the intended attributes, and it only ever
grants privileges — it never drops a role or revokes anything. The reverse is a
documented no-op: a role is shared infrastructure and dropping it would be far
more destructive than creating it. The migration is guarded the same way as the
other RLS migrations, so SQLite (the default local test engine) skips it.

Note: RLS and roles are PostgreSQL features. On SQLite these operations are
wrapped in a conditional that checks the DB engine.
"""

from django.db import migrations

APP_ROLE = "sigpi_app"

# Idempotent role creation. The DO block makes re-running the migration a
# no-op when the role already exists, without erroring.
CREATE_ROLE_SQL = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        CREATE ROLE {APP_ROLE}
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOBYPASSRLS
            NOLOGIN;
    ELSE
        -- Converge an existing role on the intended attributes. Without this,
        -- a role already provisioned (by hand or by an older environment) as
        -- SUPERUSER or with BYPASSRLS would silently keep skipping every
        -- policy, which is the exact defect this role exists to remove.
        ALTER ROLE {APP_ROLE}
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOBYPASSRLS
            NOLOGIN;
    END IF;
END
$$;
"""

# Grants for the tables and sequences that exist now, plus default privileges
# so any future table created in `public` is covered automatically.
GRANT_SQL = f"""
GRANT USAGE ON SCHEMA public TO {APP_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE};
GRANT {APP_ROLE} TO CURRENT_USER;
"""


def _is_postgresql(schema_editor):
    """Check if the current database is PostgreSQL."""
    engine = schema_editor.connection.vendor
    return engine == "postgresql"


def apply_role(apps, schema_editor):
    """Create the least-privilege role and grant it — PostgreSQL only, no-op on SQLite."""
    if _is_postgresql(schema_editor):
        schema_editor.execute(CREATE_ROLE_SQL)
        schema_editor.execute(GRANT_SQL)


def noop(apps, schema_editor):
    """Documented no-op reverse.

    The reverse migration intentionally does nothing. Roles are shared
    infrastructure that may be referenced by other databases, sessions, or
    grants; dropping `sigpi_app` on rollback could break a running cluster.
    The forward migration is strictly additive, so leaving the role in place
    is the safe inverse.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_audit_rls"),
    ]

    operations = [
        migrations.RunPython(
            code=apply_role,
            reverse_code=noop,
        ),
    ]
