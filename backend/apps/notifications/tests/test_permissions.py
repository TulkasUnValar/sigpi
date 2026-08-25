"""
Permission tests for the notifications module — STRICT TDD (RED phase).

Unit-level: IsNotificationOwner and IsAdminOrOwner object permission logic.
API-level:   the queryset enforces recipient == request.user, so cross-user
             access is a 404 even for admins and superusers (design invariant).

Spec reference: openspec/changes/notifications/spec.md — Permissions Matrix
Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
"""

import uuid
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution
from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.permissions import IsAdminOrOwner, IsNotificationOwner

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _request(user, institution=None, membership=None):
    """Minimal DRF-Request-shaped object for unit-level permission checks."""
    return SimpleNamespace(
        user=user,
        institution_id=str(institution.pk) if institution else None,
        active_membership=membership,
    )


def _make_notification(recipient, institution):
    template = NotificationTemplate.objects.get(code="PROJECT_SUBMITTED")
    return Notification.objects.create(
        institution=institution,
        recipient=recipient,
        event_type="PROJECT_SUBMITTED",
        template=template,
        title="Test notification",
        body="Test body",
        context={},
        entity_type="project",
        entity_id=uuid.uuid4(),
    )


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def researcher_role(db):
    return get_role("Investigador")


@pytest.fixture
def admin_role(db):
    return get_role("Admin Institucional")


@pytest.fixture
def owner_user(db, institution, researcher_role):
    user = User.objects.create_user(email="owner@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def other_user(db, institution, researcher_role):
    user = User.objects.create_user(email="other@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(email="admin@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="root@test.edu", password="p")


@pytest.fixture
def notification(owner_user, institution):
    return _make_notification(owner_user, institution)


# ════════════════════════════════════════════════════════
# IsNotificationOwner
# ════════════════════════════════════════════════════════


class TestIsNotificationOwner:
    def test_owner_allowed(self, notification, owner_user):
        perm = IsNotificationOwner()
        req = _request(owner_user)
        assert perm.has_permission(req, None) is True
        assert perm.has_object_permission(req, None, notification) is True

    def test_other_user_denied(self, notification, other_user):
        perm = IsNotificationOwner()
        req = _request(other_user)
        assert perm.has_object_permission(req, None, notification) is False

    def test_anonymous_denied(self, notification):
        perm = IsNotificationOwner()
        req = _request(AnonymousUser())
        assert perm.has_permission(req, None) is False
        assert perm.has_object_permission(req, None, notification) is False


# ════════════════════════════════════════════════════════
# IsAdminOrOwner
# ════════════════════════════════════════════════════════


class TestIsAdminOrOwner:
    def test_superuser_allowed_any(self, notification, superuser):
        perm = IsAdminOrOwner()
        req = _request(superuser)
        assert perm.has_object_permission(req, None, notification) is True

    def test_admin_allowed_any(self, notification, admin_user, institution):
        perm = IsAdminOrOwner()
        membership = InstitutionMembership.objects.get(user=admin_user, institution=institution)
        req = _request(admin_user, institution, membership)
        assert perm.has_object_permission(req, None, notification) is True

    def test_owner_allowed(self, notification, owner_user):
        perm = IsAdminOrOwner()
        req = _request(owner_user)
        assert perm.has_object_permission(req, None, notification) is True

    def test_other_researcher_denied(self, notification, other_user):
        perm = IsAdminOrOwner()
        req = _request(other_user)
        assert perm.has_object_permission(req, None, notification) is False

    def test_anonymous_denied(self, notification):
        perm = IsAdminOrOwner()
        req = _request(AnonymousUser())
        assert perm.has_permission(req, None) is False
        assert perm.has_object_permission(req, None, notification) is False


# ════════════════════════════════════════════════════════
# Queryset enforcement (recipient == request.user, incl. superusers)
# ════════════════════════════════════════════════════════


class TestQuerysetEnforcement:
    def test_admin_cross_user_detail_404(self, api_client, institution, admin_user, notification):
        _login(api_client, admin_user, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[notification.id]))
        assert r.status_code == 404

    def test_superuser_cross_user_detail_404(self, api_client, institution, superuser, notification):
        _login(api_client, superuser, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[notification.id]))
        assert r.status_code == 404

    def test_own_detail_200(self, api_client, institution, owner_user, notification):
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[notification.id]))
        assert r.status_code == 200
