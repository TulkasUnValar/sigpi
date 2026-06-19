"""
Factory-boy factories for the researchers module.

Provides ergonomic test data generation for Researcher,
ResearcherAffiliation, ExternalProfile, and ResearcherAttachment.
"""
import factory
from factory.django import DjangoModelFactory

from apps.researchers.models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)


class ResearcherFactory(DjangoModelFactory):
    """Factory for Researcher — institution-scoped with optional User."""

    user = None  # no user by default
    institution = factory.SubFactory(
        "apps.institutions.tests.conftest.InstitutionFactory"
    )
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    document_type = "CC"
    document_number = factory.Sequence(lambda n: f"DOC-{n:06d}")
    primary_email = factory.Faker("email")
    phone = ""
    bio = ""
    academic_formation = ""
    is_active = True

    class Meta:
        model = Researcher


class ResearcherAffiliationFactory(DjangoModelFactory):
    """Factory for ResearcherAffiliation — links researcher to center/group/line.

    Shares the researcher's institution with the center/group/line
    via SelfAttribute to satisfy same-institution validation.
    """

    researcher = factory.SubFactory(ResearcherFactory)
    center = factory.SubFactory(
        "apps.institutions.tests.conftest.ResearchCenterFactory",
        institution=factory.SelfAttribute("..researcher.institution"),
    )
    group = None
    line = None
    is_primary = False

    class Meta:
        model = ResearcherAffiliation


class ExternalProfileFactory(DjangoModelFactory):
    """Factory for ExternalProfile — stores researcher's external profile URLs."""

    researcher = factory.SubFactory(ResearcherFactory)
    provider = "cvlac"
    url = factory.Faker("url")

    class Meta:
        model = ExternalProfile


class ResearcherAttachmentFactory(DjangoModelFactory):
    """Factory for ResearcherAttachment — metadata-only attachment records."""

    researcher = factory.SubFactory(ResearcherFactory)
    name = factory.Faker("file_name")
    type = "cv"
    external_url = factory.Faker("url")

    class Meta:
        model = ResearcherAttachment
