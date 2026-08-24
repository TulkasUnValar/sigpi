"""
django-filter FilterSets for the documents module.

Provides:
- DocumentFilter: doc_type (DocumentType code), entity (entity_type
  choice), is_signed — per the API Contract list filters.
- MinutesFilter: acta_type, project.

Used by the Phase 5 ViewSets via DjangoFilterBackend.

Design reference: openspec/changes/attachments/design.md — Filtering
Spec reference:   openspec/changes/attachments/specs/documents/spec.md — API Contract
"""

import django_filters

from apps.documents.models import Document, EntityType, Minutes


class DocumentFilter(django_filters.FilterSet):
    """FilterSet for the Document list endpoint.

    - doc_type: exact DocumentType code (e.g. ?doc_type=acta_inicio)
    - entity: entity_type choice (advance/report/product/call)
    - is_signed: boolean flag
    """

    doc_type = django_filters.CharFilter(field_name="doc_type__code", lookup_expr="exact")
    entity = django_filters.ChoiceFilter(field_name="entity_type", choices=EntityType.choices)
    is_signed = django_filters.BooleanFilter()

    class Meta:
        model = Document
        fields = ["doc_type", "entity", "is_signed"]


class MinutesFilter(django_filters.FilterSet):
    """FilterSet for the Minutes list endpoint.

    - acta_type: one of the four acta choices (inicio/comite/aprobacion/cierre)
    - project: exact project UUID
    """

    acta_type = django_filters.ChoiceFilter(choices=Minutes.ActaType.choices)
    project = django_filters.UUIDFilter(field_name="project")

    class Meta:
        model = Minutes
        fields = ["acta_type", "project"]
