"""
Products — Research Products module (SIGPI §6.7).

Implements the data model defined in design.md and spec.md:
- ResearchProduct: institution-scoped research product linked to a project
- ProductAuthor: junction linking researchers to products with principal flag
- ProductAttachment: metadata-only attachment records

Design reference: openspec/changes/products/design.md
Spec reference:   openspec/changes/products/specs/products/spec.md
"""
import datetime
import uuid

from django.core.exceptions import ValidationError
from django.db import models

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class ProductType(models.TextChoices):
    """Product type choices per SIGPI §6.7 (11 hardcoded types)."""

    ARTICULO = "articulo", "Artículo"
    LIBRO = "libro", "Libro"
    CAPITULO = "capitulo", "Capítulo"
    SOFTWARE = "software", "Software"
    PROTOTIPO = "prototipo", "Prototipo"
    EVENTO = "evento", "Evento"
    CONSULTORIA = "consultoria", "Consultoría"
    DISENO_INDUSTRIAL = "diseno_industrial", "Diseño Industrial"
    INNOVACION_PROCESO = "innovacion_proceso", "Innovación de Proceso"
    INNOVACION_GESTION = "innovacion_gestion", "Innovación de Gestión"
    CARTA = "carta", "Carta"


# ──────────────────────────────────────────────
# ResearchProduct
# ──────────────────────────────────────────────


class ResearchProduct(models.Model):
    """Research product scoped to an institution and linked to a project.

    Denormalized institution_id for RLS. Validation in clean() enforces
    type choices and publication_year bounds (1900 to current_year+1).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="products",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="products",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=30, choices=ProductType.choices)
    publication_year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products_created",
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products_updated",
    )

    class Meta:
        db_table = "products_researchproduct"
        verbose_name = "Research Product"
        verbose_name_plural = "Research Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["institution", "type"],
                name="idx_product_inst_type",
            ),
            models.Index(
                fields=["institution", "publication_year"],
                name="idx_product_inst_year",
            ),
            models.Index(
                fields=["project"],
                name="idx_product_project",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        errors = {}

        # RF-081: type must be a valid choice
        if self.type not in {choice[0] for choice in ProductType.choices}:
            errors.setdefault("type", []).append(
                "Invalid product type."
            )

        # RF-081: publication_year between 1900 and current_year+1
        current_year = datetime.date.today().year
        if self.publication_year is not None:
            if self.publication_year < 1900:
                errors.setdefault("publication_year", []).append(
                    "Publication year must be 1900 or later."
                )
            elif self.publication_year > current_year + 1:
                errors.setdefault("publication_year", []).append(
                    f"Publication year must not exceed {current_year + 1}."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# ProductAuthor
# ──────────────────────────────────────────────


class ProductAuthor(models.Model):
    """Junction linking a Researcher to a ResearchProduct.

    A researcher can only appear once per product (unique constraint).
    is_principal flags the main author. order controls display sequence.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        ResearchProduct,
        on_delete=models.CASCADE,
        related_name="authors",
    )
    researcher = models.ForeignKey(
        "researchers.Researcher",
        on_delete=models.CASCADE,
        related_name="product_authorships",
    )
    is_principal = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "products_productauthor"
        verbose_name = "Product Author"
        verbose_name_plural = "Product Authors"
        ordering = ["product", "order", "researcher"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "researcher"],
                name="unique_product_researcher",
            ),
        ]

    def __str__(self) -> str:
        principal = " (principal)" if self.is_principal else ""
        return f"{self.researcher} — {self.product}{principal}"


# ──────────────────────────────────────────────
# ProductAttachment
# ──────────────────────────────────────────────


class ProductAttachment(models.Model):
    """Metadata-only attachment record for a ResearchProduct.

    Stores name, doc_type, and external URL. No file upload in MVP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        ResearchProduct,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=50)
    external_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products_productattachment"
        verbose_name = "Product Attachment"
        verbose_name_plural = "Product Attachments"
        ordering = ["product", "-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.doc_type})"
