"""
Manager tests for SIGPI TenantScopedQuerySet — STRICT TDD.

Tests define the expected behavior of:
- TenantScopedQuerySet.for_tenant(): auto-filter by institution_id
- Superadmin bypass: returns unfiltered queryset
- Edge cases: no institution, no request attr

Design reference: openspec/changes/auth/design.md — TenantScopedQuerySet
"""

from unittest.mock import MagicMock

import pytest
from django.http import HttpRequest
from rest_framework.request import Request

# ── RED: These imports WILL fail until managers.py is created ──
from apps.accounts.managers import TenantScopedQuerySet
from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution

# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def make_request(user=None, institution_id=None, is_superuser=False):
    """Build a DRF-style request with tenant attributes."""
    http_req = HttpRequest()
    if user is not None:
        http_req.user = user
    else:
        http_req.user = MagicMock(is_authenticated=False, is_superuser=is_superuser)
    http_req.institution_id = institution_id

    drf_request = Request(http_req)
    # DRF Request.user authenticates from session, not HttpRequest.user.
    # Pre-set _user to bypass this for unit tests.
    drf_request._user = http_req.user  # type: ignore
    return drf_request


# ──────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────


class TestTenantScopedQuerySet:
    """Tests for TenantScopedQuerySet.for_tenant() method."""

    def test_filters_by_institution_id(self, db, institution):
        """Queryset is filtered to only the request's institution."""
        other_inst = Institution.objects.create(name="Other Inst", code="OTHER")

        # Create users in each institution
        user_a = User.objects.create_user(email="a@test.com", auth_source="local", password="pass")
        role = Role.objects.get(name="Investigador")
        InstitutionMembership.objects.create(
            user=user_a, institution=institution, role=role, is_active=True
        )

        user_b = User.objects.create_user(email="b@test.com", auth_source="local", password="pass")
        InstitutionMembership.objects.create(
            user=user_b, institution=other_inst, role=role, is_active=True
        )

        request = make_request(institution_id=str(institution.id))
        qs = TenantScopedQuerySet(model=InstitutionMembership)
        filtered = qs.for_tenant(request)

        # Should only include membership from the active institution
        assert filtered.count() == 1
        assert filtered.first().user.email == "a@test.com"

    def test_superadmin_bypasses_filter(self, db, institution):
        """Superadmin gets unfiltered queryset (all institutions)."""
        other_inst = Institution.objects.create(name="Other Inst", code="OTHER")

        user_a = User.objects.create_user(email="a@test.com", auth_source="local", password="pass")
        role = Role.objects.get(name="Investigador")
        InstitutionMembership.objects.create(
            user=user_a, institution=institution, role=role, is_active=True
        )

        user_b = User.objects.create_user(email="b@test.com", auth_source="local", password="pass")
        InstitutionMembership.objects.create(
            user=user_b, institution=other_inst, role=role, is_active=True
        )

        superuser = User.objects.create_superuser(email="super@test.com", password="pass")
        request = make_request(
            user=superuser,
            institution_id=str(institution.id),
            is_superuser=True,
        )
        qs = TenantScopedQuerySet(model=InstitutionMembership)
        filtered = qs.for_tenant(request)

        # Superadmin sees all institutions
        assert filtered.count() == 2

    def test_no_institution_returns_all(self, db):
        """When no institution_id is set, returns unfiltered queryset."""
        inst = Institution.objects.create(name="Inst", code="INST")
        user = User.objects.create_user(email="u@test.com", auth_source="local", password="pass")
        role = Role.objects.get(name="Investigador")
        InstitutionMembership.objects.create(user=user, institution=inst, role=role, is_active=True)

        request = make_request(institution_id=None)
        qs = TenantScopedQuerySet(model=InstitutionMembership)
        filtered = qs.for_tenant(request)

        assert filtered.count() == 1  # unfiltered — all rows

    def test_returns_same_queryset_when_no_institution_id_attribute(self):
        """If request has no institution_id attr, returns unfiltered queryset."""
        http_req = HttpRequest()
        http_req.user = MagicMock(is_authenticated=False, is_superuser=False)
        request = Request(http_req)  # No institution_id set

        qs = TenantScopedQuerySet(model=User)
        filtered = qs.for_tenant(request)

        # Should not crash, and should return unfiltered (identity)
        assert filtered is qs or filtered.count() == qs.count()

    def test_works_with_user_model(self, db, institution):
        """for_tenant works with models that have institution_id FK."""
        user_in = User.objects.create_user(
            email="in@test.com", auth_source="local", password="pass"
        )
        role = Role.objects.get(name="Investigador")
        InstitutionMembership.objects.create(
            user=user_in, institution=institution, role=role, is_active=True
        )

        # Create another user with no membership in this institution
        other_inst = Institution.objects.create(name="Other", code="OTH")
        user_out = User.objects.create_user(
            email="out@test.com", auth_source="local", password="pass"
        )
        InstitutionMembership.objects.create(
            user=user_out, institution=other_inst, role=role, is_active=True
        )

        request = make_request(institution_id=str(institution.id))
        qs = TenantScopedQuerySet(model=InstitutionMembership)
        filtered = qs.for_tenant(request)

        assert filtered.count() == 1
        assert filtered.first().user.email == "in@test.com"
