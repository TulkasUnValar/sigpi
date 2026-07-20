"""
Integration tests for institutions ViewSets — STRICT TDD.

Tests define the expected behavior of the 6 ModelViewSets per spec:
- Institution: superadmin-only (all CRUD + lifecycle)
- Sede/Facultad/Center: IsInstitutionAdminOrReadOnly
- Group/Line: IsCenterDirectorOrReadOnly
- Lifecycle actions: activate/deactivate/archive via POST
- Nested routes: parent FK injection from URL kwargs

Spec reference: openspec/changes/institutions/spec.md
Design reference: openspec/changes/institutions/design.md
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import (
    Facultad,
    Institution,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
    Sede,
)

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ── Fixtures ───────────────────────────────────────────


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def institution(db):
    return Institution.objects.create(name="Test University", code="TU001")


@pytest.fixture
def another_institution(db):
    return Institution.objects.create(name="Other University", code="OU001")


@pytest.fixture
def superadmin_role(db):
    return Role.objects.get(name="Superadmin")


@pytest.fixture
def admin_role(db):
    return Role.objects.get(name="Admin Institucional")


@pytest.fixture
def director_role(db):
    return Role.objects.get(name="Director de Centro")


@pytest.fixture
def researcher_role(db):
    return Role.objects.get(name="Investigador")


@pytest.fixture
def superadmin_user(db, institution, superadmin_role):
    user = User.objects.create_user(email="sa@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=superadmin_role, is_active=True
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
def director_user(db, institution, director_role):
    user = User.objects.create_user(email="dir@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(email="res@test.edu", auth_source="local", password="p")
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


# ════════════════════════════════════════════════════════
# InstitutionViewSet — superadmin-only CRUD + lifecycle
# ════════════════════════════════════════════════════════


class TestInstitutionViewSet:
    def test_list_as_superadmin(self, api_client, institution, superadmin_user):
        _login(api_client, superadmin_user, institution)
        r = api_client.get(reverse("institutions:institution-list"))
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("institutions:institution-list"))
        assert r.status_code == 403

    def test_create_as_superadmin(self, api_client, institution, superadmin_user):
        _login(api_client, superadmin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-list"),
            {"name": "New Uni", "code": "NU01"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_create_denied_for_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-list"),
            {"name": "Bad", "code": "BAD1"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_create_denied_for_researcher(self, api_client, institution, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("institutions:institution-list"),
            {"name": "Bad2", "code": "BAD2"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_retrieve_as_superadmin(self, api_client, institution, superadmin_user):
        _login(api_client, superadmin_user, institution)
        r = api_client.get(
            reverse("institutions:institution-detail", kwargs={"pk": str(institution.pk)})
        )
        assert r.status_code == 200
        assert r.json()["name"] == institution.name

    def test_update_as_superadmin(self, api_client, institution, superadmin_user):
        _login(api_client, superadmin_user, institution)
        r = api_client.patch(
            reverse("institutions:institution-detail", kwargs={"pk": str(institution.pk)}),
            {"name": "Updated"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_update_denied_for_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse("institutions:institution-detail", kwargs={"pk": str(institution.pk)}),
            {"name": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_delete_as_superadmin(self, api_client, institution, superadmin_user):
        inst = Institution.objects.create(name="Del Me", code="DEL1")
        _login(api_client, superadmin_user, institution)
        r = api_client.delete(
            reverse("institutions:institution-detail", kwargs={"pk": str(inst.pk)})
        )
        assert r.status_code == 204
        assert not Institution.objects.filter(pk=inst.pk).exists()

    def test_activate(self, api_client, institution, superadmin_user):
        from apps.institutions.services import InstitutionLifecycleService

        InstitutionLifecycleService.deactivate(institution)
        institution.refresh_from_db()
        _login(api_client, superadmin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-activate", kwargs={"pk": str(institution.pk)})
        )
        assert r.status_code in (200, 201)
        institution.refresh_from_db()
        assert institution.status == "active"

    def test_deactivate(self, api_client, institution, superadmin_user):
        _login(api_client, superadmin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-deactivate", kwargs={"pk": str(institution.pk)})
        )
        assert r.status_code in (200, 201)
        institution.refresh_from_db()
        assert institution.status == "deactivated"

    def test_deactivate_blocked_by_children(self, api_client, institution, superadmin_user):
        Sede.objects.create(institution=institution, name="Campus", code="C1")
        _login(api_client, superadmin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-deactivate", kwargs={"pk": str(institution.pk)})
        )
        assert r.status_code == 409
        institution.refresh_from_db()
        assert institution.status == "active"

    def test_archive(self, api_client, institution, superadmin_user):
        from apps.institutions.services import InstitutionLifecycleService

        InstitutionLifecycleService.deactivate(institution)
        _login(api_client, superadmin_user, institution)
        r = api_client.post(
            reverse("institutions:institution-archive", kwargs={"pk": str(institution.pk)})
        )
        assert r.status_code in (200, 201)
        institution.refresh_from_db()
        assert institution.status == "archived"


# ════════════════════════════════════════════════════════
# SedeViewSet — admin writes, nested under institution
# ════════════════════════════════════════════════════════


class TestSedeViewSet:
    def test_list(self, api_client, institution, researcher_user):
        Sede.objects.create(institution=institution, name="Campus A", code="CA")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-sede-list", kwargs={"institution_pk": str(institution.pk)}
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_create_as_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-sede-list", kwargs={"institution_pk": str(institution.pk)}
            ),
            {"name": "New Campus", "code": "NC"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["name"] == "New Campus"

    def test_create_denied_for_researcher(self, api_client, institution, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-sede-list", kwargs={"institution_pk": str(institution.pk)}
            ),
            {"name": "Bad", "code": "BD"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_retrieve(self, api_client, institution, researcher_user):
        sede = Sede.objects.create(institution=institution, name="Campus B", code="CB")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-sede-detail",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            )
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Campus B"

    def test_update_as_admin(self, api_client, institution, admin_user):
        sede = Sede.objects.create(institution=institution, name="Campus C", code="CC")
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse(
                "institutions:institution-sede-detail",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            ),
            {"name": "Updated"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_delete_as_admin(self, api_client, institution, admin_user):
        sede = Sede.objects.create(institution=institution, name="Del", code="DD")
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "institutions:institution-sede-detail",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            )
        )
        assert r.status_code == 204

    def test_activate_lifecycle(self, api_client, institution, admin_user):
        from apps.institutions.services import InstitutionLifecycleService

        sede = Sede.objects.create(institution=institution, name="Dormant", code="DR")
        InstitutionLifecycleService.deactivate(sede)
        sede.refresh_from_db()
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:sede-activate",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            )
        )
        assert r.status_code in (200, 201)
        sede.refresh_from_db()
        assert sede.status == "active"

    def test_deactivate_lifecycle(self, api_client, institution, admin_user):
        sede = Sede.objects.create(institution=institution, name="ActiveSede", code="AS")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:sede-deactivate",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            )
        )
        assert r.status_code in (200, 201)
        sede.refresh_from_db()
        assert sede.status == "deactivated"

    def test_archive_lifecycle(self, api_client, institution, admin_user):
        from apps.institutions.services import InstitutionLifecycleService

        sede = Sede.objects.create(institution=institution, name="ToArchive", code="TA")
        InstitutionLifecycleService.deactivate(sede)
        sede.refresh_from_db()
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:sede-archive",
                kwargs={"institution_pk": str(institution.pk), "pk": str(sede.pk)},
            )
        )
        assert r.status_code in (200, 201)
        sede.refresh_from_db()
        assert sede.status == "archived"


# ════════════════════════════════════════════════════════
# ResearchCenterViewSet — admin writes
# ════════════════════════════════════════════════════════


class TestResearchCenterViewSet:
    def test_create_as_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-center-list",
                kwargs={"institution_pk": str(institution.pk)},
            ),
            {"name": "AI Lab", "code": "AI"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["status"] == "active"

    def test_list(self, api_client, institution, researcher_user):
        ResearchCenter.objects.create(institution=institution, name="Lab 1", code="L1")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-center-list",
                kwargs={"institution_pk": str(institution.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_create_denied_for_director(self, api_client, institution, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-center-list",
                kwargs={"institution_pk": str(institution.pk)},
            ),
            {"name": "Bad", "code": "BD"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_activate_lifecycle(self, api_client, institution, admin_user):
        from apps.institutions.services import InstitutionLifecycleService

        center = ResearchCenter.objects.create(institution=institution, name="DormantC", code="DC")
        InstitutionLifecycleService.deactivate(center)
        center.refresh_from_db()
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:center-activate",
                kwargs={"institution_pk": str(institution.pk), "pk": str(center.pk)},
            )
        )
        assert r.status_code in (200, 201)
        center.refresh_from_db()
        assert center.status == "active"

    def test_deactivate_lifecycle(self, api_client, institution, admin_user):
        center = ResearchCenter.objects.create(institution=institution, name="ActiveC", code="AC")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:center-deactivate",
                kwargs={"institution_pk": str(institution.pk), "pk": str(center.pk)},
            )
        )
        assert r.status_code in (200, 201)
        center.refresh_from_db()
        assert center.status == "deactivated"

    def test_archive_lifecycle(self, api_client, institution, admin_user):
        from apps.institutions.services import InstitutionLifecycleService

        center = ResearchCenter.objects.create(
            institution=institution, name="ToArchiveC", code="TAC"
        )
        InstitutionLifecycleService.deactivate(center)
        center.refresh_from_db()
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:center-archive",
                kwargs={"institution_pk": str(institution.pk), "pk": str(center.pk)},
            )
        )
        assert r.status_code in (200, 201)
        center.refresh_from_db()
        assert center.status == "archived"


# ════════════════════════════════════════════════════════
# ResearchGroupViewSet — director writes, nested under center
# ════════════════════════════════════════════════════════


class TestResearchGroupViewSet:
    @pytest.fixture
    def center(self, institution):
        return ResearchCenter.objects.create(institution=institution, name="TC", code="TC")

    def test_create_as_director(self, api_client, institution, center, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("institutions:center-group-list", kwargs={"center_pk": str(center.pk)}),
            {"name": "NLP", "code": "NLP"},
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_create_denied_for_researcher(self, api_client, institution, center, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("institutions:center-group-list", kwargs={"center_pk": str(center.pk)}),
            {"name": "Bad", "code": "BD"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_list(self, api_client, institution, center, researcher_user):
        ResearchGroup.objects.create(institution=institution, center=center, name="ML", code="ML")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("institutions:center-group-list", kwargs={"center_pk": str(center.pk)})
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_retrieve(self, api_client, institution, center, researcher_user):
        group = ResearchGroup.objects.create(
            institution=institution, center=center, name="DL", code="DL"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:center-group-detail",
                kwargs={"center_pk": str(center.pk), "pk": str(group.pk)},
            )
        )
        assert r.status_code == 200

    def test_activate_lifecycle(self, api_client, institution, center, director_user):
        from apps.institutions.services import InstitutionLifecycleService

        group = ResearchGroup.objects.create(
            institution=institution, center=center, name="TG", code="TG"
        )
        InstitutionLifecycleService.deactivate(group)
        group.refresh_from_db()
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:group-activate",
                kwargs={"center_pk": str(center.pk), "pk": str(group.pk)},
            )
        )
        assert r.status_code in (200, 201)
        group.refresh_from_db()
        assert group.status == "active"

    def test_deactivate_lifecycle(self, api_client, institution, center, director_user):
        group = ResearchGroup.objects.create(
            institution=institution, center=center, name="DG", code="DG"
        )
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:group-deactivate",
                kwargs={"center_pk": str(center.pk), "pk": str(group.pk)},
            )
        )
        assert r.status_code in (200, 201)
        group.refresh_from_db()
        assert group.status == "deactivated"

    def test_archive_lifecycle(self, api_client, institution, center, director_user):
        from apps.institutions.services import InstitutionLifecycleService

        group = ResearchGroup.objects.create(
            institution=institution, center=center, name="AG", code="AG"
        )
        InstitutionLifecycleService.deactivate(group)
        group.refresh_from_db()
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:group-archive",
                kwargs={"center_pk": str(center.pk), "pk": str(group.pk)},
            )
        )
        assert r.status_code in (200, 201)
        group.refresh_from_db()
        assert group.status == "archived"


# ════════════════════════════════════════════════════════
# ResearchLineViewSet — director writes, nested under group
# ════════════════════════════════════════════════════════


class TestResearchLineViewSet:
    @pytest.fixture
    def group(self, institution):
        center = ResearchCenter.objects.create(institution=institution, name="LC", code="LC")
        return ResearchGroup.objects.create(
            institution=institution, center=center, name="LG", code="LG"
        )

    def test_create_as_director(self, api_client, institution, group, director_user):
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse("institutions:group-line-list", kwargs={"group_pk": str(group.pk)}),
            {"name": "SA", "code": "SA"},
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_create_denied_for_researcher(self, api_client, institution, group, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("institutions:group-line-list", kwargs={"group_pk": str(group.pk)}),
            {"name": "Bad", "code": "BD"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_list(self, api_client, institution, group, researcher_user):
        ResearchLine.objects.create(institution=institution, group=group, name="NER", code="NE")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("institutions:group-line-list", kwargs={"group_pk": str(group.pk)})
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_retrieve(self, api_client, institution, group, researcher_user):
        line = ResearchLine.objects.create(
            institution=institution, group=group, name="QA", code="QA"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:group-line-detail",
                kwargs={"group_pk": str(group.pk), "pk": str(line.pk)},
            )
        )
        assert r.status_code == 200

    def test_deactivate_lifecycle(self, api_client, institution, group, director_user):
        line = ResearchLine.objects.create(
            institution=institution, group=group, name="TL", code="TL"
        )
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:line-deactivate",
                kwargs={"group_pk": str(group.pk), "pk": str(line.pk)},
            )
        )
        assert r.status_code in (200, 201)
        line.refresh_from_db()
        assert line.status == "deactivated"

    def test_activate_lifecycle(self, api_client, institution, group, director_user):
        from apps.institutions.services import InstitutionLifecycleService

        line = ResearchLine.objects.create(
            institution=institution, group=group, name="AL", code="AL"
        )
        InstitutionLifecycleService.deactivate(line)
        line.refresh_from_db()
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:line-activate", kwargs={"group_pk": str(group.pk), "pk": str(line.pk)}
            )
        )
        assert r.status_code in (200, 201)
        line.refresh_from_db()
        assert line.status == "active"

    def test_archive_lifecycle(self, api_client, institution, group, director_user):
        from apps.institutions.services import InstitutionLifecycleService

        line = ResearchLine.objects.create(
            institution=institution, group=group, name="ARL", code="ARL"
        )
        InstitutionLifecycleService.deactivate(line)
        line.refresh_from_db()
        _login(api_client, director_user, institution)
        r = api_client.post(
            reverse(
                "institutions:line-archive", kwargs={"group_pk": str(group.pk), "pk": str(line.pk)}
            )
        )
        assert r.status_code in (200, 201)
        line.refresh_from_db()
        assert line.status == "archived"


# ════════════════════════════════════════════════════════
# Cross-Tenant Access
# ════════════════════════════════════════════════════════


class TestCrossInstitutionAccess:
    def test_other_institution_sede_not_visible(
        self, api_client, institution, another_institution, researcher_user
    ):
        Sede.objects.create(institution=institution, name="My Campus", code="MC")
        Sede.objects.create(institution=another_institution, name="Their Campus", code="TC")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-sede-list", kwargs={"institution_pk": str(institution.pk)}
            )
        )
        assert r.status_code == 200
        for item in r.json()["results"]:
            assert str(item["institution"]) != str(another_institution.pk)

    def test_other_institution_center_not_found(
        self, api_client, institution, another_institution, researcher_user
    ):
        other_center = ResearchCenter.objects.create(
            institution=another_institution, name="Their Lab", code="TL"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-center-detail",
                kwargs={"institution_pk": str(institution.pk), "pk": str(other_center.pk)},
            )
        )
        assert r.status_code in (403, 404)


# ════════════════════════════════════════════════════════
# FacultadViewSet — admin writes
# ════════════════════════════════════════════════════════


class TestFacultadViewSet:
    def test_create_as_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-facultad-list",
                kwargs={"institution_pk": str(institution.pk)},
            ),
            {"name": "Engineering", "code": "ENG"},
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_list(self, api_client, institution, researcher_user):
        Facultad.objects.create(institution=institution, name="Science", code="SCI")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "institutions:institution-facultad-list",
                kwargs={"institution_pk": str(institution.pk)},
            )
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_create_with_sede(self, api_client, institution, admin_user):
        sede = Sede.objects.create(institution=institution, name="Main", code="MN")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:institution-facultad-list",
                kwargs={"institution_pk": str(institution.pk)},
            ),
            {"name": "Medicine", "code": "MED", "sede": str(sede.pk)},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["sede"] == str(sede.pk)

    def test_deactivate_lifecycle(self, api_client, institution, admin_user):
        facultad = Facultad.objects.create(institution=institution, name="ToDeact", code="TD")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:facultad-deactivate",
                kwargs={"institution_pk": str(institution.pk), "pk": str(facultad.pk)},
            )
        )
        assert r.status_code in (200, 201)
        facultad.refresh_from_db()
        assert facultad.status == "deactivated"

    def test_archive_lifecycle(self, api_client, institution, admin_user):
        from apps.institutions.services import InstitutionLifecycleService

        facultad = Facultad.objects.create(institution=institution, name="ToArchiveF", code="TAF")
        InstitutionLifecycleService.deactivate(facultad)
        facultad.refresh_from_db()
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "institutions:facultad-archive",
                kwargs={"institution_pk": str(institution.pk), "pk": str(facultad.pk)},
            )
        )
        assert r.status_code in (200, 201)
        facultad.refresh_from_db()
        assert facultad.status == "archived"
