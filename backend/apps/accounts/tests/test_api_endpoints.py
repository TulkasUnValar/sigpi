"""
API endpoint tests for SIGPI PR 3 — STRICT TDD.

Tests define the expected behavior of:
- POST /auth/switch-institution/ — switch active institution (FR-004)
- GET /auth/callback/ — OIDC callback from Keycloak
- GET /auth/me/ — updated user profile with serializer shape
- POST /auth/login/ — updated to use DRF serializers

Spec references: FR-004, FR-001
Design reference: openspec/changes/auth/design.md — API Design (Expanded)
"""
import json
import uuid
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Django test client for API requests."""
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Universidad Nacional", code="UNAL")


@pytest.fixture
def other_institution(db):
    return Institution.objects.create(name="Universidad de Antioquia", code="UDEA")


@pytest.fixture
def researcher_role(db):
    return Role.objects.get(name="Investigador")


@pytest.fixture
def admin_role(db):
    return Role.objects.get(name="Admin Institucional")


@pytest.fixture
def local_user(db):
    """A local-auth user with password."""
    return User.objects.create_user(
        email="test@unal.edu.co",
        auth_source="local",
        password="testpass123",
    )


@pytest.fixture
def user_with_membership(db, local_user, institution, researcher_role):
    """User with active membership in UNAL."""
    InstitutionMembership.objects.create(
        user=local_user,
        institution=institution,
        role=researcher_role,
        is_active=True,
    )
    return local_user


@pytest.fixture
def user_multi_institution(db, local_user, institution, other_institution,
                            researcher_role, admin_role):
    """User with memberships in two institutions."""
    # Remove existing memberships first
    InstitutionMembership.objects.filter(user=local_user).delete()
    InstitutionMembership.objects.create(
        user=local_user,
        institution=institution,
        role=researcher_role,
    )
    InstitutionMembership.objects.create(
        user=local_user,
        institution=other_institution,
        role=admin_role,
    )
    return local_user


@pytest.fixture
def center(db, institution):
    return ResearchCenter.objects.create(
        name="Centro de Investigaciones",
        institution=institution,
        code="CIUNAL",
    )


# ──────────────────────────────────────────────────────────
# switch-institution endpoint (FR-004)
# ──────────────────────────────────────────────────────────


class TestSwitchInstitution:
    """POST /auth/switch-institution/ — Switch active institution."""

    def test_switch_requires_authentication(self, api_client):
        """Unauthenticated users cannot switch institution."""
        url = reverse("switch_institution")
        response = api_client.post(
            url,
            data={"institution_id": str(uuid.uuid4())},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_switch_to_valid_institution(self, api_client, user_multi_institution,
                                          other_institution):
        """User can switch to an institution they belong to."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")

        response = api_client.post(
            url,
            data={"institution_id": str(other_institution.id)},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "active_institution" in data
        assert data["active_institution"]["name"] == other_institution.name
        assert "role" in data

    def test_switch_updates_session(self, api_client, user_multi_institution,
                                      other_institution):
        """Switching updates the session institution_id."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")

        api_client.post(
            url,
            data={"institution_id": str(other_institution.id)},
            content_type="application/json",
        )

        # Verify session was updated via /auth/me/
        me_url = reverse("auth_me")
        me_response = api_client.get(me_url)
        data = me_response.json()
        assert data["active_institution_id"] == str(other_institution.id)

    def test_switch_to_invalid_institution(self, api_client, user_with_membership):
        """403 when user doesn't belong to target institution."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")
        fake_id = str(uuid.uuid4())

        response = api_client.post(
            url,
            data={"institution_id": fake_id},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_switch_to_inactive_membership(self, api_client, db, local_user,
                                             institution, researcher_role):
        """403 when membership is inactive."""
        membership = InstitutionMembership.objects.create(
            user=local_user,
            institution=institution,
            role=researcher_role,
            is_active=False,
        )
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")

        response = api_client.post(
            url,
            data={"institution_id": str(institution.id)},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_switch_requires_post(self, api_client, user_with_membership):
        """GET not allowed on switch endpoint."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")
        response = api_client.get(url)
        assert response.status_code == 405

    def test_switch_missing_institution_id(self, api_client, user_with_membership):
        """400 when institution_id is missing from request body."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")

        response = api_client.post(
            url,
            data={},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_switch_with_centers_in_response(self, api_client, db, local_user,
                                               institution, researcher_role, center):
        """Response includes centers when membership has centers assigned."""
        membership = InstitutionMembership.objects.create(
            user=local_user,
            institution=institution,
            role=researcher_role,
            is_active=True,
        )
        membership.centers.add(center)

        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("switch_institution")

        response = api_client.post(
            url,
            data={"institution_id": str(institution.id)},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "centers" in data
        assert len(data["centers"]) == 1
        assert data["centers"][0]["name"] == center.name


# ──────────────────────────────────────────────────────────
# /auth/me/ — Updated user profile
# ──────────────────────────────────────────────────────────


class TestAuthMeUpdated:
    """GET /auth/me/ returns full user profile with serializer shape."""

    def test_me_includes_active_institution(self, api_client, user_multi_institution,
                                              institution):
        """me response includes active_institution_id and active_role from session."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        # Simulate having switched to an institution
        session = api_client.session
        session["institution_id"] = str(institution.id)
        session["active_role"] = "Investigador"
        session.save()

        url = reverse("auth_me")
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["active_institution_id"] == str(institution.id)
        assert data["active_role"] == "Investigador"

    def test_me_includes_centers_in_memberships(self, api_client, db, local_user,
                                                  institution, researcher_role,
                                                  center):
        """Memberships in me response include centers list."""
        membership = InstitutionMembership.objects.create(
            user=local_user,
            institution=institution,
            role=researcher_role,
            is_active=True,
        )
        membership.centers.add(center)

        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("auth_me")
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "memberships" in data
        assert len(data["memberships"]) >= 1
        m = data["memberships"][0]
        assert "centers" in m
        if m["centers"]:
            assert m["centers"][0]["name"] == center.name

    def test_me_includes_is_superuser(self, api_client, user_with_membership):
        """me response includes is_superuser flag."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("auth_me")
        response = api_client.get(url)
        data = response.json()
        assert "is_superuser" in data
        assert data["is_superuser"] is False

    def test_me_includes_auth_source(self, api_client, user_with_membership):
        """me response includes auth_source field."""
        api_client.login(
            username="test@unal.edu.co", password="testpass123"
        )
        url = reverse("auth_me")
        response = api_client.get(url)
        data = response.json()
        assert data["auth_source"] == "local"


# ──────────────────────────────────────────────────────────
# /auth/callback/ — OIDC Callback
# ──────────────────────────────────────────────────────────


class TestOIDCCallback:
    """GET /auth/callback/ — OIDC authorization code callback."""

    def test_callback_endpoint_exists(self, api_client):
        """The OIDC callback URL is registered."""
        url = reverse("oidc_callback")
        # Callback is handled by mozilla-django-oidc which requires
        # code+state params. Without them, the view will fail.
        # We just verify the endpoint is reachable (200 or 302).
        response = api_client.get(url)
        # mozilla-django-oidc will fail to validate, resulting in error
        assert response.status_code in (302, 400, 403)

    @patch("mozilla_django_oidc.views.OIDCAuthenticationCallbackView.get")
    def test_callback_delegates_to_oidc_view(self, mock_get, api_client):
        """The callback URL routes to mozilla-django-oidc callback view."""
        from django.http import HttpResponseRedirect
        mock_get.return_value = HttpResponseRedirect("/dashboard/")
        url = reverse("oidc_callback")
        response = api_client.get(url)
        assert response.status_code == 302


# ──────────────────────────────────────────────────────────
# /auth/login/ — Updated login response shape
# ──────────────────────────────────────────────────────────


class TestLoginResponseShape:
    """POST /auth/login/ returns proper DRF serializer response."""

    def test_login_response_includes_user_id(self, api_client, user_with_membership):
        """Login response includes user id as a string UUID."""
        response = api_client.post(
            reverse("local_login"),
            data={"email": "test@unal.edu.co", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "id" in data["user"]
        assert data["user"]["email"] == "test@unal.edu.co"

    def test_login_sets_active_institution_from_primary(self, api_client, db,
                                                          local_user, institution,
                                                          researcher_role):
        """Login sets institution_id in session from primary membership."""
        InstitutionMembership.objects.create(
            user=local_user,
            institution=institution,
            role=researcher_role,
            is_primary=True,
        )
        response = api_client.post(
            reverse("local_login"),
            data={"email": "test@unal.edu.co", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        # Verify session has institution_id
        session = api_client.session
        assert session.get("institution_id") == str(institution.id)
