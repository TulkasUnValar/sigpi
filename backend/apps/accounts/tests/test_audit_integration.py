"""
Audit integration tests — verifies AuditEventEmitter is wired into views and tasks.

Tests that each auth endpoint emits the correct audit event:
- Local login success → LOGIN
- Local login failure → FAILED_LOGIN
- Logout → LOGOUT
- Institution switch → INSTITUTION_SWITCH
- Role sync → ROLE_CHANGE (when roles actually change)
- OIDC login → LOGIN (via user_logged_in signal)

Spec references: FR-007
Design reference: openspec/changes/auth/design.md — AuditEventEmitter
"""
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.audit import AuditEvent, AuditEventType
from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution

# Module-level import so mock paths resolve correctly
from apps.accounts.tasks import sync_keycloak_roles  # noqa: F401


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    """Django test client for API requests."""
    return Client(REMOTE_ADDR="192.168.1.100")


@pytest.fixture
def local_user(db):
    """A local-auth user with a password and primary institution membership."""
    user = User.objects.create_user(
        email="localuser@example.com",
        auth_source="local",
        password="testpass123",
    )
    inst = Institution.objects.create(name="Universidad Test", code="UTEST")
    role = Role.objects.get(name="Investigador")
    InstitutionMembership.objects.create(
        user=user,
        institution=inst,
        role=role,
        is_primary=True,
    )
    return user


@pytest.fixture
def institution(db, local_user):
    """The institution associated with local_user."""
    return Institution.objects.get(code="UTEST")


@pytest.fixture
def other_institution(db):
    """Another institution for switch testing."""
    return Institution.objects.create(name="Otra Universidad", code="OTRA")


@pytest.fixture
def researcher_role(db):
    """The default researcher role."""
    return Role.objects.get(name="Investigador")


# ──────────────────────────────────────────────────────────
# Test: Local Login → LOGIN / FAILED_LOGIN audit events
# ──────────────────────────────────────────────────────────


class TestLoginAudit:
    """Audit events emitted during local login."""

    def test_successful_login_emits_login_event(self, api_client, local_user):
        """A successful local login emits a LOGIN audit event."""
        login_url = reverse("local_login")
        count_before = AuditEvent.objects.count()

        response = api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert AuditEvent.objects.count() == count_before + 1

        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.LOGIN
        assert event.user == local_user
        assert event.ip_address == "192.168.1.100"

    def test_failed_login_emits_failed_login_event(self, api_client, db):
        """A failed local login emits a FAILED_LOGIN audit event."""
        login_url = reverse("local_login")
        count_before = AuditEvent.objects.count()

        response = api_client.post(
            login_url,
            data={"email": "nobody@example.com", "password": "wrong"},
            content_type="application/json",
        )

        assert response.status_code == 401
        assert AuditEvent.objects.count() == count_before + 1

        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.FAILED_LOGIN
        assert event.user is None
        assert event.ip_address == "192.168.1.100"
        assert event.details["email_attempted"] == "nobody@example.com"

    def test_failed_login_with_disabled_user_emits_event(self, api_client, db):
        """Login with a disabled (inactive) user emits FAILED_LOGIN."""
        disabled = User.objects.create_user(
            email="disabled@example.com",
            auth_source="local",
            password="testpass123",
            is_active=False,
        )
        login_url = reverse("local_login")
        count_before = AuditEvent.objects.count()

        response = api_client.post(
            login_url,
            data={"email": "disabled@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        assert response.status_code == 401
        assert AuditEvent.objects.count() == count_before + 1
        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.FAILED_LOGIN
        assert event.details["email_attempted"] == "disabled@example.com"


# ──────────────────────────────────────────────────────────
# Test: Logout → LOGOUT audit event
# ──────────────────────────────────────────────────────────


class TestLogoutAudit:
    """Audit events emitted during logout."""

    def test_logout_emits_logout_event(self, api_client, local_user):
        """POST /auth/logout/ emits a LOGOUT audit event."""
        # Login first
        api_client.login(username="localuser@example.com", password="testpass123")

        logout_url = reverse("logout")
        count_before = AuditEvent.objects.count()

        response = api_client.post(logout_url)

        assert response.status_code == 200
        assert AuditEvent.objects.count() == count_before + 1

        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.LOGOUT
        assert event.user == local_user

    def test_logout_with_institution_in_session(self, api_client, local_user, institution):
        """Logout event includes institution_id when set in session."""
        api_client.login(username="localuser@example.com", password="testpass123")
        # Set session institution
        session = api_client.session
        session["institution_id"] = str(institution.id)
        session.save()

        logout_url = reverse("logout")
        response = api_client.post(logout_url)

        assert response.status_code == 200
        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.LOGOUT
        assert event.institution_id == institution.id


# ──────────────────────────────────────────────────────────
# Test: Institution Switch → INSTITUTION_SWITCH audit event
# ──────────────────────────────────────────────────────────


class TestInstitutionSwitchAudit:
    """Audit events emitted during institution switch."""

    def test_switch_institution_emits_event(
        self, api_client, local_user, institution, other_institution, researcher_role
    ):
        """Switching institution emits INSTITUTION_SWITCH with old/new context."""
        # Add membership to other institution
        InstitutionMembership.objects.create(
            user=local_user,
            institution=other_institution,
            role=researcher_role,
        )
        api_client.login(username="localuser@example.com", password="testpass123")
        # Set current institution in session (simulating post-login state)
        session = api_client.session
        session["institution_id"] = str(institution.id)
        session.save()

        switch_url = reverse("switch_institution")
        count_before = AuditEvent.objects.count()

        response = api_client.post(
            switch_url,
            data={"institution_id": str(other_institution.id)},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert AuditEvent.objects.count() == count_before + 1

        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.INSTITUTION_SWITCH
        assert event.user == local_user
        assert event.institution_id == other_institution.id
        assert "previous_institution_id" in event.details
        assert event.details["previous_institution_id"] == str(institution.id)

    def test_switch_fails_no_membership_does_not_emit(self, api_client, local_user, other_institution):
        """Failed switch (no membership) does NOT emit an audit event."""
        api_client.login(username="localuser@example.com", password="testpass123")

        switch_url = reverse("switch_institution")
        count_before = AuditEvent.objects.count()

        response = api_client.post(
            switch_url,
            data={"institution_id": str(other_institution.id)},
            content_type="application/json",
        )

        assert response.status_code == 403
        assert AuditEvent.objects.count() == count_before  # No new events


# ──────────────────────────────────────────────────────────
# Test: Role Sync → ROLE_CHANGE audit event
# ──────────────────────────────────────────────────────────


class TestRoleSyncAudit:
    """Audit events emitted during Keycloak role sync."""

    @patch("apps.accounts.tasks._sync_user_groups")
    @patch("apps.accounts.tasks._fetch_keycloak_users")
    def test_role_change_emits_audit_event(self, mock_fetch, mock_sync, db):
        """When _sync_user_groups returns changed=True, a ROLE_CHANGE event is emitted."""
        kc_uuid = str(uuid.uuid4())
        user = User.objects.create_user(
            email="kcuser@example.com",
            auth_source="keycloak",
            keycloak_uuid=kc_uuid,
            password="pass",
        )

        # Ensure groups exist
        Group.objects.get_or_create(name="sigpi_researcher")
        Group.objects.get_or_create(name="sigpi_admin")

        mock_fetch.side_effect = [
            [{"id": kc_uuid, "email": "kcuser@example.com", "realmRoles": ["sigpi_admin"]}],
            [],
        ]
        mock_sync.return_value = {
            "added": ["sigpi_admin"],
            "removed": ["sigpi_researcher"],
            "changed": True,
        }

        count_before = AuditEvent.objects.count()
        result = sync_keycloak_roles()

        assert result["synced"] == 1
        assert AuditEvent.objects.count() == count_before + 1

        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.ROLE_CHANGE
        assert event.user == user
        assert event.details["added"] == ["sigpi_admin"]
        assert event.details["removed"] == ["sigpi_researcher"]

    @patch("apps.accounts.tasks._sync_user_groups")
    @patch("apps.accounts.tasks._fetch_keycloak_users")
    def test_no_role_change_does_not_emit(self, mock_fetch, mock_sync, db):
        """When _sync_user_groups returns changed=False, no event is emitted."""
        kc_uuid = str(uuid.uuid4())
        User.objects.create_user(
            email="kcuser@example.com",
            auth_source="keycloak",
            keycloak_uuid=kc_uuid,
            password="pass",
        )

        mock_fetch.side_effect = [
            [{"id": kc_uuid, "email": "kcuser@example.com", "realmRoles": ["sigpi_researcher"]}],
            [],
        ]
        mock_sync.return_value = {"added": [], "removed": [], "changed": False}

        count_before = AuditEvent.objects.count()
        sync_keycloak_roles()
        assert AuditEvent.objects.count() == count_before  # No new events


# ──────────────────────────────────────────────────────────
# Test: OIDC Login → LOGIN audit event (via user_logged_in signal)
# ──────────────────────────────────────────────────────────


class TestOIDCLoginAudit:
    """OIDC login emits LOGIN via Django's user_logged_in signal."""

    def test_oidc_login_signal_emits_login_event(self, db):
        """When a keycloak user logs in, a LOGIN audit event is emitted."""
        from django.contrib.auth import login as auth_login
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware

        kc_uuid = uuid.uuid4()
        user = User.objects.create_user(
            email="oidcuser@example.com",
            auth_source="keycloak",
            keycloak_uuid=kc_uuid,
        )
        # Must set backend for login() to work
        user.backend = "apps.accounts.backends.SIGPIOIDCBackend"

        count_before = AuditEvent.objects.count()

        factory = RequestFactory()
        request = factory.get("/auth/callback/")
        request.META["REMOTE_ADDR"] = "203.0.113.50"
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

        auth_login(request, user)

        assert AuditEvent.objects.count() == count_before + 1
        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.LOGIN
        assert event.user == user
        assert event.ip_address == "203.0.113.50"

    def test_local_login_does_not_double_emit_via_signal(self, api_client, local_user):
        """The signal handler skips local-auth users to avoid double-counting."""
        # local_user has auth_source='local'
        # The signal handler should NOT emit for local users
        # because local_login_view handles it explicitly
        login_url = reverse("local_login")
        count_before = AuditEvent.objects.count()

        api_client.post(
            login_url,
            data={"email": "localuser@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        # Only ONE event should be emitted (by local_login_view, not the signal)
        assert AuditEvent.objects.count() == count_before + 1
        event = AuditEvent.objects.latest("timestamp")
        assert event.event_type == AuditEventType.LOGIN
