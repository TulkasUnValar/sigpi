"""
Shared RLS test helpers for the per-app enforcement suites.

The generic RLS mechanics — GUC names, migration loading, SQL collection,
apply-function source extraction, GUC writing and the isolation assertions —
are identical across the app test files. This module is their single source of
truth; app-specific seeds, table lists and expectations stay local.
"""

import importlib
import inspect
import re

from django.db import connection
from django.db.migrations.loader import MigrationLoader

TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def load_migration(app_label, migration_name):
    """Load a migration from the migration loader by (app_label, name)."""
    loader = MigrationLoader(connection)
    key = (app_label, migration_name)
    if key not in loader.disk_migrations:
        return None
    return loader.disk_migrations[key]


def get_all_sql(migration):
    """Collect all SQL from the migration module."""
    if migration is None:
        return ""
    module_name = migration.__class__.__module__
    mod = importlib.import_module(module_name)
    sql_parts = []
    for attr_name in dir(mod):
        val = getattr(mod, attr_name)
        if isinstance(val, str) and "tenant_isolation" in val:
            sql_parts.append(val)
    return "\n".join(sql_parts)


def policy_using(sql, table, policy="tenant_isolation"):
    """Return the whitespace-normalized USING predicate of ``<policy>`` on ``table``.

    Anchors on ``CREATE POLICY`` (never ``DROP POLICY``) and captures the
    balanced ``USING (...)`` clause up to the statement-terminating semicolon,
    so nested parentheses (NULLIF, subqueries) survive. Returns None when the
    policy is absent.
    """
    pattern = re.compile(
        r"CREATE\s+POLICY\s+"
        + re.escape(policy)
        + r"\s+ON\s+"
        + re.escape(table)
        + r"\b\s+USING\s*\((.*?)\)\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(sql)
    if match is None:
        return None
    return " ".join(match.group(1).split())


def get_apply_function_source(migration):
    """Extract the source code of the RunPython forward function."""
    for operation in migration.operations:
        if hasattr(operation, "code") and operation.code is not None:
            return inspect.getsource(operation.code)
    return ""


def set_rls(connection, institution_id, bypass):
    """Write the RLS GUCs at connection scope, exactly like production does."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


def assert_only_a_visible(model, pk_a, pk_b):
    """Non-vacuous assertion pair: A's row visible, B's row denied."""
    assert model.objects.filter(pk=pk_a).exists(), (
        f"{model.__name__}: institution A's seeded row is not visible under "
        f"institution A's tenant context."
    )
    assert model.objects.filter(pk=pk_b).count() == 0, (
        f"{model.__name__}: institution B's seeded row leaked into institution A's tenant context."
    )


def assert_both_visible(model, pk_a, pk_b):
    """Bypass must reveal both institutions' rows, not merely zero rows."""
    both = model.objects.filter(pk__in=[pk_a, pk_b]).count()
    assert both == 2, (
        f"{model.__name__}: superadmin bypass exposed {both} of 2 seeded rows; "
        f"it must reveal more than a single tenant scope."
    )
