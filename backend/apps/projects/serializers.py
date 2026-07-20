"""
DRF ModelSerializers for the projects module (Phase 3.2).

Provides 7 serializers implementing the API contract from spec.md:
- ProjectListSerializer — lightweight list (7 fields)
- ProjectSerializer — full detail with nested members/documents (read-only)
- ProjectCreateSerializer — writable fields; institution injected by view
- ProjectMemberSerializer — researcher, role; project read-only
- ProjectDocumentSerializer — name, doc_type, external_url; project read-only
- ProjectObservationSerializer — read-only observation data
- ProjectStateLogSerializer — read-only state history data

Design decisions (from design.md):
- Nested serializers on ProjectSerializer are read-only
- institution is read-only on ProjectCreateSerializer (set by view)
- project FK is read-only on child serializers (set by view from URL)
- Observations are append-only — no update/delete (RN-014)

Spec reference: openspec/changes/projects/spec.md — API Contract
Design reference: openspec/changes/projects/design.md — Serializer Mapping
"""
from rest_framework import serializers

from apps.projects.models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)

# ──────────────────────────────────────────────────────────
# ProjectListSerializer
# ──────────────────────────────────────────────────────────


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project list views.

    Exposes only 7 fields: id, title, status, center,
    principal_investigator, start_date, created_at.
    """

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "status",
            "center",
            "principal_investigator",
            "start_date",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ProjectSerializer (full detail)
# ──────────────────────────────────────────────────────────


class ProjectSerializer(serializers.ModelSerializer):
    """Full-detail serializer with nested members and documents.

    Nested data is read-only — mutations go through dedicated
    nested endpoints (/members/, /documents/).
    """

    members = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "institution",
            "center",
            "group",
            "line",
            "principal_investigator",
            "title",
            "abstract",
            "objectives",
            "methodology",
            "expected_results",
            "keywords",
            "start_date",
            "estimated_end_date",
            "actual_end_date",
            "status",
            "is_active",
            "created_at",
            "updated_at",
            "members",
            "documents",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_members(self, obj):
        """Return nested members — read-only."""
        members = obj.members.all()
        return ProjectMemberSerializer(members, many=True).data

    def get_documents(self, obj):
        """Return nested documents — read-only."""
        documents = obj.documents.all()
        return ProjectDocumentSerializer(documents, many=True).data


# ──────────────────────────────────────────────────────────
# ProjectCreateSerializer
# ──────────────────────────────────────────────────────────


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating Project instances.

    Only writable fields are exposed. institution is read-only
    (injected by the view via serializer.save(institution=inst)).
    No nested writes — members and documents are managed through
    their own dedicated nested endpoints.
    """

    class Meta:
        model = Project
        fields = [
            "id",
            "institution",
            "center",
            "group",
            "line",
            "principal_investigator",
            "title",
            "abstract",
            "objectives",
            "methodology",
            "expected_results",
            "keywords",
            "start_date",
            "estimated_end_date",
            "actual_end_date",
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
# ProjectMemberSerializer
# ──────────────────────────────────────────────────────────


class ProjectMemberSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMember CRUD.

    project FK is read-only — set by the view from the URL path.
    researcher FK is writable; role is writable.
    """

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "project",
            "researcher",
            "role",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "joined_at",
        ]


# ──────────────────────────────────────────────────────────
# ProjectDocumentSerializer
# ──────────────────────────────────────────────────────────


class ProjectDocumentSerializer(serializers.ModelSerializer):
    """Serializer for ProjectDocument CRUD.

    project FK is read-only — set by the view from the URL path.
    """

    class Meta:
        model = ProjectDocument
        fields = [
            "id",
            "project",
            "name",
            "doc_type",
            "external_url",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "uploaded_at",
        ]


# ──────────────────────────────────────────────────────────
# ProjectObservationSerializer
# ──────────────────────────────────────────────────────────


class ProjectObservationSerializer(serializers.ModelSerializer):
    """Read-only serializer for ProjectObservation (RN-014).

    All fields are read-only — observations are append-only,
    created via the observe() transition in ProjectService.
    No create/update/delete endpoints exposed.
    """

    class Meta:
        model = ProjectObservation
        fields = [
            "id",
            "project",
            "observed_by",
            "observation_text",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "observed_by",
            "observation_text",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# ProjectStateLogSerializer
# ──────────────────────────────────────────────────────────


class ProjectStateLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for ProjectStateLog (RN-012).

    All fields are read-only — state logs are append-only,
    created via the _log_transition() private method in ProjectService.
    No create/update/delete endpoints exposed.
    """

    class Meta:
        model = ProjectStateLog
        fields = [
            "id",
            "project",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "from_state",
            "to_state",
            "triggered_by",
            "reason",
            "created_at",
        ]
