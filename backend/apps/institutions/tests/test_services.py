"""
Service layer tests for institutions app — STRICT TDD (RED phase).

Tests define expected behavior of InstitutionLifecycleService:
- activate: deactivated → active
- deactivate: active → deactivated (guard: no active children)
- archive: active|deactivated → archived (guard: no active children, terminal)
- Child resolution for all 6 entity types

Spec reference: openspec/changes/institutions/spec.md — RF-008
Design reference: openspec/changes/institutions/design.md — LifecycleService contract

RED PHASE: Tests fail because services.py does not exist.
"""

import pytest
from django.core.exceptions import ValidationError
from django_fsm import TransitionNotAllowed

from apps.institutions.models import (
    Institution,
    Sede,
    Facultad,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
)
from apps.institutions.services import InstitutionLifecycleService


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_institution(name="Test University", code="TU"):
    return Institution.objects.create(name=name, code=code)


def _make_sede(institution, name="Main Campus", code="MC"):
    return Sede.objects.create(institution=institution, name=name, code=code)


def _make_facultad(institution, name="Engineering", code="ENG", sede=None):
    return Facultad.objects.create(institution=institution, name=name, code=code, sede=sede)


def _make_center(institution, name="AI Lab", code="AI", sede=None, facultad=None):
    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code, sede=sede, facultad=facultad,
    )


def _make_group(institution, center, name="NLP", code="NLP"):
    return ResearchGroup.objects.create(institution=institution, center=center, name=name, code=code)


def _make_line(institution, group, name="SA", code="SA"):
    return ResearchLine.objects.create(institution=institution, group=group, name=name, code=code)


# ──────────────────────────────────────────────
# Institution Lifecycle Tests
# ──────────────────────────────────────────────


class TestInstitutionLifecycle:
    """Institution-level lifecycle transitions via the service."""

    def test_activate_from_deactivated(self, db):
        """Service.activate() transitions deactivated → active."""
        inst = _make_institution()
        inst.deactivate()  # bypass service to set up state
        inst.save()
        assert inst.status == "deactivated"

        updated = InstitutionLifecycleService.activate(inst)
        assert updated.status == "active"
        assert updated.is_active is True

    def test_deactivate_without_children(self, db):
        """Service.deactivate() transitions active → deactivated when no children."""
        inst = _make_institution()
        assert inst.status == "active"

        updated = InstitutionLifecycleService.deactivate(inst)
        assert updated.status == "deactivated"
        assert updated.is_active is False

    def test_deactivate_blocked_by_active_sede(self, db):
        """Service.deactivate() rejects if institution has active Sedes."""
        inst = _make_institution()
        _make_sede(inst, name="Campus", code="C1")  # active by default

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(inst)

    def test_deactivate_blocked_by_active_center(self, db):
        """Service.deactivate() rejects if institution has active ResearchCenters."""
        inst = _make_institution()
        _make_center(inst, name="Lab", code="L1")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(inst)

    def test_deactivate_allowed_after_children_deactivated(self, db):
        """Service.deactivate() succeeds after all children are deactivated."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")
        # deactivate the child first
        InstitutionLifecycleService.deactivate(sede)
        assert sede.status == "deactivated"

        # now parent can be deactivated
        updated = InstitutionLifecycleService.deactivate(inst)
        assert updated.status == "deactivated"

    def test_archive_from_active_without_children(self, db):
        """Service.archive() transitions active → archived when no children."""
        inst = _make_institution()

        updated = InstitutionLifecycleService.archive(inst)
        assert updated.status == "archived"
        assert updated.is_active is False

    def test_archive_from_deactivated(self, db):
        """Service.archive() transitions deactivated → archived."""
        inst = _make_institution()
        InstitutionLifecycleService.deactivate(inst)
        assert inst.status == "deactivated"

        updated = InstitutionLifecycleService.archive(inst)
        assert updated.status == "archived"

    def test_archive_blocked_by_active_children(self, db):
        """Service.archive() rejects if institution has active children."""
        inst = _make_institution()
        _make_sede(inst, name="Campus", code="C1")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.archive(inst)

    def test_activate_on_already_active_raises(self, db):
        """Service.activate() on active entity raises TransitionNotAllowed."""
        inst = _make_institution()
        with pytest.raises(TransitionNotAllowed):
            InstitutionLifecycleService.activate(inst)

    def test_archived_is_terminal(self, db):
        """Archived entity cannot transition further."""
        inst = _make_institution()
        InstitutionLifecycleService.archive(inst)
        with pytest.raises(TransitionNotAllowed):
            InstitutionLifecycleService.activate(inst)
        with pytest.raises(TransitionNotAllowed):
            InstitutionLifecycleService.deactivate(inst)


# ──────────────────────────────────────────────
# Sede Lifecycle Tests
# ──────────────────────────────────────────────


class TestSedeLifecycle:
    """Sede-level lifecycle transitions."""

    def test_deactivate_without_children(self, db):
        """Sede without facultades or centers can be deactivated."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")

        updated = InstitutionLifecycleService.deactivate(sede)
        assert updated.status == "deactivated"

    def test_deactivate_blocked_by_active_center(self, db):
        """Sede with active ResearchCenter cannot be deactivated."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")
        _make_center(inst, name="Lab", code="L1", sede=sede)

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(sede)

    def test_deactivate_blocked_by_active_facultad(self, db):
        """Sede with active Facultad cannot be deactivated."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")
        _make_facultad(inst, name="Engineering", code="ENG", sede=sede)

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(sede)

    def test_archive_sede(self, db):
        """Sede can be archived (terminal)."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")

        updated = InstitutionLifecycleService.archive(sede)
        assert updated.status == "archived"


# ──────────────────────────────────────────────
# Facultad Lifecycle Tests
# ──────────────────────────────────────────────


class TestFacultadLifecycle:
    """Facultad-level lifecycle transitions."""

    def test_deactivate_without_children(self, db):
        """Facultad without centers can be deactivated."""
        inst = _make_institution()
        facultad = _make_facultad(inst, name="Science", code="SCI")

        updated = InstitutionLifecycleService.deactivate(facultad)
        assert updated.status == "deactivated"

    def test_deactivate_blocked_by_active_center(self, db):
        """Facultad with active ResearchCenter cannot be deactivated."""
        inst = _make_institution()
        facultad = _make_facultad(inst, name="Science", code="SCI")
        _make_center(inst, name="Lab", code="L1", facultad=facultad)

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(facultad)

    def test_activate(self, db):
        """Facultad can be reactivated."""
        inst = _make_institution()
        facultad = _make_facultad(inst, name="Science", code="SCI")
        InstitutionLifecycleService.deactivate(facultad)

        updated = InstitutionLifecycleService.activate(facultad)
        assert updated.status == "active"
        assert updated.is_active is True


# ──────────────────────────────────────────────
# ResearchCenter Lifecycle Tests
# ──────────────────────────────────────────────


class TestResearchCenterLifecycle:
    """ResearchCenter-level lifecycle transitions."""

    def test_deactivate_without_groups(self, db):
        """Center without groups can be deactivated."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")

        updated = InstitutionLifecycleService.deactivate(center)
        assert updated.status == "deactivated"

    def test_deactivate_blocked_by_active_group(self, db):
        """Center with active ResearchGroup cannot be deactivated."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        _make_group(inst, center, name="NLP", code="NLP")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(center)

    def test_archive_blocked_by_active_group(self, db):
        """Center with active group cannot be archived."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        _make_group(inst, center, name="NLP", code="NLP")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.archive(center)


# ──────────────────────────────────────────────
# ResearchGroup Lifecycle Tests
# ──────────────────────────────────────────────


class TestResearchGroupLifecycle:
    """ResearchGroup-level lifecycle transitions."""

    def test_deactivate_without_lines(self, db):
        """Group without lines can be deactivated."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = _make_group(inst, center, name="NLP", code="NLP")

        updated = InstitutionLifecycleService.deactivate(group)
        assert updated.status == "deactivated"

    def test_deactivate_blocked_by_active_line(self, db):
        """Group with active ResearchLine cannot be deactivated."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = _make_group(inst, center, name="NLP", code="NLP")
        _make_line(inst, group, name="Sentiment", code="SA")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(group)


# ──────────────────────────────────────────────
# ResearchLine Lifecycle Tests (Leaf)
# ──────────────────────────────────────────────


class TestResearchLineLifecycle:
    """ResearchLine is the leaf — no children exist."""

    def test_deactivate_always_allowed(self, db):
        """Line has no children — deactivate always succeeds."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = _make_group(inst, center, name="NLP", code="NLP")
        line = _make_line(inst, group, name="Sentiment", code="SA")

        updated = InstitutionLifecycleService.deactivate(line)
        assert updated.status == "deactivated"

    def test_archive_line(self, db):
        """Line can be archived (terminal)."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = _make_group(inst, center, name="NLP", code="NLP")
        line = _make_line(inst, group, name="Sentiment", code="SA")

        updated = InstitutionLifecycleService.archive(line)
        assert updated.status == "archived"

    def test_reactivate_line(self, db):
        """Line can be reactivated from deactivated."""
        inst = _make_institution()
        center = _make_center(inst, name="AI Lab", code="AI")
        group = _make_group(inst, center, name="NLP", code="NLP")
        line = _make_line(inst, group, name="Sentiment", code="SA")
        InstitutionLifecycleService.deactivate(line)

        updated = InstitutionLifecycleService.activate(line)
        assert updated.status == "active"
        assert updated.is_active is True


# ──────────────────────────────────────────────
# Institution-specific child scope test
# ──────────────────────────────────────────────


class TestInstitutionChildScope:
    """Institution checks ALL direct children (Sede, Facultad, Center)."""

    def test_deactivate_blocked_by_direct_facultad(self, db):
        """Institution with active Facultad (no sede) blocks deactivate."""
        inst = _make_institution()
        _make_facultad(inst, name="Science", code="SCI")

        with pytest.raises(ValidationError, match="children first"):
            InstitutionLifecycleService.deactivate(inst)

    def test_only_active_children_block(self, db):
        """Deactivated children do not block parent deactivation."""
        inst = _make_institution()
        sede = _make_sede(inst, name="Campus", code="C1")
        InstitutionLifecycleService.deactivate(sede)  # child is deactivated
        _make_facultad(inst, name="Science", code="SCI")
        InstitutionLifecycleService.deactivate(
            Facultad.objects.get(code="SCI")
        )

        # now both children are deactivated, parent can deactivate
        updated = InstitutionLifecycleService.deactivate(inst)
        assert updated.status == "deactivated"
