"""
View tests for SIGPI auth endpoints — STRICT TDD.

Tests define the expected behavior of login/logout views
per spec FR-002 (local fallback) and FR-003 (account linking).

Spec reference: openspec/changes/auth/spec.md
Design reference: openspec/changes/auth/design.md
"""
import uuid
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.institutions.models import Institution

# The views module does not exist yet — these imports WILL fail.
# That is the point of RED: the test references code that must be built.
from apps.accounts.views import (
    account_linking_view,
    keycloak_health_view,
    local_login_view,
)

# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Django test client for API requests."""
    return Client()


@pytest.fixture
def local_user(db):
    """A local-auth user with a password."""
    user = User.objects.create_user(
        email="localuser@example.com",
        auth_source="local",
        password="testpass123",
    )
    return user


# ──────────────────────────────────────────────────────────
# Keycloak Health Endpoint
# ──────────────────────────────────────────────────────────


class TestKeycloakHealthView:
    """Keycloak availability health-check endpoint."""

    def test_health_endpoint_returns_json(self, api_client):
        """GET /auth/keycloak-status/ returns a JSON response."""
        url = reverse("keycloak_health")
        response = api_client.get(url)
        assert response.status_code == 200
        assert "application/json" in response["Content-Type"]

    def test_health_endpoint_has_status_field(self, api_client):
        """The health response includes a 'status' field."""
        url = reverse("keycloak_health")
        response = api_client.get(url)
        data = response.json()
        assert "status" in data
        assert data["status"] in ("available", "unavailable", "unknown")


# ──────────────────────────────────────────────────────────
# Local Login View (FR-002)
# ──────────────────────────────────────────────────────────


class TestLocalLoginView:
    """Local username/password login via django-allauth (FR-002)."""

    @pytest.fixture
    def login_url(self):
        return reverse("local_login")

    def test_login_requires_post(self, api_client, login_url):
        """GET requests to the login endpoint are not allowed."""
        response = api_client.get(login_url)
        assert response.status_code == 405  # Method Not Allowed

    def test_login_with_valid_credentials(self, api_client, local_user, login_url):
        """A local user can authenticate with email+password."""
        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "localuser@example.com"

    def test_login_returns_session_cookie(self, api_client, local_user, login_url):
        """Successful login sets a session cookie."""
        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        # Session cookie should be set
        assert "sessionid" in response.cookies

    def test_login_with_invalid_credentials(self, db, api_client, login_url):
        """Invalid credentials return 401."""
        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_with_missing_fields(self, api_client, login_url):
        """Missing email or password returns 400."""
        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_login_session_has_user_data(self, api_client, local_user, login_url):
        """After login, the session contains user data."""
        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        # Check /auth/me/ endpoint with the session cookie
        session_cookie = response.cookies.get("sessionid")
        api_client.cookies["sessionid"] = session_cookie

        me_url = reverse("auth_me")
        me_response = api_client.get(me_url)
        assert me_response.status_code == 200


# ──────────────────────────────────────────────────────────
# Account Linking View (FR-003)
# ──────────────────────────────────────────────────────────


class TestAccountLinkingView:
    """Manual account linking confirmation (FR-003)."""

    @pytest.fixture
    def linking_url(self):
        return reverse("account_linking")

    def test_linking_requires_post(self, api_client, linking_url):
        """GET requests to the linking endpoint are not allowed."""
        response = api_client.get(linking_url)
        assert response.status_code == 405

    def test_linking_requires_authentication(self, api_client, linking_url):
        """Unlinked user cannot access the linking endpoint."""
        response = api_client.post(
            linking_url,
            data={"confirm": True},
            content_type="application/json",
        )
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────
# Auth Me Endpoint
# ──────────────────────────────────────────────────────────


class TestAuthMeView:
    """GET /auth/me/ returns current user profile."""

    @pytest.fixture
    def me_url(self):
        return reverse("auth_me")

    def test_me_requires_authentication(self, api_client, me_url):
        """Unauthenticated users get 401."""
        response = api_client.get(me_url)
        assert response.status_code == 401

    def test_me_returns_user_data(self, api_client, local_user, me_url):
        """Authenticated user gets their profile."""
        api_client.login(username="localuser@example.com", password="testpass123")
        response = api_client.get(me_url)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "localuser@example.com"
        assert data["auth_source"] == "local"
        assert "memberships" in data


# ──────────────────────────────────────────────────────────
# Logout View
# ──────────────────────────────────────────────────────────


class TestLogoutView:
    """POST /auth/logout/ destroys the session."""

    @pytest.fixture
    def logout_url(self):
        return reverse("logout")

    def test_logout_clears_session(self, api_client, local_user, logout_url):
        """After logout, /auth/me/ returns 401."""
        api_client.login(username="localuser@example.com", password="testpass123")

        # Confirm logged in
        me_url = reverse("auth_me")
        me_before = api_client.get(me_url)
        assert me_before.status_code == 200

        # Logout
        logout_response = api_client.post(logout_url)
        assert logout_response.status_code == 200

        # Now should be unauthenticated
        me_after = api_client.get(me_url)
        assert me_after.status_code == 401
