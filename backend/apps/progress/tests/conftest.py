"""
Factory-boy factories for the progress (advances) module.

Provides ergonomic test data generation for ProgressReport,
ProgressReview, ProgressDocument, ProgressStateLog, and
state-scoped fixtures.

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md

RED PHASE: Factories reference model fields that don't exist yet.
"""
import datetime

import factory
import pytest
from factory.django import DjangoModelFactory

from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)


class UserFactory(DjangoModelFactory):
    """Minimal User factory for progress tests."""

    email = factory.Sequence(lambda n: f"progress-user-{n}@test.edu")
    is_active = True

    class Meta:
        model = "accounts.User"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        return user_model.objects.create_user(*args, **kwargs)


class ProgressReportFactory(DjangoModelFactory):
    """Factory for ProgressReport — institution-scoped with 6-state FSM."""

    institution = factory.SubFactory(
        "apps.institutions.tests.conftest.InstitutionFactory"
    )
    project = factory.SubFactory(
        "apps.projects.tests.conftest.ProjectFactory",
        institution=factory.SelfAttribute("..institution"),
    )
    created_by = factory.SubFactory(UserFactory)
    period_start = factory.Faker(
        "date_between",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 3, 31),
    )
    period_end = factory.Faker(
        "date_between",
        start_date=datetime.date(2026, 4, 1),
        end_date=datetime.date(2026, 6, 30),
    )
    description = factory.Faker("paragraph", nb_sentences=3)
    cumulative_percentage = factory.Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        max_value=100,
    )
    activities = factory.Faker("paragraph", nb_sentences=3)
    difficulties = factory.Faker("paragraph", nb_sentences=1)
    next_steps = factory.Faker("paragraph", nb_sentences=1)
    status = "borrador"

    class Meta:
        model = ProgressReport


class ProgressReviewFactory(DjangoModelFactory):
    """Factory for ProgressReview — append-only observation/rejection."""

    progress_report = factory.SubFactory(ProgressReportFactory)
    reviewed_by = factory.SubFactory(UserFactory)
    review_text = factory.Faker("paragraph", nb_sentences=2)
    review_type = "observation"

    class Meta:
        model = ProgressReview


class ProgressDocumentFactory(DjangoModelFactory):
    """Factory for ProgressDocument — metadata-only document record."""

    progress_report = factory.SubFactory(ProgressReportFactory)
    name = factory.Faker("file_name")
    doc_type = "evidence"
    external_url = factory.Faker("url")

    class Meta:
        model = ProgressDocument


class ProgressStateLogFactory(DjangoModelFactory):
    """Factory for ProgressStateLog — domain audit log."""

    progress_report = factory.SubFactory(ProgressReportFactory)
    from_state = "borrador"
    to_state = "enviado"
    triggered_by = factory.SubFactory(UserFactory)
    reason = ""

    class Meta:
        model = ProgressStateLog


# ──────────────────────────────────────────────
# State-scoped ProgressReport fixtures (6 states)
# ──────────────────────────────────────────────


@pytest.fixture
def progress_borrador(db):
    """ProgressReport in borrador state (default)."""
    return ProgressReportFactory()


@pytest.fixture
def progress_enviado(db):
    """ProgressReport in enviado state."""
    return ProgressReportFactory(status="enviado")


@pytest.fixture
def progress_en_revision(db):
    """ProgressReport in en_revision state."""
    return ProgressReportFactory(status="en_revision")


@pytest.fixture
def progress_observado(db):
    """ProgressReport in observado state."""
    return ProgressReportFactory(status="observado")


@pytest.fixture
def progress_aprobado(db):
    """ProgressReport in aprobado state (terminal)."""
    return ProgressReportFactory(status="aprobado")


@pytest.fixture
def progress_rechazado(db):
    """ProgressReport in rechazado state."""
    return ProgressReportFactory(status="rechazado")
