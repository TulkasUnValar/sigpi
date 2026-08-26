"""Dependency tests for PR 1 — Foundation (STRICT TDD).

Verifies:
- backend/pyproject.toml declares the pinned sync meilisearch-python-sdk
- the sync Client is importable from the installed package

Design reference: meilisearch-module design — File Changes (backend/pyproject.toml).
"""

import tomllib
from pathlib import Path

from django.conf import settings


def _backend_pyproject() -> dict:
    pyproject_path = Path(settings.BASE_DIR) / "pyproject.toml"
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


class TestPyprojectDependency:
    def test_declares_meilisearch_sdk(self):
        deps = _backend_pyproject()["project"]["dependencies"]
        assert any(dep.startswith("meilisearch-python-sdk") for dep in deps)

    def test_meilisearch_sdk_is_bounded_pin(self):
        deps = _backend_pyproject()["project"]["dependencies"]
        pinned = [dep for dep in deps if dep.startswith("meilisearch-python-sdk")]
        assert pinned, "meilisearch-python-sdk must be declared"
        assert "," in pinned[0], "dependency must use a bounded pin (e.g. >=7.0,<8.0)"

    def test_sync_client_importable(self):
        from meilisearch_python_sdk import Client

        assert Client is not None
