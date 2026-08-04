"""
Model tests for products app — STRICT TDD.

Tests define the expected behavior of the 3-entity products module:
ResearchProduct, ProductAuthor, ProductAttachment.

Spec reference:  openspec/changes/products/specs/products/spec.md
Design reference: openspec/changes/products/design.md

RED PHASE: All tests fail because models do not exist yet.
"""
import datetime
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.products.models import (
    ProductAttachment,
    ProductAuthor,
    ProductType,
    ResearchProduct,
)

# ──────────────────────────────────────────────
# Helpers (mirror projects test pattern)
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(
        name=f"Test University {code}", code=code,
    )


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code,
    )


def _make_researcher(institution, user=None):
    import uuid as _uuid

    from apps.researchers.models import Researcher

    return Researcher.objects.create(
        institution=institution,
        user=user,
        first_name="Maria",
        last_name="Gomez",
        document_type="CC",
        document_number=f"DN-{_uuid.uuid4().hex[:8]}",
        primary_email=f"maria.{_uuid.uuid4().hex[:4]}@test.edu",
    )


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_project(institution, center, pi, title="Test Project"):
    from apps.projects.models import Project

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


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestProductTypeEnum:
    """ProductType TextChoices has 11 types."""

    def test_all_eleven_types_defined(self):
        """All 11 product types are present in ProductType."""
        expected = {
            "articulo",
            "libro",
            "capitulo",
            "software",
            "prototipo",
            "evento",
            "consultoria",
            "diseno_industrial",
            "innovacion_proceso",
            "innovacion_gestion",
            "carta",
        }
        actual = {choice[0] for choice in ProductType.choices}
        assert actual == expected


# ──────────────────────────────────────────────
# ResearchProduct Model Field Tests
# ──────────────────────────────────────────────


class TestResearchProductFields:
    """ResearchProduct model field behavior and defaults."""

    def test_create_product_minimal(self, db):
        """ResearchProduct can be created with required fields."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="AI Paper",
            description="A great paper on AI",
            type="articulo",
            publication_year=2025,
        )
        assert product.id is not None
        assert isinstance(product.id, uuid.UUID)
        assert product.institution == inst
        assert product.project == project
        assert product.title == "AI Paper"
        assert product.type == "articulo"
        assert product.publication_year == 2025
        assert product.created_at is not None
        assert product.updated_at is not None

    def test_str_representation(self, db):
        """ResearchProduct __str__ returns the title."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Deep Learning Survey",
            description="Survey",
            type="articulo",
            publication_year=2025,
        )
        assert str(product) == "Deep Learning Survey"

    def test_timestamps_auto_set(self, db):
        """created_at and updated_at are set automatically."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="libro",
            publication_year=2024,
        )
        assert product.created_at is not None
        assert product.updated_at is not None


# ──────────────────────────────────────────────
# ResearchProduct clean() Validation Tests
# ──────────────────────────────────────────────


class TestResearchProductCleanValidation:
    """ResearchProduct.clean() enforces type and year validation (RF-081)."""

    def test_clean_rejects_invalid_type(self, db):
        """RF-081: invalid type raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="patente",
            publication_year=2025,
        )
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_clean_rejects_empty_type(self, db):
        """RF-081: empty type raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="",
            publication_year=2025,
        )
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_clean_accepts_valid_types(self, db):
        """RF-081: all 11 valid types pass clean()."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        for ptype in (
            "articulo",
            "libro",
            "capitulo",
            "software",
            "prototipo",
            "evento",
            "consultoria",
            "diseno_industrial",
            "innovacion_proceso",
            "innovacion_gestion",
            "carta",
        ):
            product = ResearchProduct(
                institution=inst,
                project=project,
                title=f"Test {ptype}",
                description="D",
                type=ptype,
                publication_year=2025,
            )
            product.full_clean()  # should not raise

    def test_clean_rejects_year_too_low(self, db):
        """RF-081: publication_year < 1900 raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=1899,
        )
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_clean_rejects_year_too_high(self, db):
        """RF-081: publication_year > current_year+1 raises ValidationError."""
        import datetime as dt

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        current_year = dt.date.today().year
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=current_year + 2,
        )
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_clean_accepts_year_at_upper_bound(self, db):
        """RF-081: publication_year == current_year+1 passes clean()."""
        import datetime as dt

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        current_year = dt.date.today().year
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=current_year + 1,
        )
        product.full_clean()  # should not raise

    def test_clean_accepts_year_at_lower_bound(self, db):
        """RF-081: publication_year == 1900 passes clean()."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=1900,
        )
        product.full_clean()  # should not raise


# ──────────────────────────────────────────────
# ProductAuthor Tests
# ──────────────────────────────────────────────


class TestProductAuthorFields:
    """ProductAuthor model field behavior and constraints."""

    def test_create_author(self, db):
        """ProductAuthor links a Researcher to a ResearchProduct."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        author = ProductAuthor.objects.create(
            product=product,
            researcher=pi,
            is_principal=True,
            order=1,
        )
        assert author.product == product
        assert author.researcher == pi
        assert author.is_principal is True
        assert author.order == 1

    def test_unique_product_researcher(self, db):
        """UniqueConstraint (product, researcher) enforced."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        researcher2 = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        ProductAuthor.objects.create(
            product=product, researcher=researcher2, is_principal=False,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductAuthor.objects.create(
                    product=product, researcher=researcher2, is_principal=True,
                )

    def test_str_representation(self, db):
        """ProductAuthor __str__ includes researcher and product."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="AI Paper",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        author = ProductAuthor.objects.create(
            product=product, researcher=pi, is_principal=True,
        )
        assert str(pi) in str(author)
        assert "AI Paper" in str(author)

    def test_order_defaults_to_zero(self, db):
        """order defaults to 0."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        author = ProductAuthor.objects.create(
            product=product, researcher=pi, is_principal=False,
        )
        assert author.order == 0


# ──────────────────────────────────────────────
# ProductAttachment Tests
# ──────────────────────────────────────────────


class TestProductAttachmentFields:
    """ProductAttachment model field behavior."""

    def test_create_attachment(self, db):
        """ProductAttachment stores name, type, and external URL (RF-083)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        attachment = ProductAttachment.objects.create(
            product=product,
            name="Evidence.pdf",
            doc_type="article",
            external_url="https://storage.example.com/evidence.pdf",
        )
        assert attachment.name == "Evidence.pdf"
        assert attachment.doc_type == "article"
        assert attachment.external_url == "https://storage.example.com/evidence.pdf"
        assert attachment.product == product
        assert attachment.created_at is not None

    def test_str_representation(self, db):
        """ProductAttachment __str__ includes name."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        product = ResearchProduct.objects.create(
            institution=inst,
            project=project,
            title="Test",
            description="D",
            type="articulo",
            publication_year=2025,
        )
        attachment = ProductAttachment.objects.create(
            product=product,
            name="Evidence.pdf",
            doc_type="article",
            external_url="https://example.com/evidence.pdf",
        )
        assert "Evidence.pdf" in str(attachment)
