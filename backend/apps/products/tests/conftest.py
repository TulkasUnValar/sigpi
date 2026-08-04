"""
Factory-boy factories for the products module.

Provides ergonomic test data generation for ResearchProduct,
ProductAuthor, and ProductAttachment.
"""
import datetime

import factory
from factory.django import DjangoModelFactory

from apps.products.models import ProductAttachment, ProductAuthor, ProductType, ResearchProduct


class ProductFactory(DjangoModelFactory):
    """Factory for ResearchProduct — institution-scoped, linked to a project."""

    institution = factory.SelfAttribute("project.institution")
    project = factory.SubFactory(
        "apps.projects.tests.conftest.ProjectFactory"
    )
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=2)
    type = factory.Iterator([choice[0] for choice in ProductType.choices])
    publication_year = factory.Faker(
        "random_int", min=2010, max=datetime.date.today().year
    )

    class Meta:
        model = ResearchProduct


class ProductAuthorFactory(DjangoModelFactory):
    """Factory for ProductAuthor — links a Researcher to a ResearchProduct."""

    product = factory.SubFactory(ProductFactory)
    researcher = factory.SubFactory(
        "apps.researchers.tests.conftest.ResearcherFactory",
        institution=factory.SelfAttribute("..product.institution"),
    )
    is_principal = False
    order = factory.Sequence(lambda n: n)

    class Meta:
        model = ProductAuthor


class ProductAttachmentFactory(DjangoModelFactory):
    """Factory for ProductAttachment — metadata-only attachment record."""

    product = factory.SubFactory(ProductFactory)
    name = factory.Faker("file_name")
    doc_type = "pdf"
    external_url = factory.Faker("url")

    class Meta:
        model = ProductAttachment
