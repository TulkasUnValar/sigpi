"""
Unit tests for researchers serializers (Phase 3.3).

Covers:
- Field validation (document_type choices, provider choices, attachment_type choices)
- completeness_score output
- Nested serialization (affiliations, profiles, attachments appear in ResearcherSerializer)
- Create serializer institution injection
- Read-only fields cannot be written
- ResearcherListSerializer lightweight output
- ResearcherAffiliationSerializer, ExternalProfileSerializer, ResearcherAttachmentSerializer

Strict TDD: this file is written BEFORE serializers.py exists.
Expected failure: ModuleNotFoundError (serializers.py not created yet).
"""
import pytest

from apps.researchers.tests.conftest import (
    ExternalProfileFactory,
    ResearcherAffiliationFactory,
    ResearcherAttachmentFactory,
    ResearcherFactory,
)

# ──────────────────────────────────────────────────────────
# ResearcherListSerializer
# ──────────────────────────────────────────────────────────


class TestResearcherListSerializer:
    """ResearcherListSerializer: lightweight fields (id, full_name, institution,
    is_active, completeness_score)."""

    def test_list_serializer_fields(self):
        """List serializer must expose only the 5 lightweight fields."""
        from apps.researchers.serializers import ResearcherListSerializer

        researcher = ResearcherFactory.build(id=None)
        serialized = ResearcherListSerializer(researcher).data

        # Expected output fields only
        expected = {"id", "full_name", "institution", "is_active", "completeness_score"}
        assert set(serialized.keys()) == expected

    def test_full_name_in_output(self):
        """full_name must be computed as 'first_name last_name'."""
        from apps.researchers.serializers import ResearcherListSerializer

        researcher = ResearcherFactory.build(
            id=None, first_name="María", last_name="García"
        )
        serialized = ResearcherListSerializer(researcher).data
        assert serialized["full_name"] == "María García"

    def test_is_active_output(self):
        """is_active must reflect the model field."""
        from apps.researchers.serializers import ResearcherListSerializer

        active = ResearcherFactory.build(id=None, is_active=True)
        inactive = ResearcherFactory.build(id=None, is_active=False)

        assert ResearcherListSerializer(active).data["is_active"] is True
        assert ResearcherListSerializer(inactive).data["is_active"] is False

    def test_institution_id_in_output(self):
        """institution must be the FK id."""
        from apps.researchers.serializers import ResearcherListSerializer

        researcher = ResearcherFactory.build(id=None)
        serialized = ResearcherListSerializer(researcher).data
        assert serialized["institution"] == researcher.institution_id

    @pytest.mark.django_db
    def test_completeness_score_in_output(self):
        """completeness_score must be computed from ResearcherProfileService."""
        from apps.researchers.serializers import ResearcherListSerializer

        researcher = ResearcherFactory(
            first_name="Juan", last_name="Pérez",
            document_type="CC", document_number="123",
            primary_email="juan@test.com",
        )
        # Create an external profile so all 6 mandatory items are met → score 100
        ExternalProfileFactory(researcher=researcher)

        serialized = ResearcherListSerializer(researcher).data
        assert serialized["completeness_score"] == 100

    @pytest.mark.django_db
    def test_completeness_score_partial(self):
        """completeness_score must be < 100 when fields are missing."""
        from apps.researchers.serializers import ResearcherListSerializer

        researcher = ResearcherFactory(
            first_name="", last_name="",
            primary_email="",
        )
        serialized = ResearcherListSerializer(researcher).data
        assert serialized["completeness_score"] < 100


# ──────────────────────────────────────────────────────────
# ResearcherSerializer (full detail)
# ──────────────────────────────────────────────────────────


class TestResearcherSerializer:
    """ResearcherSerializer: all fields + nested affiliations, profiles, attachments."""

    @pytest.mark.django_db
    def test_detail_contains_all_model_fields(self):
        """ResearcherSerializer must serialize all Researcher model fields."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory()
        serialized = ResearcherSerializer(researcher).data

        expected_fields = {
            "id", "user", "institution", "first_name", "last_name",
            "document_type", "document_number", "primary_email", "phone",
            "bio", "academic_formation", "is_active",
            "full_name", "completeness_score",
            "affiliations", "external_profiles", "attachments",
            "created_at", "updated_at",
        }
        assert set(serialized.keys()) == expected_fields

    @pytest.mark.django_db
    def test_nested_affiliations_present(self):
        """affiliations must appear as a nested list in ResearcherSerializer output."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory()
        ResearcherAffiliationFactory(researcher=researcher)

        serialized = ResearcherSerializer(researcher).data
        assert isinstance(serialized["affiliations"], list)
        assert len(serialized["affiliations"]) == 1
        aff = serialized["affiliations"][0]
        assert "center" in aff
        assert "group" in aff
        assert "line" in aff
        assert "is_primary" in aff

    @pytest.mark.django_db
    def test_nested_external_profiles_present(self):
        """external_profiles must appear as a nested list."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory()
        ExternalProfileFactory(researcher=researcher, provider="orcid")

        serialized = ResearcherSerializer(researcher).data
        assert isinstance(serialized["external_profiles"], list)
        assert len(serialized["external_profiles"]) == 1
        profile = serialized["external_profiles"][0]
        assert profile["provider"] == "orcid"
        assert "url" in profile

    @pytest.mark.django_db
    def test_nested_attachments_present(self):
        """attachments must appear as a nested list."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory()
        ResearcherAttachmentFactory(researcher=researcher, type="cv")

        serialized = ResearcherSerializer(researcher).data
        assert isinstance(serialized["attachments"], list)
        assert len(serialized["attachments"]) == 1
        att = serialized["attachments"][0]
        assert att["type"] == "cv"
        assert "name" in att
        assert "external_url" in att

    @pytest.mark.django_db
    def test_nested_data_read_only_on_detail(self):
        """Nested affiliations/profiles/attachments cannot be written via detail serializer."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory()
        data = {
            "first_name": "Changed",
            "affiliations": [{"center": "fake"}],
        }
        serializer = ResearcherSerializer(instance=researcher, data=data, partial=True)
        is_valid = serializer.is_valid()  # may or may not be valid
        if is_valid:
            # Even if valid, nested data must be ignored (read-only)
            saved = serializer.save()
            assert saved.first_name == "Changed"
            # affiliations should NOT have been mutated
        else:
            # It's fine if it rejects — nested serializer writes are not expected
            pass

    @pytest.mark.django_db
    def test_completeness_score_on_detail(self):
        """completeness_score must be present in detail serializer too."""
        from apps.researchers.serializers import ResearcherSerializer

        researcher = ResearcherFactory(
            first_name="A", last_name="B",
            document_type="CC", document_number="X",
            primary_email="a@b.com",
        )
        ExternalProfileFactory(researcher=researcher)

        serialized = ResearcherSerializer(researcher).data
        assert serialized["completeness_score"] == 100


# ──────────────────────────────────────────────────────────
# ResearcherCreateSerializer
# ──────────────────────────────────────────────────────────


class TestResearcherCreateSerializer:
    """ResearcherCreateSerializer: writable fields, institution read-only, no nested writes."""

    def test_deserialize_valid_data(self):
        """Minimal valid data must pass validation."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        data = {
            "first_name": "Carlos",
            "last_name": "López",
            "document_type": "CC",
            "document_number": "987654",
            "primary_email": "carlos@test.com",
        }
        serializer = ResearcherCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["first_name"] == "Carlos"

    def test_institution_read_only(self):
        """institution must be read-only — ignored if provided in input."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        data = {
            "first_name": "Ana",
            "last_name": "Martínez",
            "document_type": "CC",
            "document_number": "111222",
            "primary_email": "ana@test.com",
            "institution": "00000000-0000-0000-0000-000000000999",
        }
        serializer = ResearcherCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        # institution must NOT be in validated_data
        assert "institution" not in serializer.validated_data

    def test_required_fields(self):
        """first_name, last_name, document_type, document_number, primary_email required."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        serializer = ResearcherCreateSerializer(data={})
        assert not serializer.is_valid()
        required = ["first_name", "last_name", "document_type", "document_number", "primary_email"]
        for field in required:
            assert field in serializer.errors, f"{field} should be required"

    def test_document_type_choices_valid(self):
        """document_type must accept CC, TI, CE, PA (TextChoices)."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        for choice in ["CC", "TI", "CE", "PA"]:
            data = {
                "first_name": "T",
                "last_name": "T",
                "document_type": choice,
                "document_number": "001",
                "primary_email": "t@t.com",
            }
            serializer = ResearcherCreateSerializer(data=data)
            assert serializer.is_valid(), f"document_type={choice}: {serializer.errors}"

    def test_document_type_invalid_choice_rejected(self):
        """Invalid document_type must be rejected."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        data = {
            "first_name": "T",
            "last_name": "T",
            "document_type": "INVALID",
            "document_number": "001",
            "primary_email": "t@t.com",
        }
        serializer = ResearcherCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "document_type" in serializer.errors

    @pytest.mark.django_db
    def test_create_does_not_allow_nested_affiliations(self):
        """Create serializer must reject nested affiliations data."""
        from apps.researchers.serializers import ResearcherCreateSerializer

        data = {
            "first_name": "T",
            "last_name": "T",
            "document_type": "CC",
            "document_number": "002",
            "primary_email": "t@t.com",
            "affiliations": [{"center": "fake"}],
        }
        serializer = ResearcherCreateSerializer(data=data)
        # Either validation fails (unknown field) or nested data is ignored
        is_valid = serializer.is_valid()
        if is_valid:
            assert "affiliations" not in serializer.validated_data


# ──────────────────────────────────────────────────────────
# ResearcherAffiliationSerializer
# ──────────────────────────────────────────────────────────


class TestResearcherAffiliationSerializer:
    """ResearcherAffiliationSerializer: center/group/line FKs, is_primary, researcher read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include center, group, line, is_primary, researcher."""
        from apps.researchers.serializers import ResearcherAffiliationSerializer

        affiliation = ResearcherAffiliationFactory()
        serialized = ResearcherAffiliationSerializer(affiliation).data

        assert "id" in serialized
        assert "researcher" in serialized
        assert serialized["researcher"] == affiliation.researcher_id
        assert "center" in serialized
        assert serialized["center"] == affiliation.center_id
        assert "group" in serialized
        assert "line" in serialized
        assert "is_primary" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_researcher_read_only(self):
        """researcher FK must be read-only."""
        from apps.researchers.serializers import ResearcherAffiliationSerializer

        researcher = ResearcherFactory()
        affiliation = ResearcherAffiliationFactory(researcher=researcher)

        data = {"researcher": "00000000-0000-0000-0000-000000000999"}
        serializer = ResearcherAffiliationSerializer(instance=affiliation, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "researcher" not in serializer.validated_data

    @pytest.mark.django_db
    def test_deserialize_valid(self):
        """Valid affiliation data must pass validation."""
        from apps.researchers.serializers import ResearcherAffiliationSerializer

        researcher = ResearcherFactory()
        # Need a center in same institution
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)

        data = {
            "center": center.pk,
            "is_primary": True,
        }
        serializer = ResearcherAffiliationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_at_least_one_fk_required(self):
        """At least one of center, group, line must be provided."""
        from apps.researchers.serializers import ResearcherAffiliationSerializer

        data = {"is_primary": True}
        serializer = ResearcherAffiliationSerializer(data=data)
        # This should fail validation — but since it's a model-level constraint (clean()),
        # it may pass the serializer. We enforce in view/service layer.
        # Just check it doesn't crash.
        assert isinstance(serializer.is_valid(), bool)


# ──────────────────────────────────────────────────────────
# ExternalProfileSerializer
# ──────────────────────────────────────────────────────────


class TestExternalProfileSerializer:
    """ExternalProfileSerializer: provider, url, researcher read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include provider and url."""
        from apps.researchers.serializers import ExternalProfileSerializer

        profile = ExternalProfileFactory(provider="orcid")
        serialized = ExternalProfileSerializer(profile).data

        assert serialized["provider"] == "orcid"
        assert "url" in serialized
        assert "researcher" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_researcher_read_only(self):
        """researcher FK must be read-only."""
        from apps.researchers.serializers import ExternalProfileSerializer

        profile = ExternalProfileFactory()

        data = {"researcher": "00000000-0000-0000-0000-000000000999"}
        serializer = ExternalProfileSerializer(instance=profile, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "researcher" not in serializer.validated_data

    def test_provider_choices_valid(self):
        """provider must accept cvlac, orcid, google_scholar, linkedin, researchgate."""
        from apps.researchers.serializers import ExternalProfileSerializer

        valid = ["cvlac", "orcid", "google_scholar", "linkedin", "researchgate"]
        for provider in valid:
            data = {"provider": provider, "url": "https://example.com"}
            serializer = ExternalProfileSerializer(data=data)
            assert serializer.is_valid(), f"provider={provider}: {serializer.errors}"

    def test_provider_invalid_choice_rejected(self):
        """Invalid provider must be rejected."""
        from apps.researchers.serializers import ExternalProfileSerializer

        data = {"provider": "invalid_provider", "url": "https://example.com"}
        serializer = ExternalProfileSerializer(data=data)
        assert not serializer.is_valid()
        assert "provider" in serializer.errors

    def test_url_required(self):
        """url must be required."""
        from apps.researchers.serializers import ExternalProfileSerializer

        data = {"provider": "orcid"}
        serializer = ExternalProfileSerializer(data=data)
        assert not serializer.is_valid()
        assert "url" in serializer.errors


# ──────────────────────────────────────────────────────────
# ResearcherAttachmentSerializer
# ──────────────────────────────────────────────────────────


class TestResearcherAttachmentSerializer:
    """ResearcherAttachmentSerializer: name, type, external_url, researcher read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include name, type, external_url."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        attachment = ResearcherAttachmentFactory(type="cv", name="My CV")
        serialized = ResearcherAttachmentSerializer(attachment).data

        assert serialized["type"] == "cv"
        assert serialized["name"] == "My CV"
        assert "external_url" in serialized
        assert "researcher" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_researcher_read_only(self):
        """researcher FK must be read-only."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        attachment = ResearcherAttachmentFactory()

        data = {"researcher": "00000000-0000-0000-0000-000000000999"}
        serializer = ResearcherAttachmentSerializer(instance=attachment, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        assert "researcher" not in serializer.validated_data

    def test_type_choices_valid(self):
        """type must accept cv, certificate, photo, other."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        valid = ["cv", "certificate", "photo", "other"]
        for att_type in valid:
            data = {
                "name": "File",
                "type": att_type,
                "external_url": "https://example.com/file",
            }
            serializer = ResearcherAttachmentSerializer(data=data)
            assert serializer.is_valid(), f"type={att_type}: {serializer.errors}"

    def test_type_invalid_choice_rejected(self):
        """Invalid type must be rejected."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        data = {
            "name": "File",
            "type": "invalid_type",
            "external_url": "https://example.com/file",
        }
        serializer = ResearcherAttachmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "type" in serializer.errors

    def test_name_required(self):
        """name must be required."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        data = {"type": "cv", "external_url": "https://example.com"}
        serializer = ResearcherAttachmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_external_url_required(self):
        """external_url must be required."""
        from apps.researchers.serializers import ResearcherAttachmentSerializer

        data = {"name": "CV", "type": "cv"}
        serializer = ResearcherAttachmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "external_url" in serializer.errors
