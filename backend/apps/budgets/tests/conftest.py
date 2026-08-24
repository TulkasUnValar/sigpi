"""
Factory-boy factories for the budgets module.

Provides ergonomic test data generation for Budget, BudgetLine,
FundingSource, BudgetExecution, and BudgetAttachment.

Spec reference:  openspec/changes/budgets/specs/budgets/spec.md
Design reference: openspec/changes/budgets/design.md
"""

import factory
from factory.django import DjangoModelFactory

from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    BudgetStatus,
    FundingSource,
)


class BudgetFactory(DjangoModelFactory):
    """Factory for Budget — project OneToOne, institution-scoped."""

    project = factory.SubFactory("apps.projects.tests.conftest.ProjectFactory")
    institution = factory.SelfAttribute("project.institution")
    name = factory.Faker("sentence", nb_words=4)
    approved_amount = factory.Faker(
        "pydecimal", left_digits=6, right_digits=2, positive=True
    )
    status = BudgetStatus.DRAFT

    class Meta:
        model = Budget


class BudgetLineFactory(DjangoModelFactory):
    """Factory for BudgetLine — belongs to a Budget."""

    budget = factory.SubFactory(BudgetFactory)
    name = factory.Faker("word")
    approved_amount = factory.Faker(
        "pydecimal", left_digits=6, right_digits=2, positive=True
    )

    class Meta:
        model = BudgetLine


class FundingSourceFactory(DjangoModelFactory):
    """Factory for FundingSource — belongs to a Project."""

    project = factory.SubFactory("apps.projects.tests.conftest.ProjectFactory")
    name = factory.Faker("company")
    amount = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)

    class Meta:
        model = FundingSource


class BudgetExecutionFactory(DjangoModelFactory):
    """Factory for BudgetExecution — belongs to a BudgetLine."""

    line = factory.SubFactory(BudgetLineFactory)
    amount = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    executed_at = factory.Faker("date_object")
    authorized_by = None
    authorized_at = None

    class Meta:
        model = BudgetExecution


class BudgetAttachmentFactory(DjangoModelFactory):
    """Factory for BudgetAttachment — metadata-only record."""

    budget = factory.SubFactory(BudgetFactory)
    name = factory.Faker("file_name")
    doc_type = "soporte"
    external_url = factory.Faker("url")

    class Meta:
        model = BudgetAttachment
