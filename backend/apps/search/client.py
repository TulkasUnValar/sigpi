"""Meilisearch sync client access — lazy, settings-configured.

The module-level singleton is built on first use so imports, Django
startup, and tests never touch the network until an index operation
actually needs it. Configuration comes from Django settings:
``MEILISEARCH_URL`` and ``MEILISEARCH_API_KEY`` (config/settings/base.py).
"""

from django.conf import settings
from meilisearch_python_sdk import Client

_client: Client | None = None


def get_client() -> Client:
    """Return the lazily-created, cached sync Meilisearch Client."""
    global _client
    if _client is None:
        _client = Client(settings.MEILISEARCH_URL, settings.MEILISEARCH_API_KEY)
    return _client
