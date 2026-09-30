"""
Request-scoped PostgreSQL tenant context.

Why connection-scoped ``SET`` and not ``SET LOCAL`` inside a transaction
------------------------------------------------------------------------
The tenant GUCs must be in effect for every query the request issues, but a
transaction that spanned the whole request was rejected: it would hold
``select_for_update`` locks across slow external I/O (MinIO, Meilisearch, OIDC,
PDF rendering) and would degrade the existing ``transaction.atomic()`` service
blocks to savepoints, changing when data actually commits. Bare ``SET LOCAL``
without such a transaction is a verified no-op — PostgreSQL warns "SET LOCAL
can only be used in transaction blocks" and leaves the value unset. This module
therefore writes the GUCs at connection scope with
``set_config(name, value, false)``: a real, effective value that the request
must explicitly clear afterwards.

Every activation writes all three GUCs
--------------------------------------
A connection-scoped value outlives the statement that set it, so a value left
behind by a previous request could otherwise be inherited. ``apply_to`` always
writes ``sigpi.institution_id``, ``sigpi.user_id`` and ``sigpi.bypass_rls``; an
anonymous request records an empty tenant, an empty user and a ``bypass`` of
``'false'``, which the hardened ``NULLIF(...)`` policies turn into a clean deny
rather than a fallback to a stale value. ``sigpi.user_id`` backs the
``own_memberships`` policy, which lets an authenticated user read their own
membership rows without widening tenant isolation.

Driver portability
------------------
``SELECT set_config(%s, %s, false)`` is used instead of ``SET x = %s`` because
``SET`` is parsed by the server and cannot carry a bound parameter (psycopg2
only makes it appear to work by interpolating client-side), whereas
``set_config`` is a regular function call that accepts a bind parameter under
both psycopg2 and psycopg3.

Re-application after a reconnect
--------------------------------
A ``connection_created`` receiver re-applies the active context to any
connection Django opens while a context is active, so a mid-request reconnect
after a dropped connection does not silently lose the tenant scope.
"""

import contextvars
import logging
from contextlib import contextmanager

from django.db.backends.signals import connection_created
from django.dispatch import receiver

logger = logging.getLogger(__name__)

TENANT_GUC = "sigpi.institution_id"
USER_GUC = "sigpi.user_id"
BYPASS_GUC = "sigpi.bypass_rls"

# The active ``(institution_id, user_id, bypass)`` for the current request, or
# ``None`` when no request context is active. A ``ContextVar`` keeps the value
# scoped to the request/thread and reset-safe.
_context: contextvars.ContextVar[tuple | None] = contextvars.ContextVar(
    "sigpi_tenant_context", default=None
)


def get_context() -> tuple | None:
    """Return the active ``(institution_id, user_id, bypass)`` tuple, or ``None``."""
    return _context.get()


def apply_to(connection, institution_id, bypass, user_id=None) -> None:
    """Write all three tenant GUCs on ``connection`` unconditionally.

    A missing institution or user is written as the empty string and ``bypass``
    as the literal ``'true'``/``'false'``, so a previous value can never be
    inherited from a pooled connection. ``user_id`` is a trailing, optional
    parameter so existing callers that only know the institution keep working.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [USER_GUC, "" if user_id is None else str(user_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


def activate(connection, institution_id, bypass, user_id=None) -> None:
    """Store the context and apply it to ``connection``."""
    _context.set((institution_id, user_id, bypass))
    apply_to(connection, institution_id, bypass, user_id)


def clear(connection) -> None:
    """Drop the context and reset all three GUCs to the deny defaults.

    A teardown failure must never mask or replace the request's own outcome,
    but it must never be silent either: it is logged with its traceback so the
    leak stays diagnosable.
    """
    _context.set(None)
    try:
        apply_to(connection, None, False, None)
    except Exception:
        logger.warning("Failed to clear the request tenant context", exc_info=True)


@contextmanager
def tenant_context(connection, institution_id, bypass=False, user_id=None):
    """Activate a tenant context for database work outside an HTTP request.

    Celery tasks run with no request, so no middleware ever writes the RLS
    GUCs the policies read. The institution cannot be discovered from inside
    the task either: reading the row that carries it would require the very
    tenant context the task is trying to establish. The enqueuer therefore
    passes the institution in explicitly, on the request/audit context where
    it is still known, and the task activates it around its own reads.

    Tearing the context down in ``finally`` is mandatory, not cosmetic.
    ``apply_to`` writes the GUCs at connection scope (see the module
    docstring), so a value outlives the statement that set it and would
    otherwise be inherited by whatever runs next on the same pooled worker
    connection — potentially a task for another tenant.

    Reentrant: it restores the enclosing context rather than dropping it. A
    nested use — the OIDC membership sync running inside an authenticated
    request — must not clobber the request's own tenant scope, or the write
    that follows the nested block (for example the login audit event) would run
    without a GUC and be denied by the policies.

    On non-PostgreSQL backends (SQLite in local tests) this is a no-op: RLS
    is a PostgreSQL feature and there are no GUCs to write.
    """
    if connection.vendor != "postgresql":
        yield
        return

    previous = _context.get()
    activate(connection, institution_id, bypass, user_id)
    try:
        yield
    finally:
        if previous is None:
            clear(connection)
        else:
            # Restore the enclosing ``(institution_id, user_id, bypass)``
            # instead of clearing, so the outer context survives the nesting.
            try:
                activate(connection, previous[0], previous[2], previous[1])
            except Exception:
                logger.warning("Failed to restore the enclosing tenant context", exc_info=True)


@receiver(connection_created)
def _reapply_on_new_connection(sender, connection, **kwargs) -> None:
    """Re-apply the active tenant context to a freshly opened connection.

    Does nothing when no request context is active or the vendor is not
    PostgreSQL.
    """
    context = _context.get()
    if context is None:
        return
    if connection.vendor != "postgresql":
        return
    apply_to(connection, context[0], context[2], context[1])
