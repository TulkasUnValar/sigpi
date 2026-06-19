"""
DRF ModelSerializers for the researchers module (Phase 3.2).

Provides 6 serializers implementing the API contract from spec.md:
- ResearcherListSerializer — lightweight list output
- ResearcherSerializer — full detail with nested affiliations/profiles/attachments
- ResearcherCreateSerializer — writable fields, institution read-only (injected by view)
- ResearcherAffiliationSerializer — center/group/line FKs
- ExternalProfileSerializer — provider/url
- ResearcherAttachmentSerializer — name/type/external_url

Design decisions (from design.md):
- completeness_score is computed via SerializerMethodField (kept in Python, testable)
- Nested serializers on ResearcherSerializer are read-only
- institution is read-only on all sub-entity serializers (set by view)
- researcher FK is read-only on child serializers (set by view from URL)

Spec reference: openspec/changes/researchers/spec.md — API Contract
Design reference: openspec/changes/researchers/design.md — Serializer Mapping
"""
from rest_framework import serializers

from apps.researchers.models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)
from apps.researchers.services import ResearcherProfileService

# ──────────────────────────────────────────────────────────
# ResearcherListSerializer
# ──────────────────────────────────────────────────────────


class ResearcherListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for researcher list views.

    Exposes only 5 fields: id, full_name, institution, is_active, completeness_score.
    """

    full_name = serializers.SerializerMethodField()
    completeness_score = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = [
            "id",
            "full_name",
            "institution",
            "is_active",
            "completeness_score",
        ]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"

    def get_completeness_score(self, obj) -> int:
        # For unsaved instances, return 0 — completeness requires DB queries
        if obj.pk is None:
            return 0
        return ResearcherProfileService.calculate_completeness(obj)


# ──────────────────────────────────────────────────────────
# ResearcherSerializer (full detail)
# ──────────────────────────────────────────────────────────


class ResearcherSerializer(serializers.ModelSerializer):
    """Full-detail serializer with nested affiliations, profiles, attachments.

    Nested data is read-only — mutations go through dedicated nested endpoints.
    completeness_score is a computed field (not stored).
    """

    affiliations = serializers.SerializerMethodField()
    external_profiles = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    completeness_score = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = [
            "id",
            "user",
            "institution",
            "first_name",
            "last_name",
            "document_type",
            "document_number",
            "primary_email",
            "phone",
            "bio",
            "academic_formation",
            "is_active",
            "full_name",
            "completeness_score",
            "affiliations",
            "external_profiles",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"

    def get_completeness_score(self, obj) -> int:
        # For unsaved instances, return 0 — completeness requires DB queries
        if obj.pk is None:
            return 0
        return ResearcherProfileService.calculate_completeness(obj)

    def get_affiliations(self, obj):
        """Return nested affiliations — read-only."""
        affiliations = obj.affiliations.all()
        return ResearcherAffiliationSerializer(affiliations, many=True).data

    def get_external_profiles(self, obj):
        """Return nested external profiles — read-only."""
        profiles = obj.external_profiles.all()
        return ExternalProfileSerializer(profiles, many=True).data

    def get_attachments(self, obj):
        """Return nested attachments — read-only."""
        attachments = obj.attachments.all()
        return ResearcherAttachmentSerializer(attachments, many=True).data


# ──────────────────────────────────────────────────────────
# ResearcherCreateSerializer
# ──────────────────────────────────────────────────────────


class ResearcherCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Researcher instances.

    Only writable fields are exposed. institution is read-only (injected by
    the view via serializer.save(institution=inst)). No nested writes —
    affiliations, profiles, and attachments are managed through their
    own dedicated nested endpoints.
    """

    class Meta:
        model = Researcher
        fields = [
            "id",
            "first_name",
            "last_name",
            "document_type",
            "document_number",
            "primary_email",
            "phone",
            "bio",
            "academic_formation",
            "is_active",
            "institution",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# ResearcherAffiliationSerializer
# ──────────────────────────────────────────────────────────


class ResearcherAffiliationSerializer(serializers.ModelSerializer):
    """Serializer for ResearcherAffiliation CRUD.

    researcher FK is read-only — set by the view from the URL path.
    center, group, line are optional PrimaryKeyRelatedFields.
    """

    class Meta:
        model = ResearcherAffiliation
        fields = [
            "id",
            "researcher",
            "center",
            "group",
            "line",
            "is_primary",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "researcher",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ExternalProfileSerializer
# ──────────────────────────────────────────────────────────


class ExternalProfileSerializer(serializers.ModelSerializer):
    """Serializer for ExternalProfile CRUD.

    researcher FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = ExternalProfile
        fields = [
            "id",
            "researcher",
            "provider",
            "url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "researcher",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ResearcherAttachmentSerializer
# ──────────────────────────────────────────────────────────


class ResearcherAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for ResearcherAttachment CRUD.

    researcher FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = ResearcherAttachment
        fields = [
            "id",
            "researcher",
            "name",
            "type",
            "external_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "researcher",
            "created_at",
        ]
