"""
DRF Serializers for SIGPI Auth API.

Implements the API contract defined in design.md:
- LoginSerializer: validates login credentials
- UserSerializer: serializes User profile
- MembershipSerializer: serializes InstitutionMembership with nested data
- InstitutionSwitchSerializer: validates institution switch request

Spec references: FR-004
Design reference: openspec/changes/auth/design.md — API Design (Expanded)
"""
from rest_framework import serializers

from apps.accounts.models import InstitutionMembership


class LoginSerializer(serializers.Serializer):
    """Validates local login credentials."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})


class InstitutionSwitchSerializer(serializers.Serializer):
    """Validates institution switch request."""
    institution_id = serializers.UUIDField(required=True)


class InstitutionSerializer(serializers.Serializer):
    """Minimal institution representation."""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class CenterSerializer(serializers.Serializer):
    """Minimal research center representation."""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)


class RoleSerializer(serializers.Serializer):
    """Minimal role representation."""
    name = serializers.CharField(read_only=True)
    level = serializers.IntegerField(read_only=True)


class MembershipSerializer(serializers.Serializer):
    """Serializes an InstitutionMembership with nested institution, role, and centers."""
    institution = InstitutionSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    centers = CenterSerializer(many=True, read_only=True)
    is_primary = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    def to_representation(self, instance: InstitutionMembership) -> dict:
        return {
            "institution": {
                "id": str(instance.institution_id),
                "name": instance.institution.name if hasattr(instance.institution, "name") else "",
            },
            "role": {
                "name": instance.role.name if instance.role else "",
                "level": instance.role.level if instance.role else 0,
            },
            "centers": [
                {"id": str(c.id), "name": c.name}
                for c in instance.centers.all()
            ],
            "is_primary": instance.is_primary,
            "is_active": instance.is_active,
        }


class UserSerializer(serializers.Serializer):
    """Serializes the current User profile with memberships."""
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    auth_source = serializers.CharField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    active_institution_id = serializers.CharField(read_only=True, allow_null=True)
    active_role = serializers.CharField(read_only=True, allow_null=True)
    memberships = MembershipSerializer(many=True, read_only=True)

    def to_representation(self, instance) -> dict:
        """Serialize a User with memberships and session data."""
        request = self.context.get("request")
        memberships = instance.memberships.select_related(
            "institution", "role"
        ).prefetch_related("centers").filter(is_active=True)

        return {
            "id": str(instance.id),
            "email": instance.email,
            "auth_source": instance.auth_source,
            "is_superuser": instance.is_superuser,
            "is_active": instance.is_active,
            "active_institution_id": (
                request.session.get("institution_id") if request else None
            ),
            "active_role": (
                request.session.get("active_role") if request else None
            ),
            "memberships": MembershipSerializer(memberships, many=True).data,
        }


class SwitchInstitutionResponseSerializer(serializers.Serializer):
    """Response shape for institution switch."""
    user = UserSerializer(read_only=True)
    active_institution = InstitutionSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    centers = CenterSerializer(many=True, read_only=True)
