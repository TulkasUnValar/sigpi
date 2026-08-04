"""
Edge-case and permission tests for products app.

Covers gaps not exercised by the main CRUD tests:
- PUT full updates
- Anonymous access to nested endpoints
- Cross-institution retrieval/update/delete
- Filter empty results
- Year upper bound rejection via API
"""
import datetime
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.products.models import ResearchProduct
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _make_researcher(institution, user=None, **kwargs):
    defaults = {
        "first_name": "Alice",
        "last_name": "Smith",
        "document_type": "CC",
        "document_number": f"RES-{uuid.uuid4().hex[:8]}",
        "primary_email": f"alice.{uuid.uuid4().hex[:4]}@test.edu",
        "user": user,
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


def _make_project(institution, center, pi, **kwargs):
    today = datetime.date.today()
    defaults = {
        "institution": institution,
        "center": center,
        "principal_investigator": pi,
        "title": "Test Project",
        "abstract": "Test abstract",
        "objectives": "Test objectives",
        "methodology": "Test methodology",
        "expected_results": "Test results",
        "keywords": "test, project",
        "start_date": today,
        "estimated_end_date": today + datetime.timedelta(days=365),
        "status": "borrador",
    }
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


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
def center(db, institution):
    return ResearchCenter.objects.create(institution=institution, name="AI Lab", code="AI")


@pytest.fixture
def admin_role(db):
    return Role.objects.get(name="Admin Institucional")


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
def researcher_pi(db, institution, center):
    return _make_researcher(institution, document_number="PI000001")


# ════════════════════════════════════════════════════════
# PUT / full update
# ════════════════════════════════════════════════════════


class TestProductPutUpdate:
    """Full PUT updates replace all fields."""

    def test_put_product_full_update(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution,
            project=project,
            title="Old Title",
            description="Old Desc",
            type="articulo",
            publication_year=2024,
        )
        r = api_client.put(
            reverse("products:product-detail", kwargs={"pk": str(product.id)}),
            {
                "title": "New Title",
                "description": "New Desc",
                "type": "libro",
                "publication_year": 2025,
                "project": str(project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "New Title"
        assert data["description"] == "New Desc"
        assert data["type"] == "libro"
        assert data["publication_year"] == 2025


# ════════════════════════════════════════════════════════
# Anonymous access to nested endpoints
# ════════════════════════════════════════════════════════


class TestAnonymousNestedAccess:
    """Unauthenticated users are rejected from nested endpoints."""

    def test_anonymous_author_list(
        self, api_client, institution, center, researcher_pi
    ):
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        r = api_client.get(
            reverse("products:author-list", kwargs={"product_pk": str(product.id)})
        )
        assert r.status_code in (401, 403)

    def test_anonymous_attachment_list(
        self, api_client, institution, center, researcher_pi
    ):
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        r = api_client.get(
            reverse(
                "products:attachment-list",
                kwargs={"product_pk": str(product.id)},
            )
        )
        assert r.status_code in (401, 403)


# ════════════════════════════════════════════════════════
# Cross-institution isolation
# ════════════════════════════════════════════════════════


class TestCrossInstitutionIsolation:
    """Users cannot access products from other institutions."""

    def test_cannot_retrieve_foreign_product(
        self, api_client, institution, admin_user, another_institution, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        foreign_center = ResearchCenter.objects.create(
            institution=another_institution, name="Foreign Lab", code="FL"
        )
        foreign_pi = _make_researcher(another_institution)
        foreign_project = _make_project(another_institution, foreign_center, foreign_pi)
        product = ResearchProduct.objects.create(
            institution=another_institution,
            project=foreign_project,
            title="Foreign",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        r = api_client.get(
            reverse("products:product-detail", kwargs={"pk": str(product.id)})
        )
        assert r.status_code == 404

    def test_cannot_update_foreign_product(
        self, api_client, institution, admin_user, another_institution, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        foreign_center = ResearchCenter.objects.create(
            institution=another_institution, name="Foreign Lab", code="FL"
        )
        foreign_pi = _make_researcher(another_institution)
        foreign_project = _make_project(another_institution, foreign_center, foreign_pi)
        product = ResearchProduct.objects.create(
            institution=another_institution,
            project=foreign_project,
            title="Foreign",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        r = api_client.patch(
            reverse("products:product-detail", kwargs={"pk": str(product.id)}),
            {"title": "Hacked"},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_cannot_delete_foreign_product(
        self, api_client, institution, admin_user, another_institution, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        foreign_center = ResearchCenter.objects.create(
            institution=another_institution, name="Foreign Lab", code="FL"
        )
        foreign_pi = _make_researcher(another_institution)
        foreign_project = _make_project(another_institution, foreign_center, foreign_pi)
        product = ResearchProduct.objects.create(
            institution=another_institution,
            project=foreign_project,
            title="Foreign",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        r = api_client.delete(
            reverse("products:product-detail", kwargs={"pk": str(product.id)})
        )
        assert r.status_code == 404


# ════════════════════════════════════════════════════════
# Filter edge cases
# ════════════════════════════════════════════════════════


class TestFilterEdgeCases:
    """Filters that return empty or test boundary conditions."""

    def test_filter_returns_empty(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        ResearchProduct.objects.create(
            institution=institution, project=project, title="P2024",
            description="D", type="articulo", publication_year=2024,
        )
        r = api_client.get(
            reverse("products:product-list") + "?year=9999"
        )
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_reject_year_too_high_via_api(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        current_year = datetime.date.today().year
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "Bad Year",
                "description": "Desc",
                "type": "articulo",
                "publication_year": current_year + 2,
                "project": str(project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 400
