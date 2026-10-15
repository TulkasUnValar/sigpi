"""
View layer tests for dashboard endpoint.

Tests:
- Authentication required
- Permission levels (allowed/denied roles)
- Response shape and serializer validation
- Institution scoping via request.institution_id
"""

from django.test import Client
from django.urls import reverse
from rest_framework import status


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _make_user_with_membership(institution, role_level, is_superuser=False):
    """Helper to create a user with membership at specific role level."""
    from apps.accounts.models import InstitutionMembership, Role, User

    user = User.objects.create_user(
        email=f"view_{User.objects.count()}@test.edu",
        auth_source="local",
        password="testpass123",
        is_superuser=is_superuser,
    )

    if institution and role_level:
        # Map role_level to seeded role names from migration 0002_seed_roles.py
        role_level_to_name = {
            1: "Superadmin",
            2: "Admin Institucional",
            3: "Director de Centro",
            4: "Investigador",
            5: "Evaluador",
            6: "Asistente",
            7: "Auditor",
        }
        role_name = role_level_to_name.get(role_level)
        if not role_name:
            raise ValueError(f"Invalid role_level: {role_level}")

        # Get the seeded role (should exist from migration)
        role = Role.objects.get(name=role_name)

        membership = InstitutionMembership.objects.create(
            user=user,
            institution=institution,
            role=role,
            is_active=True,
        )
        # Store membership on user for easy access in tests
        user._test_membership = membership

    return user


class TestDashboardPermissions:
    """Test role-based access control."""

    def test_unauthenticated_user_denied(self, db):
        """Unauthenticated users cannot access dashboard."""
        client = Client()
        url = reverse("dashboard-summary")
        response = client.get(url)
        # DRF returns 403 for unauthenticated users (not 401)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_superadmin_has_access(self, db):
        """Superadmin (level 1) can access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=1)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_has_access(self, db):
        """Admin (level 2) can access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=2)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_director_has_access(self, db):
        """Director (level 3) can access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=3)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_researcher_has_access(self, db):
        """Researcher (level 4) can access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=4)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_auditor_has_access(self, db):
        """Auditor (level 7) can access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=7)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_evaluador_denied(self, db):
        """Evaluador (level 5) cannot access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=5)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_asistente_denied(self, db):
        """Asistente (level 6) cannot access dashboard."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=6)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_no_institution_returns_400(self, db):
        """User without active institution gets 400."""
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="no_inst@test.edu", auth_source="local", password="testpass123"
        )

        client = Client()
        client.force_login(user)
        # No institution_id in session

        url = reverse("dashboard-summary")
        response = client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Middleware returns JsonResponse, so use json() instead of data
        response_data = response.json()
        assert "institution" in response_data.get("detail", "").lower()


class TestDashboardResponseShape:
    """Test response structure and data types."""

    def test_response_contains_all_indicators(self, db):
        """Response includes all 14 indicators."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=1)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check all 14 indicators present
        indicators = data["indicators"]
        assert "IND-001" in indicators
        assert "IND-002" in indicators
        assert "IND-003" in indicators
        assert "IND-004" in indicators
        assert "IND-005" in indicators
        assert "IND-006" in indicators
        assert "IND-007" in indicators
        assert "IND-008" in indicators
        assert "IND-009" in indicators
        assert "IND-010" in indicators
        assert "IND-011" in indicators
        assert "IND-012" in indicators
        assert "IND-013" in indicators
        assert "IND-014" in indicators

    def test_response_contains_charts(self, db):
        """Response includes charts section."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=1)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check charts structure
        charts = data["charts"]
        assert "projects_by_status" in charts
        assert "projects_by_center" in charts
        assert "budget" in charts
        assert "progress_reports" in charts

    def test_indicator_data_types(self, db):
        """Verify data types for each indicator."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=1)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        data = response.json()["indicators"]

        # Integer indicators
        assert isinstance(data["IND-001"], int)
        assert isinstance(data["IND-004"], int)
        assert isinstance(data["IND-005"], int)
        assert isinstance(data["IND-013"], int)
        assert isinstance(data["IND-014"], int)

        # List indicators
        assert isinstance(data["IND-002"], list)
        assert isinstance(data["IND-003"], list)
        assert isinstance(data["IND-010"], list)
        assert isinstance(data["IND-011"], list)

        # Float indicator
        assert isinstance(data["IND-006"], float)

        # String indicators (formatted decimals)
        assert isinstance(data["IND-007"], str)
        assert isinstance(data["IND-008"], str)
        assert isinstance(data["IND-009"], str)

        # Dict indicator
        assert isinstance(data["IND-012"], dict)
        assert "total" in data["IND-012"]
        assert "complete" in data["IND-012"]
        assert "rate" in data["IND-012"]

    def test_empty_institution_returns_zeros(self, db):
        """Empty institution returns zero values."""
        from apps.institutions.tests.conftest import InstitutionFactory

        institution = InstitutionFactory()
        user = _make_user_with_membership(institution, role_level=1)

        client = Client()
        _login(client, user, institution)

        url = reverse("dashboard-summary")
        response = client.get(url)
        data = response.json()["indicators"]

        assert data["IND-001"] == 0
        assert data["IND-004"] == 0
        assert data["IND-005"] == 0
        assert data["IND-007"] == "0.00"
        assert data["IND-008"] == "0.00"
        assert data["IND-009"] == "0.00"
        assert data["IND-013"] == 0
        assert data["IND-014"] == 0
