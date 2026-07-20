"""
Factory-boy factories for the projects module.

Provides ergonomic test data generation for Project,
ProjectMember, ProjectDocument, ProjectObservation,
ProjectStateLog, and state-scoped fixtures.

Spec reference:  openspec/changes/projects/spec.md
Design reference: openspec/changes/projects/design.md

GREEN PHASE: Factories now create valid instances from full models.
"""
import datetime

import factory
import pytest
from factory.django import DjangoModelFactory

from apps.projects.models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)


class UserFactory(DjangoModelFactory):
    """Minimal User factory — defined here because accounts has no test conftest."""

    email = factory.Sequence(lambda n: f"user-{n}@test.edu")
    is_active = True

    class Meta:
        model = "accounts.User"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use create_user so password is hashed."""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        return user_model.objects.create_user(*args, **kwargs)


class ProjectFactory(DjangoModelFactory):
    """Factory for Project — institution-scoped with 12-state FSM."""

    institution = factory.SubFactory(
        "apps.institutions.tests.conftest.InstitutionFactory"
    )
    center = factory.SubFactory(
        "apps.institutions.tests.conftest.ResearchCenterFactory",
        institution=factory.SelfAttribute("..institution"),
    )
    group = None
    line = None
    principal_investigator = factory.SubFactory(
        "apps.researchers.tests.conftest.ResearcherFactory",
        institution=factory.SelfAttribute("..institution"),
    )
    title = factory.Faker("sentence", nb_words=6)
    abstract = factory.Faker("paragraph", nb_sentences=3)
    objectives = factory.Faker("paragraph", nb_sentences=2)
    methodology = factory.Faker("paragraph", nb_sentences=2)
    expected_results = factory.Faker("paragraph", nb_sentences=2)
    keywords = factory.Faker("words", nb=3)
    start_date = factory.Faker(
        "date_between", start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2025, 6, 30)
    )
    estimated_end_date = factory.Faker(
        "date_between", start_date=datetime.date(2025, 7, 1), end_date=datetime.date(2026, 12, 31)
    )
    actual_end_date = None
    status = "borrador"
    is_active = True

    class Meta:
        model = Project

    class Params:
        with_group = factory.Trait(
            group=factory.SubFactory(
                "apps.institutions.tests.conftest.ResearchGroupFactory",
                institution=factory.SelfAttribute("..institution"),
                center=factory.SelfAttribute("..center"),
            ),
        )
        with_line = factory.Trait(
            line=factory.SubFactory(
                "apps.institutions.tests.conftest.ResearchLineFactory",
                institution=factory.SelfAttribute("..institution"),
                group=factory.SelfAttribute("..group"),
            ),
        )


class ProjectMemberFactory(DjangoModelFactory):
    """Factory for ProjectMember — links Researcher to Project with a role."""

    project = factory.SubFactory(ProjectFactory)
    researcher = factory.SubFactory(
        "apps.researchers.tests.conftest.ResearcherFactory",
        institution=factory.SelfAttribute("..project.institution"),
    )
    role = "co_investigator"

    class Meta:
        model = ProjectMember


class ProjectDocumentFactory(DjangoModelFactory):
    """Factory for ProjectDocument — metadata-only document record."""

    project = factory.SubFactory(ProjectFactory)
    name = factory.Faker("file_name")
    doc_type = "proposal"
    external_url = factory.Faker("url")

    class Meta:
        model = ProjectDocument


class ProjectObservationFactory(DjangoModelFactory):
    """Factory for ProjectObservation — append-only observation log."""

    project = factory.SubFactory(ProjectFactory)
    observed_by = factory.SubFactory(UserFactory)
    observation_text = factory.Faker("paragraph", nb_sentences=2)

    class Meta:
        model = ProjectObservation


class ProjectStateLogFactory(DjangoModelFactory):
    """Factory for ProjectStateLog — domain audit log."""

    project = factory.SubFactory(ProjectFactory)
    from_state = "borrador"
    to_state = "enviado"
    triggered_by = factory.SubFactory(UserFactory)
    reason = ""

    class Meta:
        model = ProjectStateLog


# ──────────────────────────────────────────────
# State-scoped Project fixtures (12 states)
# ──────────────────────────────────────────────


@pytest.fixture
def project_borrador(db):
    """Project in borrador state (default factory)."""
    return ProjectFactory()


@pytest.fixture
def project_enviado(db):
    """Project in enviado state."""
    return ProjectFactory(status="enviado")


@pytest.fixture
def project_en_revision(db):
    """Project in en_revision state."""
    return ProjectFactory(status="en_revision")


@pytest.fixture
def project_observado(db):
    """Project in observado state."""
    return ProjectFactory(status="observado")


@pytest.fixture
def project_aprobado(db):
    """Project in aprobado state."""
    return ProjectFactory(status="aprobado")


@pytest.fixture
def project_en_ejecucion(db):
    """Project in en_ejecucion state."""
    return ProjectFactory(status="en_ejecucion")


@pytest.fixture
def project_suspendido(db):
    """Project in suspendido state."""
    return ProjectFactory(status="suspendido")


@pytest.fixture
def project_finalizado(db):
    """Project in finalizado state."""
    return ProjectFactory(status="finalizado")


@pytest.fixture
def project_en_cierre(db):
    """Project in en_cierre state."""
    return ProjectFactory(status="en_cierre")


@pytest.fixture
def project_cerrado(db):
    """Project in cerrado state (terminal)."""
    return ProjectFactory(status="cerrado")


@pytest.fixture
def project_rechazado(db):
    """Project in rechazado state (terminal)."""
    return ProjectFactory(status="rechazado")


@pytest.fixture
def project_cancelado(db):
    """Project in cancelado state (terminal)."""
    return ProjectFactory(status="cancelado")
