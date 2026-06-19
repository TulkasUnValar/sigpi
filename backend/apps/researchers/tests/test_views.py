"""
Integration tests for researchers ViewSets — STRICT TDD (RED phase).

Tests define the expected behavior of 4 ViewSets per spec:
- ResearcherViewSet: CRUD + deactivate action + role-gated permissions
- ResearcherAffiliationViewSet: nested under researcher, set_primary action
- ExternalProfileViewSet: nested under researcher
- ResearcherAttachmentViewSet: nested under researcher

Error cases: duplicate document (409→400 via DRF), cross-institution (403),
multiple-primary (400), missing fields (400).

Spec reference: openspec/changes/researchers/spec.md — API Contract
Design reference: openspec/changes/researchers/design.md — ViewSets & Permissions
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.researchers.models import Researcher, ResearcherAffiliation

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _make_researcher(institution, **kwargs):
    """Create a researcher with minimal required fields."""
    defaults = {
        "first_name": "Alice",
        "last_name": "Smith",
        "document_type": "CC",
        "document_number": "123456",
        "primary_email": "alice@test.edu",
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


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
def authenticated_role(db):
    return Role.objects.get(name="Auditor")


@pytest.fixture
def superadmin_user(db, institution, superadmin_role):
    user = User.objects.create_user(
        email="sa@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=superadmin_role, is_active=True
    )
    return user


@pytest.fixture
def admin_user(db, institution, admin_role):
    user = User.objects.create_user(
        email="admin@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=admin_role, is_active=True
    )
    return user


@pytest.fixture
def director_user(db, institution, director_role):
    user = User.objects.create_user(
        email="dir@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=director_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(
        email="res@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def authenticated_user(db, institution, authenticated_role):
    user = User.objects.create_user(
        email="auth@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=authenticated_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_owner(db, institution, researcher_role):
    """A researcher user who owns a researcher profile (for self-edit tests)."""
    user = User.objects.create_user(
        email="owner@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    profile = _make_researcher(institution, user=user, document_number="OWNER001")
    return user, profile


@pytest.fixture
def center(db, institution):
    return ResearchCenter.objects.create(
        institution=institution, name="AI Lab", code="AI"
    )


# ════════════════════════════════════════════════════════
# ResearcherViewSet — CRUD + deactivate
# ════════════════════════════════════════════════════════


class TestResearcherViewSet:
    """CRUD operations on /researchers/ — admin for writes, any auth for reads."""

    def test_list_as_admin(self, api_client, institution, admin_user):
        _make_researcher(institution, document_number="L001")
        _login(api_client, admin_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code in (401, 403)

    def test_create_as_admin(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "Bob",
                "last_name": "Jones",
                "document_type": "CC",
                "document_number": "NEW001",
                "primary_email": "bob@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["first_name"] == "Bob"
        assert data["is_active"] is True

    def test_create_denied_for_researcher(self, api_client, institution, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "Bad",
                "last_name": "Actor",
                "document_type": "CC",
                "document_number": "BAD001",
                "primary_email": "bad@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_retrieve_as_researcher(self, api_client, institution, researcher_user):
        res = _make_researcher(institution, document_number="R001")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)})
        )
        assert r.status_code == 200
        data = r.json()
        assert data["first_name"] == "Alice"
        assert "completeness_score" in data
        assert "affiliations" in data

    def test_update_as_admin(self, api_client, institution, admin_user):
        res = _make_researcher(institution, document_number="U001")
        _login(api_client, admin_user, institution)
        r = api_client.patch(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)}),
            {"first_name": "Updated"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["first_name"] == "Updated"

    def test_update_denied_for_authenticated(self, api_client, institution, authenticated_user):
        res = _make_researcher(institution, document_number="U002")
        _login(api_client, authenticated_user, institution)
        r = api_client.patch(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)}),
            {"first_name": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_delete_as_superadmin(self, api_client, institution, superadmin_user):
        res = _make_researcher(institution, document_number="D001")
        _login(api_client, superadmin_user, institution)
        r = api_client.delete(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)})
        )
        assert r.status_code == 204
        assert not Researcher.objects.filter(pk=res.pk).exists()

    def test_delete_denied_for_admin(self, api_client, institution, admin_user):
        res = _make_researcher(institution, document_number="D002")
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)})
        )
        assert r.status_code in (403, 401)

    def test_deactivate_as_admin(self, api_client, institution, admin_user):
        res = _make_researcher(institution, document_number="DA001")
        assert res.is_active is True
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-deactivate",
                kwargs={"pk": str(res.pk)},
            )
        )
        assert r.status_code == 200
        res.refresh_from_db()
        assert res.is_active is False

    def test_deactivate_denied_for_researcher(self, api_client, institution, researcher_user):
        res = _make_researcher(institution, document_number="DA002")
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-deactivate",
                kwargs={"pk": str(res.pk)},
            )
        )
        assert r.status_code in (403, 401)

    def test_deactivate_not_found(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = api_client.post(
            reverse("researchers:researcher-deactivate", kwargs={"pk": fake_id})
        )
        assert r.status_code in (404, 403)

    def test_self_update_allowed(self, api_client, institution, researcher_owner):
        user, profile = researcher_owner
        _login(api_client, user, institution)
        r = api_client.patch(
            reverse("researchers:researcher-detail", kwargs={"pk": str(profile.pk)}),
            {"phone": "555-1234"},
            content_type="application/json",
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.content}"
        profile.refresh_from_db()
        assert profile.phone == "555-1234"

    def test_self_delete_denied(self, api_client, institution, researcher_owner):
        user, profile = researcher_owner
        _login(api_client, user, institution)
        r = api_client.delete(
            reverse("researchers:researcher-detail", kwargs={"pk": str(profile.pk)})
        )
        assert r.status_code in (403, 401)

    def test_other_researcher_cannot_update(self, api_client, institution, researcher_user):
        """A researcher cannot update another researcher's profile."""
        other = _make_researcher(institution, document_number="OTHER01")
        _login(api_client, researcher_user, institution)
        r = api_client.patch(
            reverse("researchers:researcher-detail", kwargs={"pk": str(other.pk)}),
            {"first_name": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)


# ════════════════════════════════════════════════════════
# ResearcherAffiliationViewSet — nested under researcher
# ════════════════════════════════════════════════════════


class TestResearcherAffiliationViewSet:
    """Nested affiliation CRUD under /researchers/{pk}/affiliations/"""

    @pytest.fixture
    def researcher(self, institution):
        return _make_researcher(institution, document_number="AFF001")

    def test_list(self, api_client, institution, researcher, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            )
        )
        assert r.status_code == 200

    def test_create_as_admin_assigns_researcher(
        self, api_client, institution, researcher, center, admin_user
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {"center": str(center.pk), "is_primary": False},
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["researcher"] == str(researcher.pk)
        assert data["is_primary"] is True  # auto-set as first affiliation

    def test_create_second_affiliation_not_primary(
        self, api_client, institution, researcher, center, admin_user
    ):
        # First affiliation exists and is primary
        ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=True
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {"center": str(center.pk), "is_primary": False},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["is_primary"] is False

    def test_set_primary(self, api_client, institution, researcher, center, admin_user):
        aff1 = ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=True
        )
        aff2 = ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=False
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-set-primary",
                kwargs={"researcher_pk": str(researcher.pk), "pk": str(aff2.pk)},
            )
        )
        assert r.status_code == 200
        aff1.refresh_from_db()
        aff2.refresh_from_db()
        assert aff1.is_primary is False
        assert aff2.is_primary is True

    def test_create_denied_for_authenticated(
        self, api_client, institution, researcher, center, authenticated_user
    ):
        _login(api_client, authenticated_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {"center": str(center.pk)},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_self_affiliation_create_allowed(
        self, api_client, institution, researcher_owner, center
    ):
        """Researcher can add affiliations to their own profile."""
        user, profile = researcher_owner
        _login(api_client, user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(profile.pk)},
            ),
            {"center": str(center.pk)},
            content_type="application/json",
        )
        assert r.status_code == 201


# ════════════════════════════════════════════════════════
# ExternalProfileViewSet — nested under researcher
# ════════════════════════════════════════════════════════


class TestExternalProfileViewSet:
    """Nested external profile CRUD under /researchers/{pk}/profiles/"""

    @pytest.fixture
    def researcher(self, institution):
        return _make_researcher(institution, document_number="PROF001")

    def test_list(self, api_client, institution, researcher, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "researchers:researcher-profile-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            )
        )
        assert r.status_code == 200

    def test_create_as_admin(self, api_client, institution, researcher, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-profile-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {"provider": "orcid", "url": "https://orcid.org/0000-0001-2345-6789"},
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["researcher"] == str(researcher.pk)
        assert r.json()["provider"] == "orcid"

    def test_create_denied_for_authenticated(
        self, api_client, institution, researcher, authenticated_user
    ):
        _login(api_client, authenticated_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-profile-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {"provider": "orcid", "url": "https://orcid.org/test"},
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_delete_as_admin(self, api_client, institution, researcher, admin_user):
        from apps.researchers.models import ExternalProfile

        profile = ExternalProfile.objects.create(
            researcher=researcher, provider="orcid", url="https://orcid.org/test"
        )
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "researchers:researcher-profile-detail",
                kwargs={"researcher_pk": str(researcher.pk), "pk": str(profile.pk)},
            )
        )
        assert r.status_code == 204

    def test_self_profile_create_allowed(
        self, api_client, institution, researcher_owner
    ):
        user, profile = researcher_owner
        _login(api_client, user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-profile-list",
                kwargs={"researcher_pk": str(profile.pk)},
            ),
            {"provider": "google_scholar", "url": "https://scholar.google.com/test"},
            content_type="application/json",
        )
        assert r.status_code == 201


# ════════════════════════════════════════════════════════
# ResearcherAttachmentViewSet — nested under researcher
# ════════════════════════════════════════════════════════


class TestResearcherAttachmentViewSet:
    """Nested attachment CRUD under /researchers/{pk}/attachments/"""

    @pytest.fixture
    def researcher(self, institution):
        return _make_researcher(institution, document_number="ATT001")

    def test_list(self, api_client, institution, researcher, researcher_user):
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "researchers:researcher-attachment-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            )
        )
        assert r.status_code == 200

    def test_create_as_admin(self, api_client, institution, researcher, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-attachment-list",
                kwargs={"researcher_pk": str(researcher.pk)},
            ),
            {
                "name": "CV_Alice.pdf",
                "type": "cv",
                "external_url": "https://files.example.com/cv_alice.pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        assert r.json()["researcher"] == str(researcher.pk)
        assert r.json()["type"] == "cv"

    def test_delete_as_admin(self, api_client, institution, researcher, admin_user):
        from apps.researchers.models import ResearcherAttachment

        att = ResearcherAttachment.objects.create(
            researcher=researcher,
            name="photo.jpg",
            type="photo",
            external_url="https://files.example.com/photo.jpg",
        )
        _login(api_client, admin_user, institution)
        r = api_client.delete(
            reverse(
                "researchers:researcher-attachment-detail",
                kwargs={"researcher_pk": str(researcher.pk), "pk": str(att.pk)},
            )
        )
        assert r.status_code == 204

    def test_self_attachment_create_allowed(
        self, api_client, institution, researcher_owner
    ):
        user, profile = researcher_owner
        _login(api_client, user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-attachment-list",
                kwargs={"researcher_pk": str(profile.pk)},
            ),
            {
                "name": "cert.pdf",
                "type": "certificate",
                "external_url": "https://files.example.com/cert.pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201


# ════════════════════════════════════════════════════════
# Error Responses
# ════════════════════════════════════════════════════════


class TestResearcherErrorResponses:
    """Verify error codes for business rule violations."""

    def test_duplicate_document_same_institution(
        self, api_client, institution, admin_user
    ):
        _make_researcher(institution, document_number="DUP001")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "document_type": "CC",
                "document_number": "DUP001",
                "primary_email": "jane@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_cross_institution_access_denied(
        self, api_client, institution, another_institution, researcher_user
    ):
        # Create researcher in another institution
        other_res = _make_researcher(
            another_institution, document_number="CROSS01"
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse(
                "researchers:researcher-detail",
                kwargs={"pk": str(other_res.pk)},
            )
        )
        assert r.status_code in (403, 404)

    def test_multiple_primary_affiliation_rejected(
        self, api_client, institution, center, admin_user
    ):
        """Creating a second primary affiliation should be rejected."""
        res = _make_researcher(institution, document_number="MP001")
        ResearcherAffiliation.objects.create(
            researcher=res, center=center, is_primary=True
        )
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(res.pk)},
            ),
            {"center": str(center.pk), "is_primary": True},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_affiliation_cross_institution_rejected(
        self, api_client, institution, another_institution, admin_user
    ):
        """Affiliation to center from another institution should be rejected."""
        other_center = ResearchCenter.objects.create(
            institution=another_institution, name="Other Lab", code="OL"
        )
        res = _make_researcher(institution, document_number="AFFCROSS01")
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse(
                "researchers:researcher-affiliation-list",
                kwargs={"researcher_pk": str(res.pk)},
            ),
            {"center": str(other_center.pk)},
            content_type="application/json",
        )
        assert r.status_code == 400


# ════════════════════════════════════════════════════════
# Permission Matrix Tests
# ════════════════════════════════════════════════════════


class TestResearcherPermissions:
    """Verify role-based access matrix per spec §Security."""

    def test_superadmin_can_read(self, api_client, institution, superadmin_user):
        _make_researcher(institution, document_number="PM001")
        _login(api_client, superadmin_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200

    def test_admin_can_create(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "Perm",
                "last_name": "Test",
                "document_type": "CC",
                "document_number": "PM002",
                "primary_email": "perm@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code == 201

    def test_director_can_read(self, api_client, institution, director_user):
        _make_researcher(institution, document_number="PM003")
        _login(api_client, director_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200

    def test_researcher_can_read(self, api_client, institution, researcher_user):
        _make_researcher(institution, document_number="PM004")
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200

    def test_authenticated_can_read(self, api_client, institution, authenticated_user):
        _make_researcher(institution, document_number="PM005")
        _login(api_client, authenticated_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200

    def test_authenticated_cannot_create(
        self, api_client, institution, authenticated_user
    ):
        _login(api_client, authenticated_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "No",
                "last_name": "Perm",
                "document_type": "CC",
                "document_number": "PM006",
                "primary_email": "no@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code in (403, 401)

    def test_researcher_cannot_create(
        self, api_client, institution, researcher_user
    ):
        _login(api_client, researcher_user, institution)
        r = api_client.post(
            reverse("researchers:researcher-list"),
            {
                "first_name": "No",
                "last_name": "Create",
                "document_type": "CC",
                "document_number": "PM007",
                "primary_email": "nocreate@test.edu",
            },
            content_type="application/json",
        )
        assert r.status_code in (403, 401)


# ════════════════════════════════════════════════════════
# Completeness Score in Response
# ════════════════════════════════════════════════════════


class TestCompletenessScore:
    """Verify completeness_score appears in list and detail responses."""

    def test_list_includes_completeness(self, api_client, institution, researcher_user):
        _make_researcher(institution, document_number="CC001")
        _login(api_client, researcher_user, institution)
        r = api_client.get(reverse("researchers:researcher-list"))
        assert r.status_code == 200
        for item in r.json()["results"]:
            assert "completeness_score" in item

    def test_detail_includes_completeness(
        self, api_client, institution, researcher_user
    ):
        res = _make_researcher(institution, document_number="CC002")
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)})
        )
        assert r.status_code == 200
        assert "completeness_score" in r.json()

    def test_completeness_below_100_without_profile(
        self, api_client, institution, researcher_user
    ):
        # Create researcher with no external profile
        res = _make_researcher(
            institution, document_number="CC003", bio="", academic_formation=""
        )
        _login(api_client, researcher_user, institution)
        r = api_client.get(
            reverse("researchers:researcher-detail", kwargs={"pk": str(res.pk)})
        )
        assert r.status_code == 200
        assert r.json()["completeness_score"] < 100
