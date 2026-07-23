"""
Permission tests for the Reports / Informes module (§6.6).

Covers: CanGenerateReport — anonymous, admin bypass, researcher role,
object-level cross-institution denial, and SAFE_METHODS.

Spec reference:   sdd/reports/spec — RN-015, RN-016
Design reference: openspec/changes/reports/design.md
"""

import uuid

from rest_framework.test import APIRequestFactory

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution
from apps.reports.models import Report
from apps.reports.permissions import CanGenerateReport

# ═══════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════


def _make_request(user=None, method="GET", institution=None):
    """Build a DRF request with the given user and method."""
    factory = APIRequestFactory()
    request = factory.get("/dummy/") if method == "GET" else factory.post("/dummy/")
    request.user = user if user else type("AnonymousUser", (), {"is_authenticated": False})()
    request.method = method
    if institution:
        request.institution_id = str(institution.pk)
    return request


def _make_user(email, level=4, institution=None):
    """Create a user with optional membership."""
    user = User.objects.create_user(email=email, password="testpass")
    if institution:
        role = Role.objects.create(name=f"Role-{level}-{uuid.uuid4().hex[:4]}", level=level)
        membership = InstitutionMembership.objects.create(
            user=user,
            institution=institution,
            role=role,
        )
        # Attach membership to request manually (middleware does this in prod)
        user._test_membership = membership
    return user


# ═══════════════════════════════════════════════════════
# CanGenerateReport Tests
# ═══════════════════════════════════════════════════════


class TestCanGenerateReport:
    """Unit tests for the CanGenerateReport permission class."""

    def test_anonymous_user_denied(self, db):
        """Anonymous users are denied (line 33)."""
        perm = CanGenerateReport()
        request = _make_request(user=None)
        assert perm.has_permission(request, None) is False

    def test_admin_user_bypasses(self, db):
        """Admin (level <= 2) bypasses all checks (line 37)."""
        inst = Institution.objects.create(name="Admin Inst", code="ADM01")
        user = _make_user("admin@test.edu", level=2, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=user, institution=inst)
        request.active_membership = user._test_membership
        assert perm.has_permission(request, None) is True

    def test_researcher_role_allowed(self, db):
        """Researcher (level 4) is allowed (line 44)."""
        inst = Institution.objects.create(name="Res Inst", code="RES01")
        user = _make_user("res@test.edu", level=4, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=user, institution=inst)
        request.active_membership = user._test_membership
        assert perm.has_permission(request, None) is True

    def test_safe_methods_pass_at_view_level(self, db):
        """SAFE_METHODS (GET) pass at view level even for non-researcher (line 40-41)."""
        inst = Institution.objects.create(name="Safe Inst", code="SAFE01")
        # Create a user with a high level (5 = no permission for write)
        user = _make_user("safe@test.edu", level=5, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=user, method="GET", institution=inst)
        request.active_membership = user._test_membership
        # SAFE_METHODS should pass at view level
        assert perm.has_permission(request, None) is True

    def test_unsafe_methods_rejected_for_high_level(self, db):
        """POST/PUT for level 5 is rejected at view level."""
        inst = Institution.objects.create(name="Unsafe Inst", code="UNSAFE01")
        user = _make_user("unsafe@test.edu", level=5, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=user, method="POST", institution=inst)
        request.active_membership = user._test_membership
        assert perm.has_permission(request, None) is False

    def test_object_permission_anonymous_denied(self, db):
        """Anonymous users denied at object level (line 47-48)."""
        perm = CanGenerateReport()
        request = _make_request(user=None)
        assert perm.has_object_permission(request, None, None) is False

    def test_object_permission_admin_bypasses(self, db):
        """Admin bypasses at object level (line 50-52)."""
        inst = Institution.objects.create(name="Obj Admin", code="OA01")
        user = _make_user("objadmin@test.edu", level=2, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=user, institution=inst)
        request.active_membership = user._test_membership
        assert perm.has_object_permission(request, None, None) is True

    def test_object_permission_same_institution_allowed(self, db):
        """Same institution object permission is allowed (line 54-55)."""
        inst = Institution.objects.create(name="Same", code="SAME01")
        user = _make_user("same@test.edu", level=4, institution=inst)
        report = Report.objects.create(
            report_type="project",
            entity_id=uuid.uuid4(),
            institution=inst,
            created_by=user,
        )
        perm = CanGenerateReport()
        request = _make_request(user=user, institution=inst)
        request.active_membership = user._test_membership
        assert perm.has_object_permission(request, None, report) is True

    def test_object_permission_cross_institution_denied(self, db):
        """Cross-institution object permission is denied (RN-015)."""
        inst_a = Institution.objects.create(name="Inst A", code="A01")
        inst_b = Institution.objects.create(name="Inst B", code="B01")
        user = _make_user("cross@test.edu", level=4, institution=inst_a)
        report_b = Report.objects.create(
            report_type="project",
            entity_id=uuid.uuid4(),
            institution=inst_b,
            created_by=user,
        )
        perm = CanGenerateReport()
        request = _make_request(user=user, institution=inst_a)
        request.active_membership = user._test_membership
        assert perm.has_object_permission(request, None, report_b) is False

    def test_supervisor_vs_director_roles(self, db):
        """Supervisor (level 3) and Director (level 3) both pass."""
        inst = Institution.objects.create(name="Dir Inst", code="DIR01")
        director = _make_user("director@test.edu", level=3, institution=inst)
        perm = CanGenerateReport()
        request = _make_request(user=director, institution=inst)
        request.active_membership = director._test_membership
        assert perm.has_permission(request, None) is True
