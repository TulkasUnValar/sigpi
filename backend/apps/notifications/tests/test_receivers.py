"""
Receiver tests for the notifications module — STRICT TDD (RED phase).

Covers the receiver contracts from spec RN-1..RN-4:

- project_state_changed → center director on to_state=enviado (RN-1)
- progress_state_changed → report author on to_state=observado (RN-2)
- document_signed → signer + project PI (RN-3)
- budget_overrun_attempted → institution admin (RN-4)

Cross-cutting contracts (design.md — Receivers):
- filters (non-matching states are ignored)
- dedup via get_or_create on the unique event tuple
- inactive templates suppress creation
- no I/O (ORM only; no SMTP/email)
- missing recipients log a warning and never fail the sender
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from unittest import mock

from apps.budgets.models import Budget, BudgetLine
from apps.documents.models import Document, DocumentType
from apps.notifications.models import Notification
from apps.progress.services import ProgressService
from apps.project_workflow.signals import project_state_changed
from apps.projects.models import Project, ProjectStatus

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_user(email="user@test.edu"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_role(name, level):
    """Look up a seeded Role by name (fall back to create for new roles)."""
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(name=name, defaults={"level": level})
    return role


def _make_center(institution, code="C1"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution,
        code=code,
        name=f"Center {code}",
    )


def _make_membership(user, institution, role, center=None):
    from apps.accounts.models import InstitutionMembership

    membership = InstitutionMembership.objects.create(
        user=user,
        institution=institution,
        role=role,
    )
    if center is not None:
        membership.centers.add(center)
    return membership


def _make_researcher(institution, user=None):
    from apps.researchers.models import Researcher

    return Researcher.objects.create(
        institution=institution,
        user=user,
        first_name="Jane",
        last_name="Doe",
        document_type="CC",
        document_number=uuid.uuid4().hex[:16],
        primary_email=user.email if user else "pi@test.edu",
    )


def _make_project(institution, center=None, researcher=None):
    center = center or _make_center(institution)
    researcher = researcher or _make_researcher(institution)
    project = Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=researcher,
        title=f"Project {uuid.uuid4().hex[:8]}",
        abstract="Abstract",
        objectives="Objectives",
        methodology="Methodology",
        expected_results="Expected results",
        keywords="test",
        start_date=date(2026, 1, 1),
        estimated_end_date=date(2026, 12, 31),
    )
    return project


def _make_report(project, author):
    from apps.progress.models import ProgressReport

    return ProgressReport.objects.create(
        institution=project.institution,
        project=project,
        created_by=author,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        description="Progress report",
        cumulative_percentage=Decimal("50.00"),
        activities="Activities done",
        difficulties="",
        next_steps="",
    )


def _make_budget(institution, project=None):
    project = project or _make_project(institution)
    return Budget.objects.create(
        project=project,
        institution=institution,
        name="Test Budget",
        approved_amount=Decimal("5000.00"),
    )


def _make_line(institution, approved=Decimal("1000.00"), project=None):
    budget = _make_budget(institution, project=project)
    return BudgetLine.objects.create(
        budget=budget,
        name="Line item",
        approved_amount=approved,
    )


def _make_document(institution, signer, project=None):
    doc_type = DocumentType.objects.get(code="informe_final")
    return Document.objects.create(
        institution=institution,
        doc_type=doc_type,
        title="Acta doc",
        created_by=signer,
        project=project,
    )


def _make_execution_project(institution, researcher, center=None):
    """A project in en_ejecucion (progress reports require execution state)."""
    project = _make_project(institution, center=center, researcher=researcher)
    project.status = ProjectStatus.EN_EJECUCION
    project.save(update_fields=["status"])
    return project


# ──────────────────────────────────────────────
# Signal emission helpers (same kwargs as services)
# ──────────────────────────────────────────────


def _emit_project_submitted(project, user):
    project_state_changed.send(
        sender=Project,
        project=project,
        from_state="borrador",
        to_state="enviado",
        triggered_by=user,
    )


def _emit_progress_observed(report, user):
    from apps.progress.models import ProgressReport
    from apps.progress.signals import progress_state_changed

    progress_state_changed.send(
        sender=ProgressReport,
        instance=report,
        progress_report=report,
        old_status="en_revision",
        new_status="observado",
        from_state="en_revision",
        to_state="observado",
        user=user,
        triggered_by=user,
    )


def _emit_document_signed(document, signer, version=1):
    from apps.documents.models import DigitalSignature
    from apps.documents.signals import document_signed

    document_signed.send(
        sender=DigitalSignature,
        instance=document,
        document=document,
        version=version,
        signer=signer,
        sha256="a" * 64,
    )


def _emit_budget_overrun(line, user, institution, amount=Decimal("200.00")):
    from apps.budgets.models import BudgetExecution
    from apps.budgets.signals import budget_overrun_attempted

    budget_overrun_attempted.send(
        sender=BudgetExecution,
        instance=line,
        budget_line=line,
        attempted_amount=amount,
        approved_amount=line.approved_amount,
        requested_by=user,
        institution=institution,
    )


# ──────────────────────────────────────────────
# RN-1 — Project Submitted → Center Director
# ──────────────────────────────────────────────


class TestProjectSubmittedReceiver:
    """RN-1: submit → center director notification."""

    def _setup(self):
        inst = _make_institution()
        director = _make_user("director@test.edu")
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        director_role = _make_role("Director de Centro", 3)
        _make_membership(director, inst, director_role, center=center)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_project(inst, center=center, researcher=researcher)
        return inst, director, project

    def test_director_notified_on_submit(self, db):
        inst, director, project = self._setup()

        _emit_project_submitted(project, director)

        notifications = Notification.objects.filter(recipient=director)
        assert notifications.count() == 1
        notification = notifications.get()
        assert notification.event_type == "PROJECT_SUBMITTED"
        assert notification.institution == inst
        assert notification.entity_type == "project"
        assert notification.entity_id == project.pk
        assert notification.template.code == "PROJECT_SUBMITTED"
        assert project.title in notification.body
        assert notification.title

    def test_non_submit_transition_ignored(self, db):
        inst, director, project = self._setup()

        project_state_changed.send(
            sender=Project,
            project=project,
            from_state="enviado",
            to_state="en_revision",
            triggered_by=director,
        )

        assert Notification.objects.count() == 0

    def test_no_director_no_notification_and_warns(self, db, caplog):
        inst = _make_institution()
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_project(inst, center=center, researcher=researcher)

        with caplog.at_level(logging.WARNING, logger="apps.notifications.receivers"):
            _emit_project_submitted(project, pi_user)

        assert Notification.objects.count() == 0
        assert any("No active center director" in r.getMessage() for r in caplog.records)

    def test_inactive_template_skips_creation(self, db):
        from apps.notifications.models import NotificationTemplate

        inst, director, project = self._setup()
        NotificationTemplate.objects.filter(code="PROJECT_SUBMITTED").update(
            is_active=False
        )

        _emit_project_submitted(project, director)

        assert Notification.objects.count() == 0

    def test_deduplication_on_resubmit(self, db):
        inst, director, project = self._setup()

        _emit_project_submitted(project, director)
        _emit_project_submitted(project, director)  # resubmit cycle

        assert Notification.objects.count() == 1


# ──────────────────────────────────────────────
# RN-2 — Observed Advance → Researcher
# ──────────────────────────────────────────────


class TestProgressObservedReceiver:
    """RN-2: observe → report author notification."""

    def _setup(self):
        inst = _make_institution()
        author = _make_user("author@test.edu")
        director = _make_user("director@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=author)
        project = _make_execution_project(inst, researcher, center=center)
        report = _make_report(project, author)
        return inst, author, director, report

    def test_researcher_notified_on_observe(self, db):
        inst, author, director, report = self._setup()

        ProgressService.submit(report, author)
        ProgressService.accept_review(report, director)
        ProgressService.observe(report, director, review_text="Fix it")

        notification = Notification.objects.get(recipient=author)
        assert notification.event_type == "PROGRESS_OBSERVED"
        assert notification.entity_type == "progress_report"
        assert notification.entity_id == report.pk
        assert notification.institution == inst
        assert report.project.title in notification.body

    def test_approval_does_not_notify(self, db):
        inst, author, director, report = self._setup()

        ProgressService.submit(report, author)
        ProgressService.accept_review(report, director)
        ProgressService.approve(report, director)

        assert Notification.objects.count() == 0

    def test_deduplication_on_repeated_signal(self, db):
        inst, author, director, report = self._setup()

        _emit_progress_observed(report, director)
        _emit_progress_observed(report, director)

        assert Notification.objects.count() == 1


# ──────────────────────────────────────────────
# RN-3 — Signed Document → Signer + PI
# ──────────────────────────────────────────────


class TestDocumentSignedReceiver:
    """RN-3: sign → signer + project PI notification."""

    def _setup(self, with_project=True):
        inst = _make_institution()
        signer = _make_user("signer@test.edu")
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_project(inst, center=center, researcher=researcher)
        document = _make_document(
            inst,
            signer,
            project=project if with_project else None,
        )
        return inst, signer, pi_user, document

    def test_signer_and_pi_notified(self, db):
        inst, signer, pi_user, document = self._setup(with_project=True)

        _emit_document_signed(document, signer)

        notifications = Notification.objects.filter(event_type="DOCUMENT_SIGNED")
        assert notifications.count() == 2
        recipients = set(notifications.values_list("recipient_id", flat=True))
        assert recipients == {signer.pk, pi_user.pk}
        for notification in notifications:
            assert notification.entity_type == "document"
            assert notification.entity_id == document.pk
            assert notification.institution == inst

    def test_document_without_project_notifies_signer_only(self, db):
        inst, signer, pi_user, document = self._setup(with_project=False)

        _emit_document_signed(document, signer)

        notifications = Notification.objects.filter(event_type="DOCUMENT_SIGNED")
        assert notifications.count() == 1
        assert notifications.get().recipient == signer

    def test_deduplication(self, db):
        inst, signer, pi_user, document = self._setup(with_project=True)

        _emit_document_signed(document, signer)
        _emit_document_signed(document, signer)

        assert Notification.objects.filter(event_type="DOCUMENT_SIGNED").count() == 2


# ──────────────────────────────────────────────
# RN-4 — Budget Overrun Attempt → Institution Admin
# ──────────────────────────────────────────────


class TestBudgetOverrunReceiver:
    """RN-4: unauthorized overrun → institution admin notification."""

    def _setup(self):
        inst = _make_institution()
        admin = _make_user("admin@test.edu")
        exec_user = _make_user("exec@test.edu")
        admin_role = _make_role("Admin Institucional", 2)
        _make_membership(admin, inst, admin_role)
        line = _make_line(inst, approved=Decimal("1000.00"))
        return inst, admin, exec_user, line

    def test_admin_notified_on_overrun(self, db):
        inst, admin, exec_user, line = self._setup()

        _emit_budget_overrun(line, exec_user, inst)

        notification = Notification.objects.get(recipient=admin)
        assert notification.event_type == "BUDGET_OVERRUN_ATTEMPTED"
        assert notification.entity_type == "budget_line"
        assert notification.entity_id == line.pk
        assert notification.institution == inst
        assert line.name in notification.body

    def test_director_also_recipient(self, db):
        inst, admin, exec_user, line = self._setup()
        director = _make_user("director@test.edu")
        director_role = _make_role("Director de Centro", 3)
        _make_membership(director, inst, director_role)

        _emit_budget_overrun(line, exec_user, inst)

        recipients = set(
            Notification.objects.filter(event_type="BUDGET_OVERRUN_ATTEMPTED").values_list(
                "recipient_id", flat=True
            )
        )
        assert recipients == {admin.pk, director.pk}

    def test_no_admin_no_notification_and_warns(self, db, caplog):
        inst = _make_institution()
        exec_user = _make_user("exec@test.edu")
        line = _make_line(inst, approved=Decimal("1000.00"))

        with caplog.at_level(logging.WARNING, logger="apps.notifications.receivers"):
            _emit_budget_overrun(line, exec_user, inst)

        assert Notification.objects.count() == 0
        assert any("No institutional admin" in r.getMessage() for r in caplog.records)


# ──────────────────────────────────────────────
# Cross-cutting receiver contracts
# ──────────────────────────────────────────────


class TestReceiverContracts:
    """Design contracts: no I/O, sender isolation, idempotency."""

    def test_receivers_perform_no_io(self, db):
        """All four receivers only do ORM work — no email/SMTP calls."""
        inst = _make_institution()
        director = _make_user("director@test.edu")
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        director_role = _make_role("Director de Centro", 3)
        _make_membership(director, inst, director_role, center=center)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_execution_project(inst, researcher, center=center)
        report = _make_report(project, pi_user)

        signer = _make_user("signer@test.edu")
        document = _make_document(inst, signer, project=project)

        admin = _make_user("admin@test.edu")
        admin_role = _make_role("Admin Institucional", 2)
        _make_membership(admin, inst, admin_role)
        line = _make_line(inst, approved=Decimal("1000.00"), project=project)

        with mock.patch("django.core.mail.send_mail") as send_mail, mock.patch(
            "smtplib.SMTP"
        ) as smtp:
            _emit_project_submitted(project, director)
            _emit_progress_observed(report, director)
            _emit_document_signed(document, signer)
            _emit_budget_overrun(line, signer, inst)

        send_mail.assert_not_called()
        smtp.assert_not_called()
        # submit→director(1) + observe→author(1) + sign→signer+PI(2)
        # + overrun→admin+director(2, both resolve_admin recipients)
        assert Notification.objects.count() == 6

    def test_receiver_error_does_not_propagate_to_sender(self, db):
        inst = _make_institution()
        director = _make_user("director@test.edu")
        center = _make_center(inst)
        director_role = _make_role("Director de Centro", 3)
        _make_membership(director, inst, director_role, center=center)
        researcher = _make_researcher(inst)
        project = _make_project(inst, center=center, researcher=researcher)

        from apps.notifications import receivers

        with mock.patch.object(
            receivers, "resolve_director", side_effect=RuntimeError("boom")
        ):
            _emit_project_submitted(project, director)  # must not raise

        assert Notification.objects.count() == 0
