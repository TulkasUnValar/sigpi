"""
Permission tests for SIGPI DRF permission classes — STRICT TDD.

Tests define the expected behavior of:
- IsSuperAdmin: only Django superuser or Superadmin role
- IsInstitutionAdmin: Admin role (level <= 2) in active institution
- IsCenterDirector: Director role (level <= 3) with center-specific access
- IsResearcher: Researcher role (level <= 4)
- IsEvaluador: Evaluador role (level <= 5)
- IsAssistant: Assistant role (level <= 6)
- IsAuditor: Auditor role (level <= 7), SAFE_METHODS only
- IsSameInstitution: object's institution matches request's institution
- Role hierarchy: higher roles include lower permissions

Spec references: FR-005
Design reference: openspec/changes/auth/design.md — DRF Permission Classes
"""
from unittest.mock import MagicMock

import pytest
from django.http import HttpRequest
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter

from apps.accounts.permissions import (
    HasRoleLevelOrHigher,
    IsAssistant,
    IsAuditor,
    IsCenterDirector,
    IsEvaluador,
    IsInstitutionAdmin,
    IsResearcher,
    IsSameInstitution,
    IsSuperAdmin,
)


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


@pytest.fixture
def researcher_role(db) -> Role:
    return Role.objects.get(name="Investigador")


@pytest.fixture
def user_with_membership(db, institution, researcher_role) -> User:
    """User with an active membership in the test institution."""
    user = User.objects.create_user(
        email="member@example.com",
        auth_source="local",
        password="testpass123",
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=researcher_role,
        is_active=True,
    )
    return user


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def make_mock_request(
    user: User | None = None,
    institution_id: str | None = None,
    method: str = "GET",
    membership=None,
) -> Request:
    """Build a DRF Request with mocked attributes.

    Note: DRF Request.user is a property that authenticates from session.
    We bypass that by setting _user directly on the DRF Request wrapper.
    """
    http_req = HttpRequest()
    http_req.method = method

    if user is not None:
        http_req.user = user
    else:
        http_req.user = MagicMock(is_authenticated=False, is_superuser=False)

    http_req.institution_id = institution_id
    http_req.active_membership = membership

    drf_request = Request(http_req)
    # DRF Request.user property authenticates from session, not HttpRequest.user.
    # We pre-set _user to avoid this overhead in unit tests.
    drf_request._user = http_req.user  # type: ignore
    return drf_request


def make_membership(user: User, institution: Institution, role: Role,
                    centers: list | None = None,
                    is_primary: bool = True,
                    is_active: bool = True) -> InstitutionMembership:
    """Create an InstitutionMembership for testing."""
    membership = InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=role,
        is_primary=is_primary,
        is_active=is_active,
    )
    if centers:
        membership.centers.set(centers)
    return membership


# ──────────────────────────────────────────────────────────
# Test HasRoleLevelOrHigher (base utility)
# ──────────────────────────────────────────────────────────


class TestHasRoleLevelOrHigher:
    """Tests for the role hierarchy utility function."""

    def test_superadmin_has_level_1(self, db, institution):
        """Superadmin can access anything up to level 1."""
        user = User.objects.create_superuser(email="super@test.com", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        assert HasRoleLevelOrHigher.has_level(request, 1) is True

    def test_admin_has_level_2(self, db, institution):
        """Admin role (level 2) can access level <= 2."""
        user = User.objects.create_user(email="admin@test.com", auth_source="local", password="pass")
        role_admin = Role.objects.get(name="Admin Institucional")
        membership = make_membership(user, institution, role_admin)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert HasRoleLevelOrHigher.has_level(request, 2) is True
        assert HasRoleLevelOrHigher.has_level(request, 3) is True  # Higher number = lower privilege

    def test_researcher_cannot_access_admin_level(self, db, institution):
        """Researcher (level 4) cannot access admin level (2)."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_researcher = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_researcher)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert HasRoleLevelOrHigher.has_level(request, 2) is False  # Need level <= 2, have 4

    def test_no_membership_returns_false(self, db):
        """User without active membership cannot access any role level."""
        user = User.objects.create_user(email="nomem@test.com", auth_source="local", password="pass")
        request = make_mock_request(user=user, institution_id=None)
        assert HasRoleLevelOrHigher.has_level(request, 7) is False  # Even lowest level

    def test_no_institution_returns_false(self, db, user_with_membership):
        """User with membership but no active institution returns false."""
        role_admin = Role.objects.get(name="Admin Institucional")
        user = user_with_membership
        # user has researcher membership but no active institution
        request = make_mock_request(user=user, institution_id=None)
        assert HasRoleLevelOrHigher.has_level(request, 2) is False

    def test_hierarchy_superadmin_bypasses_all(self, db, institution):
        """Superadmin (django is_superuser) bypasses all level checks."""
        user = User.objects.create_superuser(email="super@test.com", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        assert HasRoleLevelOrHigher.has_level(request, 1) is True
        assert HasRoleLevelOrHigher.has_level(request, 7) is True


# ──────────────────────────────────────────────────────────
# Test IsSuperAdmin
# ──────────────────────────────────────────────────────────


class TestIsSuperAdmin:
    """Tests for IsSuperAdmin permission class."""

    def test_superuser_has_permission(self, db):
        """Django superuser always has permission."""
        user = User.objects.create_superuser(email="super@test.com", password="pass")
        request = make_mock_request(user=user)
        assert IsSuperAdmin().has_permission(request, None) is True

    def test_superadmin_role_has_permission(self, db, institution):
        """User with Superadmin role has permission."""
        user = User.objects.create_user(email="sa@test.com", auth_source="local", password="pass")
        role_sa = Role.objects.get(name="Superadmin")
        membership = make_membership(user, institution, role_sa)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsSuperAdmin().has_permission(request, None) is True

    def test_normal_user_denied(self, db, institution):
        """Normal researcher is denied."""
        user = User.objects.create_user(email="normal@test.com", auth_source="local", password="pass")
        role_researcher = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_researcher)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsSuperAdmin().has_permission(request, None) is False

    def test_unauthenticated_denied(self):
        """Unauthenticated user is denied."""
        request = make_mock_request()
        assert IsSuperAdmin().has_permission(request, None) is False


# ──────────────────────────────────────────────────────────
# Test IsInstitutionAdmin
# ──────────────────────────────────────────────────────────


class TestIsInstitutionAdmin:
    """Tests for IsInstitutionAdmin permission class."""

    def test_admin_role_has_permission(self, db, institution):
        """Admin Institucional has permission."""
        user = User.objects.create_user(email="admin@test.com", auth_source="local", password="pass")
        role_admin = Role.objects.get(name="Admin Institucional")
        membership = make_membership(user, institution, role_admin)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsInstitutionAdmin().has_permission(request, None) is True

    def test_superadmin_role_has_permission(self, db, institution):
        """Superadmin (higher role) also has admin permission."""
        user = User.objects.create_user(email="sa@test.com", auth_source="local", password="pass")
        role_sa = Role.objects.get(name="Superadmin")
        membership = make_membership(user, institution, role_sa)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsInstitutionAdmin().has_permission(request, None) is True

    def test_director_denied(self, db, institution):
        """Director de Centro (level 3) is denied admin access."""
        user = User.objects.create_user(email="dir@test.com", auth_source="local", password="pass")
        role_dir = Role.objects.get(name="Director de Centro")
        membership = make_membership(user, institution, role_dir)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsInstitutionAdmin().has_permission(request, None) is False

    def test_researcher_denied(self, db, institution):
        """Researcher is denied admin access."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_res = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_res)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsInstitutionAdmin().has_permission(request, None) is False

    def test_requires_active_institution(self, db):
        """Admin without active institution is denied."""
        user = User.objects.create_user(email="admin@test.com", auth_source="local", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=None,
        )
        assert IsInstitutionAdmin().has_permission(request, None) is False


# ──────────────────────────────────────────────────────────
# Test IsCenterDirector
# ──────────────────────────────────────────────────────────


class TestIsCenterDirector:
    """Tests for IsCenterDirector permission class (object-level)."""

    def test_director_has_permission(self, db, institution, researcher_role):
        """Director with matching center has object permission."""
        user = User.objects.create_user(email="dir@test.com", auth_source="local", password="pass")
        role_dir = Role.objects.get(name="Director de Centro")
        center = ResearchCenter.objects.create(name="Centro A", institution=institution)
        membership = make_membership(user, institution, role_dir, centers=[center])
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )

        # Mock object with center_id attribute
        class MockObj:
            center_id = center.id
        obj = MockObj()

        assert IsCenterDirector().has_object_permission(request, None, obj) is True

    def test_director_wrong_center_denied(self, db, institution):
        """Director assigned to center A cannot access center B."""
        user = User.objects.create_user(email="dir@test.com", auth_source="local", password="pass")
        role_dir = Role.objects.get(name="Director de Centro")
        center_a = ResearchCenter.objects.create(name="Centro A", code="CA", institution=institution)
        center_b = ResearchCenter.objects.create(name="Centro B", code="CB", institution=institution)
        membership = make_membership(user, institution, role_dir, centers=[center_a])
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )

        class MockObj:
            center_id = center_b.id
        obj = MockObj()

        assert IsCenterDirector().has_object_permission(request, None, obj) is False

    def test_researcher_denied_director_access(self, db, institution):
        """Researcher cannot access director-level resources."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_res = Role.objects.get(name="Investigador")
        center = ResearchCenter.objects.create(name="Centro A", institution=institution)
        membership = make_membership(user, institution, role_res, centers=[center])
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )

        class MockObj:
            center_id = center.id
        obj = MockObj()

        assert IsCenterDirector().has_object_permission(request, None, obj) is False

    def test_superadmin_bypasses_has_permission(self, db, institution):
        """Superadmin passes has_permission check regardless of center."""
        user = User.objects.create_superuser(email="super@test.com", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        assert IsCenterDirector().has_permission(request, None) is True

    def test_admin_role_has_center_director_permission(self, db, institution):
        """Admin Institucional (higher role) has center director access."""
        user = User.objects.create_user(email="admin@test.com", auth_source="local", password="pass")
        role_admin = Role.objects.get(name="Admin Institucional")
        membership = make_membership(user, institution, role_admin)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsCenterDirector().has_permission(request, None) is True


# ──────────────────────────────────────────────────────────
# Test IsResearcher
# ──────────────────────────────────────────────────────────


class TestIsResearcher:
    """Tests for IsResearcher permission class."""

    def test_researcher_has_permission(self, db, institution):
        """Researcher role has permission."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_res = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_res)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsResearcher().has_permission(request, None) is True

    def test_evaluador_also_has_researcher_permission(self, db, institution):
        """Evaluador (level 5, higher number) - wait, researcher is level 4.
        Researcher is HIGHER than Evaluador, so Evaluador should NOT have it.
        Actually: level 1=highest, so level 4 > level 5.
        So Researcher can do what Evaluador can, but NOT vice versa."""
        user = User.objects.create_user(email="eval@test.com", auth_source="local", password="pass")
        role_eval = Role.objects.get(name="Evaluador")
        membership = make_membership(user, institution, role_eval)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsResearcher().has_permission(request, None) is False  # Evaluador < Researcher

    def test_director_has_researcher_permission(self, db, institution):
        """Director (higher role) also has researcher permission."""
        user = User.objects.create_user(email="dir@test.com", auth_source="local", password="pass")
        role_dir = Role.objects.get(name="Director de Centro")
        membership = make_membership(user, institution, role_dir)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsResearcher().has_permission(request, None) is True

    def test_assistant_denied_researcher_access(self, db, institution):
        """Assistant (level 6) cannot access researcher-level resources."""
        user = User.objects.create_user(email="asst@test.com", auth_source="local", password="pass")
        role_asst = Role.objects.get(name="Asistente")
        membership = make_membership(user, institution, role_asst)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsResearcher().has_permission(request, None) is False


# ──────────────────────────────────────────────────────────
# Test IsEvaluador
# ──────────────────────────────────────────────────────────


class TestIsEvaluador:
    """Tests for IsEvaluador permission class."""

    def test_evaluador_has_permission(self, db, institution):
        """Evaluador role has permission."""
        user = User.objects.create_user(email="eval@test.com", auth_source="local", password="pass")
        role_eval = Role.objects.get(name="Evaluador")
        membership = make_membership(user, institution, role_eval)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsEvaluador().has_permission(request, None) is True

    def test_researcher_has_evaluador_permission(self, db, institution):
        """Researcher (higher role) also has evaluador permission."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_res = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_res)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsEvaluador().has_permission(request, None) is True

    def test_assistant_denied(self, db, institution):
        """Assistant cannot access evaluador resources."""
        user = User.objects.create_user(email="asst@test.com", auth_source="local", password="pass")
        role_asst = Role.objects.get(name="Asistente")
        membership = make_membership(user, institution, role_asst)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsEvaluador().has_permission(request, None) is False


# ──────────────────────────────────────────────────────────
# Test IsAssistant
# ──────────────────────────────────────────────────────────


class TestIsAssistant:
    """Tests for IsAssistant permission class."""

    def test_assistant_has_permission(self, db, institution):
        """Assistant role has permission."""
        user = User.objects.create_user(email="asst@test.com", auth_source="local", password="pass")
        role_asst = Role.objects.get(name="Asistente")
        membership = make_membership(user, institution, role_asst)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsAssistant().has_permission(request, None) is True

    def test_auditor_denied(self, db, institution):
        """Auditor (level 7) cannot access assistant resources."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsAssistant().has_permission(request, None) is False

    def test_evaluador_has_assistant_permission(self, db, institution):
        """Evaluador (higher) has assistant permission."""
        user = User.objects.create_user(email="eval@test.com", auth_source="local", password="pass")
        role_eval = Role.objects.get(name="Evaluador")
        membership = make_membership(user, institution, role_eval)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )
        assert IsAssistant().has_permission(request, None) is True


# ──────────────────────────────────────────────────────────
# Test IsAuditor
# ──────────────────────────────────────────────────────────


class TestIsAuditor:
    """Tests for IsAuditor permission class (read-only)."""

    def test_auditor_get_has_permission(self, db, institution):
        """Auditor has permission on GET (safe method)."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="GET",
        )
        assert IsAuditor().has_permission(request, None) is True

    def test_auditor_head_has_permission(self, db, institution):
        """Auditor has permission on HEAD (safe method)."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="HEAD",
        )
        assert IsAuditor().has_permission(request, None) is True

    def test_auditor_post_denied(self, db, institution):
        """Auditor is denied on POST (unsafe method)."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="POST",
        )
        assert IsAuditor().has_permission(request, None) is False

    def test_auditor_put_denied(self, db, institution):
        """Auditor is denied on PUT."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="PUT",
        )
        assert IsAuditor().has_permission(request, None) is False

    def test_auditor_delete_denied(self, db, institution):
        """Auditor is denied on DELETE."""
        user = User.objects.create_user(email="aud@test.com", auth_source="local", password="pass")
        role_aud = Role.objects.get(name="Auditor")
        membership = make_membership(user, institution, role_aud)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="DELETE",
        )
        assert IsAuditor().has_permission(request, None) is False

    def test_researcher_has_auditor_permission(self, db, institution):
        """Researcher (higher role) can read like an auditor."""
        user = User.objects.create_user(email="res@test.com", auth_source="local", password="pass")
        role_res = Role.objects.get(name="Investigador")
        membership = make_membership(user, institution, role_res)
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
            method="GET",
        )
        assert IsAuditor().has_permission(request, None) is True


# ──────────────────────────────────────────────────────────
# Test IsSameInstitution
# ──────────────────────────────────────────────────────────


class TestIsSameInstitution:
    """Tests for IsSameInstitution object-level permission."""

    def test_same_institution_allowed(self, db, institution):
        """Object from same institution as request is allowed."""
        user = User.objects.create_user(email="user@test.com", auth_source="local", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        obj = MagicMock(institution_id=institution.id)
        assert IsSameInstitution().has_object_permission(request, None, obj) is True

    def test_different_institution_denied(self, db, institution):
        """Object from different institution is denied."""
        user = User.objects.create_user(email="user@test.com", auth_source="local", password="pass")
        other_inst = Institution.objects.create(name="Other Inst", code="OTHER")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        obj = MagicMock(institution_id=other_inst.id)
        assert IsSameInstitution().has_object_permission(request, None, obj) is False

    def test_no_institution_denied(self, db, institution):
        """No active institution returns false."""
        user = User.objects.create_user(email="user@test.com", auth_source="local", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=None,
        )
        obj = MagicMock(institution_id=institution.id)
        assert IsSameInstitution().has_object_permission(request, None, obj) is False

    def test_obj_no_institution_id_denied(self, db, institution):
        """Object without institution_id returns false."""
        user = User.objects.create_user(email="user@test.com", auth_source="local", password="pass")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        obj = MagicMock(spec=[])  # No institution_id
        assert IsSameInstitution().has_object_permission(request, None, obj) is False

    def test_superadmin_bypasses(self, db, institution):
        """Superadmin bypasses institution check."""
        user = User.objects.create_superuser(email="super@test.com", password="pass")
        other_inst = Institution.objects.create(name="Other Inst", code="OTHER")
        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
        )
        obj = MagicMock(institution_id=other_inst.id)
        assert IsSameInstitution().has_object_permission(request, None, obj) is True

    def test_has_permission_always_true(self, db):
        """IsSameInstitution always allows at view level (object-level check only)."""
        user = User.objects.create_user(email="user@test.com", auth_source="local", password="pass")
        request = make_mock_request(user=user)
        assert IsSameInstitution().has_permission(request, None) is True


# ──────────────────────────────────────────────────────────
# Role Hierarchy Tests (cross-cutting)
# ──────────────────────────────────────────────────────────


class TestRoleHierarchy:
    """Tests verifying the role hierarchy is correctly enforced."""

    ROLES_BY_LEVEL = [
        (1, "Superadmin"),
        (2, "Admin Institucional"),
        (3, "Director de Centro"),
        (4, "Investigador"),
        (5, "Evaluador"),
        (6, "Asistente"),
        (7, "Auditor"),
    ]

    PERMISSION_CLASSES = {
        1: IsSuperAdmin,
        2: IsInstitutionAdmin,
        3: IsCenterDirector,
        4: IsResearcher,
        5: IsEvaluador,
        6: IsAssistant,
        7: IsAuditor,
    }

    @pytest.mark.parametrize("user_level,perm_level,expected", [
        # Superadmin (1) can access everything
        (1, 1, True), (1, 2, True), (1, 3, True), (1, 4, True),
        (1, 5, True), (1, 6, True), (1, 7, True),
        # Admin (2)
        (2, 1, False), (2, 2, True), (2, 3, True), (2, 4, True),
        (2, 5, True), (2, 6, True), (2, 7, True),
        # Director (3)
        (3, 1, False), (3, 2, False), (3, 3, True), (3, 4, True),
        (3, 5, True), (3, 6, True), (3, 7, True),
        # Researcher (4)
        (4, 1, False), (4, 2, False), (4, 3, False), (4, 4, True),
        (4, 5, True), (4, 6, True), (4, 7, True),
        # Evaluador (5)
        (5, 1, False), (5, 2, False), (5, 3, False), (5, 4, False),
        (5, 5, True), (5, 6, True), (5, 7, True),
        # Assistant (6)
        (6, 1, False), (6, 2, False), (6, 3, False), (6, 4, False),
        (6, 5, False), (6, 6, True), (6, 7, True),
        # Auditor (7)
        (7, 1, False), (7, 2, False), (7, 3, False), (7, 4, False),
        (7, 5, False), (7, 6, False), (7, 7, True),
    ])
    def test_hierarchy_matrix(self, db, institution, user_level, perm_level, expected):
        """Verify each role level can access the expected permission levels.

        Lower level number = higher privilege. A user can access
        any permission with level >= their own level.
        """
        perm_class = self.PERMISSION_CLASSES[perm_level]

        if user_level == 1 and perm_level == 1:
            # Superadmin special case: use is_superuser
            user = User.objects.create_superuser(
                email=f"lvl{user_level}_p{perm_level}@test.com",
                password="pass",
            )
            membership = None
        else:
            user = User.objects.create_user(
                email=f"lvl{user_level}_p{perm_level}@test.com",
                auth_source="local",
                password="pass",
            )
            role_name = dict(self.ROLES_BY_LEVEL)[user_level]
            role = Role.objects.get(name=role_name)
            membership = make_membership(user, institution, role)

        request = make_mock_request(
            user=user,
            institution_id=str(institution.id),
            membership=membership,
        )

        # For IsAuditor (perm_level=7), test on GET to avoid method issues
        if perm_level == 7:
            request._request.method = "GET"

        # For IsCenterDirector with object perm, test has_permission only
        result = perm_class().has_permission(request, None)
        assert result is expected, (
            f"User level {user_level} accessing perm level {perm_level}: "
            f"expected {expected}, got {result}"
        )
