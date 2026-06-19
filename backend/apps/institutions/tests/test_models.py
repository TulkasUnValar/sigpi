"""
Model tests for institutions app — STRICT TDD.

Tests define the expected behavior of the 6-entity hierarchy:
Institution, Sede, Facultad, ResearchCenter, ResearchGroup, ResearchLine.

Spec reference: openspec/changes/institutions/spec.md
Design reference: openspec/changes/institutions/design.md

RED PHASE: All tests will fail because models don't have new fields/transitions yet.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_fsm import TransitionNotAllowed

from apps.institutions.models import (
    Institution,
    Sede,
    Facultad,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(name="Test University", code="TU"):
    return Institution.objects.create(name=name, code=code)


def _make_sede(institution, name="Main Campus", code="MC"):
    return Sede.objects.create(
        institution=institution, name=name, code=code,
    )


def _make_center(institution, name="Research Center", code="RC"):
    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code,
    )


# ──────────────────────────────────────────────
# Institution Model Tests
# ──────────────────────────────────────────────


class TestInstitutionFields:
    """Institution model expanded fields."""

    def test_defaults(self, db):
        """New Institution starts with status='active' and is_active=True."""
        inst = _make_institution()
        assert inst.status == "active"
        assert inst.is_active is True
        assert inst.description == ""
        assert inst.address == ""

    def test_optional_fields(self, db):
        """Optional fields can be set on creation."""
        inst = Institution.objects.create(
            name="Test",
            code="T",
            description="A research university",
            address="123 Academic St",
            contact_email="info@test.edu",
            contact_phone="+1-555-0100",
            logo_url="https://test.edu/logo.png",
        )
        assert inst.description == "A research university"
        assert inst.address == "123 Academic St"
        assert inst.contact_email == "info@test.edu"
        assert inst.contact_phone == "+1-555-0100"
        assert inst.logo_url == "https://test.edu/logo.png"

    def test_str_representation(self, db):
        """Institution __str__ returns name."""
        inst = _make_institution()
        assert str(inst) == "Test University"


class TestInstitutionFSM:
    """Institution FSM lifecycle transitions."""

    def test_default_status_active(self, db):
        """New institution starts in 'active' status."""
        inst = _make_institution()
        assert inst.status == "active"

    def test_deactivate_transition(self, db):
        """active → deactivated is a valid transition."""
        inst = _make_institution()
        inst.deactivate()
        assert inst.status == "deactivated"

    def test_reactivate_from_deactivated(self, db):
        """deactivated → active is a valid transition."""
        inst = _make_institution()
        inst.deactivate()
        inst.activate()
        assert inst.status == "active"

    def test_archive_from_active(self, db):
        """active → archived is a valid (terminal) transition."""
        inst = _make_institution()
        inst.archive()
        assert inst.status == "archived"

    def test_archive_from_deactivated(self, db):
        """deactivated → archived is a valid (terminal) transition."""
        inst = _make_institution()
        inst.deactivate()
        inst.archive()
        assert inst.status == "archived"

    def test_cannot_deactivate_archived(self, db):
        """Archived is terminal — cannot transition from it."""
        inst = _make_institution()
        inst.archive()
        with pytest.raises(TransitionNotAllowed):
            inst.deactivate()

    def test_cannot_activate_archived(self, db):
        """Archived is terminal — cannot transition from it."""
        inst = _make_institution()
        inst.archive()
        with pytest.raises(TransitionNotAllowed):
            inst.activate()

    def test_cannot_deactivate_already_deactivated(self, db):
        """deactivated → deactivated is an invalid transition."""
        inst = _make_institution()
        inst.deactivate()
        with pytest.raises(TransitionNotAllowed):
            inst.deactivate()

    def test_cannot_activate_already_active(self, db):
        """active → active is an invalid transition."""
        inst = _make_institution()
        with pytest.raises(TransitionNotAllowed):
            inst.activate()


# ──────────────────────────────────────────────
# Sede Model Tests
# ──────────────────────────────────────────────


class TestSedeFields:
    """Sede model field behavior."""

    def test_create_sede(self, db):
        """A Sede belongs to an Institution with name and code."""
        inst = _make_institution()
        sede = _make_sede(inst, name="North Campus", code="NC")
        assert sede.id is not None
        assert sede.institution == inst
        assert sede.name == "North Campus"
        assert sede.code == "NC"
        assert sede.status == "active"
        assert sede.description == ""

    def test_sede_str(self, db):
        """Sede __str__ includes name and institution code."""
        inst = _make_institution(code="TU")
        sede = _make_sede(inst, name="Main Campus", code="MC")
        expected = f"Main Campus (TU)"
        assert str(sede) == expected

    def test_institution_code_unique(self, db):
        """(institution, code) must be unique for Sede."""
        inst_a = _make_institution(name="Uni A", code="UA")
        inst_b = _make_institution(name="Uni B", code="UB")
        _make_sede(inst_a, name="Campus A", code="S1")
        # Same code, same institution → should fail
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_sede(inst_a, name="Campus A2", code="S1")
        # Same code, different institution → allowed
        _make_sede(inst_b, name="Campus B", code="S1")
        assert Sede.objects.filter(code="S1").count() == 2

    def test_cascade_delete_institution(self, db):
        """Deleting an Institution cascades to its Sedes."""
        inst = _make_institution()
        _make_sede(inst, name="A", code="A")
        _make_sede(inst, name="B", code="B")
        assert Sede.objects.count() == 2
        inst.delete()
        assert Sede.objects.count() == 0


class TestSedeFSM:
    """Sede FSM lifecycle transitions."""

    def test_default_status(self, db):
        inst = _make_institution()
        sede = _make_sede(inst)
        assert sede.status == "active"

    def test_deactivate(self, db):
        inst = _make_institution()
        sede = _make_sede(inst)
        sede.deactivate()
        assert sede.status == "deactivated"

    def test_reactivate(self, db):
        inst = _make_institution()
        sede = _make_sede(inst)
        sede.deactivate()
        sede.activate()
        assert sede.status == "active"

    def test_archive(self, db):
        inst = _make_institution()
        sede = _make_sede(inst)
        sede.archive()
        assert sede.status == "archived"

    def test_archived_is_terminal(self, db):
        inst = _make_institution()
        sede = _make_sede(inst)
        sede.archive()
        with pytest.raises(TransitionNotAllowed):
            sede.activate()


# ──────────────────────────────────────────────
# Facultad Model Tests
# ──────────────────────────────────────────────


class TestFacultadFields:
    """Facultad model field behavior."""

    def test_create_facultad_without_sede(self, db):
        """A Facultad can be created without a Sede."""
        inst = _make_institution()
        facultad = Facultad.objects.create(
            institution=inst, name="Engineering", code="ENG",
        )
        assert facultad.sede is None
        assert facultad.institution == inst
        assert facultad.status == "active"

    def test_create_facultad_with_sede(self, db):
        """A Facultad can be linked to a Sede."""
        inst = _make_institution()
        sede = _make_sede(inst, name="North", code="N")
        facultad = Facultad.objects.create(
            institution=inst, sede=sede, name="Engineering", code="ENG",
        )
        assert facultad.sede == sede

    def test_facultad_str(self, db):
        """Facultad __str__ includes name and institution code."""
        inst = _make_institution(code="TU")
        facultad = Facultad.objects.create(
            institution=inst, name="Engineering", code="ENG",
        )
        assert str(facultad) == "Engineering (TU)"

    def test_institution_code_unique(self, db):
        """(institution, code) unique per Facultad."""
        inst = _make_institution()
        Facultad.objects.create(
            institution=inst, name="A", code="F1",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Facultad.objects.create(
                    institution=inst, name="B", code="F1",
                )

    def test_sede_must_belong_to_same_institution(self, db):
        """clean() rejects a sede from a different institution."""
        inst_a = _make_institution(name="A", code="A")
        inst_b = _make_institution(name="B", code="B")
        sede_b = _make_sede(inst_b, name="B Sede", code="BS")
        facultad = Facultad(
            institution=inst_a, sede=sede_b, name="Bad", code="BAD",
        )
        with pytest.raises(ValidationError, match="different institution"):
            facultad.full_clean()

    def test_cascade_delete(self, db):
        """Deleting Institution cascades to Facultades."""
        inst = _make_institution()
        Facultad.objects.create(institution=inst, name="A", code="A")
        Facultad.objects.create(institution=inst, name="B", code="B")
        assert Facultad.objects.count() == 2
        inst.delete()
        assert Facultad.objects.count() == 0


# ──────────────────────────────────────────────
# ResearchCenter Model Tests
# ──────────────────────────────────────────────


class TestResearchCenterExpandedFields:
    """ResearchCenter expanded fields from stub."""

    def test_new_optional_fields(self, db):
        """ResearchCenter gains description, contact_email, contact_phone, status."""
        inst = _make_institution()
        center = ResearchCenter.objects.create(
            institution=inst,
            name="AI Lab",
            code="AILAB",
            description="Artificial Intelligence research",
            contact_email="ailab@test.edu",
            contact_phone="+1-555-0200",
        )
        assert center.description == "Artificial Intelligence research"
        assert center.contact_email == "ailab@test.edu"
        assert center.contact_phone == "+1-555-0200"
        assert center.status == "active"

    def test_code_no_longer_blank(self, db):
        """code is now required (no longer blank=True from stub)."""
        inst = _make_institution()
        center = ResearchCenter(institution=inst, name="Test", code="")
        with pytest.raises(ValidationError):
            center.full_clean()

    def test_flexible_parenting_sede(self, db):
        """ResearchCenter can link to a Sede (optional FK)."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")
        center = ResearchCenter.objects.create(
            institution=inst, name="Lab", code="L1", sede=sede,
        )
        assert center.sede == sede
        assert center.facultad is None

    def test_flexible_parenting_facultad(self, db):
        """ResearchCenter can link to a Facultad (optional FK)."""
        inst = _make_institution()
        facultad = Facultad.objects.create(
            institution=inst, name="Science", code="SCI",
        )
        center = ResearchCenter.objects.create(
            institution=inst, name="Bio Lab", code="BIO",
            facultad=facultad,
        )
        assert center.facultad == facultad
        assert center.sede is None

    def test_institution_code_unique(self, db):
        """(institution, code) must be unique for ResearchCenter."""
        inst = _make_institution()
        _make_center(inst, name="C1", code="X")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _make_center(inst, name="C2", code="X")

    def test_parent_must_belong_to_same_institution(self, db):
        """clean() rejects sede/facultad from different institution."""
        inst_a = _make_institution(name="A", code="A")
        inst_b = _make_institution(name="B", code="B")
        sede_b = _make_sede(inst_b, name="B Sede", code="BS")
        center = ResearchCenter(
            institution=inst_a, name="Bad", code="BAD", sede=sede_b,
        )
        with pytest.raises(ValidationError, match="different institution"):
            center.full_clean()

    def test_str_representation(self, db):
        """ResearchCenter __str__ includes name and institution code."""
        inst = _make_institution(code="TU")
        center = _make_center(inst, name="AI Lab", code="AI")
        assert str(center) == "AI Lab (TU)"


class TestResearchCenterFSM:
    """ResearchCenter FSM lifecycle transitions."""

    def test_default_status(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        assert center.status == "active"

    def test_deactivate_transition(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        center.deactivate()
        assert center.status == "deactivated"

    def test_archive_transition(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        center.archive()
        assert center.status == "archived"

    def test_reactivate(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        center.deactivate()
        center.activate()
        assert center.status == "active"

    def test_archived_is_terminal(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        center.archive()
        with pytest.raises(TransitionNotAllowed):
            center.activate()


# ──────────────────────────────────────────────
# ResearchGroup Model Tests
# ──────────────────────────────────────────────


class TestResearchGroupFields:
    """ResearchGroup model field behavior."""

    def test_create_group(self, db):
        """ResearchGroup belongs to Institution and ResearchCenter."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = ResearchGroup.objects.create(
            institution=inst,
            center=center,
            name="NLP Group",
            code="NLP",
        )
        assert group.institution == inst
        assert group.center == center
        assert group.name == "NLP Group"
        assert group.code == "NLP"
        assert group.status == "active"

    def test_group_str(self, db):
        """ResearchGroup __str__ includes name and institution code."""
        inst = _make_institution(code="TU")
        center = _make_center(inst, name="AI Lab", code="AI")
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="NLP", code="NLP",
        )
        assert str(group) == "NLP (TU)"

    def test_institution_code_unique(self, db):
        """(institution, code) must be unique for Group."""
        inst = _make_institution()
        center = _make_center(inst, name="C", code="C")
        ResearchGroup.objects.create(
            institution=inst, center=center, name="G1", code="GX",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ResearchGroup.objects.create(
                    institution=inst, center=center, name="G2", code="GX",
                )

    def test_center_must_match_institution(self, db):
        """Group institution must match center's institution."""
        inst_a = _make_institution(name="A", code="A")
        inst_b = _make_institution(name="B", code="B")
        center_b = _make_center(inst_b, name="B Center", code="BC")
        group = ResearchGroup(
            institution=inst_a, center=center_b, name="Bad", code="BAD",
        )
        with pytest.raises(ValidationError, match="different institution"):
            group.full_clean()


class TestResearchGroupFSM:
    """ResearchGroup FSM lifecycle transitions."""

    def test_default_status(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        assert group.status == "active"

    def test_deactivate(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        group.deactivate()
        assert group.status == "deactivated"

    def test_archive(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        group.archive()
        assert group.status == "archived"

    def test_archived_is_terminal(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        group.archive()
        with pytest.raises(TransitionNotAllowed):
            group.activate()


# ──────────────────────────────────────────────
# ResearchLine Model Tests
# ──────────────────────────────────────────────


class TestResearchLineFields:
    """ResearchLine model field behavior."""

    def test_create_line(self, db):
        """ResearchLine belongs to Institution and ResearchGroup."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="NLP", code="NLP",
        )
        line = ResearchLine.objects.create(
            institution=inst,
            group=group,
            name="Sentiment Analysis",
            code="SA",
        )
        assert line.institution == inst
        assert line.group == group
        assert line.name == "Sentiment Analysis"
        assert line.code == "SA"
        assert line.status == "active"

    def test_line_str(self, db):
        """ResearchLine __str__ includes name and institution code."""
        inst = _make_institution(code="TU")
        center = _make_center(inst, name="AI Lab", code="AI")
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="NLP", code="NLP",
        )
        line = ResearchLine.objects.create(
            institution=inst, group=group, name="Sentiment", code="SA",
        )
        assert str(line) == "Sentiment (TU)"

    def test_institution_code_unique(self, db):
        """(institution, code) must be unique for Line."""
        inst = _make_institution()
        center = _make_center(inst, name="C", code="C")
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        ResearchLine.objects.create(
            institution=inst, group=group, name="L1", code="LX",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ResearchLine.objects.create(
                    institution=inst, group=group, name="L2", code="LX",
                )

    def test_group_must_match_institution(self, db):
        """Line institution must match group's institution."""
        inst_a = _make_institution(name="A", code="A")
        inst_b = _make_institution(name="B", code="B")
        center_b = _make_center(inst_b, name="BC", code="BC")
        group_b = ResearchGroup.objects.create(
            institution=inst_b, center=center_b, name="B Group", code="BG",
        )
        line = ResearchLine(
            institution=inst_a, group=group_b, name="Bad", code="BAD",
        )
        with pytest.raises(ValidationError, match="different institution"):
            line.full_clean()


class TestResearchLineFSM:
    """ResearchLine FSM lifecycle transitions."""

    def test_default_status(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        line = ResearchLine.objects.create(
            institution=inst, group=group, name="L", code="L",
        )
        assert line.status == "active"

    def test_deactivate(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        line = ResearchLine.objects.create(
            institution=inst, group=group, name="L", code="L",
        )
        line.deactivate()
        assert line.status == "deactivated"

    def test_archive(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        line = ResearchLine.objects.create(
            institution=inst, group=group, name="L", code="L",
        )
        line.archive()
        assert line.status == "archived"

    def test_archived_is_terminal(self, db):
        inst = _make_institution()
        center = _make_center(inst)
        group = ResearchGroup.objects.create(
            institution=inst, center=center, name="G", code="G",
        )
        line = ResearchLine.objects.create(
            institution=inst, group=group, name="L", code="L",
        )
        line.archive()
        with pytest.raises(TransitionNotAllowed):
            line.activate()
