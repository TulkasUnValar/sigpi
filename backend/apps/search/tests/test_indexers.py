"""Indexer document-shape tests for PR 2 — Indexers + Client (STRICT TDD).

Verifies, per the spec Index Layout:
- ``INDEX_CONFIG`` declares the exact searchable/filterable maps for the
  five indexes (filter layout names ``institution``/``center``/``line``
  are projected onto the document attributes ``institution_id`` /
  ``center_id`` / ``line_id`` per the tenant isolation contract).
- Each ``to_*_document`` indexer produces the exact document shape:
  string UUID ``id``, string ``institution_id``, denormalized display
  fields (``center_id``, ``line_id``, ``project_title``) and numeric/date
  filter values.
- The ``to_document(index_name, instance)`` dispatcher routes to the
  right indexer and rejects unknown indexes.

Spec reference:   meilisearch-module spec — Index Layout
Design reference: meilisearch-module design — Interfaces / Contracts
"""

import datetime

import pytest

from apps.calls.tests.conftest import CallFactory
from apps.institutions.tests.conftest import (
    ResearchCenterFactory,
    ResearchGroupFactory,
    ResearchLineFactory,
)
from apps.products.tests.conftest import ProductFactory
from apps.progress.tests.conftest import ProgressReportFactory
from apps.projects.tests.conftest import ProjectFactory
from apps.researchers.tests.conftest import ResearcherAffiliationFactory, ResearcherFactory
from apps.search.indexers import (
    INDEX_CONFIG,
    INDEXERS,
    to_advance_document,
    to_call_document,
    to_document,
    to_product_document,
    to_project_document,
    to_researcher_document,
)


class TestIndexConfig:
    """INDEX_CONFIG searchable/filterable maps match the spec Index Layout."""

    def test_index_config_declares_all_five_indexes(self):
        assert set(INDEX_CONFIG) == {"projects", "researchers", "products", "calls", "advances"}

    def test_projects_maps_spec_layout(self):
        assert INDEX_CONFIG["projects"] == {
            "searchable": [
                "title",
                "abstract",
                "objectives",
                "methodology",
                "expected_results",
                "keywords",
            ],
            "filterable": ["institution_id", "center_id", "line_id", "status", "year"],
        }

    def test_researchers_maps_spec_layout(self):
        assert INDEX_CONFIG["researchers"] == {
            "searchable": [
                "first_name",
                "last_name",
                "primary_email",
                "document_number",
                "bio",
                "academic_formation",
            ],
            "filterable": ["institution_id", "center_id", "line_id", "is_active"],
        }

    def test_products_maps_spec_layout(self):
        assert INDEX_CONFIG["products"] == {
            "searchable": ["title", "description", "type", "publication_year"],
            "filterable": ["institution_id", "type", "year"],
        }

    def test_calls_maps_spec_layout(self):
        assert INDEX_CONFIG["calls"] == {
            "searchable": [
                "title",
                "description",
                "external_entity",
                "call_type",
                "status",
                "submission_start",
            ],
            "filterable": ["institution_id", "type", "status", "year"],
        }

    def test_advances_maps_spec_layout(self):
        assert INDEX_CONFIG["advances"] == {
            "searchable": [
                "description",
                "activities",
                "difficulties",
                "next_steps",
                "project_title",
                "status",
                "period_start",
            ],
            "filterable": ["institution_id", "status", "year", "center_id"],
        }

    def test_indexers_registry_keys_match_config(self):
        assert set(INDEXERS) == set(INDEX_CONFIG)


@pytest.mark.django_db
class TestProjectIndexer:
    def test_document_shape_without_line(self):
        project = ProjectFactory(
            title="Biotecnología aplicada",
            abstract="Resumen del proyecto",
            objectives="Objetivo general",
            methodology="Método experimental",
            expected_results="Resultados esperados",
            keywords="biotecnología, agricultura",
            start_date=datetime.date(2026, 3, 1),
            estimated_end_date=datetime.date(2027, 2, 28),
            status="aprobado",
        )
        assert to_project_document(project) == {
            "id": str(project.id),
            "institution_id": str(project.institution_id),
            "center_id": str(project.center_id),
            "line_id": None,
            "title": "Biotecnología aplicada",
            "abstract": "Resumen del proyecto",
            "objectives": "Objetivo general",
            "methodology": "Método experimental",
            "expected_results": "Resultados esperados",
            "keywords": "biotecnología, agricultura",
            "status": "aprobado",
            "year": 2026,
        }

    def test_document_shape_with_line_different_year(self):
        center = ResearchCenterFactory()
        group = ResearchGroupFactory(center=center)
        line = ResearchLineFactory(group=group)
        project = ProjectFactory(
            center=center,
            line=line,
            start_date=datetime.date(2025, 11, 20),
            estimated_end_date=datetime.date(2026, 11, 19),
            status="en_ejecucion",
        )
        doc = to_project_document(project)
        assert doc["line_id"] == str(line.id)
        assert doc["center_id"] == str(center.id)
        assert doc["year"] == 2025
        assert doc["status"] == "en_ejecucion"


@pytest.mark.django_db
class TestResearcherIndexer:
    def test_document_shape_with_primary_affiliation(self):
        researcher = ResearcherFactory(
            first_name="Ana",
            last_name="García",
            primary_email="ana.garcia@test.edu",
            document_number="DOC-123456",
            bio="Investigadora principal",
            academic_formation="Doctorado en Biología",
            is_active=True,
        )
        center = ResearchCenterFactory(institution=researcher.institution)
        group = ResearchGroupFactory(institution=researcher.institution, center=center)
        line = ResearchLineFactory(institution=researcher.institution, group=group)
        ResearcherAffiliationFactory(
            researcher=researcher,
            center=center,
            line=line,
            is_primary=True,
        )
        assert to_researcher_document(researcher) == {
            "id": str(researcher.id),
            "institution_id": str(researcher.institution_id),
            "center_id": str(center.id),
            "line_id": str(line.id),
            "first_name": "Ana",
            "last_name": "García",
            "primary_email": "ana.garcia@test.edu",
            "document_number": "DOC-123456",
            "bio": "Investigadora principal",
            "academic_formation": "Doctorado en Biología",
            "is_active": True,
        }

    def test_document_shape_without_affiliation(self):
        researcher = ResearcherFactory(is_active=False)
        doc = to_researcher_document(researcher)
        assert doc["center_id"] is None
        assert doc["line_id"] is None
        assert doc["is_active"] is False


@pytest.mark.django_db
class TestProductIndexer:
    def test_document_shape(self):
        product = ProductFactory(
            title="Artículo de revisión",
            description="Revisión sistemática de la literatura",
            type="articulo",
            publication_year=2025,
        )
        assert to_product_document(product) == {
            "id": str(product.id),
            "institution_id": str(product.institution_id),
            "title": "Artículo de revisión",
            "description": "Revisión sistemática de la literatura",
            "type": "articulo",
            "publication_year": 2025,
            "year": 2025,
        }

    def test_software_type_years_match(self):
        product = ProductFactory(type="software", publication_year=2024)
        doc = to_product_document(product)
        assert doc["type"] == "software"
        assert doc["year"] == doc["publication_year"] == 2024


@pytest.mark.django_db
class TestCallIndexer:
    def test_document_shape_with_submission_start(self):
        call = CallFactory(
            title="Convocatoria interna 2026",
            description="Convocatoria para proyectos de investigación",
            call_type="internal",
            external_entity="",
            submission_start=datetime.date(2026, 2, 1),
            status="abierta",
        )
        assert to_call_document(call) == {
            "id": str(call.id),
            "institution_id": str(call.institution_id),
            "title": "Convocatoria interna 2026",
            "description": "Convocatoria para proyectos de investigación",
            "external_entity": "",
            "call_type": "internal",
            "type": "internal",
            "status": "abierta",
            "submission_start": "2026-02-01",
            "year": 2026,
        }

    def test_document_shape_without_submission_start(self):
        call = CallFactory(status="borrador")
        doc = to_call_document(call)
        assert doc["submission_start"] is None
        assert doc["year"] == call.created_at.year


@pytest.mark.django_db
class TestAdvanceIndexer:
    def test_document_shape(self):
        report = ProgressReportFactory(
            description="Avance del proyecto",
            activities="Actividades realizadas en el periodo",
            difficulties="Dificultades encontradas",
            next_steps="Próximos pasos planificados",
            status="enviado",
        )
        assert to_advance_document(report) == {
            "id": str(report.id),
            "institution_id": str(report.institution_id),
            "center_id": str(report.project.center_id),
            "project_title": report.project.title,
            "description": "Avance del proyecto",
            "activities": "Actividades realizadas en el periodo",
            "difficulties": "Dificultades encontradas",
            "next_steps": "Próximos pasos planificados",
            "status": "enviado",
            "period_start": report.period_start.isoformat(),
            "year": report.period_start.year,
        }

    def test_document_shape_with_fixed_period_and_status(self):
        report = ProgressReportFactory(
            period_start=datetime.date(2025, 7, 15),
            period_end=datetime.date(2025, 12, 20),
            status="aprobado",
        )
        doc = to_advance_document(report)
        assert doc["period_start"] == "2025-07-15"
        assert doc["year"] == 2025
        assert doc["status"] == "aprobado"
        assert doc["center_id"] == str(report.project.center_id)


@pytest.mark.django_db
class TestDispatcher:
    def test_to_document_routes_to_indexer(self):
        project = ProjectFactory()
        assert to_document("projects", project) == to_project_document(project)

    def test_unknown_index_raises_key_error(self):
        with pytest.raises(KeyError, match="nope"):
            to_document("nope", object())
