"""
Pytest configuration for SIGPI backend.

Sets PYTEST_RUNNING=true so settings use in-memory SQLite.
"""
import os

# Must be set at module level BEFORE Django settings are imported.
# pytest_configure() hook runs too late — settings already loaded.
os.environ["PYTEST_RUNNING"] = "true"

import pytest


def pytest_configure():
    """Ensure PYTEST_RUNNING is set (belt-and-suspenders)."""
    os.environ["PYTEST_RUNNING"] = "true"


@pytest.fixture(autouse=True)
def _media_root(settings, tmpdir):
    """Ensure MEDIA_ROOT points to a temp directory during tests."""
    settings.MEDIA_ROOT = str(tmpdir.mkdir("media"))
