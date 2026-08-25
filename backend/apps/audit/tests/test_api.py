"""
Audit read-only API tests — STRICT TDD (RED phase).

Covers the PR 3 API contract from spec.md (RA-3..RA-8) and the tasks.md
5.3 checklist:

- GET /api/audit/ returns 200 for an auditor and 403 for a researcher.
- Filters: project_id (RA-3), user_id (RA-4), entity_type + entity_id
  (RA-5), action, event_type, date_from/date_to.
- Pagination: PageNumberPagination, page_size 50, capped at 100.
- Ordering: -timestamp default.
- Read-only: non-safe methods are denied (403).
- Institution isolation: an auditor sees only their own institution.
- Superuser bypass: cross-institution read without an active institution.

Test pattern: Django test Client + force_login + session institution_id
(matches apps/documents/tests/test_views.py).

RED PHASE: views.py / serializers.py / filters.py / urls.py do not exist
yet — module import fails.

Design reference: openspec/changes/audit/design.md — Interfaces/Contracts
Spec reference:   openspec/changes/audit/specs/audit/spec.md — API Contract
"""

import uuid
from datetime import UTC, datetime

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.audit import AuditEvent, AuditEventType
from apps.accounts.models import InstitutionMembership, User
from apps.accounts.tests._helpers import get_role
from apps.institutions.models import Institution

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _make_user(email: str, **extra) -> User:
    return User.objects.create_user(email=email, auth_source="local", password="pass", **extra)


def _login(client: Client, user: User, institution: Institution | None = None) -> None:
    client.force_login(user)
    session = client.session
    if institution is not None:
        session["institution_id"] = str(institution.pk)
    session.save()


def _make_membership(user: User, institution: Institution, role_name: str) -> InstitutionMembership:
    return InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=get_role(role_name),
        is_active=True,
    )


def _make_event(institution, *, user=None, project_id=None, entity_type="project",
                entity_id=None, action="CREATE", event_type=AuditEventType.CREATE,
                timestamp=None, **overrides) -> AuditEvent:
    """Create an AuditEvent row directly (bypasses signals — test data only)."""
    defaults = {
        "event_type": event_type,
        "user": user,
        "ip_address": "10.0.0.1",
        "institution_id": institution.pk,
        "entity_type": entity_type,
        "entity_id": entity_id or uuid.uuid4(),
        "action": action,
        "old_values": {"status": "old"},
        "new_values": {"status": "new"},
        "project_id": project_id or uuid.uuid4(),
        "timestamp": timestamp or datetime.now(UTC),
    }
    defaults.update(overrides)
    return AuditEvent.objects.create(**defaults)


def _url() -> str:
    return reverse("audit:audit-list")


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad A", code="UA001")


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(name="Universidad B", code="UB001")


@pytest.fixture
def auditor(db, institution) -> User:
    user = _make_user("auditor@test.com")
    _make_membership(user, institution, "Auditor")
    return user


@pytest.fixture
def researcher(db, institution) -> User:
    user = _make_user("researcher@test.com")
    _make_membership(user, institution, "Investigador")
    return user


# ════════════════════════════════════════════════════════
# Access control (RA-8)
# ════════════════════════════════════════════════════════


class TestAuditListAccess:
    def test_list_returns_200_for_auditor(self, db, api_client, institution, auditor):
        _make_event(institution)
        _login(api_client, auditor, institution)

        response = api_client.get(_url())

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_list_denied_for_researcher_403(self, db, api_client, institution, researcher):
        _make_event(institution)
        _login(api_client, researcher, institution)

        response = api_client.get(_url())

        assert response.status_code == 403

    def test_anonymous_denied(self, db, api_client, institution):
        _make_event(institution)

        response = api_client.get(_url())

        assert response.status_code in (401, 403)

    def test_retrieve_returns_200_for_auditor(self, db, api_client, institution, auditor):
        event = _make_event(institution)
        _login(api_client, auditor, institution)

        response = api_client.get(reverse("audit:audit-detail", args=[event.pk]))

        assert response.status_code == 200
        assert response.data["id"] == str(event.pk)

    def test_write_methods_denied_403(self, db, api_client, institution, auditor):
        _make_event(institution)
        _login(api_client, auditor, institution)

        assert api_client.post(_url(), data={}).status_code == 403
        assert api_client.patch(_url() + f"{uuid.uuid4()}/", data={}).status_code == 403
        assert api_client.delete(_url() + f"{uuid.uuid4()}/").status_code == 403


# ════════════════════════════════════════════════════════
# Filters (RA-3, RA-4, RA-5)
# ════════════════════════════════════════════════════════


class TestAuditFilters:
    def test_filter_by_project_id(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        target_project = uuid.uuid4()
        _make_event(institution, project_id=target_project)
        _make_event(institution, project_id=uuid.uuid4())

        response = api_client.get(_url(), {"project_id": str(target_project)})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert str(response.data["results"][0]["project_id"]) == str(target_project)

    def test_filter_by_user_id(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        actor = _make_user("actor@test.com")
        _make_event(institution, user=actor)
        _make_event(institution, user=auditor)

        response = api_client.get(_url(), {"user_id": str(actor.pk)})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["user"]["id"] == str(actor.pk)

    def test_filter_by_entity_type(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        _make_event(institution, entity_type="document")
        _make_event(institution, entity_type="budget")

        response = api_client.get(_url(), {"entity_type": "document"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["entity_type"] == "document"

    def test_filter_by_entity_type_and_entity_id(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        target_entity = uuid.uuid4()
        _make_event(institution, entity_type="project", entity_id=target_entity)
        _make_event(institution, entity_type="project", entity_id=uuid.uuid4())

        response = api_client.get(_url(), {"entity_type": "project", "entity_id": str(target_entity)})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert str(response.data["results"][0]["entity_id"]) == str(target_entity)

    def test_filter_by_action(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        _make_event(institution, action="DELETE")
        _make_event(institution, action="CREATE")

        response = api_client.get(_url(), {"action": "DELETE"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["action"] == "DELETE"

    def test_filter_by_event_type(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        _make_event(institution, event_type=AuditEventType.STATE_CHANGE, action="STATE_CHANGE")
        _make_event(institution, event_type=AuditEventType.CREATE)

        response = api_client.get(_url(), {"event_type": "STATE_CHANGE"})

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["event_type"] == "STATE_CHANGE"

    def test_filter_by_date_range(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        _make_event(institution, timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC))
        _make_event(institution, timestamp=datetime(2026, 7, 1, 12, 0, tzinfo=UTC))

        response = api_client.get(
            _url(),
            {"date_from": "2026-06-15", "date_to": "2026-07-31"},
        )

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["timestamp"].startswith("2026-07-01")


# ════════════════════════════════════════════════════════
# Ordering & pagination
# ════════════════════════════════════════════════════════


class TestAuditOrderingAndPagination:
    def test_default_ordering_is_descending_timestamp(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        _make_event(institution, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
        _make_event(institution, timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC))

        response = api_client.get(_url())

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert response.data["results"][0]["timestamp"].startswith("2026-06-01")

    def test_pagination_page_size_50(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        for i in range(55):
            _make_event(institution)

        response = api_client.get(_url())

        assert response.status_code == 200
        assert response.data["count"] == 55
        assert len(response.data["results"]) == 50
        assert response.data["next"] is not None

    def test_pagination_second_page(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        for i in range(55):
            _make_event(institution)

        page_two = api_client.get(_url(), {"page": 2})

        assert page_two.status_code == 200
        assert len(page_two.data["results"]) == 5

    def test_page_size_capped_at_100(self, db, api_client, institution, auditor):
        _login(api_client, auditor, institution)
        for i in range(120):
            _make_event(institution)

        response = api_client.get(_url(), {"page_size": 500})

        assert response.status_code == 200
        assert len(response.data["results"]) == 100


# ════════════════════════════════════════════════════════
# Institution isolation & superuser bypass
# ════════════════════════════════════════════════════════


class TestAuditInstitutionScope:
    def test_auditor_sees_only_own_institution(
        self, db, api_client, institution, other_institution, auditor
    ):
        _login(api_client, auditor, institution)
        _make_event(institution)
        _make_event(other_institution)

        response = api_client.get(_url())

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert str(response.data["results"][0]["institution_id"]) == str(institution.pk)

    def test_superadmin_can_read_cross_institution(
        self, db, api_client, institution, other_institution
    ):
        superuser = User.objects.create_superuser(email="root@test.com", password="pass")
        _login(api_client, superuser, institution=None)  # no active institution
        _make_event(institution)
        _make_event(other_institution)

        response = api_client.get(_url())

        assert response.status_code == 200
        assert response.data["count"] == 2
