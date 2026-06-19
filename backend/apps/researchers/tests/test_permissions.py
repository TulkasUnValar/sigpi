"""
Unit tests for researchers permission classes (Phase 3.4).

Covers:
- IsResearcherOrReadOnly: has_permission (write: level≤4, read: authenticated)
- IsResearcherOrReadOnly: has_object_permission (owner or level≤2 for write, read allows all)
- Role-based access matrix (superadmin, admin, director, researcher, authenticated)
- Self-profile edit allowed for owning researcher
- Cross-institution denial via re-exported IsSameInstitution
- Re-exported IsInstitutionAdminOrReadOnly and IsSameInstitution from accounts

Strict TDD: this file is written BEFORE permissions.py exists.
Expected failure: ModuleNotFoundError (permissions.py not created yet).
"""
from unittest.mock import MagicMock

import pytest
from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Test Helpers (matching institutions test_permissions.py pattern)
# ──────────────────────────────────────────────────────────


class _FakeObj:
    """Minimal object without MagicMock auto-creation for attribute tests.

    MagicMock auto-creates attributes on access, which breaks duck-typing
    checks like getattr(obj, 'researcher', None). This plain class does not.
    """
    pass


def _make_request(
    method="GET",
    authenticated=True,
    is_superuser=False,
    institution_id=None,
    role_level=None,
    center_ids=None,
):
    """Build a mock DRF Request with the given attributes.

    Matches the institutions test_permissions.py _make_request helper.
    """
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
# IsResearcherOrReadOnly — has_permission (view-level)
# ──────────────────────────────────────────────────────────


class TestIsResearcherOrReadOnlyHasPermission:
    """View-level permission checks for IsResearcherOrReadOnly."""

    def test_safe_methods_allow_authenticated(self):
        """GET/HEAD/OPTIONS must be allowed for any authenticated user."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        # Auditor (level 7) — lowest role, but authenticated
        request = _make_request(method="GET", role_level=7)
        assert perm.has_permission(request, _mock_view()) is True

    def test_safe_methods_deny_unauthenticated(self):
        """GET must be denied for unauthenticated users."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="GET", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_allowed_for_researcher(self):
        """POST must be allowed for researcher (level 4)."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_allowed_for_superadmin(self):
        """POST must be allowed for superadmin (level 1)."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="DELETE", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_allowed_for_admin(self):
        """POST must be allowed for institution admin (level 2 ≤ 4)."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_allowed_for_director(self):
        """POST must be allowed for center director (level 3 ≤ 4)."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="POST", role_level=3, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_write_denied_no_membership(self):
        """POST must be denied when no active membership."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="POST", role_level=None, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_write_denied_unauthenticated(self):
        """POST must be denied for unauthenticated users."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False


# ──────────────────────────────────────────────────────────
# IsResearcherOrReadOnly — has_object_permission (object-level)
# ──────────────────────────────────────────────────────────


class TestIsResearcherOrReadOnlyHasObjectPermission:
    """Object-level permission checks for IsResearcherOrReadOnly."""

    def test_safe_methods_allow_all_authenticated(self):
        """GET/HEAD/OPTIONS must allow any authenticated user at object level."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="GET", role_level=7)
        obj = object()  # plain object won't auto-create attributes
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_write_owner_allowed(self):
        """POST/PATCH must be allowed when user is the owning researcher."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 42

        # Object is a Researcher where user_id matches
        obj = _FakeObj()
        obj.user_id = 42
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_write_non_owner_denied(self):
        """POST/PATCH must be denied for researcher who is not the owner."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 42

        # Object is a different researcher's profile
        obj = _FakeObj()
        obj.user_id = 99
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_write_admin_overrides_ownership(self):
        """Admin (level 2) can write even if not the owning researcher."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=2, institution_id="uuid-1")
        request.user.id = 42

        # Admin is not the owner, but role level ≤ 2 allows write
        obj = _FakeObj()
        obj.user_id = 99
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_write_superadmin_overrides_ownership(self):
        """Superadmin (level 1) can write any researcher profile."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="DELETE", role_level=1, institution_id="uuid-1")
        request.user.id = 42

        obj = _FakeObj()
        obj.user_id = 99
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_write_director_denied_for_non_self(self):
        """Center director (level 3) cannot write another researcher's profile."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=3, institution_id="uuid-1")
        request.user.id = 42

        obj = _FakeObj()
        obj.user_id = 99
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_write_director_own_profile_allowed(self):
        """Center director can write their own profile."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=3, institution_id="uuid-1")
        request.user.id = 77

        obj = _FakeObj()
        obj.user_id = 77
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_nested_object_uses_researcher_attribute(self):
        """For nested objects (affiliations, profiles, attachments),
        has_object_permission extracts researcher from obj.researcher."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 55

        # Nested object like ResearcherAffiliation — has .researcher FK
        nested_obj = MagicMock()
        nested_obj.researcher = MagicMock()
        nested_obj.researcher.user_id = 55
        assert perm.has_object_permission(request, _mock_view(), nested_obj) is True


# ──────────────────────────────────────────────────────────
# Re-exports from accounts.permissions
# ──────────────────────────────────────────────────────────


class TestReExportedPermissions:
    """IsInstitutionAdminOrReadOnly, IsSameInstitution should be re-exported."""

    def test_is_institution_admin_available(self):
        """IsInstitutionAdminOrReadOnly must be importable from researchers.permissions."""
        from apps.researchers.permissions import IsInstitutionAdminOrReadOnly

        assert IsInstitutionAdminOrReadOnly is not None

    def test_is_same_institution_available(self):
        """IsSameInstitution must be importable from researchers.permissions."""
        from apps.researchers.permissions import IsSameInstitution

        assert IsSameInstitution is not None

    def test_is_institution_admin_works(self):
        """Re-exported IsInstitutionAdminOrReadOnly must behave correctly."""
        from apps.researchers.permissions import IsInstitutionAdminOrReadOnly

        perm = IsInstitutionAdminOrReadOnly()
        # Admin (level 2) can write
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True
        # Researcher (level 4) cannot write
        request2 = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request2, _mock_view()) is False

    def test_is_same_institution_works(self):
        """Re-exported IsSameInstitution must check institution_id on object."""
        from apps.researchers.permissions import IsSameInstitution

        perm = IsSameInstitution()
        request = _make_request(method="GET", institution_id="uuid-aaa", role_level=3)

        obj_matching = _FakeObj()
        obj_matching.institution_id = "uuid-aaa"
        assert perm.has_object_permission(request, _mock_view(), obj_matching) is True

        obj_different = _FakeObj()
        obj_different.institution_id = "uuid-bbb"
        assert perm.has_object_permission(request, _mock_view(), obj_different) is False


# ──────────────────────────────────────────────────────────
# SAFE_METHODS completeness
# ──────────────────────────────────────────────────────────


class TestSafeMethodsCoverage:
    """IsResearcherOrReadOnly must handle all SAFE_METHODS."""

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_all_safe_methods_allowed(self, method):
        """All SAFE_METHODS must be allowed for any authenticated user."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method=method, role_level=7)
        assert perm.has_permission(request, _mock_view()) is True

    @pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
    def test_write_methods_restricted(self, method):
        """Write methods must check role level."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        # Without a role level, writes fail
        request = _make_request(method=method, role_level=None, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    @pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
    def test_write_methods_allowed_for_researcher(self, method):
        """Write methods must be allowed for researcher level (4)."""
        from apps.researchers.permissions import IsResearcherOrReadOnly

        perm = IsResearcherOrReadOnly()
        request = _make_request(method=method, role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True
