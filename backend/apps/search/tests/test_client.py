"""Lazy sync client tests for PR 2 — Indexers + Client (STRICT TDD).

Verifies the acceptance criteria of task 2.2:
- ``get_client()`` is lazy: the SDK Client is constructed on first use,
  not at import time.
- The client is configured from ``MEILISEARCH_URL`` / ``MEILISEARCH_API_KEY``
  Django settings.
- The client is cached: repeated calls return the same instance.

Design reference: meilisearch-module design — File Changes (client.py).
"""

from unittest import mock

from django.conf import settings
from meilisearch_python_sdk import Client

import apps.search.client as search_client


class TestGetClient:
    def test_lazy_and_configured_from_settings(self):
        with mock.patch.object(search_client, "Client") as fake_client_cls:
            search_client._client = None
            first = search_client.get_client()
            second = search_client.get_client()
            assert first is second
            assert fake_client_cls.call_count == 1
            fake_client_cls.assert_called_once_with(
                settings.MEILISEARCH_URL,
                settings.MEILISEARCH_API_KEY,
            )

    def test_returns_real_sync_client_and_caches_it(self):
        search_client._client = None
        client = search_client.get_client()
        assert isinstance(client, Client)
        assert search_client.get_client() is client
