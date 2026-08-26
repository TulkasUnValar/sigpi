"""Document projections for the five Meilisearch indexes (SIGPI §6.11).

Each indexer maps a Django model instance to the flat document shape
declared by the spec Index Layout:

- ``id`` and ``institution_id`` are always strings: Meilisearch requires
  string primary keys and the tenant filter compares string UUIDs
  (``institution_id == request.institution_id``).
- Denormalized display fields (``center_id``, ``line_id``,
  ``project_title``) avoid joins at query time.
- Layout filters ``institution``/``center``/``line`` are projected onto
  the document attributes ``institution_id``/``center_id``/``line_id`` —
  these are the actual filterable attribute names applied as index
  settings.

``INDEX_CONFIG`` maps each index to its searchable/filterable attribute
lists (applied by ``reindex_search``). ``INDEXERS`` maps index names to
the matching ``to_document`` projection; ``to_document()`` is the
dispatcher used by the Celery tasks.
"""

from collections.abc import Callable
from typing import Any

from apps.calls.models import Call
from apps.products.models import ResearchProduct
from apps.progress.models import ProgressReport
from apps.projects.models import Project
from apps.researchers.models import Researcher, ResearcherAffiliation

INDEX_CONFIG: dict[str, dict[str, list[str]]] = {
    "projects": {
        "searchable": [
            "title",
            "abstract",
            "objectives",
            "methodology",
            "expected_results",
            "keywords",
        ],
        "filterable": ["institution_id", "center_id", "line_id", "status", "year"],
    },
    "researchers": {
        "searchable": [
            "first_name",
            "last_name",
            "primary_email",
            "document_number",
            "bio",
            "academic_formation",
        ],
        "filterable": ["institution_id", "center_id", "line_id", "is_active"],
    },
    "products": {
        "searchable": ["title", "description", "type", "publication_year"],
        "filterable": ["institution_id", "type", "year"],
    },
    "calls": {
        "searchable": [
            "title",
            "description",
            "external_entity",
            "call_type",
            "status",
            "submission_start",
        ],
        "filterable": ["institution_id", "type", "status", "year"],
    },
    "advances": {
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
    },
}


def _primary_affiliation(researcher: Researcher) -> ResearcherAffiliation | None:
    """Return the researcher's primary affiliation, if any.

    The domain enforces exactly one primary affiliation per researcher
    (ResearcherAffiliation.clean), so this is deterministic.
    """
    return researcher.affiliations.filter(is_primary=True).first()


def to_project_document(project: Project) -> dict[str, Any]:
    """Project → ``projects`` document."""
    return {
        "id": str(project.id),
        "institution_id": str(project.institution_id),
        "center_id": str(project.center_id),
        "line_id": str(project.line_id) if project.line_id else None,
        "title": project.title,
        "abstract": project.abstract,
        "objectives": project.objectives,
        "methodology": project.methodology,
        "expected_results": project.expected_results,
        "keywords": project.keywords,
        "status": project.status,
        "year": project.start_date.year,
    }


def to_researcher_document(researcher: Researcher) -> dict[str, Any]:
    """Researcher → ``researchers`` document (center/line from primary affiliation)."""
    affiliation = _primary_affiliation(researcher)
    return {
        "id": str(researcher.id),
        "institution_id": str(researcher.institution_id),
        "center_id": str(affiliation.center_id) if affiliation and affiliation.center_id else None,
        "line_id": str(affiliation.line_id) if affiliation and affiliation.line_id else None,
        "first_name": researcher.first_name,
        "last_name": researcher.last_name,
        "primary_email": researcher.primary_email,
        "document_number": researcher.document_number,
        "bio": researcher.bio,
        "academic_formation": researcher.academic_formation,
        "is_active": researcher.is_active,
    }


def to_product_document(product: ResearchProduct) -> dict[str, Any]:
    """ResearchProduct → ``products`` document."""
    return {
        "id": str(product.id),
        "institution_id": str(product.institution_id),
        "title": product.title,
        "description": product.description,
        "type": product.type,
        "publication_year": product.publication_year,
        "year": product.publication_year,
    }


def to_call_document(call: Call) -> dict[str, Any]:
    """Call → ``calls`` document (year falls back to the creation year)."""
    return {
        "id": str(call.id),
        "institution_id": str(call.institution_id),
        "title": call.title,
        "description": call.description,
        "external_entity": call.external_entity,
        "call_type": call.call_type,
        "type": call.call_type,
        "status": call.status,
        "submission_start": call.submission_start.isoformat() if call.submission_start else None,
        "year": call.submission_start.year if call.submission_start else call.created_at.year,
    }


def to_advance_document(report: ProgressReport) -> dict[str, Any]:
    """ProgressReport → ``advances`` document (center/project_title denormalized)."""
    return {
        "id": str(report.id),
        "institution_id": str(report.institution_id),
        "center_id": str(report.center_id) if report.center_id else None,
        "project_title": report.project.title,
        "description": report.description,
        "activities": report.activities,
        "difficulties": report.difficulties,
        "next_steps": report.next_steps,
        "status": report.status,
        "period_start": report.period_start.isoformat(),
        "year": report.period_start.year,
    }


INDEXERS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "projects": to_project_document,
    "researchers": to_researcher_document,
    "products": to_product_document,
    "calls": to_call_document,
    "advances": to_advance_document,
}


def to_document(index_name: str, instance: Any) -> dict[str, Any]:
    """Project ``instance`` into the document shape of ``index_name``."""
    try:
        indexer = INDEXERS[index_name]
    except KeyError:
        raise KeyError(f"Unknown search index: {index_name}") from None
    return indexer(instance)
