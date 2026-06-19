"""
Researchers & Academic Profiles — 4-entity module (SIGPI §6.3).

Implements the data model defined in design.md and spec.md:
- Researcher: institution-scoped, optional User FK, unique (institution, document_number)
- ResearcherAffiliation: M2M junction to centers/groups/lines with is_primary
- ExternalProfile: external profile URLs (CvLAC, ORCID, etc.)
- ResearcherAttachment: metadata-only attachment records

Design reference: openspec/changes/researchers/design.md
Spec reference:   openspec/changes/researchers/spec.md
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models

# ──────────────────────────────────────────────
# Choise Enums
# ──────────────────────────────────────────────


class DocumentTypeChoices(models.TextChoices):
    """Document type choices for Researcher (RN-001)."""

    CC = "CC", "Cédula de Ciudadanía"
    TI = "TI", "Tarjeta de Identidad"
    CE = "CE", "Cédula de Extranjería"
    PA = "PA", "Pasaporte"


class ProviderChoices(models.TextChoices):
    """External profile provider choices (RN-EXT-01)."""

    CVLAC = "cvlac", "CvLAC"
    ORCID = "orcid", "ORCID"
    GOOGLE_SCHOLAR = "google_scholar", "Google Scholar"
    LINKEDIN = "linkedin", "LinkedIn"
    RESEARCHGATE = "researchgate", "ResearchGate"


class AttachmentTypeChoices(models.TextChoices):
    """Attachment type choices (RN-ATT-01)."""

    CV = "cv", "Curriculum Vitae"
    CERTIFICATE = "certificate", "Certificate"
    PHOTO = "photo", "Photo"
    OTHER = "other", "Other"


# ──────────────────────────────────────────────
# Researcher
# ──────────────────────────────────────────────


class Researcher(models.Model):
    """Researcher profile scoped to a single Institution.

    Follows the institution-scoped pattern (denormalized institution_id
    for RLS) but does NOT inherit InstitutionScopedModel — that base
    carries FSM + code/name/description fields irrelevant to a
    researcher profile.

    Design decisions:
    - user FK is nullable + unique: a system user may not have a
      researcher profile yet; each user can have at most one.
    - document_type uses TextChoices enum (CC, TI, CE, PA).
    - (institution, document_number) unique per RN-001.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researcher_profile",
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="researchers",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    document_type = models.CharField(
        max_length=30,
        choices=DocumentTypeChoices.choices,
    )
    document_number = models.CharField(max_length=30)
    primary_email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    academic_formation = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "researchers_researcher"
        verbose_name = "Researcher"
        verbose_name_plural = "Researchers"
        ordering = ["institution", "last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "document_number"],
                name="unique_document_per_institution",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "is_active"],
                name="idx_researcher_inst_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────
# ResearcherAffiliation
# ──────────────────────────────────────────────


class ResearcherAffiliation(models.Model):
    """Junction linking a Researcher to research structure entities.

    A researcher can be affiliated with multiple centers, groups, or
    lines. At least one of (center, group, line) must be set. All FK
    targets must belong to the researcher's institution. Exactly one
    affiliation per researcher must be is_primary=True.

    clean() enforces all three invariants at the Python level.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        related_name="affiliations",
    )
    center = models.ForeignKey(
        "institutions.ResearchCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researcher_affiliations",
    )
    group = models.ForeignKey(
        "institutions.ResearchGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researcher_affiliations",
    )
    line = models.ForeignKey(
        "institutions.ResearchLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="researcher_affiliations",
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "researchers_researcheraffiliation"
        verbose_name = "Researcher Affiliation"
        verbose_name_plural = "Researcher Affiliations"
        ordering = ["researcher", "-is_primary", "created_at"]

    def clean(self):
        super().clean()

        # 1. At least one FK must be set
        if not self.center and not self.group and not self.line:
            raise ValidationError(
                "At least one of center, group, or line must be set."
            )

        institution_id = self.researcher.institution_id

        # 2. All FK targets must belong to researcher's institution
        errors = {}
        if self.center and self.center.institution_id != institution_id:
            errors["center"] = (
                "Center belongs to a different institution."
            )
        if self.group and self.group.institution_id != institution_id:
            errors["group"] = (
                "Group belongs to a different institution."
            )
        if self.line and self.line.institution_id != institution_id:
            errors["line"] = (
                "Line belongs to a different institution."
            )
        if errors:
            raise ValidationError(errors)

        # 3. Only one is_primary=True per researcher
        if self.is_primary:
            conflicting = (
                ResearcherAffiliation.objects
                .filter(researcher=self.researcher, is_primary=True)
                .exclude(pk=self.pk)
            )
            if conflicting.exists():
                raise ValidationError(
                    {"is_primary": "Only one primary affiliation allowed per researcher."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        parts = [str(self.researcher)]
        if self.center:
            parts.append(f"→ {self.center.name}")
        elif self.group:
            parts.append(f"→ {self.group.name}")
        elif self.line:
            parts.append(f"→ {self.line.name}")
        return " ".join(parts)


# ──────────────────────────────────────────────
# ExternalProfile
# ──────────────────────────────────────────────


class ExternalProfile(models.Model):
    """External profile URL for a Researcher (CvLAC, ORCID, etc.).

    Stores provider and URL — no file upload, reference only.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        related_name="external_profiles",
    )
    provider = models.CharField(
        max_length=20,
        choices=ProviderChoices.choices,
    )
    url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "researchers_externalprofile"
        verbose_name = "External Profile"
        verbose_name_plural = "External Profiles"
        ordering = ["researcher", "provider"]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} — {self.researcher}"


# ──────────────────────────────────────────────
# ResearcherAttachment
# ──────────────────────────────────────────────


class ResearcherAttachment(models.Model):
    """Metadata-only attachment record for a Researcher.

    Stores name, type, and external URL. No file upload in MVP —
    the actual file lives in external storage referenced by URL.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    researcher = models.ForeignKey(
        Researcher,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=AttachmentTypeChoices.choices,
    )
    external_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "researchers_researcherattachment"
        verbose_name = "Researcher Attachment"
        verbose_name_plural = "Researcher Attachments"
        ordering = ["researcher", "-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_type_display()})"
