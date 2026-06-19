"""
Service layer for researchers — business logic + completeness calculation.

ResearcherProfileService: CRUD orchestration for Researcher profiles.
ResearcherAffiliationService: M2M management for affiliations with
cross-institution validation, primary uniqueness, and atomicity.

Design reference: openspec/changes/researchers/design.md — Service Layer
Spec reference:   openspec/changes/researchers/spec.md — RF-018, RF-019, RF-024
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.researchers.models import Researcher, ResearcherAffiliation

# ──────────────────────────────────────────────
# ResearcherProfileService
# ──────────────────────────────────────────────


class ResearcherProfileService:
    """CRUD operations for Researcher profiles.

    All methods are static — this is a plain Python class, not a Django
    model. Service signatures accept model instances, not ORM primitives.
    """

    # Mandatory fields for completeness calculation (design.md §Service Layer).
    MANDATORY_FIELDS = [
        "first_name",
        "last_name",
        "document_type",
        "document_number",
        "primary_email",
    ]

    @staticmethod
    def create(institution, user=None, **validated_data):
        """Create a Researcher profile and calculate initial completeness.

        Args:
            institution: Institution instance (scoped tenant).
            user: Optional User FK (nullable, unique).
            **validated_data: Field values matching Researcher model.

        Returns:
            Researcher: The newly created (saved) instance.
        """
        researcher = Researcher(
            institution=institution,
            user=user,
            **validated_data,
        )
        researcher.full_clean()
        researcher.save()
        return researcher

    @staticmethod
    def update(researcher, **validated_data):
        """Update a Researcher profile with partial data.

        Only fields present in validated_data are updated. Missing keys
        in the dict leave the current value untouched.

        Args:
            researcher: Existing Researcher instance.
            **validated_data: Fields to update.

        Returns:
            Researcher: The updated instance.
        """
        for field, value in validated_data.items():
            setattr(researcher, field, value)
        researcher.full_clean()
        researcher.save()
        return researcher

    @staticmethod
    def deactivate(researcher):
        """Deactivate a Researcher profile.

        Sets is_active=False and saves. Note: ResearcherAffiliation does
        NOT have an is_active field — deactivation of the researcher
        logically disables all affiliations (access is gated by
        researcher.is_active at the queryset level).

        Args:
            researcher: Researcher instance to deactivate.

        Returns:
            Researcher: The deactivated instance.
        """
        researcher.is_active = False
        researcher.save()
        return researcher

    @staticmethod
    def calculate_completeness(researcher) -> int:
        """Calculate the profile completeness score (0–100).

        Mandatory criteria (6 items):
        1. first_name is non-empty
        2. last_name is non-empty
        3. document_type is non-empty
        4. document_number is non-empty
        5. primary_email is non-empty
        6. At least one ExternalProfile exists

        Each item contributes 1/6 of the total (16.66… rounded to int).

        Args:
            researcher: Researcher instance.

        Returns:
            int: Completeness percentage (0–100).
        """
        total = 6  # 5 base fields + 1 external profile requirement
        populated = 0

        # Check base mandatory fields (non-empty strings)
        for field_name in ResearcherProfileService.MANDATORY_FIELDS:
            value = getattr(researcher, field_name, "")
            if value and str(value).strip():
                populated += 1

        # Check at least one external profile exists
        if researcher.external_profiles.exists():
            populated += 1

        return int((populated / total) * 100)


# ──────────────────────────────────────────────
# ResearcherAffiliationService
# ──────────────────────────────────────────────


class ResearcherAffiliationService:
    """M2M management for Researcher affiliations.

    Handles creation, deletion, and primary-affiliation switching with
    cross-institution validation and primary-uniqueness enforcement.
    """

    @staticmethod
    def add(researcher, center=None, group=None, line=None, is_primary=False):
        """Add a new affiliation to a researcher.

        Validates:
        - At least one of (center, group, line) is set.
        - All FK targets belong to the researcher's institution.
        - If this is the first affiliation, auto-set is_primary=True
          (RN-AFF-02 requires exactly one primary per researcher).

        Args:
            researcher: Researcher instance.
            center: Optional ResearchCenter (same institution required).
            group: Optional ResearchGroup (same institution required).
            line: Optional ResearchLine (same institution required).
            is_primary: Whether this is the primary affiliation.

        Returns:
            ResearcherAffiliation: The created affiliation.

        Raises:
            ValidationError: If no FK is set or cross-institution detected.
        """
        # At least one FK must be set
        if not center and not group and not line:
            raise ValidationError(
                "At least one of center, group, or line must be set."
            )

        institution_id = researcher.institution_id

        # Cross-institution validation
        if center and center.institution_id != institution_id:
            raise ValidationError(
                "Affiliation entity does not belong to researcher's institution."
            )
        if group and group.institution_id != institution_id:
            raise ValidationError(
                "Affiliation entity does not belong to researcher's institution."
            )
        if line and line.institution_id != institution_id:
            raise ValidationError(
                "Affiliation entity does not belong to researcher's institution."
            )

        # Auto-set primary if this is the first affiliation
        if not ResearcherAffiliation.objects.filter(researcher=researcher).exists():
            is_primary = True

        affiliation = ResearcherAffiliation(
            researcher=researcher,
            center=center,
            group=group,
            line=line,
            is_primary=is_primary,
        )
        affiliation.full_clean()
        affiliation.save()
        return affiliation

    @staticmethod
    def remove(affiliation):
        """Delete an affiliation.

        Args:
            affiliation: ResearcherAffiliation instance to delete.

        Returns:
            None
        """
        affiliation.delete()

    @staticmethod
    @transaction.atomic
    def set_primary(affiliation):
        """Atomically switch the primary affiliation for the researcher.

        Unsets is_primary=False on the current primary (if any), then
        sets is_primary=True on the target affiliation. Uses a database
        transaction to guarantee atomicity.

        Args:
            affiliation: ResearcherAffiliation instance to make primary.

        Returns:
            ResearcherAffiliation: The updated (now primary) affiliation.
        """
        researcher = affiliation.researcher

        # Unset all existing primary affiliations for this researcher
        ResearcherAffiliation.objects.filter(
            researcher=researcher, is_primary=True
        ).update(is_primary=False)

        # Set the target as primary
        affiliation.is_primary = True
        affiliation.save()
        return affiliation
