"""
DRF ModelSerializers for the 6-entity institutions hierarchy.

Design decisions (from design.md):
- FSM status is read-only — transitions go through InstitutionLifecycleService
- InstitutionSerializer excludes institution_id (no RLS on root table)
- All sub-entity serializers include institution as read-only
  (set by the view via serializer.save(institution=inst))
- Parent FK fields (sede, facultad, center, group) are read-only on write
  but exposed in serialized output for consumers

Spec reference: openspec/changes/institutions/spec.md — API Contract
Design reference: openspec/changes/institutions/design.md — File Changes / Contracts
"""

from rest_framework import serializers

from apps.institutions.models import (
    Facultad,
    Institution,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
    Sede,
)

# ──────────────────────────────────────────────────────────
# InstitutionSerializer
# ──────────────────────────────────────────────────────────


class InstitutionSerializer(serializers.ModelSerializer):
    """Serializes Institution. institution_id excluded (root entity, no RLS)."""

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "code",
            "description",
            "address",
            "contact_email",
            "contact_phone",
            "logo_url",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# SedeSerializer
# ──────────────────────────────────────────────────────────


class SedeSerializer(serializers.ModelSerializer):
    """Serializes Sede. institution is read-only (set by view from URL)."""

    institution_name = serializers.ReadOnlyField(source="institution.name")

    class Meta:
        model = Sede
        fields = [
            "id",
            "institution",
            "institution_name",
            "code",
            "name",
            "description",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# FacultadSerializer
# ──────────────────────────────────────────────────────────


class FacultadSerializer(serializers.ModelSerializer):
    """Serializes Facultad. institution + sede are read-only."""

    institution_name = serializers.ReadOnlyField(source="institution.name")

    class Meta:
        model = Facultad
        fields = [
            "id",
            "institution",
            "institution_name",
            "sede",
            "code",
            "name",
            "description",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_sede(self, value):
        """Validate that sede belongs to the same institution if provided."""
        if value is not None:
            institution = self.context.get("institution")
            if institution is not None and value.institution_id != institution.pk:
                raise serializers.ValidationError("Sede belongs to a different institution.")
        return value


# ──────────────────────────────────────────────────────────
# ResearchCenterSerializer
# ──────────────────────────────────────────────────────────


class ResearchCenterSerializer(serializers.ModelSerializer):
    """Serializes ResearchCenter. institution, sede, facultad are read-only."""

    institution_name = serializers.ReadOnlyField(source="institution.name")

    class Meta:
        model = ResearchCenter
        fields = [
            "id",
            "institution",
            "institution_name",
            "sede",
            "facultad",
            "code",
            "name",
            "description",
            "contact_email",
            "contact_phone",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_sede(self, value):
        """Validate sede belongs to same institution."""
        if value is not None:
            institution = self.context.get("institution")
            if institution is not None and value.institution_id != institution.pk:
                raise serializers.ValidationError("Sede belongs to a different institution.")
        return value

    def validate_facultad(self, value):
        """Validate facultad belongs to same institution."""
        if value is not None:
            institution = self.context.get("institution")
            if institution is not None and value.institution_id != institution.pk:
                raise serializers.ValidationError("Facultad belongs to a different institution.")
        return value


# ──────────────────────────────────────────────────────────
# ResearchGroupSerializer
# ──────────────────────────────────────────────────────────


class ResearchGroupSerializer(serializers.ModelSerializer):
    """Serializes ResearchGroup. institution + center are read-only.

    center is set by the view from the URL path (/centers/{id}/groups/).
    """

    institution_name = serializers.ReadOnlyField(source="institution.name")
    center = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ResearchGroup
        fields = [
            "id",
            "institution",
            "institution_name",
            "center",
            "code",
            "name",
            "description",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]


# ──────────────────────────────────────────────────────────
# ResearchLineSerializer
# ──────────────────────────────────────────────────────────


class ResearchLineSerializer(serializers.ModelSerializer):
    """Serializes ResearchLine. institution + group are read-only.

    group is set by the view from the URL path (/groups/{id}/lines/).
    """

    institution_name = serializers.ReadOnlyField(source="institution.name")
    group = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ResearchLine
        fields = [
            "id",
            "institution",
            "institution_name",
            "group",
            "code",
            "name",
            "description",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "status",
            "created_at",
            "updated_at",
        ]
