"""
Request-scoped audit context for the audit module.

The TenantMiddleware populates the request audit context (actor, IP and
institution). Signals and services read this context when writing
AuditEvents, so ordinary CRUD captures the acting user even though the
signal layer itself has no access to the current HttpRequest.

A ``ContextVar`` is used so the value is scoped to the current request
(context/coroutine) and is reset in the middleware ``finally`` block.
Explicit emitter kwargs always override the context-derived values.

Design reference: openspec/changes/audit/design.md
"""

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class AuditContext:
    """Actor/IP/institution captured for a single request."""

    user: Any = None
    ip_address: str | None = None
    institution_id: Any = None


_audit_context_var: contextvars.ContextVar[AuditContext] = contextvars.ContextVar(
    "sigpi_audit_context", default=AuditContext()
)


def get_audit_context() -> AuditContext:
    """Return the audit context active in the current request scope."""
    return _audit_context_var.get()


def set_audit_context(
    user=None,
    ip_address: str | None = None,
    institution_id=None,
) -> AuditContext:
    """Set and return the audit context for the current request scope."""
    ctx = AuditContext(user=user, ip_address=ip_address, institution_id=institution_id)
    _audit_context_var.set(ctx)
    return ctx


def reset_audit_context() -> None:
    """Reset the audit context (called from middleware ``finally``)."""
    _audit_context_var.set(AuditContext())


@contextmanager
def audit_context(user=None, ip_address: str | None = None, institution_id=None):
    """Context manager that sets a scoped audit context and resets it after.

    Primarily used in tests and by the middleware to wrap request handling.
    """
    token = _audit_context_var.set(
        AuditContext(user=user, ip_address=ip_address, institution_id=institution_id)
    )
    try:
        yield
    finally:
        _audit_context_var.reset(token)
