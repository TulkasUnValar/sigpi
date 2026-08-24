"""
Permission tests for the budgets module — STRICT TDD (RED phase).

Covers:
- CanManageBudget: role level ≤3 mutate; researcher (level 4) denied;
  director center membership on object permission; Admin+/superadmin bypass.
- CanAuthorizeExecution: role level ≤3 for over-execution authorization.
- IsSameInstitution (re-export from accounts): tenant object scoping.

Test pattern: MagicMock-based request construction (matches
progress/tests/test_permissions.py and project_workflow).

Spec reference: openspec/changes/budgets/specs/budgets/spec.md — Security
Design reference: openspec/changes/budgets/design.md — API and Permissions
"""

from unittest.mock import MagicMock

from rest_framework.request import Request


class _FakeObj:
    pass


def _make_request(
    method="GET",
    authenticated=True,
    is_superuser=False,
    institution_id=None,
    role_level=None,
    center_ids=None,
):
    user = MagicMock()
    user.is_authenticated = authenticated
    user.is_superuser = is_superuser

    membership = None
    if role_level is not None:
        role = MagicMock()
        role.level = role_level
        membership = MagicMock()
        membership.role = role
        membership.centers.values_list.return_value = list(center_ids or [])

    request = MagicMock(spec=Request)
    request.user = user
    request.method = method
    request.institution_id = institution_id
    request.active_membership = membership

    return request


def _mock_view():
    return MagicMock()


# ════════════════════════════════════════════════════════
# CanManageBudget — has_permission (role level ≤3)
# ════════════════════════════════════════════════════════


class TestCanManageBudgetHasPermission:
    def test_superadmin_allowed(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(authenticated=True, is_superuser=True)
        assert CanManageBudget().has_permission(req, _mock_view()) is True

    def test_institution_admin_allowed(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=2, institution_id="inst-1")
        assert CanManageBudget().has_permission(req, _mock_view()) is True

    def test_center_director_allowed(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=3, institution_id="inst-1")
        assert CanManageBudget().has_permission(req, _mock_view()) is True

    def test_researcher_denied(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=4, institution_id="inst-1")
        assert CanManageBudget().has_permission(req, _mock_view()) is False

    def test_unauthenticated_denied(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(authenticated=False)
        assert CanManageBudget().has_permission(req, _mock_view()) is False


# ════════════════════════════════════════════════════════
# CanManageBudget — has_object_permission (center membership)
# ════════════════════════════════════════════════════════


class TestCanManageBudgetObjectPermission:
    def test_admin_bypasses_center_check(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=2, institution_id="inst-1")
        obj = _FakeObj()
        assert CanManageBudget().has_object_permission(req, _mock_view(), obj) is True

    def test_director_in_center_allowed(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=3, institution_id="inst-1", center_ids=["center-1"])
        obj = _FakeObj()
        obj.center_id = "center-1"
        assert CanManageBudget().has_object_permission(req, _mock_view(), obj) is True

    def test_director_outside_center_denied(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=3, institution_id="inst-1", center_ids=["center-2"])
        obj = _FakeObj()
        obj.center_id = "center-1"
        assert CanManageBudget().has_object_permission(req, _mock_view(), obj) is False

    def test_director_no_membership_denied(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=3, institution_id="inst-1", center_ids=[])
        obj = _FakeObj()
        obj.center_id = "center-1"
        # active_membership has no centers
        assert CanManageBudget().has_object_permission(req, _mock_view(), obj) is False

    def test_researcher_denied_object(self):
        from apps.budgets.permissions import CanManageBudget

        req = _make_request(role_level=4, institution_id="inst-1")
        obj = _FakeObj()
        assert CanManageBudget().has_object_permission(req, _mock_view(), obj) is False


# ════════════════════════════════════════════════════════
# CanAuthorizeExecution — role level ≤3
# ════════════════════════════════════════════════════════


class TestCanAuthorizeExecution:
    def test_director_allowed(self):
        from apps.budgets.permissions import CanAuthorizeExecution

        req = _make_request(role_level=3, institution_id="inst-1")
        assert CanAuthorizeExecution().has_permission(req, _mock_view()) is True

    def test_admin_allowed(self):
        from apps.budgets.permissions import CanAuthorizeExecution

        req = _make_request(role_level=2, institution_id="inst-1")
        assert CanAuthorizeExecution().has_permission(req, _mock_view()) is True

    def test_researcher_denied(self):
        from apps.budgets.permissions import CanAuthorizeExecution

        req = _make_request(role_level=4, institution_id="inst-1")
        assert CanAuthorizeExecution().has_permission(req, _mock_view()) is False

    def test_unauthenticated_denied(self):
        from apps.budgets.permissions import CanAuthorizeExecution

        req = _make_request(authenticated=False)
        assert CanAuthorizeExecution().has_permission(req, _mock_view()) is False


# ════════════════════════════════════════════════════════
# IsSameInstitution re-export
# ════════════════════════════════════════════════════════


class TestIsSameInstitution:
    def test_matching_institution_allowed(self):
        from apps.budgets.permissions import IsSameInstitution

        req = _make_request(institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-1"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is True

    def test_mismatched_institution_denied(self):
        from apps.budgets.permissions import IsSameInstitution

        req = _make_request(institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-9"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is False

    def test_superadmin_bypasses(self):
        from apps.budgets.permissions import IsSameInstitution

        req = _make_request(is_superuser=True, institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-9"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is True
