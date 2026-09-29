"""Row-level-security policy contracts that must hold for every migration.

This guards a bug class that is invisible on SQLite and fatal on PostgreSQL,
which is the database CI and production actually run on.

The unsafe tenant expression casts the raw ``sigpi.institution_id`` GUC to
``uuid`` with no missing-safe fallback. When the GUC is unset or empty,
PostgreSQL raises instead of simply denying the row — ``unrecognized
configuration parameter`` when it was never set, ``invalid input syntax for
type uuid: ""`` when it is empty. Because permissive policies are all evaluated
against a query, a failing cast in ``tenant_isolation`` kills the query
outright, so the ``superadmin_bypass`` policy cannot rescue it. SQLite never
executes these policy statements, so the suite looked green while PostgreSQL
stayed red.

The bypass predicate has the same failure mode one step removed.
``COALESCE(current_setting('sigpi.bypass_rls', true), 'false')`` only covers the
GUC being *unset* (``missing_ok`` yields NULL); an *empty* string is not NULL, so
the cast raises ``invalid input syntax for type boolean: ""`` instead of
denying. Wrapping the read in ``NULLIF(..., '')`` turns that empty value into
NULL, which the ``COALESCE``/``NULLIF`` then resolves to false.

These contracts are deliberately whitespace- and line-break-tolerant. An
earlier line-oriented version missed a cast split across two lines inside a
helper dict, which a mutation test proved; matching on a normalized pattern
instead of on lines closes that hole.
"""

import re
from pathlib import Path

# Path is resolved relative to this test file, never hardcoded.
APPS_DIR = Path(__file__).resolve().parents[1] / "apps"

# The two GUCs that RLS policies read. Both are read with ``missing_ok`` so an
# unset GUC is NULL rather than an error, and both need ``NULLIF(..., '')`` so
# an empty GUC denies rather than raises.
TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def _unguarded_read(guc_name):
    """``current_setting('<guc>')`` with no ``missing_ok`` argument.

    Reading it raises ``unrecognized configuration parameter`` when the GUC was
    never set, which is exactly what the tenant middleware produces today.
    """
    return re.compile(rf"current_setting\(\s*'{re.escape(guc_name)}'\s*\)")


def _guarded_read(guc_name):
    """Any read of ``guc_name`` that does pass ``missing_ok``."""
    return re.compile(rf"current_setting\(\s*'{re.escape(guc_name)}'\s*,\s*true\s*\)")


def _safe_wrapper(guc_name):
    """The safe wrapper for ``guc_name``.

    ``NULLIF(<guarded read>, '')`` makes an empty GUC evaluate to NULL, so the
    row is denied without raising.
    """
    return re.compile(
        rf"NULLIF\(\s*current_setting\(\s*'{re.escape(guc_name)}'\s*,\s*true\s*\)\s*,\s*''\s*\)"
    )


def _migration_files():
    """Every migration module under ``backend/apps/*/migrations/``."""
    return sorted(APPS_DIR.glob("*/migrations/*.py"))


def _relative(path):
    return str(path.relative_to(APPS_DIR.parent))


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def _unwrapped_reads(text, guc_name):
    """Guarded reads of ``guc_name`` that no ``NULLIF(..., '')`` wraps."""
    wrapped = [match.span() for match in _safe_wrapper(guc_name).finditer(text)]
    return [
        match
        for match in _guarded_read(guc_name).finditer(text)
        if not any(start <= match.start() and match.end() <= end for start, end in wrapped)
    ]


def test_no_migration_reads_the_tenant_guc_without_missing_ok():
    """Without ``missing_ok`` a read raises when the GUC was never set."""
    offenders = [
        f"{_relative(path)}:{_line_of(text, match.start())}"
        for path in _migration_files()
        for text in [path.read_text(encoding="utf-8")]
        for match in _unguarded_read(TENANT_GUC).finditer(text)
    ]
    assert not offenders, (
        "Every read of the sigpi.institution_id GUC must pass missing_ok, i.e. "
        "current_setting('sigpi.institution_id', true); without it PostgreSQL "
        "raises 'unrecognized configuration parameter' instead of denying the "
        "row: " + ", ".join(sorted(offenders))
    )


def test_every_tenant_guc_read_is_wrapped_in_nullif():
    """``NULLIF(..., '')`` is what makes an empty GUC deny rather than raise."""
    offenders = [
        f"{_relative(path)}:{_line_of(text, match.start())} {match.group(0)!r}"
        for path in _migration_files()
        for text in [path.read_text(encoding="utf-8")]
        for match in _unwrapped_reads(text, TENANT_GUC)
    ]
    assert not offenders, (
        "Every read of sigpi.institution_id must be wrapped as "
        "NULLIF(current_setting('sigpi.institution_id', true), '')::uuid so an "
        "unset or empty GUC denies the row without raising. Unwrapped reads: "
        + " | ".join(sorted(offenders))
    )


def test_every_bypass_guc_read_is_wrapped_in_nullif():
    """``COALESCE(..., 'false')`` covers an unset bypass GUC but not an empty one."""
    offenders = [
        f"{_relative(path)}:{_line_of(text, match.start())} {match.group(0)!r}"
        for path in _migration_files()
        for text in [path.read_text(encoding="utf-8")]
        for match in _unwrapped_reads(text, BYPASS_GUC)
    ]
    assert not offenders, (
        "Every read of sigpi.bypass_rls must be wrapped as "
        "NULLIF(current_setting('sigpi.bypass_rls', true), '')::bool. "
        "COALESCE(current_setting('sigpi.bypass_rls', true), 'false') only "
        "covers the GUC being unset; when it is set to an empty string "
        "PostgreSQL raises 'invalid input syntax for type boolean: \"\"' instead "
        "of denying the row. Unwrapped reads: " + " | ".join(sorted(offenders))
    )
