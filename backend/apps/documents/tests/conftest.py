"""
Factory-boy factories for the documents module.

Provides ergonomic test data generation for DocumentType,
Document, DocumentVersion, DigitalSignature, and Minutes.

Spec reference:  openspec/changes/attachments/specs/documents/spec.md
Design reference: openspec/changes/attachments/design.md

RED PHASE: Factories reference models that do not exist yet.
"""

import factory
from factory.django import DjangoModelFactory

from apps.documents.models import (
    DigitalSignature,
    Document,
    DocumentType,
    DocumentVersion,
    Minutes,
)


class DocumentTypeFactory(DjangoModelFactory):
    """Factory for DocumentType — code/label pair."""

    code = factory.Sequence(lambda n: f"tipo_{n}")
    label = factory.Faker("word")

    class Meta:
        model = DocumentType


class DocumentFactory(DjangoModelFactory):
    """Factory for Document — institution-scoped, unsigned by default."""

    institution = factory.SubFactory("apps.institutions.tests.conftest.InstitutionFactory")
    doc_type = factory.SubFactory(DocumentTypeFactory)
    title = factory.Faker("sentence", nb_words=6)
    created_by = factory.SubFactory("apps.projects.tests.conftest.UserFactory")

    class Meta:
        model = Document


class DocumentVersionFactory(DjangoModelFactory):
    """Factory for DocumentVersion — v1+ with valid 64-hex sha256."""

    document = factory.SubFactory(DocumentFactory)
    version = factory.Sequence(lambda n: n + 1)
    object_key = factory.LazyAttribute(
        lambda o: f"documents/{o.document.institution.pk}/{o.document.pk}/v{o.version}/file.pdf"
    )
    sha256 = factory.LazyFunction(lambda: "a" * 64)
    size_bytes = 1024
    mime_type = "application/pdf"
    uploaded_by = factory.SubFactory("apps.projects.tests.conftest.UserFactory")

    class Meta:
        model = DocumentVersion


class DigitalSignatureFactory(DjangoModelFactory):
    """Factory for DigitalSignature — one per version."""

    document_version = factory.SubFactory(DocumentVersionFactory)
    signer = factory.SubFactory("apps.projects.tests.conftest.UserFactory")
    sha256 = factory.LazyFunction(lambda: "a" * 64)
    signer_metadata = {"ip": "127.0.0.1"}

    class Meta:
        model = DigitalSignature


class MinutesFactory(DjangoModelFactory):
    """Factory for Minutes — acta row backed by a Document."""

    acta_type = Minutes.ActaType.INICIO
    institution = factory.SubFactory("apps.institutions.tests.conftest.InstitutionFactory")
    document = factory.SubFactory(
        DocumentFactory,
        institution=factory.SelfAttribute("..institution"),
    )
    created_by = factory.SubFactory("apps.projects.tests.conftest.UserFactory")

    class Meta:
        model = Minutes
