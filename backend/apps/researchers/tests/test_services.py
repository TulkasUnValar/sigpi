"""
Service layer tests for researchers app — STRICT TDD (RED phase).

Tests define expected behavior of:
- ResearcherProfileService: create, update, deactivate, calculate_completeness
- ResearcherAffiliationService: add, remove, set_primary atomicity

Spec reference: openspec/changes/researchers/spec.md — RF-018, RF-019, RF-024, RN-006
Design reference: openspec/changes/researchers/design.md — Service Layer

RED PHASE: Tests fail because services.py does not exist.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.researchers.models import Researcher, ResearcherAffiliation
from apps.researchers.services import ResearcherAffiliationService, ResearcherProfileService
from apps.researchers.tests.conftest import (
    ExternalProfileFactory,
    ResearcherFactory,
)

# ──────────────────────────────────────────────
# ResearcherProfileService Tests
# ──────────────────────────────────────────────


class TestResearcherProfileServiceCreate:
    """ResearcherProfileService.create() — profile creation with completeness."""

    def test_create_researcher(self, db):
        """create() returns a saved Researcher with calculated completeness."""
        institution = ResearcherFactory.build().institution
        # Save the institution first (build doesn't persist)
        institution.save()

        researcher = ResearcherProfileService.create(
            institution=institution,
            first_name="Alice",
            last_name="Smith",
            document_type="CC",
            document_number="1234567890",
            primary_email="alice@example.com",
            phone="+57 300 000 0000",
            bio="Computer scientist",
            academic_formation="PhD Computer Science",
        )

        assert researcher.pk is not None
        assert researcher.institution == institution
        assert researcher.first_name == "Alice"
        assert researcher.last_name == "Smith"
        assert researcher.document_type == "CC"
        assert researcher.document_number == "1234567890"
        assert researcher.primary_email == "alice@example.com"
        assert researcher.is_active is True

    def test_create_persists_to_db(self, db):
        """create() persists the Researcher to the database."""
        institution = ResearcherFactory.build().institution
        institution.save()

        ResearcherProfileService.create(
            institution=institution,
            first_name="Bob",
            last_name="Jones",
            document_type="TI",
            document_number="9876543210",
            primary_email="bob@example.com",
        )

        assert Researcher.objects.filter(first_name="Bob", last_name="Jones").exists()


class TestResearcherProfileServiceUpdate:
    """ResearcherProfileService.update() — profile updates with completeness."""

    def test_update_researcher_fields(self, db):
        """update() modifies Researcher fields and returns updated instance."""
        researcher = ResearcherFactory()
        assert researcher.first_name != "Updated"

        updated = ResearcherProfileService.update(
            researcher,
            first_name="Updated",
            bio="New bio text",
        )

        assert updated.first_name == "Updated"
        assert updated.bio == "New bio text"
        # Fields not in the update dict should stay unchanged
        assert updated.last_name == researcher.last_name

    def test_update_saves_to_db(self, db):
        """update() persists changes to the database."""
        researcher = ResearcherFactory()
        original_name = researcher.first_name

        ResearcherProfileService.update(researcher, first_name="Changed")

        db_researcher = Researcher.objects.get(pk=researcher.pk)
        assert db_researcher.first_name == "Changed"
        assert db_researcher.first_name != original_name


class TestResearcherProfileServiceDeactivate:
    """ResearcherProfileService.deactivate() — profile deactivation."""

    def test_deactivate_sets_inactive(self, db):
        """deactivate() sets is_active=False on the Researcher."""
        researcher = ResearcherFactory(is_active=True)
        assert researcher.is_active is True

        updated = ResearcherProfileService.deactivate(researcher)
        assert updated.is_active is False

    def test_deactivate_persists(self, db):
        """deactivate() persists the inactive state to DB."""
        researcher = ResearcherFactory(is_active=True)

        ResearcherProfileService.deactivate(researcher)

        db_researcher = Researcher.objects.get(pk=researcher.pk)
        assert db_researcher.is_active is False

    def test_deactivate_persists_with_affiliations(self, db):
        """deactivate() sets is_active=False even when researcher has affiliations.

        Note: ResearcherAffiliation has no is_active field per the Phase 1 models.
        The design's "deactivate all affiliations" is satisfied by gating access
        through researcher.is_active at the queryset level.
        """
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)
        ResearcherAffiliation.objects.create(
            researcher=researcher,
            center=center,
            is_primary=True,
        )

        ResearcherProfileService.deactivate(researcher)

        db_researcher = Researcher.objects.get(pk=researcher.pk)
        assert db_researcher.is_active is False
        # Affiliations still exist but access gated by researcher.is_active
        assert ResearcherAffiliation.objects.filter(researcher=researcher).exists()


class TestResearcherProfileServiceCompleteness:
    """ResearcherProfileService.calculate_completeness() — mandatory field scoring."""

    def test_all_mandatory_fields_populated_score_100(self, db):
        """When all mandatory fields + 1 external profile exist → 100%."""
        researcher = ResearcherFactory(
            first_name="Alice",
            last_name="Smith",
            document_type="CC",
            document_number="12345",
            primary_email="alice@example.com",
        )
        ExternalProfileFactory(researcher=researcher, provider="cvlac")

        score = ResearcherProfileService.calculate_completeness(researcher)
        assert score == 100

    def test_missing_external_profile_reduces_score(self, db):
        """Missing external profile → score < 100."""
        researcher = ResearcherFactory(
            first_name="Bob",
            last_name="Jones",
            document_type="CC",
            document_number="67890",
            primary_email="bob@example.com",
        )
        # No ExternalProfile created

        score = ResearcherProfileService.calculate_completeness(researcher)
        assert score < 100

    def test_missing_first_name_reduces_score(self, db):
        """Missing mandatory field first_name → score < 100."""
        researcher = ResearcherFactory(
            first_name="",
            last_name="Smith",
            document_type="CC",
            document_number="54321",
            primary_email="alice@example.com",
        )
        ExternalProfileFactory(researcher=researcher, provider="cvlac")

        score = ResearcherProfileService.calculate_completeness(researcher)
        assert score < 100

    def test_missing_multiple_fields_calculates_correctly(self, db):
        """Multiple missing fields → score reflects fraction populated."""
        researcher = ResearcherFactory(
            first_name="",           # missing
            last_name="",            # missing
            document_type="CC",      # populated
            document_number="12345", # populated
            primary_email="",        # missing
        )
        # No external profile either → 2/6 mandatory = 33%

        score = ResearcherProfileService.calculate_completeness(researcher)
        # 2 populated out of 6 mandatory: first_name, last_name, doc_type,
        # doc_number, primary_email, external_profile
        assert score == 33  # (2/6) * 100 = 33

    def test_all_fields_but_no_profile_score_below_100(self, db):
        """All base fields populated but no external profile → score < 100."""
        researcher = ResearcherFactory(
            first_name="Carol",
            last_name="Davis",
            document_type="TI",
            document_number="11111",
            primary_email="carol@example.com",
        )
        # No ExternalProfile

        score = ResearcherProfileService.calculate_completeness(researcher)
        # 5/6 mandatory populated = 83%
        assert score == 83


# ──────────────────────────────────────────────
# ResearcherAffiliationService Tests
# ──────────────────────────────────────────────


class TestResearcherAffiliationServiceAdd:
    """ResearcherAffiliationService.add() — create affiliation with validation."""

    def test_add_affiliation_with_center(self, db):
        """add() creates an affiliation linking researcher to a center."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)

        affiliation = ResearcherAffiliationService.add(
            researcher=researcher,
            center=center,
        )

        assert affiliation.pk is not None
        assert affiliation.researcher == researcher
        assert affiliation.center == center
        # First affiliation is auto-set as primary (RN-AFF-02)
        assert affiliation.is_primary is True

    def test_add_affiliation_with_group(self, db):
        """add() creates an affiliation linking researcher to a group."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchGroupFactory
        group = ResearchGroupFactory(institution=researcher.institution)

        affiliation = ResearcherAffiliationService.add(
            researcher=researcher,
            group=group,
        )

        assert affiliation.group == group
        assert affiliation.center is None
        assert affiliation.line is None

    def test_add_affiliation_with_line(self, db):
        """add() creates an affiliation linking researcher to a line."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchLineFactory
        line = ResearchLineFactory(institution=researcher.institution)

        affiliation = ResearcherAffiliationService.add(
            researcher=researcher,
            line=line,
        )

        assert affiliation.line == line

    def test_add_primary_affiliation(self, db):
        """add() with is_primary=True sets primary affiliation."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)

        affiliation = ResearcherAffiliationService.add(
            researcher=researcher,
            center=center,
            is_primary=True,
        )

        assert affiliation.is_primary is True

    def test_add_rejects_no_fk(self, db):
        """add() rejects affiliation with no center/group/line set."""
        researcher = ResearcherFactory()

        with pytest.raises(ValidationError, match="must be set"):
            ResearcherAffiliationService.add(researcher=researcher)

    def test_add_rejects_cross_institution(self, db):
        """add() rejects affiliation where entity belongs to different institution."""
        researcher = ResearcherFactory()
        # Create a center in a DIFFERENT institution
        from apps.institutions.models import Institution
        other_inst = Institution.objects.create(name="Other", code="OTH")
        from apps.institutions.models import ResearchCenter
        other_center = ResearchCenter.objects.create(
            institution=other_inst, name="Other Center", code="OC"
        )

        with pytest.raises(ValidationError, match="does not belong"):
            ResearcherAffiliationService.add(
                researcher=researcher,
                center=other_center,
            )

    def test_add_first_affiliation_auto_primary(self, db):
        """First affiliation for a researcher is auto-set as primary if no is_primary given."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)

        # No existing affiliations — first one should get is_primary=True
        affiliation = ResearcherAffiliationService.add(
            researcher=researcher,
            center=center,
        )
        # The service should auto-set primary if it's the only affiliation
        # (Design implies one must be primary per RN-AFF-02)
        assert affiliation.is_primary is True


class TestResearcherAffiliationServiceRemove:
    """ResearcherAffiliationService.remove() — delete an affiliation."""

    def test_remove_deletes_affiliation(self, db):
        """remove() deletes the affiliation record."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)
        affiliation = ResearcherAffiliationService.add(
            researcher=researcher, center=center,
        )

        ResearcherAffiliationService.remove(affiliation)

        assert not ResearcherAffiliation.objects.filter(pk=affiliation.pk).exists()

    def test_remove_does_not_affect_researcher(self, db):
        """remove() deletes only the affiliation, not the researcher."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)
        affiliation = ResearcherAffiliationService.add(
            researcher=researcher, center=center,
        )

        ResearcherAffiliationService.remove(affiliation)

        assert Researcher.objects.filter(pk=researcher.pk).exists()


class TestResearcherAffiliationServiceSetPrimary:
    """ResearcherAffiliationService.set_primary() — atomic primary switch."""

    def test_set_primary_sets_is_primary_true(self, db):
        """set_primary() sets is_primary=True on the target affiliation."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)
        affiliation = ResearcherAffiliationService.add(
            researcher=researcher, center=center, is_primary=False,
        )

        updated = ResearcherAffiliationService.set_primary(affiliation)
        assert updated.is_primary is True

    def test_set_primary_unset_previous_primary(self, db):
        """set_primary() unsets the previous primary affiliation atomically."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center1 = ResearchCenterFactory(institution=researcher.institution)
        center2 = ResearchCenterFactory(institution=researcher.institution)

        primary = ResearcherAffiliationService.add(
            researcher=researcher, center=center1, is_primary=True,
        )
        secondary = ResearcherAffiliationService.add(
            researcher=researcher, center=center2, is_primary=False,
        )

        # Switch primary
        ResearcherAffiliationService.set_primary(secondary)

        # Old primary should be unset
        primary.refresh_from_db()
        assert primary.is_primary is False
        # New primary should be set
        secondary.refresh_from_db()
        assert secondary.is_primary is True

    def test_set_primary_already_primary_is_noop(self, db):
        """set_primary() on already-primary affiliation is a no-op."""
        researcher = ResearcherFactory()
        from apps.institutions.tests.conftest import ResearchCenterFactory
        center = ResearchCenterFactory(institution=researcher.institution)
        affiliation = ResearcherAffiliationService.add(
            researcher=researcher, center=center, is_primary=True,
        )

        updated = ResearcherAffiliationService.set_primary(affiliation)
        assert updated.is_primary is True
        # Should still be the only primary
        assert ResearcherAffiliation.objects.filter(
            researcher=researcher, is_primary=True
        ).count() == 1
