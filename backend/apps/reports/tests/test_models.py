"""
Model validation tests for the Reports / Informes module (§6.6).

Covers: ReportType/ReportStatus enum values, Report model defaults,
clean() validation, constraints, and ReportApproval model behavior.

Spec reference:   sdd/reports/spec — RF-050–RF-058, RN-015–RN-018
Design reference: openspec/changes/reports/design.md

RED PHASE: Tests written BEFORE production implementation.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.reports.models import Report, ReportApproval, ReportStatus, ReportType

# ═══════════════════════════════════════════════════════
# ReportType Enum Tests
# ═══════════════════════════════════════════════════════


class TestReportTypeEnum:
    """ReportType choices match the spec (4 report types)."""

    def test_report_type_has_four_members(self):
        """ReportType enum has exactly 4 members: project, researcher, center, advances."""
        assert len(ReportType.choices) == 4

    def test_report_type_project(self):
        assert ReportType.PROJECT.value == "project"
        assert ReportType.PROJECT.label == "Project Report"

    def test_report_type_researcher(self):
        assert ReportType.RESEARCHER.value == "researcher"
        assert ReportType.RESEARCHER.label == "Researcher Report"

    def test_report_type_center(self):
        assert ReportType.CENTER.value == "center"
        assert ReportType.CENTER.label == "Center Report"

    def test_report_type_advances(self):
        assert ReportType.ADVANCES.value == "advances"
        assert ReportType.ADVANCES.label == "Advances Report"


# ═══════════════════════════════════════════════════════
# ReportStatus Enum Tests
# ═══════════════════════════════════════════════════════


class TestReportStatusEnum:
    """ReportStatus choices match the design (4 states)."""

    def test_report_status_has_four_members(self):
        """ReportStatus enum has 4 members: draft, generated, approved, rejected."""
        assert len(ReportStatus.choices) == 4

    def test_report_status_draft(self):
        assert ReportStatus.DRAFT.value == "draft"
        assert ReportStatus.DRAFT.label == "Draft"

    def test_report_status_generated(self):
        assert ReportStatus.GENERATED.value == "generated"
        assert ReportStatus.GENERATED.label == "Generated"

    def test_report_status_approved(self):
        assert ReportStatus.APPROVED.value == "approved"
        assert ReportStatus.APPROVED.label == "Approved"

    def test_report_status_rejected(self):
        assert ReportStatus.REJECTED.value == "rejected"
        assert ReportStatus.REJECTED.label == "Rejected"


# ═══════════════════════════════════════════════════════
# Report Model Tests
# ═══════════════════════════════════════════════════════


class TestReportModel:
    """Report model — defaults, constraints, and behavior."""

    def test_create_report_defaults(self, db):
        """New Report auto-assigns UUID PK, default status='generated', version=1."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        assert isinstance(report.id, uuid.UUID)
        assert report.status == ReportStatus.GENERATED
        assert report.version == 1
        assert report.report_type == ReportType.PROJECT

    def test_report_str_contains_type_and_entity(self, db):
        """__str__ includes report_type display and entity_id."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory(report_type="researcher")
        out = str(report)
        assert "Researcher Report" in out
        assert str(report.entity_id)[:8] in out

    def test_report_created_at_auto_set(self, db):
        """created_at is automatically set on creation."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        assert report.created_at is not None

    def test_report_institution_is_required(self, db):
        """Report must have an institution FK — validated by full_clean()."""
        from apps.reports.tests.conftest import UserFactory

        user = UserFactory()
        with pytest.raises(ValidationError, match="institution|nulo"):
            Report.objects.create(
                report_type=ReportType.PROJECT,
                entity_id=uuid.uuid4(),
                created_by=user,
            )

    def test_report_created_by_is_required(self, db):
        """Report must have a created_by FK — validated by full_clean()."""
        from apps.institutions.tests.conftest import InstitutionFactory

        inst = InstitutionFactory()
        with pytest.raises(ValidationError, match="created_by|nulo"):
            Report.objects.create(
                report_type=ReportType.PROJECT,
                entity_id=uuid.uuid4(),
                institution=inst,
            )

    def test_report_type_choices_are_valid(self, db):
        """All ReportType choices can be saved without error."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.reports.tests.conftest import UserFactory

        user = UserFactory()
        inst = InstitutionFactory()
        for rt in ReportType.values:
            report = Report.objects.create(
                report_type=rt,
                entity_id=uuid.uuid4(),
                institution=inst,
                created_by=user,
            )
            assert report.report_type == rt

    def test_report_status_choices_are_valid(self, db):
        """All ReportStatus choices can be saved without error."""
        from apps.institutions.tests.conftest import InstitutionFactory
        from apps.reports.tests.conftest import UserFactory

        user = UserFactory()
        inst = InstitutionFactory()
        for st in ReportStatus.values:
            report = Report.objects.create(
                report_type=ReportType.PROJECT,
                entity_id=uuid.uuid4(),
                institution=inst,
                created_by=user,
                status=st,
            )
            assert report.status == st

    def test_report_version_default_is_one(self, db):
        """Report.version defaults to 1."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        assert report.version == 1

    def test_report_version_positive_default(self, db):
        """Report.version attribute exists and is a PositiveIntegerField."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory(version=3)
        assert report.version == 3


class TestReportClean:
    """Report.clean() validation rules."""

    def test_clean_passes_for_valid_report(self, db):
        """clean() does not raise for a valid report."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        # full_clean() is called in save() already, so this is double check
        report.full_clean()  # should not raise

    def test_clean_rejects_invalid_report_type(self, db):
        """clean() rejects report_type outside ReportType choices."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory.build(report_type="invalid_type")
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_rejects_invalid_status(self, db):
        """clean() rejects status outside ReportStatus choices."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory.build(status="nonexistent")
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_rejects_missing_entity_id(self, db):
        """clean() rejects reports without entity_id."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory.build(entity_id=None)
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_rejects_zero_version(self, db):
        """clean() rejects version=0 (must be positive)."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory.build(version=0)
        with pytest.raises(ValidationError):
            report.full_clean()

    def test_clean_rejects_negative_version(self, db):
        """clean() rejects negative versions."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory.build(version=-1)
        with pytest.raises(ValidationError):
            report.full_clean()


# ═══════════════════════════════════════════════════════
# ReportApproval Model Tests
# ═══════════════════════════════════════════════════════


class TestReportApprovalModel:
    """ReportApproval model — defaults, constraints, and behavior."""

    def test_create_approval_auto_assigns_uuid_pk(self, db):
        """ReportApproval auto-assigns UUID PK."""
        from apps.reports.tests.conftest import ReportApprovalFactory

        approval = ReportApprovalFactory()
        assert isinstance(approval.id, uuid.UUID)

    def test_approval_str(self, db):
        """__str__ includes report and approver info."""
        from apps.reports.tests.conftest import ReportApprovalFactory

        approval = ReportApprovalFactory()
        out = str(approval)
        assert "approved by" in out or str(approval.report_id)[:8] in out

    def test_approval_approved_at_auto_set(self, db):
        """approved_at is automatically set on creation."""
        from apps.reports.tests.conftest import ReportApprovalFactory

        approval = ReportApprovalFactory()
        assert approval.approved_at is not None

    def test_approval_report_fk_is_required(self, db):
        """ReportApproval must have a report FK."""
        with pytest.raises(IntegrityError):
            ReportApproval.objects.create(
                approved_by=None,
                report_version=1,
            )

    def test_approval_approved_by_nullable(self, db):
        """approved_by can be null (SET_NULL on user deletion)."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        approval = ReportApproval.objects.create(
            report=report,
            approved_by=None,
            report_version=1,
        )
        assert approval.approved_by is None

    def test_approval_report_version_matches_report(self, db):
        """report_version can be set independently (snapshot)."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory(version=2)
        approval = ReportApproval.objects.create(
            report=report,
            approved_by=report.created_by,
            report_version=report.version,
        )
        assert approval.report_version == 2
        assert approval.report_version == report.version

    def test_approval_report_version_is_positive(self, db):
        """report_version must be a positive integer."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        approval = ReportApproval.objects.create(
            report=report,
            approved_by=report.created_by,
            report_version=5,
        )
        assert approval.report_version == 5


# ═══════════════════════════════════════════════════════
# Model Relationship Tests
# ═══════════════════════════════════════════════════════


class TestModelRelationships:
    """FK relationships and related_name access."""

    def test_report_has_institution(self, db):
        """Report.institution FK resolves correctly."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        assert report.institution is not None
        assert report.institution_id is not None

    def test_report_has_created_by(self, db):
        """Report.created_by FK resolves correctly."""
        from apps.reports.tests.conftest import ReportFactory

        report = ReportFactory()
        assert report.created_by is not None
        assert report.created_by_id is not None

    def test_approval_belongs_to_report(self, db):
        """ReportApproval.report FK resolves correctly."""
        from apps.reports.tests.conftest import ReportApprovalFactory

        approval = ReportApprovalFactory()
        assert approval.report is not None
        assert approval.report_id is not None

    def test_report_related_name_approvals(self, db):
        """Report.approvals related_name resolves."""
        from apps.reports.tests.conftest import ReportApprovalFactory, ReportFactory

        report = ReportFactory()
        ReportApprovalFactory(report=report)
        ReportApprovalFactory(report=report)
        assert report.approvals.count() == 2
