"""
API tests for the notifications module — STRICT TDD (RED phase).

Covers the API Contract from spec.md and design.md for PR 4:
- GET   /api/notifications/               list own notifications (paginated 50, -created_at)
- GET   /api/notifications/{id}/          detail — own notification only (cross-user 404)
- POST  /api/notifications/{id}/read/     mark read (idempotent)
- POST  /api/notifications/read_all/      mark all own notifications read
- GET   /api/notifications/unread_count/  unread count of own notifications
- GET/PATCH /api/notifications/preferences/   own UserPreference (list/retrieve/update)

Design invariants:
- recipient == request.user enforced at queryset level (incl. superusers) → cross-user 404
- /api/notifications/ requires an active tenant → 400 without institution
- filters: is_read, event_type, entity_type, entity_id, date_from, date_to

Spec reference: openspec/changes/notifications/spec.md — API Contract
Design reference: openspec/changes/notifications/design.md — Interfaces / Contracts
"""

import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution
from apps.notifications.models import Notification, NotificationTemplate, UserPreference

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _make_notification(
    recipient,
    institution,
    *,
    event_type="PROJECT_SUBMITTED",
    entity_type="project",
    entity_id=None,
    is_read=False,
    read_at=None,
):
    template = NotificationTemplate.objects.get(code=event_type)
    return Notification.objects.create(
        institution=institution,
        recipient=recipient,
        event_type=event_type,
        template=template,
        title="Test notification",
        body="Test body",
        context={"source": "test"},
        entity_type=entity_type,
        entity_id=entity_id or uuid.uuid4(),
        is_read=is_read,
        read_at=read_at,
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
def admin_role(db):
    return get_role("Admin Institucional")


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
# NotificationViewSet — list
# ════════════════════════════════════════════════════════


class TestNotificationList:
    def test_list_requires_tenant(self, api_client, owner_user, institution):
        """No active institution in session → 400 (TENANT_REQUIRED_PREFIXES)."""
        api_client.force_login(owner_user)
        r = api_client.get(reverse("notifications:notification-list"))
        assert r.status_code == 400

    def test_list_unauthenticated_denied(self, api_client):
        r = api_client.get(reverse("notifications:notification-list"))
        assert r.status_code == 403

    def test_list_returns_only_own_notifications(
        self, api_client, institution, owner_user, other_user
    ):
        own = [_make_notification(owner_user, institution) for _ in range(3)]
        _make_notification(other_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"))
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 3
        assert {item["id"] for item in data["results"]} == {str(n.id) for n in own}

    def test_list_default_ordering_newest_first(
        self, api_client, institution, owner_user
    ):
        base = timezone.now()
        n1 = _make_notification(owner_user, institution)
        n2 = _make_notification(owner_user, institution)
        n3 = _make_notification(owner_user, institution)
        Notification.objects.filter(pk=n1.pk).update(created_at=base - timedelta(days=3))
        Notification.objects.filter(pk=n2.pk).update(created_at=base - timedelta(days=2))
        Notification.objects.filter(pk=n3.pk).update(created_at=base - timedelta(days=1))
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"))
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["results"]]
        assert ids == [str(n3.id), str(n2.id), str(n1.id)]

    def test_list_filter_is_read(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution, is_read=True)
        unread = _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"), {"is_read": "false"})
        assert r.status_code == 200
        assert [item["id"] for item in r.json()["results"]] == [str(unread.id)]

    def test_list_filter_event_type(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution, event_type="PROJECT_SUBMITTED")
        observed = _make_notification(owner_user, institution, event_type="PROGRESS_OBSERVED")
        _login(api_client, owner_user, institution)
        r = api_client.get(
            reverse("notifications:notification-list"), {"event_type": "PROGRESS_OBSERVED"}
        )
        assert r.status_code == 200
        assert [item["id"] for item in r.json()["results"]] == [str(observed.id)]

    def test_list_filter_entity_type(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution, entity_type="project")
        doc = _make_notification(owner_user, institution, entity_type="document")
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"), {"entity_type": "document"})
        assert r.status_code == 200
        assert [item["id"] for item in r.json()["results"]] == [str(doc.id)]

    def test_list_filter_entity_id(self, api_client, institution, owner_user):
        target = uuid.uuid4()
        _make_notification(owner_user, institution, entity_id=target)
        _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"), {"entity_id": str(target)})
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_list_filter_date_range(self, api_client, institution, owner_user):
        base = timezone.now()
        n1 = _make_notification(owner_user, institution)
        n2 = _make_notification(owner_user, institution)
        Notification.objects.filter(pk=n1.pk).update(created_at=base - timedelta(days=3))
        Notification.objects.filter(pk=n2.pk).update(created_at=base - timedelta(days=1))
        _login(api_client, owner_user, institution)
        r = api_client.get(
            reverse("notifications:notification-list"),
            {
                "date_from": (base - timedelta(days=2)).isoformat(),
                "date_to": (base + timedelta(hours=1)).isoformat(),
            },
        )
        assert r.status_code == 200
        assert [item["id"] for item in r.json()["results"]] == [str(n2.id)]

    def test_list_paginated_50_per_page(self, api_client, institution, owner_user):
        for _ in range(55):
            _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"))
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 55
        assert len(data["results"]) == 50
        r2 = api_client.get(reverse("notifications:notification-list"), {"page": 2})
        assert len(r2.json()["results"]) == 5

    def test_list_uses_summary_payload(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-list"))
        item = r.json()["results"][0]
        assert set(item) == {"id", "title", "is_read", "created_at", "entity_type"}


# ════════════════════════════════════════════════════════
# NotificationViewSet — detail
# ════════════════════════════════════════════════════════


class TestNotificationDetail:
    def test_retrieve_own_notification_full_payload(
        self, api_client, institution, owner_user, notification
    ):
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[notification.id]))
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == str(notification.id)
        assert data["recipient"] == str(owner_user.id)
        assert data["institution"] == str(institution.id)
        assert data["event_type"] == "PROJECT_SUBMITTED"
        assert data["title"] == "Test notification"
        assert data["body"] == "Test body"
        assert data["context"] == {"source": "test"}
        assert data["entity_type"] == "project"
        assert data["is_read"] is False
        assert data["read_at"] is None
        assert data["created_at"] is not None

    def test_retrieve_cross_user_returns_404(
        self, api_client, institution, other_user, notification
    ):
        _login(api_client, other_user, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[notification.id]))
        assert r.status_code == 404

    def test_retrieve_unknown_id_returns_404(self, api_client, institution, owner_user):
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-detail", args=[uuid.uuid4()]))
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# NotificationViewSet — mark read
# ════════════════════════════════════════════════════════


class TestMarkRead:
    def test_mark_read_sets_flags(self, api_client, institution, owner_user, notification):
        _login(api_client, owner_user, institution)
        r = api_client.post(reverse("notifications:notification-read", args=[notification.id]))
        assert r.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None

    def test_mark_read_idempotent(self, api_client, institution, owner_user, notification):
        _login(api_client, owner_user, institution)
        url = reverse("notifications:notification-read", args=[notification.id])
        first = api_client.post(url)
        second = api_client.post(url)
        assert first.status_code == 200
        assert second.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_read_cross_user_404(self, api_client, institution, other_user, notification):
        _login(api_client, other_user, institution)
        r = api_client.post(reverse("notifications:notification-read", args=[notification.id]))
        assert r.status_code == 404
        notification.refresh_from_db()
        assert notification.is_read is False


# ════════════════════════════════════════════════════════
# NotificationViewSet — read_all / unread_count
# ════════════════════════════════════════════════════════


class TestReadAll:
    def test_read_all_marks_only_unread(self, api_client, institution, owner_user):
        already_read = _make_notification(owner_user, institution, is_read=True)
        first = _make_notification(owner_user, institution)
        second = _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.post(reverse("notifications:notification-read-all"))
        assert r.status_code == 200
        assert r.json() == {"updated": 2}
        already_read.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        assert already_read.is_read is True
        assert first.is_read is True
        assert second.is_read is True

    def test_read_all_does_not_touch_other_users(self, api_client, institution, owner_user, other_user):
        mine = _make_notification(owner_user, institution)
        theirs = _make_notification(other_user, institution)
        _login(api_client, owner_user, institution)
        api_client.post(reverse("notifications:notification-read-all"))
        theirs.refresh_from_db()
        assert theirs.is_read is False
        mine.refresh_from_db()
        assert mine.is_read is True

    def test_read_all_get_not_allowed(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-read-all"))
        assert r.status_code == 405


class TestUnreadCount:
    def test_unread_count(self, api_client, institution, owner_user):
        _make_notification(owner_user, institution)
        _make_notification(owner_user, institution, is_read=True)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-unread-count"))
        assert r.status_code == 200
        assert r.json() == {"count": 1}

    def test_unread_count_scoped_to_own(self, api_client, institution, owner_user, other_user):
        _make_notification(owner_user, institution)
        _make_notification(other_user, institution)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-unread-count"))
        assert r.json() == {"count": 1}

    def test_unread_count_updates_after_read(self, api_client, institution, owner_user):
        notification = _make_notification(owner_user, institution)
        _login(api_client, owner_user, institution)
        assert api_client.get(reverse("notifications:notification-unread-count")).json() == {
            "count": 1
        }
        api_client.post(reverse("notifications:notification-read", args=[notification.id]))
        assert api_client.get(reverse("notifications:notification-unread-count")).json() == {
            "count": 0
        }


# ════════════════════════════════════════════════════════
# UserPreferenceViewSet
# ════════════════════════════════════════════════════════


class TestPreferences:
    def test_preference_list_own(self, api_client, institution, owner_user):
        pref = UserPreference.objects.create(user=owner_user)
        _login(api_client, owner_user, institution)
        r = api_client.get(reverse("notifications:notification-preference-list"))
        assert r.status_code == 200
        assert r.json()["count"] == 1
        assert r.json()["results"][0]["id"] == str(pref.id)
        assert r.json()["results"][0]["user"] == str(owner_user.id)

    def test_preference_retrieve_own(self, api_client, institution, owner_user):
        pref = UserPreference.objects.create(user=owner_user)
        _login(api_client, owner_user, institution)
        r = api_client.get(
            reverse("notifications:notification-preference-detail", args=[pref.id])
        )
        assert r.status_code == 200
        assert r.json()["enabled"] is True
        assert r.json()["channel"] == "email"

    def test_preference_patch_disables_email(self, api_client, institution, owner_user):
        pref = UserPreference.objects.create(user=owner_user)
        _login(api_client, owner_user, institution)
        r = api_client.patch(
            reverse("notifications:notification-preference-detail", args=[pref.id]),
            {"enabled": False},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        pref.refresh_from_db()
        assert pref.enabled is False

    def test_preference_cross_user_404(self, api_client, institution, owner_user, other_user):
        pref = UserPreference.objects.create(user=other_user)
        _login(api_client, owner_user, institution)
        r = api_client.get(
            reverse("notifications:notification-preference-detail", args=[pref.id])
        )
        assert r.status_code == 404
