"""
Fail unless the configured database role really enforces row-level security.

This is the end-to-end gate for the least-privilege runtime switch. It is
deliberately *not* a pytest test: pytest-django creates a fresh test database
and applies migrations, and the ``sigpi_app`` role can do neither, so a test
could only ever run under the owner — the exact blind spot this command closes.
Instead it runs against the already-migrated database over the configured
connection, so the property is proven through the same credentials the runtime
uses (``POSTGRES_APP_USER`` / ``POSTGRES_APP_PASSWORD``).

The assertion is about real rows, never about the policy text:

  - a row inserted for institution A is invisible with no tenant context, and
    with a different institution's context;
  - the same row is visible once the connection carries institution A's
    context.

It also refuses to run when the connected role is a superuser or carries
``BYPASSRLS``, because such a role skips every policy and the row assertions
would pass vacuously. CI runs this command in the dedicated app-role job after
migrating as the owner and setting the role password at runtime.
"""

from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

TABLE = "accounts_auditevent"
TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def _set_context(cursor, institution_id, bypass):
    """Write both RLS GUCs at connection scope, exactly like the application."""
    cursor.execute(
        "SELECT set_config(%s, %s, false)",
        [TENANT_GUC, "" if institution_id is None else str(institution_id)],
    )
    cursor.execute(
        "SELECT set_config(%s, %s, false)",
        [BYPASS_GUC, "true" if bypass else "false"],
    )


class Command(BaseCommand):
    help = "Assert that the configured database role enforces RLS on a protected table."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError(
                "RLS enforcement requires PostgreSQL; the configured engine is "
                f"'{connection.vendor}'."
            )

        self._assert_least_privilege()

        institution_a = uuid.uuid4()
        institution_b = uuid.uuid4()
        row_id = uuid.uuid4()

        self._insert_for(row_id, institution_a)

        try:
            self._assert_invisible(row_id, institution_id=None, label="no tenant context")
            self._assert_invisible(
                row_id, institution_id=institution_b, label="a different institution"
            )
            visible = self._count(row_id, institution_id=institution_a)
        finally:
            self._cleanup(row_id)

        if visible != 1:
            raise CommandError(
                f"Institution A saw {visible} of its own row(s); expected 1. RLS is "
                "denying the tenant its own data, so the runtime switch is not safe."
            )

        role = connection.settings_dict["USER"]
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: role '{role}' enforces RLS on {TABLE} "
                f"(row {row_id}: 0 rows with no context, 0 with another institution, "
                "1 with its own institution)."
            )
        )

    def _assert_least_privilege(self):
        """Refuse a superuser/BYPASSRLS connection: every policy would be inert."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_user, r.rolsuper, r.rolbypassrls "
                "FROM pg_roles r WHERE r.rolname = current_user"
            )
            row = cursor.fetchone()
        if row is None:
            raise CommandError("Could not resolve the connected PostgreSQL role.")
        role, is_superuser, bypass_rls = row
        if is_superuser or bypass_rls:
            raise CommandError(
                f"Connected as '{role}' (rolsuper={is_superuser}, "
                f"rolbypassrls={bypass_rls}). This role skips every RLS policy, so the "
                "assertions would prove nothing. Connect as the least-privilege role "
                "by setting POSTGRES_APP_USER/POSTGRES_APP_PASSWORD."
            )

    def _insert_for(self, row_id, institution_id):
        """Insert one row while the bypass policy allows the write."""
        with connection.cursor() as cursor:
            _set_context(cursor, institution_id, bypass=True)
            cursor.execute(
                f"INSERT INTO {TABLE} (id, event_type, timestamp, institution_id) "
                "VALUES (%s, %s, now(), %s)",
                [str(row_id), "LOGIN", str(institution_id)],
            )

    def _count(self, row_id, institution_id):
        """Count the probe row under a tenant-only (non-bypass) context."""
        with connection.cursor() as cursor:
            _set_context(cursor, institution_id, bypass=False)
            cursor.execute(
                f"SELECT count(*) FROM {TABLE} WHERE id = %s",
                [str(row_id)],
            )
            return cursor.fetchone()[0]

    def _assert_invisible(self, row_id, institution_id, label):
        seen = self._count(row_id, institution_id=institution_id)
        if seen != 0:
            raise CommandError(
                f"With {label}, institution A's row was visible ({seen} row(s)). "
                "RLS is not restricting the configured role."
            )

    def _cleanup(self, row_id):
        """Best-effort removal of the probe row; never mask the real outcome."""
        try:
            with connection.cursor() as cursor:
                _set_context(cursor, None, bypass=True)
                cursor.execute(f"DELETE FROM {TABLE} WHERE id = %s", [str(row_id)])
        except Exception:
            pass
