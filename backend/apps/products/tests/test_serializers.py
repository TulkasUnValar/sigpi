"""
Serializer tests for products app — STRICT TDD (RED phase).

Tests define the expected behavior of 3 serializers:
- ResearchProductSerializer: validation, project FK, institution read-only
- ProductAuthorSerializer: researcher FK, is_principal, order
- ProductAttachmentSerializer: name, doc_type, external_url

Spec reference: openspec/changes/products/specs/products/spec.md
Design reference: openspec/changes/products/design.md
"""
import datetime
import uuid

import pytest
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.institutions.models import Institution, ResearchCenter
from apps.products.models import ProductAttachment, ProductAuthor, ProductType, ResearchProduct
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ── Helpers ────────────────────────────────────────────


def _make_institution(code="TU"):
    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    return ResearchCenter.objects.create(institution=institution, name=name, code=code)


def _make_researcher(institution, user=None):
    return Researcher.objects.create(
        institution=institution,
        user=user,
        first_name="Maria",
        last_name="Gomez",
        document_type="CC",
        document_number=f"DN-{uuid.uuid4().hex[:8]}",
        primary_email=f"maria.{uuid.uuid4().hex[:4]}@test.edu",
    )


def _make_project(institution, center, pi, title="Test Project"):
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title=title,
        abstract="An abstract",
        objectives="Objectives text",
        methodology="Methodology text",
        expected_results="Expected results text",
        keywords="ai, nlp",
        start_date=datetime.date(2026, 1, 1),
        estimated_end_date=datetime.date(2026, 12, 31),
    )


def _make_product(institution, project, **kwargs):
    defaults = {
        "institution": institution,
        "project": project,
        "title": "AI Paper",
        "description": "A great paper",
        "type": "articulo",
        "publication_year": 2025,
    }
    defaults.update(kwargs)
    return ResearchProduct.objects.create(**defaults)


# ════════════════════════════════════════════════════════
# ResearchProductSerializer
# ════════════════════════════════════════════════════════


class TestResearchProductSerializer:
    """Serialization and validation for ResearchProduct."""

    def test_serialize_existing_product(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project, title="Deep Learning")

        serializer = ResearchProductSerializer(product)
        data = serializer.data

        assert data["title"] == "Deep Learning"
        assert data["type"] == "articulo"
        assert data["publication_year"] == 2025
        assert "id" in data
        assert "institution" in data
        assert "project" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_validate_invalid_type(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "patente",
            "publication_year": 2025,
            "project": str(project.id),
        })
        assert not serializer.is_valid()
        assert "type" in serializer.errors

    def test_validate_empty_type(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "",
            "publication_year": 2025,
            "project": str(project.id),
        })
        assert not serializer.is_valid()
        assert "type" in serializer.errors

    def test_validate_year_too_low(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "articulo",
            "publication_year": 1899,
            "project": str(project.id),
        })
        assert not serializer.is_valid()
        assert "publication_year" in serializer.errors

    def test_validate_year_too_high(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        current_year = datetime.date.today().year

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "articulo",
            "publication_year": current_year + 2,
            "project": str(project.id),
        })
        assert not serializer.is_valid()
        assert "publication_year" in serializer.errors

    def test_validate_valid_year_at_bounds(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        current_year = datetime.date.today().year

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "articulo",
            "publication_year": current_year + 1,
            "project": str(project.id),
        })
        assert serializer.is_valid(), serializer.errors

    def test_institution_read_only(self, db):
        from apps.products.serializers import ResearchProductSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        serializer = ResearchProductSerializer(data={
            "title": "Test",
            "description": "D",
            "type": "articulo",
            "publication_year": 2025,
            "project": str(project.id),
            "institution": str(uuid.uuid4()),
        })
        assert serializer.is_valid(), serializer.errors
        assert "institution" not in serializer.validated_data


# ════════════════════════════════════════════════════════
# ProductAuthorSerializer
# ════════════════════════════════════════════════════════


class TestProductAuthorSerializer:
    """Serialization and validation for ProductAuthor."""

    def test_serialize_existing_author(self, db):
        from apps.products.serializers import ProductAuthorSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project)
        author = ProductAuthor.objects.create(
            product=product, researcher=pi, is_principal=True, order=1,
        )

        serializer = ProductAuthorSerializer(author)
        data = serializer.data

        assert data["is_principal"] is True
        assert data["order"] == 1
        assert "researcher" in data

    def test_validate_duplicate_researcher(self, db):
        from apps.products.serializers import ProductAuthorSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project)
        ProductAuthor.objects.create(product=product, researcher=pi, is_principal=True)

        serializer = ProductAuthorSerializer(data={
            "product": str(product.id),
            "researcher": str(pi.id),
            "is_principal": False,
            "order": 2,
        })
        assert not serializer.is_valid()
        assert "researcher" in serializer.errors or "non_field_errors" in serializer.errors


# ════════════════════════════════════════════════════════
# ProductAttachmentSerializer
# ════════════════════════════════════════════════════════


class TestProductAttachmentSerializer:
    """Serialization and validation for ProductAttachment."""

    def test_serialize_existing_attachment(self, db):
        from apps.products.serializers import ProductAttachmentSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project)
        attachment = ProductAttachment.objects.create(
            product=product,
            name="Evidence.pdf",
            doc_type="article",
            external_url="https://example.com/evidence.pdf",
        )

        serializer = ProductAttachmentSerializer(attachment)
        data = serializer.data

        assert data["name"] == "Evidence.pdf"
        assert data["doc_type"] == "article"
        assert data["external_url"] == "https://example.com/evidence.pdf"
        assert "created_at" in data

    def test_reject_empty_external_url(self, db):
        from apps.products.serializers import ProductAttachmentSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project)

        serializer = ProductAttachmentSerializer(data={
            "product": str(product.id),
            "name": "Evidence.pdf",
            "doc_type": "article",
            "external_url": "",
        })
        assert not serializer.is_valid()
        assert "external_url" in serializer.errors

    def test_reject_missing_external_url(self, db):
        from apps.products.serializers import ProductAttachmentSerializer

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = _make_product(inst, project)

        serializer = ProductAttachmentSerializer(data={
            "product": str(product.id),
            "name": "Evidence.pdf",
            "doc_type": "article",
        })
        assert not serializer.is_valid()
        assert "external_url" in serializer.errors
