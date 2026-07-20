"""
Model tests for projects app — STRICT TDD.

Tests define the expected behavior of the 5-entity project module:
Project, ProjectMember, ProjectDocument, ProjectObservation, ProjectStateLog.

Spec reference:  openspec/changes/projects/spec.md
Design reference: openspec/changes/projects/design.md

RED PHASE: All tests fail because models are empty stubs.
"""
import datetime
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django_fsm import TransitionNotAllowed

from apps.projects.models import (
    TERMINAL_STATES,
    Project,
    ProjectDocument,
    ProjectDocumentType,
    ProjectMember,
    ProjectObservation,
    ProjectRole,
    ProjectStateLog,
    ProjectStatus,
)

# ──────────────────────────────────────────────
# Helpers (mirror researchers test pattern)
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(
        name=f"Test University {code}", code=code,
    )


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code,
    )


def _make_group(institution, center, name="NLP Group", code="NLP"):
    from apps.institutions.models import ResearchGroup

    return ResearchGroup.objects.create(
        institution=institution, center=center, name=name, code=code,
    )


def _make_line(institution, group, name="Sentiment", code="SA"):
    from apps.institutions.models import ResearchLine

    return ResearchLine.objects.create(
        institution=institution, group=group, name=name, code=code,
    )


def _make_researcher(institution, user=None):
    import uuid as _uuid

    from apps.researchers.models import Researcher

    return Researcher.objects.create(
        institution=institution,
        user=user,
        first_name="Maria",
        last_name="Gomez",
        document_type="CC",
        document_number=f"DN-{_uuid.uuid4().hex[:8]}",
        primary_email=f"maria.{_uuid.uuid4().hex[:4]}@test.edu",
    )


def _make_affiliation(researcher, center):
    from apps.researchers.models import ResearcherAffiliation

    return ResearcherAffiliation.objects.create(
        researcher=researcher, center=center, is_primary=True,
    )


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestProjectStatusEnum:
    """ProjectStatus TextChoices has 12 states."""

    def test_all_twelve_states_defined(self):
        """All 12 FSM states are present in ProjectStatus."""
        expected = {
            "borrador", "enviado", "en_revision", "observado",
            "aprobado", "en_ejecucion", "suspendido", "finalizado",
            "en_cierre", "cerrado", "rechazado", "cancelado",
        }
        actual = {choice[0] for choice in ProjectStatus.choices}
        assert actual == expected

    def test_terminal_states_constant(self):
        """TERMINAL_STATES contains cerrado, rechazado, cancelado."""
        assert ProjectStatus.CERRADO in TERMINAL_STATES
        assert ProjectStatus.RECHAZADO in TERMINAL_STATES
        assert ProjectStatus.CANCELADO in TERMINAL_STATES
        assert ProjectStatus.BORRADOR not in TERMINAL_STATES


class TestProjectRoleEnum:
    """ProjectRole TextChoices has 4 roles."""

    def test_all_four_roles_defined(self):
        expected = {"co_investigator", "student", "seedbed", "collaborator"}
        actual = {choice[0] for choice in ProjectRole.choices}
        assert actual == expected


class TestProjectDocumentTypeEnum:
    """ProjectDocumentType TextChoices has 5 types."""

    def test_all_five_types_defined(self):
        expected = {"proposal", "annex", "contract", "report", "other"}
        actual = {choice[0] for choice in ProjectDocumentType.choices}
        assert actual == expected


# ──────────────────────────────────────────────
# Project Model Field Tests
# ──────────────────────────────────────────────


class TestProjectFields:
    """Project model field behavior and defaults."""

    def test_create_project_minimal(self, db):
        """Project can be created with required fields, defaults to borrador."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test Project",
            abstract="An abstract",
            objectives="Objectives text",
            methodology="Methodology text",
            expected_results="Expected results text",
            keywords="ai, nlp",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
        )
        assert project.id is not None
        assert isinstance(project.id, uuid.UUID)
        assert project.institution == inst
        assert project.center == center
        assert project.principal_investigator == pi
        assert project.status == "borrador"
        assert project.is_active is True
        assert project.title == "Test Project"
        assert project.actual_end_date is None

    def test_optional_group_and_line(self, db):
        """group and line are nullable — project can be created without them."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            keywords="",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        assert project.group is None
        assert project.line is None

    def test_str_representation(self, db):
        """Project __str__ returns the title."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="AI Research", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        assert str(project) == "AI Research"

    def test_timestamps_auto_set(self, db):
        """created_at and updated_at are set automatically."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        assert project.created_at is not None
        assert project.updated_at is not None


# ──────────────────────────────────────────────
# Project clean() Validation Tests
# ──────────────────────────────────────────────


class TestProjectCleanValidation:
    """Project.clean() enforces RN-007, RN-008, RN-013, hierarchy integrity."""

    def test_clean_rejects_missing_pi(self, db):
        """RN-007: principal_investigator must be non-null."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=None,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_rejects_missing_center(self, db):
        """RN-008: center must be non-null."""
        inst = _make_institution("TU")
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=None,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_rejects_end_date_before_start_date(self, db):
        """RN-013: estimated_end_date must be >= start_date."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 6, 1),
            estimated_end_date=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_rejects_actual_end_date_before_start_date(self, db):
        """RN-013: actual_end_date must be >= start_date if set."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 6, 1),
            estimated_end_date=datetime.date(2026, 12, 1),
            actual_end_date=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_accepts_valid_dates(self, db):
        """RN-013: valid dates pass clean() without error."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
            actual_end_date=datetime.date(2026, 12, 31),
        )
        project.full_clean()  # should not raise

    def test_clean_rejects_group_wrong_center(self, db):
        """Hierarchy: group must belong to the same center chain."""
        inst = _make_institution("TU")
        center_a = _make_center(inst, name="Center A", code="CA")
        center_b = _make_center(inst, name="Center B", code="CB")
        group_b = _make_group(inst, center_b, name="Group B", code="GB")
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center_a,
            group=group_b,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_rejects_line_wrong_chain(self, db):
        """Hierarchy: line must belong to same center chain."""
        inst = _make_institution("TU")
        center_a = _make_center(inst, name="Center A", code="CA")
        center_b = _make_center(inst, name="Center B", code="CB")
        group_b = _make_group(inst, center_b, name="Group B", code="GB")
        line_b = _make_line(inst, group_b, name="Line B", code="LB")
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center_a,
            line=line_b,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
        )
        with pytest.raises(ValidationError):
            project.full_clean()

    def test_clean_accepts_valid_group_chain(self, db):
        """Hierarchy: valid group in same center chain passes clean()."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        group = _make_group(inst, center)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            group=group,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
        )
        project.full_clean()  # should not raise

    def test_clean_accepts_valid_line_chain(self, db):
        """Hierarchy: valid line in same center chain passes clean()."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        group = _make_group(inst, center)
        line = _make_line(inst, group)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            group=group,
            line=line,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 12, 31),
        )
        project.full_clean()  # should not raise


# ──────────────────────────────────────────────
# Project DB CHECK Constraint Tests
# ──────────────────────────────────────────────


class TestProjectCheckConstraints:
    """DB CHECK constraints enforce date integrity at database level.

    Since save() calls full_clean(), Clean Validation catches date issues
    before the DB CHECK constraints fire on SQLite. These tests verify
    the constraint metadata and Django-level constraint validation.
    """

    def test_check_constraints_exist(self):
        """Both CHECK constraints are registered in Meta.constraints."""
        constraint_names = {
            c.name for c in Project._meta.constraints
        }
        assert "check_estimated_end_date_gte_start_date" in constraint_names
        assert "check_actual_end_date_gte_start_date" in constraint_names

    def test_validate_constraints_rejects_end_before_start(self, db):
        """Django validate_constraints() catches estimated_end_date < start_date."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 12, 1),
            estimated_end_date=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            project.validate_constraints()

    def test_validate_constraints_rejects_actual_end_before_start(self, db):
        """Django validate_constraints() catches actual_end_date < start_date."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project(
            institution=inst,
            center=center,
            principal_investigator=pi,
            title="Test",
            abstract="A",
            objectives="O",
            methodology="M",
            expected_results="E",
            start_date=datetime.date(2026, 12, 1),
            estimated_end_date=datetime.date(2026, 12, 15),
            actual_end_date=datetime.date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            project.validate_constraints()


# ──────────────────────────────────────────────
# ProjectMember Tests
# ──────────────────────────────────────────────


class TestProjectMemberFields:
    """ProjectMember model field behavior and constraints."""

    def test_create_member(self, db):
        """ProjectMember links a Researcher to a Project with a role."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        member = ProjectMember.objects.create(
            project=project,
            researcher=pi,
            role="co_investigator",
        )
        assert member.project == project
        assert member.researcher == pi
        assert member.role == "co_investigator"
        assert member.joined_at is not None

    def test_unique_project_researcher(self, db):
        """UniqueConstraint (project, researcher) enforced."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        researcher2 = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        ProjectMember.objects.create(
            project=project, researcher=researcher2, role="student",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProjectMember.objects.create(
                    project=project, researcher=researcher2, role="collaborator",
                )

    def test_role_choices_valid(self, db):
        """All ProjectRole choices are valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        for role in ("co_investigator", "student", "seedbed", "collaborator"):
            member = ProjectMember(
                project=project, researcher=pi, role=role,
            )
            member.full_clean()  # should not raise

    def test_role_invalid_choice(self, db):
        """Invalid role raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        member = ProjectMember(
            project=project, researcher=pi, role="invalid_role",
        )
        with pytest.raises(ValidationError):
            member.full_clean()

    def test_str_representation(self, db):
        """ProjectMember __str__ includes researcher and role."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        member = ProjectMember.objects.create(
            project=project, researcher=pi, role="co_investigator",
        )
        assert str(pi) in str(member)


# ──────────────────────────────────────────────
# ProjectDocument Tests
# ──────────────────────────────────────────────


class TestProjectDocumentFields:
    """ProjectDocument model field behavior."""

    def test_create_document(self, db):
        """ProjectDocument stores name, type, and external URL (RF-036)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        doc = ProjectDocument.objects.create(
            project=project,
            name="Proposal v1.pdf",
            doc_type="proposal",
            external_url="https://storage.example.com/proposal.pdf",
        )
        assert doc.name == "Proposal v1.pdf"
        assert doc.doc_type == "proposal"
        assert doc.external_url == "https://storage.example.com/proposal.pdf"
        assert doc.project == project
        assert doc.uploaded_at is not None

    def test_doc_type_choices_valid(self, db):
        """All ProjectDocumentType choices are valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        for dtype in ("proposal", "annex", "contract", "report", "other"):
            doc = ProjectDocument(
                project=project,
                name=f"doc.{dtype}",
                doc_type=dtype,
                external_url=f"https://example.com/{dtype}",
            )
            doc.full_clean()  # should not raise

    def test_doc_type_invalid_choice(self, db):
        """Invalid doc_type raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        doc = ProjectDocument(
            project=project,
            name="file.txt",
            doc_type="invalid",
            external_url="https://example.com/file.txt",
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_str_representation(self, db):
        """ProjectDocument __str__ includes name and type."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        doc = ProjectDocument.objects.create(
            project=project, name="Proposal.pdf", doc_type="proposal",
            external_url="https://example.com/proposal.pdf",
        )
        assert "Proposal.pdf" in str(doc)


# ──────────────────────────────────────────────
# ProjectObservation Tests
# ──────────────────────────────────────────────


class TestProjectObservationFields:
    """ProjectObservation model field behavior (RN-014)."""

    def test_create_observation(self, db):
        """ProjectObservation stores text, observer, and timestamp."""
        user = _make_user("director@test.edu")
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        obs = ProjectObservation.objects.create(
            project=project,
            observed_by=user,
            observation_text="Missing budget justification.",
        )
        assert obs.project == project
        assert obs.observed_by == user
        assert obs.observation_text == "Missing budget justification."
        assert obs.created_at is not None

    def test_observed_by_nullable(self, db):
        """observed_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        obs = ProjectObservation.objects.create(
            project=project, observation_text="System note.",
        )
        assert obs.observed_by is None

    def test_str_representation(self, db):
        """ProjectObservation __str__ includes text preview."""
        user = _make_user("director@test.edu")
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        obs = ProjectObservation.objects.create(
            project=project,
            observed_by=user,
            observation_text="Missing budget.",
        )
        assert "Missing budget" in str(obs)


# ──────────────────────────────────────────────
# ProjectStateLog Tests
# ──────────────────────────────────────────────


class TestProjectStateLogFields:
    """ProjectStateLog model field behavior (RN-012)."""

    def test_create_state_log(self, db):
        """ProjectStateLog records from_state, to_state, triggered_by."""
        user = _make_user("admin@test.edu")
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        log = ProjectStateLog.objects.create(
            project=project,
            from_state="borrador",
            to_state="enviado",
            triggered_by=user,
            reason="Submitted for review.",
        )
        assert log.project == project
        assert log.from_state == "borrador"
        assert log.to_state == "enviado"
        assert log.triggered_by == user
        assert log.reason == "Submitted for review."
        assert log.created_at is not None

    def test_triggered_by_nullable(self, db):
        """triggered_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        log = ProjectStateLog.objects.create(
            project=project,
            from_state="borrador",
            to_state="enviado",
        )
        assert log.triggered_by is None

    def test_reason_blank_by_default(self, db):
        """reason defaults to empty string."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        log = ProjectStateLog.objects.create(
            project=project,
            from_state="borrador",
            to_state="enviado",
        )
        assert log.reason == ""

    def test_str_representation(self, db):
        """ProjectStateLog __str__ includes states."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        log = ProjectStateLog.objects.create(
            project=project,
            from_state="borrador",
            to_state="enviado",
        )
        assert "borrador" in str(log)
        assert "enviado" in str(log)


# ──────────────────────────────────────────────
# FSM Transition Tests — Valid Transitions
# ──────────────────────────────────────────────


class TestFsmValidTransitions:
    """Every valid FSM transition succeeds (15 transitions)."""

    def test_submit_borrador_to_enviado(self, db):
        """submit(): borrador → enviado."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        assert project.status == "borrador"
        project.submit()
        project.save()
        assert project.status == "enviado"

    def test_accept_review_enviado_to_en_revision(self, db):
        """accept_review(): enviado → en_revision."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="enviado",
        )
        project.accept_review()
        project.save()
        assert project.status == "en_revision"

    def test_approve_en_revision_to_aprobado(self, db):
        """approve(): en_revision → aprobado."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_revision",
        )
        project.approve()
        project.save()
        assert project.status == "aprobado"

    def test_observe_en_revision_to_observado(self, db):
        """observe(): en_revision → observado."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_revision",
        )
        project.observe()
        project.save()
        assert project.status == "observado"

    def test_return_to_draft_from_en_revision(self, db):
        """return_to_draft(): en_revision → borrador."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_revision",
        )
        project.return_to_draft()
        project.save()
        assert project.status == "borrador"

    def test_reject_en_revision_to_rechazado(self, db):
        """reject(): en_revision → rechazado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_revision",
        )
        project.reject()
        project.save()
        assert project.status == "rechazado"

    def test_resubmit_observado_to_enviado(self, db):
        """resubmit(): observado → enviado."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="observado",
        )
        project.resubmit()
        project.save()
        assert project.status == "enviado"

    def test_return_to_draft_from_observado(self, db):
        """return_to_draft(): observado → borrador."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="observado",
        )
        project.return_to_draft()
        project.save()
        assert project.status == "borrador"

    def test_start_execution_aprobado_to_en_ejecucion(self, db):
        """start_execution(): aprobado → en_ejecucion."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="aprobado",
        )
        project.start_execution()
        project.save()
        assert project.status == "en_ejecucion"

    def test_suspend_en_ejecucion_to_suspendido(self, db):
        """suspend(): en_ejecucion → suspendido."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_ejecucion",
        )
        project.suspend()
        project.save()
        assert project.status == "suspendido"

    def test_resume_suspendido_to_en_ejecucion(self, db):
        """resume(): suspendido → en_ejecucion."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="suspendido",
        )
        project.resume()
        project.save()
        assert project.status == "en_ejecucion"

    def test_finalize_en_ejecucion_to_finalizado(self, db):
        """finalize(): en_ejecucion → finalizado."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_ejecucion",
        )
        project.finalize()
        project.save()
        assert project.status == "finalizado"

    def test_initiate_closure_finalizado_to_en_cierre(self, db):
        """initiate_closure(): finalizado → en_cierre."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="finalizado",
        )
        project.initiate_closure()
        project.save()
        assert project.status == "en_cierre"

    def test_close_en_cierre_to_cerrado(self, db):
        """close(): en_cierre → cerrado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="en_cierre",
        )
        project.close()
        project.save()
        assert project.status == "cerrado"

    def test_cancel_from_borrador_to_cancelado(self, db):
        """cancel(): borrador → cancelado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        project.cancel()
        project.save()
        assert project.status == "cancelado"


# ──────────────────────────────────────────────
# FSM Transition Tests — Invalid Transitions
# ──────────────────────────────────────────────


class TestFsmInvalidTransitions:
    """Invalid transitions raise TransitionNotAllowed."""

    def test_submit_from_enviado_fails(self, db):
        """submit() from enviado raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="enviado",
        )
        with pytest.raises(TransitionNotAllowed):
            project.submit()

    def test_approve_from_borrador_fails(self, db):
        """approve() from borrador raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        with pytest.raises(TransitionNotAllowed):
            project.approve()

    def test_finalize_from_borrador_fails(self, db):
        """finalize() from borrador raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        with pytest.raises(TransitionNotAllowed):
            project.finalize()

    def test_close_from_borrador_fails(self, db):
        """close() from borrador raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
        )
        with pytest.raises(TransitionNotAllowed):
            project.close()

    def test_start_execution_from_enviado_fails(self, db):
        """start_execution() from enviado raises TransitionNotAllowed."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="enviado",
        )
        with pytest.raises(TransitionNotAllowed):
            project.start_execution()


# ──────────────────────────────────────────────
# FSM Terminal State Blocking Tests
# ──────────────────────────────────────────────


class TestFsmTerminalStateBlocking:
    """Terminal states (cerrado, rechazado, cancelado) block all outbound transitions."""

    def test_cerrado_blocks_all_transitions(self, db):
        """No transition is valid from cerrado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="cerrado",
        )
        for method in [
            "submit", "accept_review", "approve", "observe",
            "return_to_draft", "reject", "resubmit", "start_execution",
            "suspend", "resume", "finalize", "initiate_closure",
            "close", "cancel",
        ]:
            with pytest.raises(TransitionNotAllowed):
                getattr(project, method)()

    def test_rechazado_blocks_all_transitions(self, db):
        """No transition is valid from rechazado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="rechazado",
        )
        for method in [
            "submit", "accept_review", "approve", "observe",
            "return_to_draft", "reject", "resubmit", "start_execution",
            "suspend", "resume", "finalize", "initiate_closure",
            "close", "cancel",
        ]:
            with pytest.raises(TransitionNotAllowed):
                getattr(project, method)()

    def test_cancelado_blocks_all_transitions(self, db):
        """No transition is valid from cancelado (terminal)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = Project.objects.create(
            institution=inst, center=center, principal_investigator=pi,
            title="Test", abstract="A", objectives="O",
            methodology="M", expected_results="E",
            start_date=datetime.date(2026, 1, 1),
            estimated_end_date=datetime.date(2026, 6, 1),
            status="cancelado",
        )
        for method in [
            "submit", "accept_review", "approve", "observe",
            "return_to_draft", "reject", "resubmit", "start_execution",
            "suspend", "resume", "finalize", "initiate_closure",
            "close", "cancel",
        ]:
            with pytest.raises(TransitionNotAllowed):
                getattr(project, method)()


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestProjectFactory:
    """ProjectFactory produces valid project instances."""

    def test_factory_creates_valid_project(self, db):
        """ProjectFactory creates a project with default borrador status."""
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        assert project.id is not None
        assert project.status == "borrador"
        assert project.is_active is True
        assert project.title != ""

    def test_factory_unique_ids(self, db):
        """Each factory call produces a unique UUID."""
        from apps.projects.tests.conftest import ProjectFactory

        p1 = ProjectFactory()
        p2 = ProjectFactory()
        assert p1.id != p2.id

    def test_factory_with_group(self, db):
        """ProjectFactory with_group trait assigns a group in the same chain."""
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory(with_group=True)
        assert project.group is not None
        assert project.group.center_id == project.center_id


class TestProjectMemberFactory:
    """ProjectMemberFactory produces valid member instances."""

    def test_factory_creates_valid_member(self, db):
        """ProjectMemberFactory creates a member with default co_investigator role."""
        from apps.projects.tests.conftest import ProjectMemberFactory

        member = ProjectMemberFactory()
        assert member.id is not None
        assert member.role == "co_investigator"
        assert member.project is not None
        assert member.researcher is not None


class TestProjectDocumentFactory:
    """ProjectDocumentFactory produces valid document instances."""

    def test_factory_creates_valid_document(self, db):
        from apps.projects.tests.conftest import ProjectDocumentFactory

        doc = ProjectDocumentFactory()
        assert doc.id is not None
        assert doc.doc_type == "proposal"
        assert doc.external_url != ""


class TestProjectObservationFactory:
    """ProjectObservationFactory produces valid observation instances."""

    def test_factory_creates_valid_observation(self, db):
        from apps.projects.tests.conftest import ProjectObservationFactory

        obs = ProjectObservationFactory()
        assert obs.id is not None
        assert obs.observation_text != ""
        assert obs.observed_by is not None


class TestProjectStateLogFactory:
    """ProjectStateLogFactory produces valid state log instances."""

    def test_factory_creates_valid_state_log(self, db):
        from apps.projects.tests.conftest import ProjectStateLogFactory

        log = ProjectStateLogFactory()
        assert log.id is not None
        assert log.from_state == "borrador"
        assert log.to_state == "enviado"
