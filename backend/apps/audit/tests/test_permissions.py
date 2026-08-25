"""
IsAuditReader permission tests — STRICT TDD (RED phase).

Tests define the read authorization contract from design.md and the
spec permissions matrix (RA-8):

- Allowed: Auditor (7), Director de Centro (3), Admin Institucional (2),
  Superadmin (1) — including Django superuser bypass.
- Denied: Investigador (4), Evaluador/Coinvestigador (5), Asistente (6),
  users without membership, anonymous users, and non-safe methods.

Design reference: openspec/changes/audit/design.md — Read authorization
Spec reference:   openspec/changes/audit/specs/audit/spec.md — Permissions Matrix
"""

from unittest.mock import MagicMock

import pytest
from django.http import HttpRequest
from rest_framework.request import Request

from apps.accounts.models import InstitutionMembership, Role, User
from apps.accounts.tests._helpers import get_role
from apps.audit.permissions import IsAuditReader
from apps.institutions.models import Institution

# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


@pytest.fixture
def auditor_role(db) -> Role:
    return get_role("Auditor")


@pytest.fixture
def director_role(db) -> Role:
    return get_role("Director de Centro")


@pytest.fixture
def admin_role(db) -> Role:
    return get_role("Admin Institucional")


@pytest.fixture
def researcher_role(db) -> Role:
    return get_role("Investigador")


@pytest.fixture
def evaluador_role(db) -> Role:
    return get_role("Evaluador")


@pytest.fixture
def assistant_role(db) -> Role:
    return get_role("Asistente")


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _make_user(email: str, **extra) -> User:
    return User.objects.create_user(email=email, auth_source="local", password="pass", **extra)


def _make_request(user, institution_id=None, membership=None, method="GET") -> Request:
    """Build a DRF Request carrying the same attributes TenantMiddleware sets."""
    http_req = HttpRequest()
    http_req.method = method
    http_req.user = user if user is not None else MagicMock(is_authenticated=False)
    http_req.institution_id = institution_id
    http_req.active_membership = membership

    drf_request = Request(http_req)
    drf_request._user = http_req.user  # type: ignore
    return drf_request


def _make_membership(user, institution, role, is_active=True) -> InstitutionMembership:
    return InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=role,
        is_active=is_active,
    )


# ──────────────────────────────────────────────────────────
# Allowed roles
# ──────────────────────────────────────────────────────────


class TestIsAuditReaderAllowedRoles:
    """Auditor, Director, Admin Institucional, and Superadmin can read."""

    def test_auditor_allowed(self, db, institution, auditor_role):
        user = _make_user("auditor@test.com")
        membership = _make_membership(user, institution, auditor_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is True

    def test_director_allowed(self, db, institution, director_role):
        user = _make_user("director@test.com")
        membership = _make_membership(user, institution, director_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is True

    def test_admin_institucional_allowed(self, db, institution, admin_role):
        user = _make_user("admin@test.com")
        membership = _make_membership(user, institution, admin_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is True

    def test_superadmin_role_allowed(self, db, institution, admin_role):
        """Role 'Superadmin' (level 1) may read even without the Django flag."""
        superadmin_role = Role.objects.get(name="Superadmin")
        user = _make_user("superadmin@test.com")
        membership = _make_membership(user, institution, superadmin_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is True

    def test_django_superuser_bypasses_without_membership(self, db, institution):
        """Django superuser may read cross-institution without any membership."""
        user = User.objects.create_superuser(email="root@test.com", password="pass")
        request = _make_request(user, institution_id=None, membership=None)

        assert IsAuditReader().has_permission(request, None) is True


# ──────────────────────────────────────────────────────────
# Denied roles
# ──────────────────────────────────────────────────────────


class TestIsAuditReaderDeniedRoles:
    """Researchers, coinvestigators (Evaluador), and assistants are denied."""

    def test_researcher_denied(self, db, institution, researcher_role):
        user = _make_user("researcher@test.com")
        membership = _make_membership(user, institution, researcher_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is False

    def test_coinvestigator_denied(self, db, institution, evaluador_role):
        """Coinvestigador maps to Evaluador (level 5) — must be denied."""
        user = _make_user("coinvest@test.com")
        membership = _make_membership(user, institution, evaluador_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is False

    def test_assistant_denied(self, db, institution, assistant_role):
        user = _make_user("assistant@test.com")
        membership = _make_membership(user, institution, assistant_role)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is False

    def test_anonymous_denied(self, db):
        request = _make_request(user=None, institution_id=None, membership=None)

        assert IsAuditReader().has_permission(request, None) is False

    def test_no_membership_denied(self, db, institution):
        user = _make_user("nomember@test.com")
        request = _make_request(user, institution_id=str(institution.pk), membership=None)

        assert IsAuditReader().has_permission(request, None) is False

    def test_inactive_membership_denied(self, db, institution, auditor_role):
        user = _make_user("inactive@test.com")
        membership = _make_membership(user, institution, auditor_role, is_active=False)
        request = _make_request(user, institution_id=str(institution.pk), membership=membership)

        assert IsAuditReader().has_permission(request, None) is False


# ──────────────────────────────────────────────────────────
# Read-only methods
# ──────────────────────────────────────────────────────────


class TestIsAuditReaderReadOnly:
    """The audit API is read-only: non-safe methods are denied."""

    def test_post_denied_for_auditor(self, db, institution, auditor_role):
        user = _make_user("auditor@test.com")
        membership = _make_membership(user, institution, auditor_role)
        request = _make_request(
            user, institution_id=str(institution.pk), membership=membership, method="POST"
        )

        assert IsAuditReader().has_permission(request, None) is False
