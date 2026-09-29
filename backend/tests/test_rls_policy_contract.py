"""Row-level-security policy contracts that must hold for every migration.

This guards a bug class that is invisible on SQLite and fatal on PostgreSQL,
which is the database CI and production actually run on.

The unsafe expression casts the raw ``sigpi.institution_id`` GUC to ``uuid``
with no missing-safe fallback. When the GUC is unset or empty, PostgreSQL
raises instead of simply denying the row — ``unrecognized configuration
parameter`` when it was never set, ``invalid input syntax for type uuid: ""``
when it is empty. Because permissive policies are all evaluated against a
query, a failing cast in ``tenant_isolation`` kills the query outright, so the
``superadmin_bypass`` policy cannot rescue it. SQLite never executes these
policy statements, so the suite looked green while PostgreSQL stayed red.

Both contracts are deliberately whitespace- and line-break-tolerant. An
earlier line-oriented version missed a cast split across two lines inside a
helper dict, which a mutation test proved; matching on a normalized pattern
instead of on lines closes that hole.
"""

import re
from pathlib import Path

# Path is resolved relative to this test file, never hardcoded.
APPS_DIR = Path(__file__).resolve().parents[1] / "apps"

# ``current_setting('sigpi.institution_id')`` with no ``missing_ok`` argument.
# Reading it raises ``unrecognized configuration parameter`` when the GUC was
# never set, which is exactly what the tenant middleware produces today.
UNGUARDED_READ = re.compile(r"current_setting\(\s*'sigpi\.institution_id'\s*\)")

# Any read of the tenant GUC that does pass ``missing_ok``.
GUARDED_READ = re.compile(r"current_setting\(\s*'sigpi\.institution_id'\s*,\s*true\s*\)")

# The safe wrapper. ``NULLIF(<guarded read>, '')`` makes an empty GUC evaluate
# to NULL, so the row is denied without raising.
SAFE_WRAPPER = re.compile(
    r"NULLIF\(\s*current_setting\(\s*'sigpi\.institution_id'\s*,\s*true\s*\)\s*,\s*''\s*\)"
)


def _migration_files():
    """Every migration module under ``backend/apps/*/migrations/``."""
    return sorted(APPS_DIR.glob("*/migrations/*.py"))


def _relative(path):
    return str(path.relative_to(APPS_DIR.parent))


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def _unwrapped_reads(text):
    """Guarded reads of the tenant GUC that no ``NULLIF(..., '')`` wraps."""
    wrapped = [match.span() for match in SAFE_WRAPPER.finditer(text)]
    return [
        match
        for match in GUARDED_READ.finditer(text)
        if not any(start <= match.start() and match.end() <= end for start, end in wrapped)
    ]


def test_no_migration_reads_the_tenant_guc_without_missing_ok():
    """Without ``missing_ok`` a read raises when the GUC was never set."""
    offenders = [
        f"{_relative(path)}:{_line_of(text, match.start())}"
        for path in _migration_files()
        for text in [path.read_text(encoding="utf-8")]
        for match in UNGUARDED_READ.finditer(text)
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
        for match in _unwrapped_reads(text)
    ]
    assert not offenders, (
        "Every read of sigpi.institution_id must be wrapped as "
        "NULLIF(current_setting('sigpi.institution_id', true), '')::uuid so an "
        "unset or empty GUC denies the row without raising. Unwrapped reads: "
        + " | ".join(sorted(offenders))
    )
