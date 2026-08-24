"""
Permission tests for the documents module — STRICT TDD (RED phase).

Covers the Phase 4 permission contract from spec.md Authorization:
- CanWriteDocuments: write actions (presign, confirm, sign, minutes-create)
  require role level ≤ 6 (all roles except Auditor); reads (SAFE_METHODS)
  allowed for any authenticated member.
- IsSameInstitution (re-export): institution-scoped object reads.
- IsAuditor (re-export): read-only.

Test pattern: MagicMock-based request construction (matches budgets/
tests/test_permissions.py).

RED PHASE: permissions.py does not exist yet — all tests fail on import.
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

    request = MagicMock(spec=Request)
    request.user = user
    request.method = method
    request.institution_id = institution_id
    request.active_membership = membership

    return request


def _mock_view():
    return MagicMock()


# ════════════════════════════════════════════════════════
# CanWriteDocuments — has_permission
# ════════════════════════════════════════════════════════


class TestCanWriteDocumentsHasPermission:
    def test_superadmin_can_write(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", authenticated=True, is_superuser=True)
        assert CanWriteDocuments().has_permission(req, _mock_view()) is True

    def test_assistant_level_6_can_write(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", role_level=6, institution_id="inst-1")
        assert CanWriteDocuments().has_permission(req, _mock_view()) is True

    def test_researcher_level_4_can_write(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", role_level=4, institution_id="inst-1")
        assert CanWriteDocuments().has_permission(req, _mock_view()) is True

    def test_auditor_level_7_cannot_write(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", role_level=7, institution_id="inst-1")
        assert CanWriteDocuments().has_permission(req, _mock_view()) is False

    def test_unauthenticated_cannot_write(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", authenticated=False)
        assert CanWriteDocuments().has_permission(req, _mock_view()) is False

    def test_unauthenticated_cannot_read(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="GET", authenticated=False)
        assert CanWriteDocuments().has_permission(req, _mock_view()) is False

    def test_get_allows_any_authenticated_member(self):
        from apps.documents.permissions import CanWriteDocuments

        # Auditor (level 7) may read; membership not even required for SAFE.
        req = _make_request(method="GET", role_level=7, institution_id="inst-1")
        assert CanWriteDocuments().has_permission(req, _mock_view()) is True

    def test_head_and_options_are_safe(self):
        from apps.documents.permissions import CanWriteDocuments

        for method in ("HEAD", "OPTIONS"):
            req = _make_request(method=method, role_level=7, institution_id="inst-1")
            assert CanWriteDocuments().has_permission(req, _mock_view()) is True

    def test_patch_and_delete_require_level_6(self):
        from apps.documents.permissions import CanWriteDocuments

        for method in ("PATCH", "DELETE"):
            req = _make_request(method=method, role_level=7, institution_id="inst-1")
            assert CanWriteDocuments().has_permission(req, _mock_view()) is False


# ════════════════════════════════════════════════════════
# CanWriteDocuments — has_object_permission
# ════════════════════════════════════════════════════════


class TestCanWriteDocumentsObjectPermission:
    def test_object_write_requires_level_6(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", role_level=6, institution_id="inst-1")
        assert CanWriteDocuments().has_object_permission(req, _mock_view(), _FakeObj()) is True

    def test_object_write_denied_for_auditor(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="POST", role_level=7, institution_id="inst-1")
        assert CanWriteDocuments().has_object_permission(req, _mock_view(), _FakeObj()) is False

    def test_object_read_allowed_for_auditor(self):
        from apps.documents.permissions import CanWriteDocuments

        req = _make_request(method="GET", role_level=7, institution_id="inst-1")
        assert CanWriteDocuments().has_object_permission(req, _mock_view(), _FakeObj()) is True


# ════════════════════════════════════════════════════════
# IsSameInstitution re-export
# ════════════════════════════════════════════════════════


class TestIsSameInstitution:
    def test_matching_institution_allowed(self):
        from apps.documents.permissions import IsSameInstitution

        req = _make_request(institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-1"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is True

    def test_mismatched_institution_denied(self):
        from apps.documents.permissions import IsSameInstitution

        req = _make_request(institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-9"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is False

    def test_superadmin_bypasses(self):
        from apps.documents.permissions import IsSameInstitution

        req = _make_request(is_superuser=True, institution_id="inst-1")
        obj = _FakeObj()
        obj.institution_id = "inst-9"
        assert IsSameInstitution().has_object_permission(req, _mock_view(), obj) is True


# ════════════════════════════════════════════════════════
# IsAuditor re-export — read-only
# ════════════════════════════════════════════════════════


class TestIsAuditorReadOnly:
    def test_auditor_can_read(self):
        from apps.documents.permissions import IsAuditor

        req = _make_request(method="GET", role_level=7, institution_id="inst-1")
        assert IsAuditor().has_permission(req, _mock_view()) is True

    def test_auditor_cannot_write(self):
        from apps.documents.permissions import IsAuditor

        req = _make_request(method="POST", role_level=7, institution_id="inst-1")
        assert IsAuditor().has_permission(req, _mock_view()) is False

    def test_non_member_denied(self):
        from apps.documents.permissions import IsAuditor

        req = _make_request(method="GET", institution_id=None, role_level=None)
        assert IsAuditor().has_permission(req, _mock_view()) is False
