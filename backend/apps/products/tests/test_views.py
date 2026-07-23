"""
View tests for products app — STRICT TDD (RED phase).

Tests define the expected behavior of 3 ViewSets:
- ResearchProductViewSet: CRUD + filtering + institution scoping
- ProductAuthorViewSet: nested under product
- ProductAttachmentViewSet: nested under product

Error cases: 400 missing project, 400 invalid type/year, 404 foreign project,
403/404 unauthenticated, empty list for foreign institution.

Spec reference: openspec/changes/products/specs/products/spec.md
Design reference: openspec/changes/products/design.md
"""
import datetime
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter, ResearchGroup, ResearchLine
from apps.products.models import ProductAttachment, ProductAuthor, ResearchProduct
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


def _make_project(institution, center, pi, group=None, line=None, **kwargs):
    today = datetime.date.today()
    defaults = {
        "institution": institution,
        "center": center,
        "group": group,
        "line": line,
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
def group(db, center):
    return ResearchGroup.objects.create(center=center, name="NLP Group", code="NLP")


@pytest.fixture
def line(db, group):
    return ResearchLine.objects.create(group=group, name="Deep Learning Line", code="DL")


@pytest.fixture
def researcher_role(db):
    return Role.objects.get(name="Investigador")


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
def researcher_user(db, institution, researcher_role):
    user = User.objects.create_user(
        email="res@test.edu", auth_source="local", password="p"
    )
    InstitutionMembership.objects.create(
        user=user, institution=institution, role=researcher_role, is_active=True
    )
    return user


@pytest.fixture
def researcher_pi(db, institution, researcher_user, center):
    pi = _make_researcher(institution, user=researcher_user, document_number="PI000001")
    return pi


@pytest.fixture
def foreign_project(db, another_institution):
    center = ResearchCenter.objects.create(
        institution=another_institution, name="Foreign Lab", code="FL"
    )
    pi = _make_researcher(another_institution)
    return _make_project(another_institution, center, pi, title="Foreign Project")


# ════════════════════════════════════════════════════════
# ResearchProductViewSet — CRUD + filtering
# ════════════════════════════════════════════════════════


class TestResearchProductViewSet:
    """CRUD operations on /products/ — institution-scoped."""

    def test_list_as_authenticated(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        ResearchProduct.objects.create(
            institution=institution,
            project=project,
            title="Paper",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        r = api_client.get(reverse("products:product-list"))
        assert r.status_code == 200
        assert len(r.json()["results"]) >= 1

    def test_list_unauthenticated(self, api_client):
        r = api_client.get(reverse("products:product-list"))
        assert r.status_code in (401, 403)

    def test_create_product_linked_to_project(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "New Paper",
                "description": "Desc",
                "type": "articulo",
                "publication_year": 2025,
                "project": str(project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "New Paper"
        assert data["institution"] == str(institution.id)

    def test_reject_product_without_project(self, api_client, institution, admin_user):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "No Project",
                "description": "Desc",
                "type": "articulo",
                "publication_year": 2025,
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_reject_foreign_project_link(
        self, api_client, institution, admin_user, foreign_project
    ):
        _login(api_client, admin_user, institution)
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "Foreign",
                "description": "Desc",
                "type": "articulo",
                "publication_year": 2025,
                "project": str(foreign_project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_reject_invalid_type(self, api_client, institution, admin_user, center, researcher_pi):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "Bad Type",
                "description": "Desc",
                "type": "patente",
                "publication_year": 2025,
                "project": str(project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_reject_year_too_low(self, api_client, institution, admin_user, center, researcher_pi):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        r = api_client.post(
            reverse("products:product-list"),
            {
                "title": "Bad Year",
                "description": "Desc",
                "type": "articulo",
                "publication_year": 1899,
                "project": str(project.id),
            },
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_retrieve_product(self, api_client, institution, admin_user, center, researcher_pi):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution,
            project=project,
            title="Retrieve Me",
            description="D",
            type="libro",
            publication_year=2024,
        )
        r = api_client.get(reverse("products:product-detail", kwargs={"pk": str(product.id)}))
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Retrieve Me"

    def test_update_product(self, api_client, institution, admin_user, center, researcher_pi):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution,
            project=project,
            title="Old Title",
            description="D",
            type="articulo",
            publication_year=2024,
        )
        r = api_client.patch(
            reverse("products:product-detail", kwargs={"pk": str(product.id)}),
            {"title": "New Title"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"

    def test_delete_product(self, api_client, institution, admin_user, center, researcher_pi):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution,
            project=project,
            title="Delete Me",
            description="D",
            type="articulo",
            publication_year=2024,
        )
        r = api_client.delete(reverse("products:product-detail", kwargs={"pk": str(product.id)}))
        assert r.status_code == 204
        assert not ResearchProduct.objects.filter(id=product.id).exists()

    def test_empty_list_for_foreign_institution(
        self, api_client, another_institution, admin_user, center, researcher_pi
    ):
        # admin_user belongs to institution, not another_institution
        _login(api_client, admin_user, another_institution)
        project = _make_project(another_institution, center, researcher_pi)
        ResearchProduct.objects.create(
            institution=another_institution,
            project=project,
            title="Foreign",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        r = api_client.get(reverse("products:product-list"))
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_filter_by_year_gte_and_type(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        ResearchProduct.objects.create(
            institution=institution, project=project, title="P2023",
            description="D", type="articulo", publication_year=2023,
        )
        ResearchProduct.objects.create(
            institution=institution, project=project, title="P2024",
            description="D", type="articulo", publication_year=2024,
        )
        ResearchProduct.objects.create(
            institution=institution, project=project, title="P2024Libro",
            description="D", type="libro", publication_year=2024,
        )
        r = api_client.get(
            reverse("products:product-list") + "?year__gte=2024&type=articulo"
        )
        assert r.status_code == 200
        data = r.json()["results"]
        assert len(data) == 1
        assert data[0]["title"] == "P2024"


# ════════════════════════════════════════════════════════
# ProductAuthorViewSet — nested under product
# ════════════════════════════════════════════════════════


class TestProductAuthorViewSet:
    """Nested CRUD for ProductAuthor under /products/{id}/authors/."""

    def test_list_authors(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        ProductAuthor.objects.create(
            product=product, researcher=researcher_pi, is_principal=True, order=1
        )
        r = api_client.get(
            reverse("products:author-list", kwargs={"product_pk": str(product.id)})
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_create_author(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        r2 = _make_researcher(institution, document_number="R2001")
        r = api_client.post(
            reverse("products:author-list", kwargs={"product_pk": str(product.id)}),
            {"researcher": str(r2.id), "is_principal": False, "order": 2},
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["researcher"] == str(r2.id)
        assert data["is_principal"] is False

    def test_reject_duplicate_researcher(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        ProductAuthor.objects.create(
            product=product, researcher=researcher_pi, is_principal=True
        )
        r = api_client.post(
            reverse("products:author-list", kwargs={"product_pk": str(product.id)}),
            {"researcher": str(researcher_pi.id), "is_principal": False, "order": 2},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_update_author(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        author = ProductAuthor.objects.create(
            product=product, researcher=researcher_pi, is_principal=False, order=2
        )
        r = api_client.patch(
            reverse(
                "products:author-detail",
                kwargs={"product_pk": str(product.id), "pk": str(author.id)},
            ),
            {"is_principal": True, "order": 1},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["is_principal"] is True

    def test_delete_author(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        author = ProductAuthor.objects.create(
            product=product, researcher=researcher_pi, is_principal=True
        )
        r = api_client.delete(
            reverse(
                "products:author-detail",
                kwargs={"product_pk": str(product.id), "pk": str(author.id)},
            )
        )
        assert r.status_code == 204
        assert not ProductAuthor.objects.filter(id=author.id).exists()


# ════════════════════════════════════════════════════════
# ProductAttachmentViewSet — nested under product
# ════════════════════════════════════════════════════════


class TestProductAttachmentViewSet:
    """Nested CRUD for ProductAttachment under /products/{id}/attachments/."""

    def test_list_attachments(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        ProductAttachment.objects.create(
            product=product, name="File.pdf", doc_type="pdf",
            external_url="https://example.com/file.pdf",
        )
        r = api_client.get(
            reverse("products:attachment-list", kwargs={"product_pk": str(product.id)})
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) == 1

    def test_create_attachment(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        r = api_client.post(
            reverse("products:attachment-list", kwargs={"product_pk": str(product.id)}),
            {
                "name": "Evidence.pdf",
                "doc_type": "article",
                "external_url": "https://example.com/evidence.pdf",
            },
            content_type="application/json",
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Evidence.pdf"
        assert data["external_url"] == "https://example.com/evidence.pdf"

    def test_reject_empty_external_url(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        r = api_client.post(
            reverse("products:attachment-list", kwargs={"product_pk": str(product.id)}),
            {"name": "Evidence.pdf", "doc_type": "article", "external_url": ""},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_update_attachment(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        attachment = ProductAttachment.objects.create(
            product=product, name="Old.pdf", doc_type="pdf",
            external_url="https://example.com/old.pdf",
        )
        r = api_client.patch(
            reverse(
                "products:attachment-detail",
                kwargs={"product_pk": str(product.id), "pk": str(attachment.id)},
            ),
            {"name": "New.pdf"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New.pdf"

    def test_delete_attachment(
        self, api_client, institution, admin_user, center, researcher_pi
    ):
        _login(api_client, admin_user, institution)
        project = _make_project(institution, center, researcher_pi)
        product = ResearchProduct.objects.create(
            institution=institution, project=project, title="Paper",
            description="D", type="articulo", publication_year=2025,
        )
        attachment = ProductAttachment.objects.create(
            product=product, name="Del.pdf", doc_type="pdf",
            external_url="https://example.com/del.pdf",
        )
        r = api_client.delete(
            reverse(
                "products:attachment-detail",
                kwargs={"product_pk": str(product.id), "pk": str(attachment.id)},
            )
        )
        assert r.status_code == 204
        assert not ProductAttachment.objects.filter(id=attachment.id).exists()
