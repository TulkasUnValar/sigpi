"""
Model tests for progress app — STRICT TDD.

Tests define the expected behavior of the 4-entity progress module:
ProgressReport, ProgressReview, ProgressDocument, ProgressStateLog.
Plus Project.cumulative_progress delta.

Spec reference:   openspec/sdd/advances/spec.md
Design reference: openspec/sdd/advances/design.md

RED PHASE: All tests fail because models are empty stubs.
"""
import datetime
import uuid
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django_fsm import TransitionNotAllowed

from apps.progress.models import (
    PROGRESS_TERMINAL_STATES,
    ProgressDocument,
    ProgressDocumentType,
    ProgressReport,
    ProgressReview,
    ProgressReviewType,
    ProgressStateLog,
    ProgressStatus,
)
from apps.projects.models import Project

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test U {code}", code=code)


def _make_center(institution, name="AI Lab", code="AI"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution, name=name, code=code,
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


def _make_user(email="progtest@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_project(institution, center, researcher):
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=researcher,
        title="Test Project",
        abstract="An abstract",
        objectives="Objectives text",
        methodology="Methodology text",
        expected_results="Expected results",
        keywords="test",
        start_date=datetime.date(2026, 1, 1),
        estimated_end_date=datetime.date(2026, 12, 31),
    )


# ──────────────────────────────────────────────
# Enum Tests
# ──────────────────────────────────────────────


class TestProgressStatusEnum:
    """ProgressStatus TextChoices has 6 states."""

    def test_all_six_states_defined(self):
        expected = {
            "borrador", "enviado", "en_revision",
            "observado", "aprobado", "rechazado",
        }
        actual = {choice[0] for choice in ProgressStatus.choices}
        assert actual == expected

    def test_terminal_states_constant(self):
        assert ProgressStatus.APROBADO in PROGRESS_TERMINAL_STATES
        assert ProgressStatus.BORRADOR not in PROGRESS_TERMINAL_STATES
        assert ProgressStatus.RECHAZADO not in PROGRESS_TERMINAL_STATES


class TestProgressDocumentTypeEnum:
    """ProgressDocumentType TextChoices has 4 types."""

    def test_all_four_types_defined(self):
        expected = {"evidence", "annex", "report", "other"}
        actual = {choice[0] for choice in ProgressDocumentType.choices}
        assert actual == expected


class TestProgressReviewTypeEnum:
    """ProgressReviewType TextChoices has 2 types."""

    def test_both_types_defined(self):
        expected = {"observation", "rejection"}
        actual = {choice[0] for choice in ProgressReviewType.choices}
        assert actual == expected


# ──────────────────────────────────────────────
# ProgressReport Model Field Tests
# ──────────────────────────────────────────────


class TestProgressReportFields:
    """ProgressReport model field behavior and defaults."""

    def test_create_report_minimal(self, db):
        """ProgressReport can be created with required fields, defaults to borrador."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Q1 Progress Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Completed literature review.",
            difficulties="None",
            next_steps="Begin experiments.",
        )
        assert report.id is not None
        assert isinstance(report.id, uuid.UUID)
        assert report.institution == inst
        assert report.project == project
        assert report.created_by == user
        assert report.status == "borrador"
        assert report.cumulative_percentage == Decimal("25.00")
        assert report.period_start == datetime.date(2026, 1, 1)
        assert report.period_end == datetime.date(2026, 3, 31)

    def test_timestamps_auto_set(self, db):
        """created_at and updated_at are set automatically."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("10.00"),
            activities="Work done.",
        )
        assert report.created_at is not None
        assert report.updated_at is not None

    def test_optional_fields_blank(self, db):
        """difficulties and next_steps are optional (blank=True)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("10.00"),
            activities="Work done.",
            difficulties="",
            next_steps="",
        )
        assert report.difficulties == ""
        assert report.next_steps == ""

    def test_str_representation(self, db):
        """ProgressReport __str__ includes project title and period."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("10.00"),
            activities="Work done.",
        )
        assert "Test Project" in str(report)


# ──────────────────────────────────────────────
# ProgressReport clean() Validation — RN-P01, RN-P02
# ──────────────────────────────────────────────


class TestProgressReportCleanValidation:
    """ProgressReport.clean() enforces RN-P01 (percentage) and RN-P02 (dates)."""

    def test_clean_rejects_percentage_negative(self, db):
        """RN-P01: cumulative_percentage must be >= 0."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("-1.00"),
            activities="Work done.",
        )
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_rejects_percentage_over_100(self, db):
        """RN-P01: cumulative_percentage must be <= 100."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("101.00"),
            activities="Work done.",
        )
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_accepts_percentage_zero(self, db):
        """RN-P01: cumulative_percentage=0 is valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("0.00"),
            activities="Work done.",
        )
        report.full_clean()  # should not raise

    def test_clean_accepts_percentage_100(self, db):
        """RN-P01: cumulative_percentage=100 is valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("100.00"),
            activities="Work done.",
        )
        report.full_clean()  # should not raise

    def test_clean_rejects_period_end_before_start(self, db):
        """RN-P02: period_end must be >= period_start."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 6, 1),
            period_end=datetime.date(2026, 1, 1),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_accepts_period_equal(self, db):
        """RN-P02: period_end == period_start is valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 3, 1),
            period_end=datetime.date(2026, 3, 1),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        report.full_clean()  # should not raise

    def test_clean_accepts_valid_data(self, db):
        """RN-P01 + RN-P02: valid data passes clean()."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("50.00"),
            activities="Work done.",
        )
        report.full_clean()  # should not raise


# ──────────────────────────────────────────────
# ProgressReport DB CHECK Constraint Tests
# ──────────────────────────────────────────────


class TestProgressReportCheckConstraints:
    """DB CHECK constraints enforce RN-P01 and RN-P02 at database level."""

    def test_check_constraints_exist(self):
        """CHECK constraints are registered in Meta.constraints."""
        constraint_names = {
            c.name for c in ProgressReport._meta.constraints
        }
        assert "check_progress_percentage_range" in constraint_names
        assert "check_progress_period_dates" in constraint_names

    def test_validate_constraints_rejects_invalid_percentage(self, db):
        """Django validate_constraints() catches out-of-range percentage."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("150.00"),
            activities="Work done.",
        )
        with pytest.raises(ValidationError):
            report.validate_constraints()

    def test_validate_constraints_rejects_reversed_dates(self, db):
        """Django validate_constraints() catches period_end < period_start."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 6, 1),
            period_end=datetime.date(2026, 1, 1),
            description="Report",
            cumulative_percentage=Decimal("10.00"),
            activities="Work done.",
        )
        with pytest.raises(ValidationError):
            report.validate_constraints()


# ──────────────────────────────────────────────
# ProgressReport Index Tests
# ──────────────────────────────────────────────


class TestProgressReportIndexes:
    """Indexes are registered in Meta."""

    def test_indexes_exist(self):
        index_names = {idx.name for idx in ProgressReport._meta.indexes}
        assert "idx_progress_inst_status" in index_names
        assert "idx_progress_project_status" in index_names
        assert "idx_progress_created_by" in index_names


# ──────────────────────────────────────────────
# ProgressReview Model Tests
# ──────────────────────────────────────────────


class TestProgressReviewFields:
    """ProgressReview model field behavior (RN-P05)."""

    def test_create_review(self, db):
        """ProgressReview stores text, reviewer, and type."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")
        director = _make_user("director@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        review = ProgressReview.objects.create(
            progress_report=report,
            reviewed_by=director,
            review_text="Need more detail on methodology.",
            review_type="observation",
        )
        assert review.progress_report == report
        assert review.reviewed_by == director
        assert review.review_text == "Need more detail on methodology."
        assert review.review_type == "observation"
        assert review.created_at is not None

    def test_reviewed_by_nullable(self, db):
        """reviewed_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        review = ProgressReview.objects.create(
            progress_report=report,
            review_text="System note.",
            review_type="observation",
        )
        assert review.reviewed_by is None

    def test_review_type_choices_valid(self, db):
        """All ProgressReviewType choices are valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        for rtype in ("observation", "rejection"):
            review = ProgressReview(
                progress_report=report,
                review_text="Feedback.",
                review_type=rtype,
            )
            review.full_clean()

    def test_review_type_invalid_choice(self, db):
        """Invalid review_type raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        review = ProgressReview(
            progress_report=report,
            review_text="Test",
            review_type="invalid",
        )
        with pytest.raises(ValidationError):
            review.full_clean()

    def test_str_representation(self, db):
        """ProgressReview __str__ includes review_text preview."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        review = ProgressReview.objects.create(
            progress_report=report,
            review_text="Missing budget.",
            review_type="observation",
        )
        assert "Missing budget" in str(review)


# ──────────────────────────────────────────────
# ProgressDocument Model Tests
# ──────────────────────────────────────────────


class TestProgressDocumentFields:
    """ProgressDocument model field behavior."""

    def test_create_document(self, db):
        """ProgressDocument stores name, type, and external URL (RF-043)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        doc = ProgressDocument.objects.create(
            progress_report=report,
            name="Evidence Q1.pdf",
            doc_type="evidence",
            external_url="https://storage.example.com/evidence.pdf",
        )
        assert doc.name == "Evidence Q1.pdf"
        assert doc.doc_type == "evidence"
        assert doc.external_url == "https://storage.example.com/evidence.pdf"
        assert doc.progress_report == report
        assert doc.uploaded_at is not None

    def test_external_url_blank_default(self, db):
        """external_url defaults to blank string."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        doc = ProgressDocument.objects.create(
            progress_report=report,
            name="Doc.txt",
            doc_type="other",
        )
        assert doc.external_url == ""

    def test_doc_type_choices_valid(self, db):
        """All ProgressDocumentType choices are valid."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        for dtype in ("evidence", "annex", "report", "other"):
            doc = ProgressDocument(
                progress_report=report,
                name=f"doc.{dtype}",
                doc_type=dtype,
                external_url=f"https://example.com/{dtype}",
            )
            doc.full_clean()

    def test_doc_type_invalid_choice(self, db):
        """Invalid doc_type raises ValidationError."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        doc = ProgressDocument(
            progress_report=report,
            name="file.txt",
            doc_type="invalid",
            external_url="https://example.com/file.txt",
        )
        with pytest.raises(ValidationError):
            doc.full_clean()

    def test_str_representation(self, db):
        """ProgressDocument __str__ includes name and type."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        doc = ProgressDocument.objects.create(
            progress_report=report,
            name="Evidence.pdf",
            doc_type="evidence",
            external_url="https://example.com/evidence.pdf",
        )
        assert "Evidence.pdf" in str(doc)


# ──────────────────────────────────────────────
# ProgressStateLog Model Tests
# ──────────────────────────────────────────────


class TestProgressStateLogFields:
    """ProgressStateLog model field behavior (RN-P04)."""

    def test_create_state_log(self, db):
        """ProgressStateLog records from_state, to_state, triggered_by."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")
        admin = _make_user("admin@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        log = ProgressStateLog.objects.create(
            progress_report=report,
            from_state="borrador",
            to_state="enviado",
            triggered_by=admin,
            reason="Submitted for review.",
        )
        assert log.progress_report == report
        assert log.from_state == "borrador"
        assert log.to_state == "enviado"
        assert log.triggered_by == admin
        assert log.reason == "Submitted for review."
        assert log.created_at is not None

    def test_triggered_by_nullable(self, db):
        """triggered_by is nullable (SET_NULL on user deletion)."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        log = ProgressStateLog.objects.create(
            progress_report=report,
            from_state="borrador",
            to_state="enviado",
        )
        assert log.triggered_by is None

    def test_reason_blank_by_default(self, db):
        """reason defaults to empty string."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        log = ProgressStateLog.objects.create(
            progress_report=report,
            from_state="borrador",
            to_state="enviado",
        )
        assert log.reason == ""

    def test_str_representation(self, db):
        """ProgressStateLog __str__ includes states."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        report = ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
        )
        log = ProgressStateLog.objects.create(
            progress_report=report,
            from_state="borrador",
            to_state="enviado",
        )
        assert "borrador" in str(log)
        assert "enviado" in str(log)

    def test_state_log_indexes_exist(self):
        """Indexes are registered in Meta."""
        index_names = {idx.name for idx in ProgressStateLog._meta.indexes}
        assert "idx_progress_sl_report_time" in index_names
        assert "idx_progress_sl_states" in index_names


# ──────────────────────────────────────────────
# FSM Transition Tests — Valid Transitions (9)
# ──────────────────────────────────────────────


class TestFsmValidTransitions:
    """Every valid FSM transition succeeds (9 transitions)."""

    def _make_report(self, db, status="borrador"):
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        return ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
            status=status,
        )

    # 1. borrador → enviado
    def test_submit_borrador_to_enviado(self, db):
        report = self._make_report(db)
        assert report.status == "borrador"
        report.submit()
        report.save()
        assert report.status == "enviado"

    # 2. enviado → en_revision
    def test_accept_review_enviado_to_en_revision(self, db):
        report = self._make_report(db, status="enviado")
        report.accept_review()
        report.save()
        assert report.status == "en_revision"

    # 3. en_revision → aprobado
    def test_approve_en_revision_to_aprobado(self, db):
        report = self._make_report(db, status="en_revision")
        report.approve()
        report.save()
        assert report.status == "aprobado"

    # 4. en_revision → observado
    def test_observe_en_revision_to_observado(self, db):
        report = self._make_report(db, status="en_revision")
        report.observe()
        report.save()
        assert report.status == "observado"

    # 5. en_revision → rechazado
    def test_reject_en_revision_to_rechazado(self, db):
        report = self._make_report(db, status="en_revision")
        report.reject()
        report.save()
        assert report.status == "rechazado"

    # 6. en_revision → borrador
    def test_return_to_draft_from_en_revision(self, db):
        report = self._make_report(db, status="en_revision")
        report.return_to_draft()
        report.save()
        assert report.status == "borrador"

    # 7. observado → enviado
    def test_resubmit_observado_to_enviado(self, db):
        report = self._make_report(db, status="observado")
        report.resubmit()
        report.save()
        assert report.status == "enviado"

    # 8. observado → borrador
    def test_return_to_draft_from_observado(self, db):
        report = self._make_report(db, status="observado")
        report.return_to_draft()
        report.save()
        assert report.status == "borrador"

    # 9. rechazado → borrador
    def test_return_to_draft_from_rechazado(self, db):
        report = self._make_report(db, status="rechazado")
        report.return_to_draft()
        report.save()
        assert report.status == "borrador"


# ──────────────────────────────────────────────
# FSM Transition Tests — Invalid Transitions
# ──────────────────────────────────────────────


class TestFsmInvalidTransitions:
    """Invalid transitions raise TransitionNotAllowed."""

    def _make_report(self, db, status="borrador"):
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        return ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
            status=status,
        )

    def test_submit_from_enviado_fails(self, db):
        report = self._make_report(db, status="enviado")
        with pytest.raises(TransitionNotAllowed):
            report.submit()

    def test_approve_from_borrador_fails(self, db):
        report = self._make_report(db)
        with pytest.raises(TransitionNotAllowed):
            report.approve()

    def test_observe_from_borrador_fails(self, db):
        report = self._make_report(db)
        with pytest.raises(TransitionNotAllowed):
            report.observe()

    def test_reject_from_borrador_fails(self, db):
        report = self._make_report(db)
        with pytest.raises(TransitionNotAllowed):
            report.reject()

    def test_resubmit_from_borrador_fails(self, db):
        report = self._make_report(db)
        with pytest.raises(TransitionNotAllowed):
            report.resubmit()

    def test_accept_review_from_borrador_fails(self, db):
        report = self._make_report(db)
        with pytest.raises(TransitionNotAllowed):
            report.accept_review()


# ──────────────────────────────────────────────
# FSM Terminal State Blocking — aprobado
# ──────────────────────────────────────────────


class TestFsmAprobadoTerminal:
    """aprobado is terminal (RN-P07) — no outbound transitions."""

    def _make_approved(self, db):
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)
        user = _make_user("creator@test.edu")

        return ProgressReport.objects.create(
            institution=inst,
            project=project,
            created_by=user,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 3, 31),
            description="Report",
            cumulative_percentage=Decimal("25.00"),
            activities="Work done.",
            status="aprobado",
        )

    def test_aprobado_blocks_all_transitions(self, db):
        """No transition is valid from aprobado."""
        report = self._make_approved(db)
        for method in [
            "submit", "accept_review", "approve", "observe",
            "return_to_draft", "reject", "resubmit",
        ]:
            with pytest.raises(TransitionNotAllowed):
                getattr(report, method)()


# ──────────────────────────────────────────────
# Project.cumulative_progress Delta Tests
# ──────────────────────────────────────────────


class TestProjectCumulativeProgress:
    """Project model gains cumulative_progress field (spec §Delta)."""

    def test_cumulative_progress_field_exists(self, db):
        """Project has cumulative_progress DecimalField with default 0.00."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        assert hasattr(project, "cumulative_progress")
        assert project.cumulative_progress == Decimal("0.00")

    def test_cumulative_progress_can_be_set(self, db):
        """cumulative_progress can be set and saved."""
        inst = _make_institution("TU")
        center = _make_center(inst)
        pi = _make_researcher(inst)
        project = _make_project(inst, center, pi)

        project.cumulative_progress = Decimal("45.50")
        project.save()
        project.refresh_from_db()
        assert project.cumulative_progress == Decimal("45.50")


# ──────────────────────────────────────────────
# Factory Tests
# ──────────────────────────────────────────────


class TestProgressReportFactory:
    """ProgressReportFactory produces valid report instances."""

    def test_factory_creates_valid_report(self, db):
        from apps.progress.tests.conftest import ProgressReportFactory

        report = ProgressReportFactory()
        assert report.id is not None
        assert report.status == "borrador"
        assert report.cumulative_percentage is not None
        assert report.project is not None
        assert report.institution is not None
        assert report.created_by is not None

    def test_factory_unique_ids(self, db):
        from apps.progress.tests.conftest import ProgressReportFactory

        r1 = ProgressReportFactory()
        r2 = ProgressReportFactory()
        assert r1.id != r2.id


class TestProgressReviewFactory:
    """ProgressReviewFactory produces valid review instances."""

    def test_factory_creates_valid_review(self, db):
        from apps.progress.tests.conftest import ProgressReviewFactory

        review = ProgressReviewFactory()
        assert review.id is not None
        assert review.review_type == "observation"
        assert review.progress_report is not None
        assert review.review_text != ""


class TestProgressDocumentFactory:
    """ProgressDocumentFactory produces valid document instances."""

    def test_factory_creates_valid_document(self, db):
        from apps.progress.tests.conftest import ProgressDocumentFactory

        doc = ProgressDocumentFactory()
        assert doc.id is not None
        assert doc.doc_type == "evidence"
        assert doc.progress_report is not None


class TestProgressStateLogFactory:
    """ProgressStateLogFactory produces valid state log instances."""

    def test_factory_creates_valid_state_log(self, db):
        from apps.progress.tests.conftest import ProgressStateLogFactory

        log = ProgressStateLogFactory()
        assert log.id is not None
        assert log.from_state == "borrador"
        assert log.to_state == "enviado"
