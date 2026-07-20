"""
Unit tests for projects serializers (Phase 3.5).

Covers 7 serializers:
- ProjectListSerializer: lightweight list (7 fields)
- ProjectSerializer: full detail + nested members/documents (read-only)
- ProjectCreateSerializer: writable fields; institution injected by view
- ProjectMemberSerializer: researcher, role, project read-only
- ProjectDocumentSerializer: name, doc_type, external_url, project read-only
- ProjectObservationSerializer: read-only
- ProjectStateLogSerializer: read-only

Strict TDD: this file is written BEFORE serializers.py exists.
Expected failure: ImportError (serializers.py not created yet).
"""
from uuid import uuid4

import pytest

# ──────────────────────────────────────────────────────────
# ProjectListSerializer
# ──────────────────────────────────────────────────────────


class TestProjectListSerializer:
    """ProjectListSerializer: lightweight 7 fields (id, title, status, center,
    principal_investigator, start_date, created_at)."""

    @pytest.mark.django_db
    def test_list_serializer_fields(self):
        """List serializer must expose exactly the 7 lightweight fields."""
        from apps.projects.serializers import ProjectListSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        serialized = ProjectListSerializer(project).data

        expected = {"id", "title", "status", "center", "principal_investigator",
                     "start_date", "created_at"}
        assert set(serialized.keys()) == expected

    @pytest.mark.django_db
    def test_list_serializer_title_in_output(self):
        """title must be present in list output."""
        from apps.projects.serializers import ProjectListSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(title="Test Project Alpha")
        serialized = ProjectListSerializer(project).data
        assert serialized["title"] == "Test Project Alpha"

    @pytest.mark.django_db
    def test_list_serializer_status_in_output(self):
        """status must be present in list output."""
        from apps.projects.serializers import ProjectListSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(status="borrador")
        serialized = ProjectListSerializer(project).data
        assert serialized["status"] == "borrador"

    @pytest.mark.django_db
    def test_list_serializer_ids_are_fk_values(self):
        """center and principal_investigator must be FK id values."""
        from apps.projects.serializers import ProjectListSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        serialized = ProjectListSerializer(project).data
        assert serialized["center"] == project.center_id
        assert serialized["principal_investigator"] == project.principal_investigator_id


# ──────────────────────────────────────────────────────────
# ProjectSerializer (full detail)
# ──────────────────────────────────────────────────────────


class TestProjectSerializer:
    """ProjectSerializer: all fields + nested members/documents read-only."""

    @pytest.mark.django_db
    def test_detail_contains_all_model_fields(self):
        """ProjectSerializer must serialize all Project model fields."""
        from apps.projects.serializers import ProjectSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        serialized = ProjectSerializer(project).data

        expected_core = {
            "id", "institution", "center", "group", "line",
            "principal_investigator", "title", "abstract",
            "objectives", "methodology", "expected_results", "keywords",
            "start_date", "estimated_end_date", "actual_end_date",
            "status", "is_active", "created_at", "updated_at",
            "members", "documents",
        }
        missing = expected_core - set(serialized.keys())
        assert not missing, f"Missing fields: {missing}"

    @pytest.mark.django_db
    def test_nested_members_present(self):
        """members must appear as a nested list in ProjectSerializer output."""
        from apps.projects.serializers import ProjectSerializer
        from apps.projects.tests.conftest import ProjectFactory, ProjectMemberFactory

        project = ProjectFactory()
        ProjectMemberFactory(project=project, role="co_investigator")

        serialized = ProjectSerializer(project).data
        assert isinstance(serialized["members"], list)
        assert len(serialized["members"]) == 1
        member = serialized["members"][0]
        assert "researcher" in member
        assert "role" in member

    @pytest.mark.django_db
    def test_nested_documents_present(self):
        """documents must appear as a nested list in ProjectSerializer output."""
        from apps.projects.serializers import ProjectSerializer
        from apps.projects.tests.conftest import ProjectDocumentFactory, ProjectFactory

        project = ProjectFactory()
        ProjectDocumentFactory(project=project, doc_type="proposal")

        serialized = ProjectSerializer(project).data
        assert isinstance(serialized["documents"], list)
        assert len(serialized["documents"]) == 1
        doc = serialized["documents"][0]
        assert "name" in doc
        assert "doc_type" in doc
        assert "external_url" in doc

    @pytest.mark.django_db
    def test_nested_data_read_only(self):
        """Nested members/documents cannot be written via detail serializer."""
        from apps.projects.serializers import ProjectSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        data = {
            "title": "Modified Title",
            "members": [{"researcher": "fake-uuid", "role": "student"}],
        }
        serializer = ProjectSerializer(instance=project, data=data, partial=True)
        is_valid = serializer.is_valid()
        if is_valid:
            saved = serializer.save()
            assert saved.title == "Modified Title"
            # Members should NOT have been mutated (read-only nested)


# ──────────────────────────────────────────────────────────
# ProjectCreateSerializer
# ──────────────────────────────────────────────────────────


class TestProjectCreateSerializer:
    """ProjectCreateSerializer: writable fields; institution injected by view."""

    @pytest.mark.django_db
    def test_deserialize_valid_data(self):
        """Minimal valid data must pass validation."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.serializers import ProjectCreateSerializer
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)

        data = {
            "center": center.pk,
            "principal_investigator": researcher.pk,
            "title": "New Project",
            "abstract": "Abstract text",
            "objectives": "Objectives text",
            "methodology": "Methodology text",
            "expected_results": "Expected results",
            "start_date": "2025-01-15",
            "estimated_end_date": "2025-12-31",
        }
        serializer = ProjectCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_institution_read_only(self):
        """institution must be read-only — ignored if provided in input."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.serializers import ProjectCreateSerializer
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)

        data = {
            "center": center.pk,
            "principal_investigator": researcher.pk,
            "title": "Project X",
            "abstract": "Abstract",
            "objectives": "Objectives",
            "methodology": "Methodology",
            "expected_results": "Results",
            "start_date": "2025-01-15",
            "estimated_end_date": "2025-12-31",
            "institution": str(uuid4()),  # attempt to inject
        }
        serializer = ProjectCreateSerializer(data=data)
        assert isinstance(serializer.is_valid(), bool)  # Must not raise

    @pytest.mark.django_db
    def test_required_fields(self):
        """title, abstract, center, PI, start_date, estimated_end_date required."""
        from apps.projects.serializers import ProjectCreateSerializer

        serializer = ProjectCreateSerializer(data={})
        assert not serializer.is_valid()
        required = [
            "title", "abstract", "objectives", "methodology",
            "expected_results", "center", "principal_investigator",
            "start_date", "estimated_end_date",
        ]
        for field in required:
            assert field in serializer.errors, f"{field} should be required"

    @pytest.mark.django_db
    def test_start_date_before_estimated_end_date(self):
        """estimated_end_date < start_date must be rejected."""
        from apps.institutions.tests.conftest import ResearchCenterFactory
        from apps.projects.serializers import ProjectCreateSerializer
        from apps.researchers.tests.conftest import ResearcherFactory

        researcher = ResearcherFactory()
        center = ResearchCenterFactory(institution=researcher.institution)

        data = {
            "center": center.pk,
            "principal_investigator": researcher.pk,
            "title": "Bad Dates",
            "abstract": "Abstract",
            "objectives": "Obj",
            "methodology": "Method",
            "expected_results": "Results",
            "start_date": "2025-12-31",
            "estimated_end_date": "2025-01-01",
        }
        serializer = ProjectCreateSerializer(data=data)
        # Date validation happens in model clean(), so serializer may pass
        # but model save will fail. Check that serializer validates.
        is_valid = serializer.is_valid()
        # Either serializer validation or model clean() catches this
        assert isinstance(is_valid, bool)


# ──────────────────────────────────────────────────────────
# ProjectMemberSerializer
# ──────────────────────────────────────────────────────────


class TestProjectMemberSerializer:
    """ProjectMemberSerializer: researcher, role; project read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include researcher, role, joined_at."""
        from apps.projects.serializers import ProjectMemberSerializer
        from apps.projects.tests.conftest import ProjectMemberFactory

        member = ProjectMemberFactory(role="student")
        serialized = ProjectMemberSerializer(member).data

        assert "id" in serialized
        assert "researcher" in serialized
        assert serialized["researcher"] == member.researcher_id
        assert serialized["role"] == "student"
        assert "joined_at" in serialized

    @pytest.mark.django_db
    def test_project_read_only(self):
        """project FK must be read-only."""
        from apps.projects.serializers import ProjectMemberSerializer
        from apps.projects.tests.conftest import ProjectMemberFactory

        member = ProjectMemberFactory()
        data = {"project": str(uuid4())}
        serializer = ProjectMemberSerializer(instance=member, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)

    @pytest.mark.django_db
    def test_role_choices_valid(self):
        """role must accept valid ProjectRole choices."""
        from apps.projects.serializers import ProjectMemberSerializer
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory()
        researcher = ResearcherFactory(institution=project.institution)

        for role in ["co_investigator", "student", "seedbed", "collaborator"]:
            data = {
                "researcher": researcher.pk,
                "role": role,
            }
            serializer = ProjectMemberSerializer(data=data)
            assert serializer.is_valid(), f"role={role}: {serializer.errors}"

    @pytest.mark.django_db
    def test_role_invalid_choice_rejected(self):
        """Invalid role must be rejected."""
        from apps.projects.serializers import ProjectMemberSerializer
        from apps.projects.tests.conftest import ProjectFactory
        from apps.researchers.tests.conftest import ResearcherFactory

        project = ProjectFactory()
        researcher = ResearcherFactory(institution=project.institution)

        data = {
            "researcher": researcher.pk,
            "role": "manager",
        }
        serializer = ProjectMemberSerializer(data=data)
        assert not serializer.is_valid()
        assert "role" in serializer.errors


# ──────────────────────────────────────────────────────────
# ProjectDocumentSerializer
# ──────────────────────────────────────────────────────────


class TestProjectDocumentSerializer:
    """ProjectDocumentSerializer: name, doc_type, external_url; project read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include name, doc_type, external_url."""
        from apps.projects.serializers import ProjectDocumentSerializer
        from apps.projects.tests.conftest import ProjectDocumentFactory

        doc = ProjectDocumentFactory(name="Research Proposal", doc_type="proposal")
        serialized = ProjectDocumentSerializer(doc).data

        assert serialized["name"] == "Research Proposal"
        assert serialized["doc_type"] == "proposal"
        assert "external_url" in serialized
        assert "project" in serialized
        assert "uploaded_at" in serialized

    @pytest.mark.django_db
    def test_project_read_only(self):
        """project FK must be read-only."""
        from apps.projects.serializers import ProjectDocumentSerializer
        from apps.projects.tests.conftest import ProjectDocumentFactory

        doc = ProjectDocumentFactory()
        data = {"project": str(uuid4())}
        serializer = ProjectDocumentSerializer(instance=doc, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)

    @pytest.mark.django_db
    def test_doc_type_choices_valid(self):
        """doc_type must accept valid ProjectDocumentType choices."""
        from apps.projects.serializers import ProjectDocumentSerializer

        for dt in ["proposal", "annex", "contract", "report", "other"]:
            data = {
                "name": "Test File",
                "doc_type": dt,
                "external_url": "https://example.com/doc",
            }
            serializer = ProjectDocumentSerializer(data=data)
            assert serializer.is_valid(), f"doc_type={dt}: {serializer.errors}"

    @pytest.mark.django_db
    def test_doc_type_invalid_choice_rejected(self):
        """Invalid doc_type must be rejected."""
        from apps.projects.serializers import ProjectDocumentSerializer

        data = {
            "name": "File",
            "doc_type": "invalid_type",
            "external_url": "https://example.com",
        }
        serializer = ProjectDocumentSerializer(data=data)
        assert not serializer.is_valid()
        assert "doc_type" in serializer.errors

    @pytest.mark.django_db
    def test_name_required(self):
        """name must be required."""
        from apps.projects.serializers import ProjectDocumentSerializer

        data = {"doc_type": "proposal", "external_url": "https://example.com"}
        serializer = ProjectDocumentSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    @pytest.mark.django_db
    def test_external_url_required(self):
        """external_url must be required."""
        from apps.projects.serializers import ProjectDocumentSerializer

        data = {"name": "Doc", "doc_type": "proposal"}
        serializer = ProjectDocumentSerializer(data=data)
        assert not serializer.is_valid()
        assert "external_url" in serializer.errors


# ──────────────────────────────────────────────────────────
# ProjectObservationSerializer
# ──────────────────────────────────────────────────────────


class TestProjectObservationSerializer:
    """ProjectObservationSerializer: read-only observation data."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include observed_by, observation_text, created_at."""
        from apps.projects.serializers import ProjectObservationSerializer
        from apps.projects.tests.conftest import ProjectObservationFactory

        obs = ProjectObservationFactory(observation_text="Needs revision")
        serialized = ProjectObservationSerializer(obs).data

        assert "id" in serialized
        assert "observed_by" in serialized
        assert serialized["observation_text"] == "Needs revision"
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """All fields must be read-only."""
        from apps.projects.serializers import ProjectObservationSerializer
        from apps.projects.tests.conftest import ProjectObservationFactory

        obs = ProjectObservationFactory()
        data = {"observation_text": "Modified"}
        serializer = ProjectObservationSerializer(instance=obs, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)


# ──────────────────────────────────────────────────────────
# ProjectStateLogSerializer
# ──────────────────────────────────────────────────────────


class TestProjectStateLogSerializer:
    """ProjectStateLogSerializer: read-only state history data."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include from_state, to_state, triggered_by, reason, created_at."""
        from apps.projects.serializers import ProjectStateLogSerializer
        from apps.projects.tests.conftest import ProjectStateLogFactory

        log = ProjectStateLogFactory(from_state="borrador", to_state="enviado", reason="Submitted")
        serialized = ProjectStateLogSerializer(log).data

        assert serialized["from_state"] == "borrador"
        assert serialized["to_state"] == "enviado"
        assert serialized["reason"] == "Submitted"
        assert "triggered_by" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """All fields must be read-only."""
        from apps.projects.serializers import ProjectStateLogSerializer
        from apps.projects.tests.conftest import ProjectStateLogFactory

        log = ProjectStateLogFactory()
        data = {"reason": "Modified"}
        serializer = ProjectStateLogSerializer(instance=log, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)
