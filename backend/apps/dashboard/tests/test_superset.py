"""
Tests for the SupersetEmbedView endpoint.

Tests:
- Authentication required
- Response shape (superset_url, dashboard_id, embed_url)
- Custom dashboard_id via query param
- Default dashboard_id when not provided
"""

from django.test import Client
from django.urls import reverse
from rest_framework import status


def _make_user(email="superset_test@test.edu"):
    """Create a simple authenticated user (no membership needed for this endpoint)."""
    from apps.accounts.models import User

    return User.objects.create_user(
        email=email,
        auth_source="local",
        password="testpass123",
    )


class TestSupersetEmbedView:
    """Test Superset embed endpoint."""

    def test_unauthenticated_user_denied(self, db):
        """Unauthenticated users cannot access superset-embed."""
        client = Client()
        url = reverse("superset-embed")
        response = client.get(url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_authenticated_user_gets_embed_config(self, db):
        """Authenticated user receives Superset embed configuration."""
        user = _make_user()
        client = Client()
        client.force_login(user)

        url = reverse("superset-embed")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "superset_url" in data
        assert "dashboard_id" in data
        assert "embed_url" in data

    def test_default_dashboard_id(self, db):
        """Default dashboard_id is '1' when not provided."""
        user = _make_user()
        client = Client()
        client.force_login(user)

        url = reverse("superset-embed")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dashboard_id"] == "1"
        assert data["embed_url"].endswith("/superset/dashboard/1/")

    def test_custom_dashboard_id(self, db):
        """Custom dashboard_id is used in embed_url."""
        user = _make_user()
        client = Client()
        client.force_login(user)

        url = reverse("superset-embed") + "?dashboard_id=42"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dashboard_id"] == "42"
        assert data["embed_url"].endswith("/superset/dashboard/42/")

    def test_superset_url_from_settings(self, db):
        """superset_url matches settings.SUPERSET_URL."""
        from django.conf import settings

        user = _make_user()
        client = Client()
        client.force_login(user)

        url = reverse("superset-embed")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["superset_url"] == settings.SUPERSET_URL
