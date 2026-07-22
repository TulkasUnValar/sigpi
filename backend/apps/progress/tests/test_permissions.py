"""
Permission tests for the progress (advances) module.

Covers:
- IsProgressCreatorOrProjectMember: creator OR member check; Admin+ bypass
- IsCenterDirectorForProject (re-export): director of project's center
- Full role × action matrix (10 actions × 6 roles = 60 cells)

Test pattern: MagicMock-based request/object construction (matches
projects/tests/test_permissions.py and researchers/tests/test_permissions.py).

Spec reference:   openspec/sdd/advances/spec.md — Permission Matrix
Design reference: openspec/sdd/advances/design.md — Permission Classes

RED PHASE: Tests written against permissions.py; will FAIL if permission
logic is incomplete or incorrect.
"""
from unittest.mock import MagicMock

import pytest
from rest_framework.request import Request

# ──────────────────────────────────────────────────────────
# Test Helpers
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
    """Build a mock DRF Request with the given attributes.

    Mirrors projects/tests/test_permissions.py:_make_request.
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
            # values_list("id", flat=True) returns raw IDs, not tuples
            membership.centers.values_list.return_value = list(center_ids)
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


def _make_obj(created_by_id=None, project_members=None, center_id=None):
    """Build a mock ProgressReport-like object.

    Args:
        created_by_id: UUID to set as created_by_id on the mock.
        project_members: If True, the project.members.filter().exists() chain
                         returns True. If None, project has no members attr.
        center_id: The project's center_id.

    NOTE: center_id is set BOTH on obj.center_id (for IsCenterDirectorForProject
          compatibility) AND on project.center_id (real model path).
          ProgressReport.center_id is a property that delegates to
          self.project.center_id.
    """
    obj = _FakeObj()
    obj.created_by_id = created_by_id
    obj.center_id = center_id  # for IsCenterDirectorForProject.getattr(obj, "center_id")

    # Build a mock project
    project = MagicMock()
    project.center_id = center_id

    if project_members is True:
        project.members.filter.return_value.exists.return_value = True
    elif project_members is False:
        project.members.filter.return_value.exists.return_value = False
    # else: project has no members attr (project_members=None)

    obj.project = project
    return obj


# ──────────────────────────────────────────────────────────
# IsProgressCreatorOrProjectMember
# ──────────────────────────────────────────────────────────


class TestIsProgressCreatorOrProjectMember:
    """Permission: user is created_by OR a ProjectMember of report.project.

    Admin+ (level ≤ 2) bypasses. SAFE_METHODS pass at view level.
    """

    def test_unauthenticated_rejected_has_permission(self):
        """Unauthenticated user fails has_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_unauthenticated_rejected_has_object_permission(self):
        """Unauthenticated user fails has_object_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", authenticated=False)
        obj = _make_obj()
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    # ── Admin+ bypass ─────────────────────────────────

    def test_superadmin_bypasses_has_permission(self):
        """Superadmin (level 1) always passes has_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", role_level=1, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_admin_bypasses_has_permission(self):
        """Admin (level 2) always passes has_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_admin_bypasses_has_object_permission(self):
        """Admin (level 2) always passes has_object_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", role_level=2, institution_id="uuid-1")
        obj = _make_obj()
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    # ── SAFE_METHODS ──────────────────────────────────

    def test_safe_methods_pass_at_view_level(self):
        """GET/HEAD/OPTIONS pass has_permission for any authenticated role."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()

        for method in ("GET", "HEAD", "OPTIONS"):
            request = _make_request(method=method, role_level=6, institution_id="uuid-1")
            assert perm.has_permission(request, _mock_view()) is True, f"{method} should pass"

    def test_safe_methods_do_not_need_object_check(self):
        """SAFE_METHODS still need has_object_permission for non-creator/non-member."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="GET", role_level=4, institution_id="uuid-1")
        # Non-creator, non-member — should fail object permission
        obj = _make_obj(created_by_id="other-uuid", project_members=False)
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    # ── Role level gate (has_permission) ──────────────

    @pytest.mark.parametrize(
        "role_level,method,expected",
        [
            (1, "POST", True),   # Superadmin
            (2, "POST", True),   # Admin
            (3, "POST", True),   # Director (level 3 ≤ 4)
            (4, "POST", True),   # Researcher
            (5, "POST", False),  # Evaluador (level 5 > 4)
            (6, "POST", False),  # Asistente (level 6 > 4)
            (7, "POST", False),  # Auditor (level 7 > 4)
        ],
    )
    def test_has_permission_role_gate(self, role_level, method, expected):
        """Level ≤ 4 passes for non-SAFE methods; level > 4 fails."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method=method, role_level=role_level, institution_id="uuid-1")
        result = perm.has_permission(request, _mock_view())
        assert result is expected

    def test_has_permission_requires_institution(self):
        """Without an institution_id, non-admin fails has_permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="POST", role_level=4, institution_id=None)
        assert perm.has_permission(request, _mock_view()) is False

    # ── Object-level: creator check ───────────────────

    def test_creator_passes_object_permission(self):
        """User who created the report passes object permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = "creator-123"
        obj = _make_obj(created_by_id="creator-123", project_members=False)
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_non_creator_non_member_rejected(self):
        """User unrelated to the report fails object permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = "unrelated"
        obj = _make_obj(created_by_id="creator-123", project_members=False)
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    # ── Object-level: member check ────────────────────

    def test_project_member_passes_object_permission(self):
        """Non-creator but project member passes object permission."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = "member-456"
        obj = _make_obj(created_by_id="creator-123", project_members=True)
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_object_without_project_is_safe(self):
        """If obj has no project attribute, no crash — just no member check."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(method="PATCH", role_level=4, institution_id="uuid-1")
        request.user.id = "someone"
        obj = _FakeObj()
        obj.created_by_id = "other"
        obj.project = None
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_superuser_bypasses_object_permission(self):
        """Django superuser (is_superuser=True) bypasses all checks."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()
        request = _make_request(
            method="DELETE",
            authenticated=True,
            is_superuser=True,
            role_level=5,
            institution_id="uuid-1",
        )
        obj = _make_obj(created_by_id="creator-123", project_members=False)
        assert perm.has_object_permission(request, _mock_view(), obj) is True


# ──────────────────────────────────────────────────────────
# IsCenterDirectorForProject (re-export from projects)
# ──────────────────────────────────────────────────────────


class TestIsCenterDirectorForProgress:
    """Permission: user's membership includes the project's center
    with Director role (level ≤ 3). Re-exported from projects.

    Verified in the context of ProgressReport objects,
    where the center is accessed via obj.project.center_id.
    """

    def test_import_available(self):
        """IsCenterDirectorForProject is re-exported from progress.permissions."""
        from apps.progress.permissions import IsCenterDirectorForProject
        from apps.projects.permissions import (
            IsCenterDirectorForProject as ProjectsIsCenterDirectorForProject,
        )

        assert IsCenterDirectorForProject is ProjectsIsCenterDirectorForProject

    def test_director_of_center_passes_has_permission(self):
        """Level 3 (Center Director) passes has_permission."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=3, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is True

    def test_researcher_fails_has_permission(self):
        """Level 4 (Researcher) fails has_permission."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=4, institution_id="uuid-1")
        assert perm.has_permission(request, _mock_view()) is False

    def test_unauthenticated_fails_has_permission(self):
        """Unauthenticated user fails has_permission."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", authenticated=False)
        assert perm.has_permission(request, _mock_view()) is False

    def test_director_of_correct_center_passes_object_permission(self):
        """Director whose center list includes the project's center passes."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(
            method="POST",
            role_level=3,
            institution_id="uuid-1",
            center_ids=["center-abc"],
        )
        obj = _make_obj(center_id="center-abc")
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_director_of_wrong_center_fails_object_permission(self):
        """Director whose center list does NOT include the project's center fails."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(
            method="POST",
            role_level=3,
            institution_id="uuid-1",
            center_ids=["center-xyz"],
        )
        obj = _make_obj(center_id="center-abc")
        assert perm.has_object_permission(request, _mock_view(), obj) is False

    def test_admin_bypasses_object_permission_center_check(self):
        """Admin (level 2) passes object permission regardless of center."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(
            method="POST",
            role_level=2,
            institution_id="uuid-1",
            center_ids=["center-xyz"],
        )
        obj = _make_obj(center_id="center-different")
        assert perm.has_object_permission(request, _mock_view(), obj) is True

    def test_director_without_active_membership_fails(self):
        """If active_membership is None, director fails object permission."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()
        request = _make_request(method="POST", role_level=3, institution_id="uuid-1")
        # No center_ids set → active_membership exists but centers list is empty
        # Need to test when active_membership is None
        request.active_membership = None
        obj = _make_obj(center_id="center-abc")
        assert perm.has_object_permission(request, _mock_view(), obj) is False


# ──────────────────────────────────────────────────────────
# Role × Action Matrix (60 cells)
# ──────────────────────────────────────────────────────────


class TestPermissionMatrix:
    """Verify the full role × action permission matrix.

    10 actions × 6 roles = 60 test cells.
    Each cell checks whether a user with a given role CAN perform a given action.

    Roles:
      1 = Superadmin (level 1)
      2 = Admin Institucional (level 2)
      3 = Director de Centro (level 3)
      4 = Investigador / PI (level 4)
      5 = Evaluador (level 5)
      6 = Otro / Asistente (level 6)

    Actions (for IsProgressCreatorOrProjectMember):
      - SAFE (GET/HEAD/OPTIONS): always allowed for authenticated
      - CREATE (POST /progress/): level ≤ 4
      - UPDATE (PATCH /progress/{id}/): creator or member
      - DELETE (DELETE /progress/{id}/): creator or member
      - SUBMIT (POST /progress/{id}/submit/): creator or member
      - RESUBMIT (POST /progress/{id}/resubmit/): creator or member

    Actions (for IsCenterDirectorForProject):
      - ACCEPT_REVIEW: level ≤ 3
      - APPROVE: level ≤ 3
      - OBSERVE: level ≤ 3
      - REJECT: level ≤ 3
    """

    # ── CreatorOrMember matrix ────────────────────────

    @pytest.mark.parametrize(
        "role_level,action,is_creator,expected",
        [
            # Superadmin (level 1): bypasses everything — object-level always True
            (1, "SAFE", False, True),
            (1, "CREATE", False, True),
            (1, "UPDATE", True, True),
            (1, "DELETE", True, True),
            (1, "SUBMIT", True, True),
            (1, "RESUBMIT", True, True),
            # Admin (level 2): bypasses everything
            (2, "SAFE", False, True),
            (2, "CREATE", False, True),
            (2, "UPDATE", True, True),
            (2, "DELETE", True, True),
            (2, "SUBMIT", True, True),
            (2, "RESUBMIT", True, True),
            # Director (level 3): passes has_permission (≤ 4); object level requires
            # creator/member — SAFE methods are NOT a bypass at object level
            (3, "SAFE", False, False),  # not creator/member — blocked
            (3, "CREATE", False, True),  # has_permission only (no object)
            (3, "UPDATE", True, True),   # is creator
            (3, "UPDATE", False, False),  # not creator
            (3, "DELETE", True, True),
            (3, "SUBMIT", True, True),
            (3, "RESUBMIT", True, True),
            # Researcher/PI (level 4): passes has_permission (≤ 4); object depends on creator
            (4, "SAFE", False, False),  # not creator/member — blocked
            (4, "CREATE", False, True),  # has_permission only
            (4, "UPDATE", True, True),   # is creator
            (4, "UPDATE", False, False),
            (4, "DELETE", True, True),
            (4, "DELETE", False, False),
            (4, "SUBMIT", True, True),
            (4, "RESUBMIT", True, True),
            # Evaluador (level 5): fails has_permission for mutations
            (5, "SAFE", False, False),  # not creator/member — blocked at object level
            (5, "CREATE", False, False),
            (5, "UPDATE", True, False),
            (5, "DELETE", True, False),
            (5, "SUBMIT", True, False),
            (5, "RESUBMIT", True, False),
            # Asistente (level 6): same as Evaluador
            (6, "SAFE", False, False),  # not creator/member — blocked
            (6, "CREATE", False, False),
            (6, "UPDATE", True, False),
            (6, "DELETE", True, False),
            (6, "SUBMIT", True, False),
            (6, "RESUBMIT", True, False),
        ],
    )
    def test_creator_or_member_matrix(self, role_level, action, is_creator, expected):
        """Role × action matrix for IsProgressCreatorOrProjectMember."""
        from apps.progress.permissions import IsProgressCreatorOrProjectMember

        perm = IsProgressCreatorOrProjectMember()

        method_map = {
            "SAFE": "GET",
            "CREATE": "POST",
            "UPDATE": "PATCH",
            "DELETE": "DELETE",
            "SUBMIT": "POST",
            "RESUBMIT": "POST",
        }
        method = method_map[action]

        request = _make_request(method=method, role_level=role_level, institution_id="uuid-1")

        if action == "CREATE":
            # CREATE has no object — only has_permission applies
            result = perm.has_permission(request, _mock_view())
        else:
            # All other actions have an object check
            if not perm.has_permission(request, _mock_view()):
                result = False
            else:
                obj = _make_obj(
                    created_by_id=request.user.id if is_creator else "other",
                    project_members=is_creator,
                )
                result = perm.has_object_permission(request, _mock_view(), obj)

        assert result is expected, (
            f"Level {role_level} × {action} (creator={is_creator}): "
            f"expected {expected}, got {result}"
        )

    # ── IsCenterDirectorForProject matrix ─────────────

    @pytest.mark.parametrize(
        "role_level,action,center_match,expected",
        [
            # Superadmin (level 1): bypasses everything
            (1, "ACCEPT_REVIEW", False, True),
            (1, "APPROVE", False, True),
            (1, "OBSERVE", False, True),
            (1, "REJECT", False, True),
            # Admin (level 2): bypasses everything
            (2, "ACCEPT_REVIEW", False, True),
            (2, "APPROVE", False, True),
            (2, "OBSERVE", False, True),
            (2, "REJECT", False, True),
            # Director (level 3): must match center
            (3, "ACCEPT_REVIEW", True, True),
            (3, "ACCEPT_REVIEW", False, False),
            (3, "APPROVE", True, True),
            (3, "APPROVE", False, False),
            (3, "OBSERVE", True, True),
            (3, "OBSERVE", False, False),
            (3, "REJECT", True, True),
            (3, "REJECT", False, False),
            # Researcher (level 4): can't perform director actions
            (4, "ACCEPT_REVIEW", True, False),
            (4, "APPROVE", True, False),
            (4, "OBSERVE", True, False),
            (4, "REJECT", True, False),
            # Evaluador (level 5): can't perform director actions
            (5, "ACCEPT_REVIEW", True, False),
            (5, "APPROVE", True, False),
            (5, "OBSERVE", True, False),
            (5, "REJECT", True, False),
            # Asistente (level 6): can't perform director actions
            (6, "ACCEPT_REVIEW", True, False),
            (6, "APPROVE", True, False),
            (6, "OBSERVE", True, False),
            (6, "REJECT", True, False),
        ],
    )
    def test_center_director_matrix(self, role_level, action, center_match, expected):
        """Role × action matrix for IsCenterDirectorForProject (director-only actions)."""
        from apps.progress.permissions import IsCenterDirectorForProject

        perm = IsCenterDirectorForProject()

        center_ids = ["center-abc"] if center_match else ["center-xyz"]
        request = _make_request(
            method="POST",
            role_level=role_level,
            institution_id="uuid-1",
            center_ids=center_ids,
        )

        # Superadmin and Admin bypass object-level but still need has_permission
        if not perm.has_permission(request, _mock_view()):
            result = False
        else:
            obj = _make_obj(center_id="center-abc")
            result = perm.has_object_permission(request, _mock_view(), obj)

        assert result is expected, (
            f"Level {role_level} × {action} (match={center_match}): "
            f"expected {expected}, got {result}"
        )
