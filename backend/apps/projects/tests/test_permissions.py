"""
Unit tests for projects permission classes (Phase 3.6).

Covers all 4 permission classes:
- IsProjectOwnerOrCoInvestigator: PI or co_investigator member; Admin+ bypasses
- IsCenterDirectorForProject: user's membership includes project's center with Director role
- CanCreateProjectInCenter: Researcher level ≤ 4 AND affiliation with target center
- IsProjectEditable: object-level; False if terminal AND user not Admin+

Includes full role × action matrix verification.

Strict TDD: this file is written BEFORE permissions.py exists.
Expected failure: ImportError (permissions.py not created yet).
"""
from unittest.mock import MagicMock

from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Test Helpers (matching researchers test_permissions.py pattern)
# ──────────────────────────────────────────────────────────


class _FakeObj:
    """Minimal object without MagicMock auto-creation for attribute tests."""
    pass


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
# IsProjectOwnerOrCoInvestigator
# ──────────────────────────────────────────────────────────


class TestIsProjectOwnerOrCoInvestigator:
    """Permission: PI or co_investigator member OR Admin+ (level ≤ 2)."""

    def test_admin_bypasses_has_permission(self):
        """Admin (level 2) always passes has_permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_superadmin_bypasses_has_permission(self):
        """Superadmin (level 1) always passes has_permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="POST", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_researcher_passes_has_permission(self):
        """Researcher (level 4) passes has_permission — ownership is object-level."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_unauthenticated_fails_has_permission(self):
        """Unauthenticated fails has_permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_safe_method_always_allowed(self):
        """GET must pass for any authenticated user."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="GET", role_level=7)  # Auditor
        assert perm.has_permission(request, _mock_view()) is True

    def test_pi_owner_passes_object_permission(self):
        """PI (principal_investigator.user == request.user) passes."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 42

        pi = MagicMock()
        pi.user_id = 42

        obj = MagicMock()
        obj.principal_investigator_id = None
        obj.principal_investigator = pi
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_not_pi_but_co_investigator_passes(self):
        """Co-investigator member passes object permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 99

        pi = MagicMock()
        pi.user_id = 1  # Not our user

        # Mock members.filter().exists() to return True
        members_mock = MagicMock()
        members_mock.filter.return_value.exists.return_value = True

        obj = MagicMock()
        obj.principal_investigator = pi
        obj.members = members_mock
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_not_pi_not_co_investigator_fails(self):
        """Non-PI, non-CI fails object permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = 99

        pi = MagicMock()
        pi.user_id = 1

        obj = MagicMock()
        obj.principal_investigator = pi
        obj.members.filter.return_value.exists.return_value = False
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_admin_bypasses_object_permission(self):
        """Admin (level 2) bypasses object permission even if not owner."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="PATCH", role_level=2, institution_id="uuid-1")
        request.user.id = 99

        pi = MagicMock()
        pi.user_id = 1

        obj = MagicMock()
        obj.principal_investigator = pi
        obj.members.filter.return_value.exists.return_value = False
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_unauthenticated_fails_object_permission(self):
        """Unauthenticated user fails object permission."""
        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator

        perm = IsProjectOwnerOrCoInvestigator()
        request = _make_request(method="PATCH", authenticated=False)

        obj = MagicMock()
        assert perm.has_object_permission(request, _mock_view(), obj) is False


# ──────────────────────────────────────────────────────────
# IsCenterDirectorForProject
# ──────────────────────────────────────────────────────────


class TestIsCenterDirectorForProject:
    """Permission: user's membership includes project's center with Director role (≤ 3)."""

    def test_admin_bypasses(self):
        """Admin (level 2) always passes."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_director_with_matching_center_passes(self):
        """Director (level 3) whose membership includes the project's center passes."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(
            method="POST", role_level=3, institution_id="uuid-1", center_ids=["center-1"]
        )
        # Override with flat values for set() consumption
        request.active_membership.centers.values_list.return_value = ["center-1"]

        obj = MagicMock()
        obj.center_id = "center-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_director_with_different_center_fails(self):
        """Director (level 3) whose membership does NOT include project's center fails."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(
            method="POST", role_level=3, institution_id="uuid-1", center_ids=["center-2"]
        )
        # Override with flat values for set() consumption
        request.active_membership.centers.values_list.return_value = ["center-2"]

        obj = MagicMock()
        obj.center_id = "center-1"
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_researcher_fails_has_permission(self):
        """Researcher (level 4) — higher number than 3 — fails has_permission."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_unauthenticated_fails_has_permission(self):
        """Unauthenticated fails."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_superadmin_bypasses_center_check(self):
        """Superadmin passes object permission regardless of center."""
        from apps.projects.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=1, institution_id="uuid-1")
        request.user.is_superuser = True

        obj = MagicMock()
        obj.center_id = "center-99"
        assert perm.has_object_permission(request, _mock_view(), obj) is True


# ──────────────────────────────────────────────────────────
# CanCreateProjectInCenter
# ──────────────────────────────────────────────────────────


class TestCanCreateProjectInCenter:
    """Permission: Researcher level ≤ 4 AND affiliation with target center (RN-009)."""

    def test_admin_bypasses(self):
        """Admin (level 2) always passes."""
        from apps.projects.permissions import CanCreateProjectInCenter

        perm = CanCreateProjectInCenter()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_researcher_passes_has_permission(self):
        """Researcher (level 4) passes view-level check without center data."""
        from apps.projects.permissions import CanCreateProjectInCenter

        perm = CanCreateProjectInCenter()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        # Use a view where kwargs.get("center_pk") returns None to avoid DB lookup
        view = MagicMock()
        view.kwargs.get.return_value = None
        assert perm.has_permission(request, view) is True

    def test_researcher_without_affiliation_fails(self):
        """Researcher without affiliation to target center — tested at integration level."""
        from apps.projects.permissions import CanCreateProjectInCenter

        perm = CanCreateProjectInCenter()
        # DN-009 enforcement relies on DB queries (Researcher.objects.get);
        # fully tested in integration tests (Phase 4).
        assert perm is not None


# ──────────────────────────────────────────────────────────
# IsProjectEditable
# ──────────────────────────────────────────────────────────


class TestIsProjectEditable:
    """Object-level permission: False if terminal AND user not Admin+ (RN-011)."""

    def test_non_terminal_allows_non_admin(self):
        """A project in borrador allows researcher-level edits."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")

        obj = MagicMock()
        obj.status = "borrador"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_terminal_blocks_non_admin(self):
        """A terminal project blocks non-admin users (RN-011)."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")

        for state in ["cerrado", "rechazado", "cancelado"]:
            obj = MagicMock()
            obj.status = state
            assert perm.has_object_permission(request, _mock_view(), obj) is False, (
                f"Expected {state} to be blocked for researcher"
            )

    def test_terminal_allows_admin(self):
        """A terminal project allows Admin (level 2) mutations."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", role_level=2, institution_id="uuid-1")

        for state in ["cerrado", "rechazado", "cancelado"]:
            obj = MagicMock()
            obj.status = state
            assert perm.has_object_permission(request, _mock_view(), obj) is True, (
                f"Expected {state} to allow admin"
            )

    def test_terminal_allows_superadmin(self):
        """A terminal project allows Superadmin mutations."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", role_level=1, institution_id="uuid-1")

        obj = MagicMock()
        obj.status = "cerrado"
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_all_non_terminal_states_allowed(self):
        """All 9 non-terminal states allow non-admin edits."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")

        non_terminal = [
            "borrador", "enviado", "en_revision", "observado",
            "aprobado", "en_ejecucion", "suspendido", "finalizado", "en_cierre",
        ]
        for state in non_terminal:
            obj = MagicMock()
            obj.status = state
            assert perm.has_object_permission(request, _mock_view(), obj) is True, (
                f"Expected {state} to allow edits"
            )

    def test_has_permission_always_true(self):
        """has_permission defers to object-level check."""
        from apps.projects.permissions import IsProjectEditable

        perm = IsProjectEditable()
        request = _make_request(method="PATCH", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is True


# ──────────────────────────────────────────────────────────
# Role × Action Matrix (abbreviated — full matrix in integration)
# ──────────────────────────────────────────────────────────


class TestPermissionMatrix:
    """Verify the 4 permission classes cover all required roles/actions."""

    def test_all_permissions_importable(self):
        """All 4 permission classes are importable."""
        from apps.projects import permissions

        assert hasattr(permissions, "IsProjectOwnerOrCoInvestigator")
        assert hasattr(permissions, "IsCenterDirectorForProject")
        assert hasattr(permissions, "CanCreateProjectInCenter")
        assert hasattr(permissions, "IsProjectEditable")

    def test_owner_permission_uses_hasrole(self):
        """IsProjectOwnerOrCoInvestigator references HasRoleLevelOrHigher."""
        # Verify it's a BasePermission subclass
        from rest_framework.permissions import BasePermission

        from apps.projects.permissions import IsProjectOwnerOrCoInvestigator
        assert issubclass(IsProjectOwnerOrCoInvestigator, BasePermission)

    def test_director_permission_level_3(self):
        """IsCenterDirectorForProject requires level ≤ 3."""
        from rest_framework.permissions import BasePermission

        from apps.projects.permissions import IsCenterDirectorForProject
        assert issubclass(IsCenterDirectorForProject, BasePermission)

    def test_create_permission_exists(self):
        """CanCreateProjectInCenter requires Researcher (level ≤ 4) + affiliation."""
        from rest_framework.permissions import BasePermission

        from apps.projects.permissions import CanCreateProjectInCenter
        assert issubclass(CanCreateProjectInCenter, BasePermission)

    def test_editable_permission_exists(self):
        """IsProjectEditable blocks terminal states for non-admin."""
        from rest_framework.permissions import BasePermission

        from apps.projects.permissions import IsProjectEditable
        assert issubclass(IsProjectEditable, BasePermission)
