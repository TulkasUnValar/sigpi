"""
Factory-boy factories for the 6-entity institution hierarchy.

Provides ergonomic test data generation for Institution, Sede,
Facultad, ResearchCenter, ResearchGroup, and ResearchLine.
"""
import factory
from factory.django import DjangoModelFactory

from apps.institutions.models import (
    Institution,
    Sede,
    Facultad,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
)


class InstitutionFactory(DjangoModelFactory):
    """Factory for Institution with auto-incrementing code."""

    name = factory.Sequence(lambda n: f"University {n}")
    code = factory.Sequence(lambda n: f"U{n:03d}")
    description = factory.Faker("sentence", nb_words=10)
    address = factory.Faker("address")
    contact_email = factory.Faker("email")
    contact_phone = factory.Faker("phone_number")

    class Meta:
        model = Institution


class SedeFactory(DjangoModelFactory):
    """Factory for Sede — belongs to an Institution."""

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Campus {n}")
    code = factory.Sequence(lambda n: f"S{n:03d}")
    description = factory.Faker("sentence", nb_words=8)

    class Meta:
        model = Sede


class FacultadFactory(DjangoModelFactory):
    """Factory for Facultad — belongs to an Institution, optionally a Sede."""

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Faculty {n}")
    code = factory.Sequence(lambda n: f"F{n:03d}")
    description = factory.Faker("sentence", nb_words=8)
    sede = None  # no sede by default

    class Meta:
        model = Facultad

    class Params:
        with_sede = factory.Trait(
            sede=factory.SubFactory(
                SedeFactory,
                institution=factory.SelfAttribute("..institution"),
            ),
        )


class ResearchCenterFactory(DjangoModelFactory):
    """Factory for ResearchCenter — belongs to an Institution."""

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Research Center {n}")
    code = factory.Sequence(lambda n: f"C{n:03d}")
    description = factory.Faker("sentence", nb_words=10)
    contact_email = factory.Faker("email")
    contact_phone = factory.Faker("phone_number")
    sede = None
    facultad = None

    class Meta:
        model = ResearchCenter


class ResearchGroupFactory(DjangoModelFactory):
    """Factory for ResearchGroup — belongs to a ResearchCenter."""

    institution = factory.SelfAttribute("center.institution")
    center = factory.SubFactory(ResearchCenterFactory)
    name = factory.Sequence(lambda n: f"Research Group {n}")
    code = factory.Sequence(lambda n: f"G{n:03d}")
    description = factory.Faker("sentence", nb_words=8)

    class Meta:
        model = ResearchGroup


class ResearchLineFactory(DjangoModelFactory):
    """Factory for ResearchLine — belongs to a ResearchGroup."""

    institution = factory.SelfAttribute("group.institution")
    group = factory.SubFactory(ResearchGroupFactory)
    name = factory.Sequence(lambda n: f"Research Line {n}")
    code = factory.Sequence(lambda n: f"L{n:03d}")
    description = factory.Faker("sentence", nb_words=8)

    class Meta:
        model = ResearchLine
