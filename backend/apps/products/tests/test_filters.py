"""
Filter tests for products app — STRICT TDD (RED phase).

Tests define the expected behavior of ResearchProductFilter:
- type, year exact, year__gte, year__lte
- project, center, group, line, researcher

Spec reference: openspec/changes/products/specs/products/spec.md — RF-084
Design reference: openspec/changes/products/design.md
"""
import datetime
import uuid

import pytest

from apps.institutions.models import Institution, ResearchCenter, ResearchGroup, ResearchLine
from apps.products.models import ProductAuthor, ProductType, ResearchProduct
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ── Helpers ────────────────────────────────────────────


def _make_institution(code="TU"):
    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    return ResearchCenter.objects.create(institution=institution, name=name, code=code)


def _make_group(center, institution, name="NLP Group", code="NLP"):
    return ResearchGroup.objects.create(center=center, institution=institution, name=name, code=code)


def _make_line(group, institution, name="Deep Learning Line", code="DL"):
    return ResearchLine.objects.create(group=group, institution=institution, name=name, code=code)


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


def _make_project(institution, center, pi, group=None, line=None, title="Test Project"):
    return Project.objects.create(
        institution=institution,
        center=center,
        group=group,
        line=line,
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
# ResearchProductFilter
# ════════════════════════════════════════════════════════


class TestResearchProductFilter:
    """FilterSet behavior for ResearchProduct list endpoint."""

    def test_filter_by_type(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        _make_product(inst, project, type="articulo")
        _make_product(inst, project, type="libro")

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"type": "articulo"}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().type == "articulo"

    def test_filter_by_year_exact(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        _make_product(inst, project, publication_year=2024)
        _make_product(inst, project, publication_year=2025)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"year": 2025}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().publication_year == 2025

    def test_filter_by_year_gte(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        _make_product(inst, project, publication_year=2023)
        _make_product(inst, project, publication_year=2024)
        _make_product(inst, project, publication_year=2025)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"year__gte": 2024}, queryset=qs)
        assert f.qs.count() == 2
        years = {p.publication_year for p in f.qs}
        assert years == {2024, 2025}

    def test_filter_by_year_lte(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        _make_product(inst, project, publication_year=2023)
        _make_product(inst, project, publication_year=2024)
        _make_product(inst, project, publication_year=2025)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"year__lte": 2024}, queryset=qs)
        assert f.qs.count() == 2
        years = {p.publication_year for p in f.qs}
        assert years == {2023, 2024}

    def test_filter_by_project(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        p1 = _make_project(inst, center, pi, title="P1")
        p2 = _make_project(inst, center, pi, title="P2")
        _make_product(inst, p1)
        _make_product(inst, p2)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"project": str(p1.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project == p1

    def test_filter_by_center(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        c1 = _make_center(inst, name="Lab1", code="L1")
        c2 = _make_center(inst, name="Lab2", code="L2")
        pi = _make_researcher(inst)
        p1 = _make_project(inst, c1, pi)
        p2 = _make_project(inst, c2, pi)
        _make_product(inst, p1)
        _make_product(inst, p2)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"center": str(c1.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project.center == c1

    def test_filter_by_group(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        g1 = _make_group(center, inst, name="G1", code="G1")
        g2 = _make_group(center, inst, name="G2", code="G2")
        pi = _make_researcher(inst)
        p1 = _make_project(inst, center, pi, group=g1)
        p2 = _make_project(inst, center, pi, group=g2)
        _make_product(inst, p1)
        _make_product(inst, p2)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"group": str(g1.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project.group == g1

    def test_filter_by_line(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        group = _make_group(center, inst)
        l1 = _make_line(group, inst, name="L1", code="L1")
        l2 = _make_line(group, inst, name="L2", code="L2")
        pi = _make_researcher(inst)
        p1 = _make_project(inst, center, pi, group=group, line=l1)
        p2 = _make_project(inst, center, pi, group=group, line=l2)
        _make_product(inst, p1)
        _make_product(inst, p2)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"line": str(l1.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first().project.line == l1

    def test_filter_by_researcher(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        r2 = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        prod1 = _make_product(inst, project, title="Prod1")
        prod2 = _make_product(inst, project, title="Prod2")
        ProductAuthor.objects.create(product=prod1, researcher=pi, is_principal=True)
        ProductAuthor.objects.create(product=prod2, researcher=r2, is_principal=True)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"researcher": str(pi.id)}, queryset=qs)
        assert f.qs.count() == 1
        assert f.qs.first() == prod1

    def test_filter_combined_year_range_and_type(self, db):
        from apps.products.filters import ResearchProductFilter

        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        _make_product(inst, project, type="articulo", publication_year=2023)
        _make_product(inst, project, type="articulo", publication_year=2024)
        _make_product(inst, project, type="libro", publication_year=2024)
        _make_product(inst, project, type="articulo", publication_year=2025)

        qs = ResearchProduct.objects.all()
        f = ResearchProductFilter(data={"year__gte": 2024, "type": "articulo"}, queryset=qs)
        assert f.qs.count() == 2
        years = {p.publication_year for p in f.qs}
        assert years == {2024, 2025}
        for p in f.qs:
            assert p.type == "articulo"
