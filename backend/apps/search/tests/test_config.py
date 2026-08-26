"""Configuration and scaffold tests for PR 1 — Foundation (STRICT TDD).

Tests verify:
- apps.search is registered in LOCAL_APPS / INSTALLED_APPS
- apps.search.apps.SearchConfig is loaded by Django
- MEILISEARCH_URL / MEILISEARCH_API_KEY load from env with dev defaults
- Django system check passes once the app is wired

Design reference: meilisearch-module design — File Changes (backend/config/settings/base.py).
"""

import importlib
import os
from unittest import mock

from django.apps import apps as django_apps
from django.conf import settings
from django.core.management import call_command

import config.settings.base as base_settings


class TestSearchAppRegistration:
    def test_search_app_registered_and_check_passes(self):
        assert "apps.search" in settings.INSTALLED_APPS
        call_command("check")

    def test_search_app_config_loaded(self):
        config = django_apps.get_app_config("search")
        assert config.name == "apps.search"


class TestMeilisearchSettings:
    def test_url_defaults_to_localhost(self):
        assert settings.MEILISEARCH_URL == "http://localhost:7700"

    def test_api_key_defaults_to_master_key(self):
        assert settings.MEILISEARCH_API_KEY == "masterKey"

    def test_url_reads_from_env(self):
        with mock.patch.dict(
            os.environ, {"MEILISEARCH_URL": "http://meili.internal:7700"}, clear=False
        ):
            importlib.reload(base_settings)
            try:
                assert base_settings.MEILISEARCH_URL == "http://meili.internal:7700"
            finally:
                importlib.reload(base_settings)

    def test_api_key_reads_from_env(self):
        with mock.patch.dict(os.environ, {"MEILISEARCH_API_KEY": "env-master-secret"}, clear=False):
            importlib.reload(base_settings)
            try:
                assert base_settings.MEILISEARCH_API_KEY == "env-master-secret"
            finally:
                importlib.reload(base_settings)
