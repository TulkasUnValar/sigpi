"""
Unit tests for calls permission classes (Phase 3.9).

Covers:
- CanManageCall: director_centro (level <= 3) + institution match.

Strict TDD: this file is written BEFORE permissions.py exists.
Expected failure: ImportError (permissions.py not created yet).
"""

from unittest.mock import MagicMock

from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Test Helpers
# ──────────────────────────────────────────────────────────


def _make_request(
    method="GET",
    authenticated=True,
    is_superuser=False,
    institution_id=None,
    role_level=None,
):
    """Build a mock DRF Request with the given attributes."""
    user = MagicMock()
    user.is_authenticated = authenticated
    user.is_superuser = is_superuser

    membership = None
    if role_level is not None:
        role = MagicMock()
        role.level = role_level
        membership = MagicMock()
        membership.role = role
        membership.institution_id = institution_id

    request = MagicMock(spec=Request)
    request.user = user
    request.method = method
    request.institution_id = institution_id
    request.active_membership = membership

    return request


def _mock_view():
    return MagicMock()


# ──────────────────────────────────────────────────────────
# CanManageCall
# ──────────────────────────────────────────────────────────


class TestCanManageCall:
    """Permission: director_centro (level <= 3) + institution match."""

    def test_admin_bypasses_has_permission(self):
        """Admin (level 2) always passes has_permission."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=2, institution_id="inst-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_director_passes_has_permission(self):
        """Director (level 3) passes has_permission."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=3, institution_id="inst-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_researcher_fails_has_permission(self):
        """Researcher (level 4) fails has_permission."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=4, institution_id="inst-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_unauthenticated_fails_has_permission(self):
        """Unauthenticated fails has_permission."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_director_same_institution_passes_object_permission(self):
        """Director whose institution matches the call's passes."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=3, institution_id="inst-1")

        obj = MagicMock()
        obj.institution_id = "inst-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_director_different_institution_fails(self):
        """Director whose institution does NOT match the call's fails."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=3, institution_id="inst-2")

        obj = MagicMock()
        obj.institution_id = "inst-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_superadmin_bypasses_institution_check(self):
        """Superadmin passes object permission regardless of institution."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(
            method="POST", role_level=1, institution_id="inst-99", is_superuser=True
        )

        obj = MagicMock()
        obj.institution_id = "inst-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_admin_bypasses_object_permission(self):
        """Admin (level 2) passes object permission even if not same institution."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", role_level=2, institution_id="inst-2")

        obj = MagicMock()
        obj.institution_id = "inst-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_unauthenticated_fails_object_permission(self):
        """Unauthenticated user fails object permission."""
        from apps.calls.permissions import CanManageCall

        perm = CanManageCall()
        request = _make_request(method="POST", authenticated=False)

        obj = MagicMock()
        assert perm.has_object_permission(request, _mock_view(), obj) is False


# ──────────────────────────────────────────────────────────
# Permission Matrix
# ──────────────────────────────────────────────────────────


class TestPermissionMatrix:
    """Verify the permission class covers all required roles/actions."""

    def test_permission_importable(self):
        """CanManageCall is importable."""
        from apps.calls import permissions

        assert hasattr(permissions, "CanManageCall")

    def test_is_base_permission_subclass(self):
        """CanManageCall must be a BasePermission subclass."""
        from rest_framework.permissions import BasePermission

        from apps.calls.permissions import CanManageCall

        assert issubclass(CanManageCall, BasePermission)
