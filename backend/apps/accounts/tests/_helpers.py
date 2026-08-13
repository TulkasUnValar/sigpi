"""Test helpers for accounts app — cached role lookup to eliminate repeated DB queries."""

from functools import lru_cache

from apps.accounts.models import Role


@lru_cache(maxsize=16)
def get_role(name: str) -> Role:
    """Cached Role lookup.

    Roles are migration-seeded and immutable. Querying them once per test
    suite run eliminates ~1,500 redundant SELECTs.
    """
    return Role.objects.get(name=name)
