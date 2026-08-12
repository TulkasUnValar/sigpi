"""
Factory-boy factories for the calls module.

Provides ergonomic test data generation for Call,
CallDocument, CallProject, and state-scoped fixtures.

Spec reference:  openspec/changes/calls/spec.md
Design reference: openspec/changes/calls/design.md

GREEN PHASE: Factories now create valid instances from full models.
"""

import factory
import pytest
from factory.django import DjangoModelFactory

from apps.calls.models import (
    Call,
    CallDocument,
    CallProject,
    CallStateLog,
    CallStatus,
    CallType,
)


class CallFactory(DjangoModelFactory):
    """Factory for Call — institution-scoped with 6-state FSM."""

    institution = factory.SubFactory("apps.institutions.tests.conftest.InstitutionFactory")
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=3)
    call_type = CallType.INTERNAL
    external_entity = ""
    submission_start = None
    submission_end = None
    evaluation_start = None
    evaluation_end = None
    status = CallStatus.BORRADOR

    class Meta:
        model = Call

    class Params:
        external = factory.Trait(
            call_type=CallType.EXTERNAL,
            external_entity=factory.Faker("company"),
        )


class CallDocumentFactory(DjangoModelFactory):
    """Factory for CallDocument — metadata-only document record."""

    call = factory.SubFactory(CallFactory)
    name = factory.Faker("file_name")
    doc_type = "convocatoria"
    external_url = factory.Faker("url")

    class Meta:
        model = CallDocument


class CallProjectFactory(DjangoModelFactory):
    """Factory for CallProject — links Project to Call."""

    call = factory.SubFactory(CallFactory)
    project = factory.SubFactory(
        "apps.projects.tests.conftest.ProjectFactory",
        institution=factory.SelfAttribute("..call.institution"),
    )

    class Meta:
        model = CallProject


class CallStateLogFactory(DjangoModelFactory):
    """Factory for CallStateLog — domain audit log."""

    call = factory.SubFactory(CallFactory)
    from_state = CallStatus.BORRADOR
    to_state = CallStatus.ABIERTA
    triggered_by = factory.SubFactory("apps.projects.tests.conftest.UserFactory")
    reason = ""

    class Meta:
        model = CallStateLog


# ──────────────────────────────────────────────
# State-scoped Call fixtures (6 states)
# ──────────────────────────────────────────────


@pytest.fixture
def call_borrador(db):
    """Call in borrador state (default factory)."""
    return CallFactory()


@pytest.fixture
def call_abierta(db):
    """Call in abierta state."""
    return CallFactory(status=CallStatus.ABIERTA)


@pytest.fixture
def call_cerrada(db):
    """Call in cerrada state."""
    return CallFactory(status=CallStatus.CERRADA)


@pytest.fixture
def call_en_evaluacion(db):
    """Call in en_evaluacion state."""
    return CallFactory(status=CallStatus.EN_EVALUACION)


@pytest.fixture
def call_resultados_publicados(db):
    """Call in resultados_publicados state."""
    return CallFactory(status=CallStatus.RESULTADOS_PUBLICADOS)


@pytest.fixture
def call_archivada(db):
    """Call in archivada state (terminal)."""
    return CallFactory(status=CallStatus.ARCHIVADA)
