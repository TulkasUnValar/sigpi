"""
Unit tests for institutions permission classes (Phase 3.1).

Covers:
- IsInstitutionAdminOrReadOnly (write: level≤2, read: authenticated)
- IsCenterDirectorOrReadOnly (write: level≤3, read: authenticated)
- IsSuperAdmin (re-exported from accounts)
- IsSameInstitution (re-exported from accounts)

Strict TDD: this file is written BEFORE permissions.py exists.
Expected failure: ModuleNotFoundError.
"""

from unittest.mock import MagicMock

import pytest
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
    center_ids=None,
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
        if center_ids:
            membership.centers.values_list.return_value = [(cid,) for cid in center_ids]
        else:
            membership.centers.values_list.return_value = []

    request = MagicMock(spec=Request)
    request.user = user
    request.method = method
    request.institution_id = institution_id
    request.active_membership = membership

    return request


def _mock_view():
    return MagicMock()


# ──────────────────────────────────────────────────────────
# IsInstitutionAdminOrReadOnly
# ──────────────────────────────────────────────────────────


class TestIsInstitutionAdminOrReadOnly:
    """Tests for the IsInstitutionAdminOrReadOnly permission class."""

    def test_safe_methods_allow_authenticated(self):
        """GET/HEAD/OPTIONS must be allowed for any authenticated user."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="GET", role_level=7)  # auditor
        assert perm.has_permission(request, _mock_view()) is True

    def test_safe_methods_deny_unauthenticated(self):
        """GET must be denied for unauthenticated users."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="GET", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_allowed_for_admin(self):
        """POST/PATCH/DELETE must be allowed for institution admin (level≤2)."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_allowed_for_superadmin(self):
        """POST must be allowed for superadmin (level 1)."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="DELETE", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_denied_for_researcher(self):
        """POST must be denied for researcher (level 4)."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_denied_no_membership(self):
        """POST must be denied when no active membership."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method="POST", role_level=None, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False


# ──────────────────────────────────────────────────────────
# IsCenterDirectorOrReadOnly
# ──────────────────────────────────────────────────────────


class TestIsCenterDirectorOrReadOnly:
    """Tests for the IsCenterDirectorOrReadOnly permission class."""

    def test_safe_methods_allow_authenticated(self):
        """GET must be allowed for any authenticated user."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="GET", role_level=7)
        assert perm.has_permission(request, _mock_view()) is True

    def test_safe_methods_deny_unauthenticated(self):
        """GET must be denied for unauthenticated."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="GET", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_allowed_for_director(self):
        """POST must be allowed for center director (level≤3)."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="POST", role_level=3, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_allowed_for_admin(self):
        """POST must be allowed for institution admin (level 2 ≤ 3)."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_denied_for_researcher(self):
        """POST must be denied for researcher (level 4 > 3)."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_denied_no_membership(self):
        """POST denied without membership."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method="DELETE", role_level=None, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False


# ──────────────────────────────────────────────────────────
# Re-exports from accounts.permissions
# ──────────────────────────────────────────────────────────


class TestReExportedPermissions:
    """IsSuperAdmin and IsSameInstitution are re-exported from accounts."""

    def test_is_superadmin_available(self):
        """IsSuperAdmin must be importable from institutions.permissions."""
        from apps.institutions.permissions import IsSuperAdmin

        assert IsSuperAdmin is not None

    def test_is_same_institution_available(self):
        """IsSameInstitution must be importable from institutions.permissions."""
        from apps.institutions.permissions import IsSameInstitution

        assert IsSameInstitution is not None

    def test_is_superadmin_works(self):
        """IsSuperAdmin from institutions must behave like accounts version."""
        from apps.institutions.permissions import IsSuperAdmin

        perm = IsSuperAdmin()
        request = _make_request(method="POST", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

        request2 = _make_request(method="POST", role_level=3, institution_id="uuid-1")
        assert perm.has_permission(request2, _mock_view()) is False

    def test_is_same_institution_works(self):
        """IsSameInstitution must check institution_id on object."""
        from apps.institutions.permissions import IsSameInstitution

        perm = IsSameInstitution()
        request = _make_request(method="GET", institution_id="uuid-aaa", role_level=3)

        obj_matching = MagicMock()
        obj_matching.institution_id = "uuid-aaa"
        assert perm.has_object_permission(request, _mock_view(), obj_matching) is True

        obj_different = MagicMock()
        obj_different.institution_id = "uuid-bbb"
        assert perm.has_object_permission(request, _mock_view(), obj_different) is False


# ──────────────────────────────────────────────────────────
# SAFE_METHODS completeness
# ──────────────────────────────────────────────────────────


class TestSafeMethodsCoverage:
    """Both OrReadOnly classes must allow all SAFE_METHODS."""

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_admin_read_only_allows_all_safe(self, method):
        """IsInstitutionAdminOrReadOnly allows all SAFE_METHODS."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        request = _make_request(method=method, role_level=7)
        assert perm.has_permission(request, _mock_view()) is True

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_director_read_only_allows_all_safe(self, method):
        """IsCenterDirectorOrReadOnly allows all SAFE_METHODS."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        request = _make_request(method=method, role_level=7)
        assert perm.has_permission(request, _mock_view()) is True

    @pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
    def test_admin_read_only_restricts_writes(self, method):
        """IsInstitutionAdminOrReadOnly restricts write methods by role."""
        from apps.institutions.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        # researcher (level 4) can't write
        request = _make_request(method=method, role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    @pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
    def test_director_read_only_restricts_writes(self, method):
        """IsCenterDirectorOrReadOnly restricts write methods by role."""
        from apps.institutions.permissions import IsCenterDirectorOrReadOnly

        perm = IsCenterDirectorOrReadOnly()
        # researcher (level 4) can't write
        request = _make_request(method=method, role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False
