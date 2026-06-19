"""
Celery task tests for Keycloak role sync — STRICT TDD.

Tests define the expected behavior of:
- sync_keycloak_roles: paginate Keycloak Admin API, map roles → Django Groups
- Idempotency: running twice doesn't create duplicates
- Error handling: logs failures, continues with next batch
- Audit events: ROLE_CHANGE events emitted on role changes

Spec references: FR-008
Design reference: openspec/changes/auth/design.md — Role Sync Flow
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import Role, User
from apps.institutions.models import Institution

# ── RED: These imports WILL fail until tasks.py is created ──
from apps.accounts.tasks import sync_keycloak_roles


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _make_kc_user(kc_uuid: str, roles: list[str]) -> dict:
    """Build a mock Keycloak user representation from Admin API."""
    return {
        "id": kc_uuid,
        "username": f"user_{kc_uuid[:8]}",
        "email": f"{kc_uuid[:8]}@example.com",
        "realmRoles": roles,
    }


def _ensure_django_user(kc_user: dict) -> User:
    """Create a Django User that matches a mocked Keycloak user."""
    return User.objects.create_user(
        email=kc_user["email"],
        auth_source="keycloak",
        keycloak_uuid=kc_user["id"],
        password="pass",
    )


# ──────────────────────────────────────────────────────────
# Test sync_keycloak_roles
# ──────────────────────────────────────────────────────────


class TestSyncKeycloakRoles:
    """Tests for the Celery sync task."""

    @patch("apps.accounts.tasks._fetch_keycloak_users")
    @patch("apps.accounts.tasks._sync_user_groups")
    def test_sync_task_calls_fetch_and_sync(self, mock_sync, mock_fetch, db):
        """Task fetches KC users and syncs each one's groups."""
        u1 = _make_kc_user(str(uuid.uuid4()), ["sigpi_researcher"])
        u2 = _make_kc_user(str(uuid.uuid4()), ["sigpi_admin"])
        _ensure_django_user(u1)
        _ensure_django_user(u2)
        mock_fetch.side_effect = [[u1, u2], []]

        result = sync_keycloak_roles()

        mock_fetch.assert_called_once()
        assert mock_sync.call_count == 2
        assert result["synced"] == 2

    @patch("apps.accounts.tasks._fetch_keycloak_users")
    def test_sync_task_handles_empty_user_list(self, mock_fetch, db):
        """Task handles empty Keycloak user list gracefully."""
        mock_fetch.return_value = []

        result = sync_keycloak_roles()

        assert result["synced"] == 0
        assert "error" not in result

    @patch("apps.accounts.tasks._fetch_keycloak_users")
    @patch("apps.accounts.tasks._sync_user_groups")
    def test_sync_task_idempotent(self, mock_sync, mock_fetch, db):
        """Running sync twice doesn't create duplicate groups or errors."""
        u1 = _make_kc_user(str(uuid.uuid4()), ["sigpi_researcher"])
        _ensure_django_user(u1)
        mock_fetch.side_effect = [[u1], []]
        mock_sync.return_value = {"added": [], "removed": [], "changed": False}

        sync_keycloak_roles()
        sync_keycloak_roles()

        assert mock_fetch.call_count == 2
        assert mock_sync.call_count == 2

    @patch("apps.accounts.tasks._fetch_keycloak_users")
    def test_sync_task_handles_fetch_error(self, mock_fetch, db):
        """Task gracefully handles errors from Keycloak API."""
        mock_fetch.side_effect = Exception("Connection refused")

        result = sync_keycloak_roles()

        assert "error" in result
        assert result["synced"] == 0

    @patch("apps.accounts.tasks._fetch_keycloak_users")
    @patch("apps.accounts.tasks._sync_user_groups")
    def test_sync_task_continues_after_individual_user_error(
        self, mock_sync, mock_fetch, db
    ):
        """If one user fails, the task continues with the next user."""
        u1 = _make_kc_user(str(uuid.uuid4()), ["sigpi_researcher"])
        u2 = _make_kc_user(str(uuid.uuid4()), ["sigpi_admin"])
        _ensure_django_user(u1)
        _ensure_django_user(u2)
        mock_fetch.side_effect = [[u1, u2], []]
        mock_sync.side_effect = [Exception("User not found"), {"added": [], "removed": [], "changed": False}]

        result = sync_keycloak_roles()

        assert result["synced"] >= 1  # At least one succeeded
        assert result.get("errors", 0) > 0

    @patch("apps.accounts.tasks._sync_user_groups")
    @patch("apps.accounts.tasks._fetch_keycloak_users")
    def test_sync_task_paginates(self, mock_fetch, mock_sync, db):
        """Task paginates through Keycloak users (cursor-based pagination)."""
        # Simulate pagination: first call returns 100 users, second returns 50
        users_page1 = [_make_kc_user(str(uuid.uuid4()), ["sigpi_researcher"]) for i in range(100)]
        users_page2 = [_make_kc_user(str(uuid.uuid4()), ["sigpi_admin"]) for i in range(100, 150)]
        for u in users_page1 + users_page2:
            _ensure_django_user(u)
        mock_fetch.side_effect = [users_page1, users_page2, []]
        mock_sync.return_value = {"added": [], "removed": [], "changed": False}

        result = sync_keycloak_roles()

        assert mock_fetch.call_count == 3
        assert result["synced"] == 150


class TestSyncUserGroups:
    """Tests for the _sync_user_groups helper function."""

    def test_adds_new_groups(self, db):
        """New Keycloak roles are added as Django Groups."""
        from apps.accounts.tasks import _sync_user_groups

        user = User.objects.create_user(
            email="u@test.com",
            auth_source="keycloak",
            keycloak_uuid=uuid.uuid4(),
            password="pass",
        )

        result = _sync_user_groups(user, ["sigpi_researcher", "sigpi_admin"])

        assert "sigpi_researcher" in result["added"]
        assert "sigpi_admin" in result["added"]
        assert Group.objects.filter(name="sigpi_researcher").exists()
        assert Group.objects.filter(name="sigpi_admin").exists()
        assert user.groups.filter(name="sigpi_researcher").exists()

    def test_removes_stale_groups(self, db):
        """Groups no longer in Keycloak are removed from the user."""
        from apps.accounts.tasks import _sync_user_groups

        user = User.objects.create_user(
            email="u@test.com",
            auth_source="keycloak",
            keycloak_uuid=uuid.uuid4(),
            password="pass",
        )
        # Pre-add groups
        g1, _ = Group.objects.get_or_create(name="sigpi_researcher")
        g2, _ = Group.objects.get_or_create(name="old_role")
        user.groups.add(g1, g2)

        # Sync with only researcher role
        result = _sync_user_groups(user, ["sigpi_researcher"])

        assert "old_role" in result["removed"]
        assert not user.groups.filter(name="old_role").exists()
        assert user.groups.filter(name="sigpi_researcher").exists()

    def test_no_change_returns_empty_diff(self, db):
        """When groups match, no changes are made."""
        from apps.accounts.tasks import _sync_user_groups

        user = User.objects.create_user(
            email="u@test.com",
            auth_source="keycloak",
            keycloak_uuid=uuid.uuid4(),
            password="pass",
        )
        g1, _ = Group.objects.get_or_create(name="sigpi_researcher")
        user.groups.add(g1)

        result = _sync_user_groups(user, ["sigpi_researcher"])

        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] is False

    def test_detects_role_change_for_audit(self, db):
        """When role changes, the result indicates a change for audit."""
        from apps.accounts.tasks import _sync_user_groups

        user = User.objects.create_user(
            email="u@test.com",
            auth_source="keycloak",
            keycloak_uuid=uuid.uuid4(),
            password="pass",
        )
        g1, _ = Group.objects.get_or_create(name="sigpi_auditor")
        user.groups.add(g1)

        result = _sync_user_groups(user, ["sigpi_admin"])

        assert result["changed"] is True
        assert "sigpi_auditor" in result["removed"]
        assert "sigpi_admin" in result["added"]
