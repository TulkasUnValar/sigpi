"""
Model tests for researchers app — STRICT TDD.

Tests define the expected behavior of the 4-entity researcher module:
Researcher, ResearcherAffiliation, ExternalProfile, ResearcherAttachment.

Spec reference:  openspec/changes/researchers/spec.md
Design reference: openspec/changes/researchers/design.md

RED PHASE: All tests will fail because models don't exist yet.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.researchers.models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)
from apps.researchers.tests.conftest import (
    ResearcherAffiliationFactory,
    ResearcherFactory,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    """Create a test Institution for researcher tests."""
    from apps.institutions.models import Institution
    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    """Create a test ResearchCenter."""
    from apps.institutions.models import ResearchCenter
    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code,
    )


def _make_group(institution, center, name="NLP Group", code="NLP"):
    """Create a test ResearchGroup."""
    from apps.institutions.models import ResearchGroup
    return ResearchGroup.objects.create(
        institution=institution, center=center, name=name, code=code,
    )


def _make_line(institution, group, name="Sentiment", code="SA"):
    """Create a test ResearchLine."""
    from apps.institutions.models import ResearchLine
    return ResearchLine.objects.create(
        institution=institution, group=group, name=name, code=code,
    )


# ──────────────────────────────────────────────
# Researcher Model Tests
# ──────────────────────────────────────────────


class TestResearcherFields:
    """Researcher model field behavior and defaults."""

    def test_create_researcher(self, db):
        """A Researcher belongs to an Institution with required name fields."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst,
            first_name="Maria",
            last_name="Gomez",
            document_type="CC",
            document_number="12345678",
            primary_email="maria@test.edu",
        )
        assert researcher.id is not None
        assert researcher.institution == inst
        assert researcher.first_name == "Maria"
        assert researcher.last_name == "Gomez"
        assert researcher.document_type == "CC"
        assert researcher.document_number == "12345678"
        assert researcher.primary_email == "maria@test.edu"
        assert researcher.is_active is True
        assert researcher.user is None
        assert researcher.phone == ""
        assert researcher.bio == ""
        assert researcher.academic_formation == ""

    def test_optional_user_fk(self, db):
        """Researcher can be linked to a User (nullable, unique)."""
        from apps.accounts.models import User

        inst = _make_institution("TU")
        user = User.objects.create_user(email="maria@test.edu")
        researcher = Researcher.objects.create(
            institution=inst,
            user=user,
            first_name="Maria",
            last_name="Gomez",
            document_type="CC",
            document_number="12345678",
            primary_email="maria@test.edu",
        )
        assert researcher.user == user

    def test_user_unique(self, db):
        """A User can have at most one Researcher profile."""
        from apps.accounts.models import User

        inst = _make_institution("TU")
        user = User.objects.create_user(email="maria@test.edu")
        Researcher.objects.create(
            institution=inst, user=user, first_name="M", last_name="G",
            document_type="CC", document_number="111", primary_email="a@t.com",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Researcher.objects.create(
                    institution=inst, user=user, first_name="X", last_name="Y",
                    document_type="TI", document_number="222",
                    primary_email="b@t.com",
                )

    def test_str_representation(self, db):
        """Researcher __str__ returns 'first_name last_name'."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="12345678",
            primary_email="maria@test.edu",
        )
        assert str(researcher) == "Maria Gomez"

    def test_institution_document_unique(self, db):
        """(institution, document_number) must be unique (RN-001)."""
        inst_a = _make_institution("UA")
        inst_b = _make_institution("UB")
        # Same institution, same document → should fail
        Researcher.objects.create(
            institution=inst_a, first_name="A", last_name="One",
            document_type="CC", document_number="DOC001",
            primary_email="a@test.edu",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Researcher.objects.create(
                    institution=inst_a, first_name="A", last_name="Two",
                    document_type="TI", document_number="DOC001",
                    primary_email="a2@test.edu",
                )
        # Same document, different institution → allowed
        Researcher.objects.create(
            institution=inst_b, first_name="B", last_name="One",
            document_type="CC", document_number="DOC001",
            primary_email="b@test.edu",
        )
        assert Researcher.objects.filter(document_number="DOC001").count() == 2

    def test_document_type_choices(self, db):
        """DocumentTypeChoices enum provides CC, TI, CE, PA."""
        inst = _make_institution("TU")
        for dtype in ("CC", "TI", "CE", "PA"):
            researcher = Researcher(
                institution=inst, first_name="Test", last_name="User",
                document_type=dtype, document_number=f"DN-{dtype}",
                primary_email=f"{dtype.lower()}@test.edu",
            )
            researcher.full_clean()  # should not raise

    def test_document_type_invalid_choice(self, db):
        """Invalid document_type raises ValidationError."""
        inst = _make_institution("TU")
        researcher = Researcher(
            institution=inst, first_name="Test", last_name="User",
            document_type="INVALID", document_number="DN-001",
            primary_email="test@test.edu",
        )
        with pytest.raises(ValidationError):
            researcher.full_clean()

    def test_defaults(self, db):
        """New Researcher starts with is_active=True and empty optional fields."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Test", last_name="User",
            document_type="CC", document_number="DN-001",
            primary_email="test@test.edu",
        )
        assert researcher.is_active is True
        assert researcher.phone == ""
        assert researcher.bio == ""
        assert researcher.academic_formation == ""


class TestResearcherFactory:
    """Factory-boy ResearcherFactory behavior."""

    def test_factory_creates_valid_instance(self, db):
        """ResearcherFactory produces a valid Researcher."""
        researcher = ResearcherFactory()
        assert researcher.id is not None
        assert researcher.first_name != ""
        assert researcher.last_name != ""
        assert researcher.document_type == "CC"
        assert researcher.is_active is True

    def test_factory_unique_document_numbers(self, db):
        """Each factory call produces a unique document_number."""
        r1 = ResearcherFactory()
        r2 = ResearcherFactory()
        assert r1.document_number != r2.document_number

    def test_factory_with_user(self, db):
        """ResearcherFactory can have user assigned post-creation."""
        from apps.accounts.models import User
        user = User.objects.create_user(email="test@example.com")
        researcher = ResearcherFactory(user=user)
        assert researcher.user == user


# ──────────────────────────────────────────────
# ResearcherAffiliation Model Tests
# ──────────────────────────────────────────────


class TestResearcherAffiliationFields:
    """ResearcherAffiliation model field behavior and validation."""

    def test_create_affiliation_with_center(self, db):
        """Affiliation can be created with a center FK."""
        inst = _make_institution("TU")
        center = _make_center(inst, name="AI Lab", code="AI")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=True,
        )
        assert affiliation.center == center
        assert affiliation.group is None
        assert affiliation.line is None
        assert affiliation.is_primary is True

    def test_create_affiliation_with_group(self, db):
        """Affiliation can be created with a group FK."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        group = _make_group(inst, center)
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation.objects.create(
            researcher=researcher, group=group,
        )
        assert affiliation.group == group
        assert affiliation.center is None

    def test_create_affiliation_with_line(self, db):
        """Affiliation can be created with a line FK."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        group = _make_group(inst, center)
        line = _make_line(inst, group)
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation.objects.create(
            researcher=researcher, line=line,
        )
        assert affiliation.line == line
        assert affiliation.center is None

    def test_clean_rejects_no_fk_set(self, db):
        """clean() rejects affiliation where no center/group/line is set (RN-AFF-02)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation(researcher=researcher)
        with pytest.raises(ValidationError, match="least one"):
            affiliation.full_clean()

    def test_clean_rejects_cross_institution_center(self, db):
        """clean() rejects center from a different institution (RN-AFF-01)."""
        inst_a = _make_institution("UA")
        inst_b = _make_institution("UB")
        center_b = _make_center(inst_b, name="B Center", code="BC")
        researcher = Researcher.objects.create(
            institution=inst_a, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation(
            researcher=researcher, center=center_b,
        )
        with pytest.raises(ValidationError, match="different institution"):
            affiliation.full_clean()

    def test_clean_rejects_cross_institution_group(self, db):
        """clean() rejects group from a different institution."""
        inst_a = _make_institution("UA")
        inst_b = _make_institution("UB")
        center_b = _make_center(inst_b, name="B Center", code="BC")
        group_b = _make_group(inst_b, center_b, name="B Group", code="BG")
        researcher = Researcher.objects.create(
            institution=inst_a, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation(
            researcher=researcher, group=group_b,
        )
        with pytest.raises(ValidationError, match="different institution"):
            affiliation.full_clean()

    def test_clean_rejects_cross_institution_line(self, db):
        """clean() rejects line from a different institution."""
        inst_a = _make_institution("UA")
        inst_b = _make_institution("UB")
        center_b = _make_center(inst_b, name="B Center", code="BC")
        group_b = _make_group(inst_b, center_b, name="B Group", code="BG")
        line_b = _make_line(inst_b, group_b, name="B Line", code="BL")
        researcher = Researcher.objects.create(
            institution=inst_a, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation(
            researcher=researcher, line=line_b,
        )
        with pytest.raises(ValidationError, match="different institution"):
            affiliation.full_clean()

    def test_only_one_primary_per_researcher(self, db):
        """Only one is_primary=True allowed per researcher (RN-AFF-02)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        # Create first primary
        ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=True,
        )
        # Second primary should fail
        affiliation2 = ResearcherAffiliation(
            researcher=researcher, center=center, is_primary=True,
        )
        with pytest.raises(ValidationError, match="Only one primary"):
            affiliation2.full_clean()

    def test_multiple_non_primary_allowed(self, db):
        """Multiple non-primary affiliations are allowed for the same researcher."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=False,
        )
        ResearcherAffiliation.objects.create(
            researcher=researcher, center=center, is_primary=False,
        )
        assert ResearcherAffiliation.objects.filter(
            researcher=researcher
        ).count() == 2

    def test_str_representation(self, db):
        """ResearcherAffiliation __str__ includes researcher name and entity."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        affiliation = ResearcherAffiliation.objects.create(
            researcher=researcher, center=center,
        )
        assert "Maria Gomez" in str(affiliation)


class TestResearcherAffiliationFactory:
    """Factory-boy ResearcherAffiliationFactory behavior."""

    def test_factory_creates_valid_instance(self, db):
        """ResearcherAffiliationFactory produces a valid affiliation."""
        affiliation = ResearcherAffiliationFactory()
        assert affiliation.id is not None
        assert affiliation.researcher is not None
        assert affiliation.center is not None
        assert affiliation.is_primary is False

    def test_factory_default_not_primary(self, db):
        """Factory default is_primary is False."""
        affiliation = ResearcherAffiliationFactory()
        assert affiliation.is_primary is False


# ──────────────────────────────────────────────
# ExternalProfile Model Tests
# ──────────────────────────────────────────────


class TestExternalProfileFields:
    """ExternalProfile model field behavior."""

    def test_create_profile(self, db):
        """ExternalProfile stores provider and URL for a researcher (RN-EXT-01)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        profile = ExternalProfile.objects.create(
            researcher=researcher,
            provider="orcid",
            url="https://orcid.org/0000-0001-2345-6789",
        )
        assert profile.provider == "orcid"
        assert profile.url == "https://orcid.org/0000-0001-2345-6789"
        assert profile.researcher == researcher

    def test_provider_choices_valid(self, db):
        """All ProviderChoices values are valid (cvlac, orcid, google_scholar,
        linkedin, researchgate)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        for provider in ("cvlac", "orcid", "google_scholar", "linkedin", "researchgate"):
            profile = ExternalProfile(
                researcher=researcher, provider=provider,
                url=f"https://example.com/{provider}",
            )
            profile.full_clean()  # should not raise

    def test_provider_invalid_choice(self, db):
        """Invalid provider raises ValidationError (RN-EXT-01)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        profile = ExternalProfile(
            researcher=researcher, provider="invalid", url="https://x.com",
        )
        with pytest.raises(ValidationError):
            profile.full_clean()

    def test_str_representation(self, db):
        """ExternalProfile __str__ includes provider and researcher name."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        profile = ExternalProfile.objects.create(
            researcher=researcher, provider="orcid",
            url="https://orcid.org/test",
        )
        assert "orcid" in str(profile).lower()
        assert "Maria Gomez" in str(profile)


# ──────────────────────────────────────────────
# ResearcherAttachment Model Tests
# ──────────────────────────────────────────────


class TestResearcherAttachmentFields:
    """ResearcherAttachment model field behavior."""

    def test_create_attachment(self, db):
        """ResearcherAttachment stores name, type, and external URL (RN-ATT-01)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        attachment = ResearcherAttachment.objects.create(
            researcher=researcher,
            name="CV Maria Gomez 2025.pdf",
            type="cv",
            external_url="https://storage.example.com/cv-maria.pdf",
        )
        assert attachment.name == "CV Maria Gomez 2025.pdf"
        assert attachment.type == "cv"
        assert attachment.external_url == "https://storage.example.com/cv-maria.pdf"
        assert attachment.researcher == researcher

    def test_type_choices_valid(self, db):
        """All TypeChoices values (cv, certificate, photo, other) are valid."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        for atype in ("cv", "certificate", "photo", "other"):
            attachment = ResearcherAttachment(
                researcher=researcher, name=f"file.{atype}",
                type=atype, external_url=f"https://storage.example.com/{atype}",
            )
            attachment.full_clean()  # should not raise

    def test_type_invalid_choice(self, db):
        """Invalid type raises ValidationError (RN-ATT-01)."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        attachment = ResearcherAttachment(
            researcher=researcher, name="file.txt", type="invalid",
            external_url="https://storage.example.com/file.txt",
        )
        with pytest.raises(ValidationError):
            attachment.full_clean()

    def test_str_representation(self, db):
        """ResearcherAttachment __str__ includes name and type."""
        inst = _make_institution("TU")
        researcher = Researcher.objects.create(
            institution=inst, first_name="Maria", last_name="Gomez",
            document_type="CC", document_number="DOC001",
            primary_email="maria@test.edu",
        )
        attachment = ResearcherAttachment.objects.create(
            researcher=researcher, name="CV.pdf", type="cv",
            external_url="https://storage.example.com/cv.pdf",
        )
        assert "CV.pdf" in str(attachment)
