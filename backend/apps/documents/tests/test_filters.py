"""
FilterSet tests for the documents module — STRICT TDD (RED phase).

Covers the Phase 4 filter contracts from spec.md API Contract:
- DocumentFilter: doc_type (code), entity (entity_type), is_signed.
- MinutesFilter: acta_type, project.

RED PHASE: filters.py does not exist yet — all tests fail on import.
"""

from apps.documents.models import Document, DocumentType, Minutes
from apps.documents.tests.conftest import DocumentFactory, DocumentVersionFactory

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


# ════════════════════════════════════════════════════════
# DocumentFilter
# ════════════════════════════════════════════════════════


class TestDocumentFilter:
    def test_filter_by_doc_type_code(self, db):
        from apps.documents.filters import DocumentFilter

        institution = _make_institution()
        user = _make_user()
        acta = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="informe_final"),
            created_by=user,
        )

        qs = DocumentFilter(data={"doc_type": "acta_inicio"}, queryset=Document.objects.all()).qs

        assert list(qs) == [acta]

    def test_filter_by_entity_type(self, db):
        from apps.calls.models import Call, CallType
        from apps.documents.filters import DocumentFilter

        institution = _make_institution()
        user = _make_user()
        call = Call.objects.create(
            institution=institution,
            title="Test Call",
            description="Desc",
            call_type=CallType.INTERNAL,
        )
        bound = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
            entity_type="call",
            call=call,
        )
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )

        qs = DocumentFilter(data={"entity": "call"}, queryset=Document.objects.all()).qs

        assert list(qs) == [bound]

    def test_filter_by_is_signed(self, db):
        from apps.documents.filters import DocumentFilter
        from apps.documents.tests.conftest import DigitalSignatureFactory

        institution = _make_institution()
        user = _make_user()
        signed = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )
        version = DocumentVersionFactory(document=signed, version=1, uploaded_by=user)
        DigitalSignatureFactory(document_version=version, signer=user, sha256=version.sha256)
        Document.objects.filter(pk=signed.pk).update(is_signed=True)
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )

        qs = DocumentFilter(data={"is_signed": "true"}, queryset=Document.objects.all()).qs

        assert list(qs) == [signed]

    def test_no_filters_returns_all(self, db):
        from apps.documents.filters import DocumentFilter

        institution = _make_institution()
        user = _make_user()
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="informe_final"),
            created_by=user,
        )

        qs = DocumentFilter(data={}, queryset=Document.objects.all()).qs

        assert qs.count() == 2

    def test_invalid_is_signed_value_ignored(self, db):
        from apps.documents.filters import DocumentFilter

        institution = _make_institution()
        user = _make_user()
        DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )

        qs = DocumentFilter(data={"is_signed": "not-a-bool"}, queryset=Document.objects.all()).qs

        assert qs.count() == 1


# ════════════════════════════════════════════════════════
# MinutesFilter
# ════════════════════════════════════════════════════════


class TestMinutesFilter:
    def test_filter_by_acta_type(self, db):
        from apps.documents.filters import MinutesFilter
        from apps.projects.tests.conftest import ProjectFactory

        institution = _make_institution()
        user = _make_user()
        project_a = ProjectFactory(institution=institution)
        project_b = ProjectFactory(institution=institution)
        doc_a = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )
        doc_b = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_cierre"),
            created_by=user,
        )
        inicio = Minutes.objects.create(
            acta_type=Minutes.ActaType.INICIO,
            project=project_a,
            institution=institution,
            document=doc_a,
            created_by=user,
        )
        Minutes.objects.create(
            acta_type=Minutes.ActaType.CIERRE,
            project=project_b,
            institution=institution,
            document=doc_b,
            created_by=user,
        )

        qs = MinutesFilter(data={"acta_type": "inicio"}, queryset=Minutes.objects.all()).qs

        assert list(qs) == [inicio]

    def test_filter_by_project(self, db):
        from apps.documents.filters import MinutesFilter
        from apps.projects.tests.conftest import ProjectFactory

        institution = _make_institution()
        user = _make_user()
        project_a = ProjectFactory(institution=institution)
        project_b = ProjectFactory(institution=institution)
        doc_a = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_inicio"),
            created_by=user,
        )
        doc_b = DocumentFactory(
            institution=institution,
            doc_type=DocumentType.objects.get(code="acta_cierre"),
            created_by=user,
        )
        target = Minutes.objects.create(
            acta_type=Minutes.ActaType.INICIO,
            project=project_a,
            institution=institution,
            document=doc_a,
            created_by=user,
        )
        Minutes.objects.create(
            acta_type=Minutes.ActaType.CIERRE,
            project=project_b,
            institution=institution,
            document=doc_b,
            created_by=user,
        )

        qs = MinutesFilter(data={"project": str(project_a.pk)}, queryset=Minutes.objects.all()).qs

        assert list(qs) == [target]
