"""
Integration tests for the notifications module — PR 5 (Phase 5).

End-to-end scenarios that drive REAL service boundaries and HTTP
endpoints — the full production path, not raw signal sends (those are
covered in test_receivers.py / test_signals.py):

- ProjectService.submit      → center director receives PROJECT_SUBMITTED (RN-1)
- ProgressService.observe    → report author receives PROGRESS_OBSERVED (RN-2)
- SignatureService.sign      → signer + project PI receive DOCUMENT_SIGNED (RN-3)
- BudgetService.add_execution → institution admin receives
  BUDGET_OVERRUN_ATTEMPTED on an unauthorized overrun (RN-4)
- API mark-read / unread_count against notifications created by real flows
- transaction.on_commit     → email dispatch enqueued once per CREATED row,
  and NOT enqueued when the recipient's email UserPreference is disabled

Deduplication is exercised through the real resubmit cycle (borrador →
enviado → en_revision → observado → enviado): the unique
(recipient, event_type, entity_type, entity_id) tuple must collapse the
two PROJECT_SUBMITTED emissions into a single Notification row.

Spec reference: openspec/changes/notifications/spec.md — Acceptance Criteria
Design reference: openspec/changes/notifications/design.md — Testing Strategy
"""

import hashlib
import io
import uuid
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.budgets.models import Budget, BudgetLine
from apps.budgets.services import BudgetService
from apps.documents.models import Document, DocumentType, DocumentVersion
from apps.documents.services import SignatureService, VersionAlreadySignedError
from apps.notifications.models import Notification, UserPreference
from apps.progress.services import ProgressService
from apps.projects.models import Project, ProjectStatus
from apps.projects.services import ProjectService

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


class FakeStorage:
    """In-memory stand-in for the MinIO storage backend (open interface only)."""

    def __init__(self, content=b"pdf-bytes"):
        self._content = content

    def open(self, object_key, mode="rb"):
        return io.BytesIO(self._content)


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
    return Project.objects.create(
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


def _make_execution_project(institution, researcher, center=None):
    """A project in en_ejecucion (progress reports require execution state)."""
    project = _make_project(institution, center=center, researcher=researcher)
    project.status = ProjectStatus.EN_EJECUCION
    project.save(update_fields=["status"])
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


def _make_director_and_project(institution, code="C1"):
    """A submit-ready project with an active center director (RN-1)."""
    director = _make_user("director@test.edu")
    pi_user = _make_user("pi@test.edu")
    center = _make_center(institution, code=code)
    director_role = _make_role("Director de Centro", 3)
    _make_membership(director, institution, director_role, center=center)
    researcher = _make_researcher(institution, user=pi_user)
    project = _make_project(institution, center=center, researcher=researcher)
    return director, pi_user, project


def _make_signable_document(institution, user, project=None):
    """An unsigned document version ready for SignatureService.sign (RN-3)."""
    doc_type = DocumentType.objects.get(code="informe_final")
    document = Document.objects.create(
        institution=institution,
        doc_type=doc_type,
        title="Signed doc",
        created_by=user,
        project=project,
    )
    content = b"pdf-bytes"
    object_key = f"documents/{institution.pk}/{document.pk}/v1/file.pdf"
    storage = FakeStorage(content)
    DocumentVersion.objects.create(
        document=document,
        version=1,
        object_key=object_key,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        mime_type="application/pdf",
        uploaded_by=user,
    )
    return document, storage


def _make_line(institution, approved=Decimal("1000.00")):
    budget = Budget.objects.create(
        project=_make_project(institution),
        institution=institution,
        name="Test Budget",
        approved_amount=Decimal("5000.00"),
    )
    return BudgetLine.objects.create(
        budget=budget,
        name="Line item",
        approved_amount=approved,
    )


def _make_admin(institution):
    """An Admin Institucional with an active membership (RN-4)."""
    admin = _make_user("admin@test.edu")
    admin_role = _make_role("Admin Institucional", 2)
    _make_membership(admin, institution, admin_role)
    return admin


def _login(client, user, institution):
    """Authenticate and activate the tenant session (API flows)."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


# ──────────────────────────────────────────────
# RN-1 — ProjectService.submit → Center Director
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestProjectSubmitEndToEnd:
    """Real ProjectService.submit drives the receiver (RN-1)."""

    def test_submit_through_service_notifies_center_director(self, db):
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)

        ProjectService.submit(project, pi_user)

        assert project.status == ProjectStatus.ENVIADO
        notification = Notification.objects.get(recipient=director)
        assert notification.event_type == "PROJECT_SUBMITTED"
        assert notification.institution == inst
        assert notification.entity_type == "project"
        assert notification.entity_id == project.pk
        assert notification.template.code == "PROJECT_SUBMITTED"
        assert project.title in notification.body
        assert notification.is_read is False

    def test_resubmit_cycle_creates_single_notification(self, db):
        """submit → accept_review → observe → resubmit: one row (dedup)."""
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)

        ProjectService.submit(project, pi_user)
        ProjectService.accept_review(project, director)
        ProjectService.observe(project, director, observation_text="Fix it")
        ProjectService.resubmit(project, pi_user)

        assert project.status == ProjectStatus.ENVIADO
        notifications = Notification.objects.filter(
            recipient=director, event_type="PROJECT_SUBMITTED"
        )
        assert notifications.count() == 1


# ──────────────────────────────────────────────
# RN-2 — ProgressService.observe → Report Author
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestProgressObserveEndToEnd:
    """Real ProgressService FSM drives the receiver (RN-2)."""

    def _setup(self):
        inst = _make_institution()
        author = _make_user("author@test.edu")
        director = _make_user("director@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=author)
        project = _make_execution_project(inst, researcher, center=center)
        report = _make_report(project, author)
        return inst, author, director, report

    def test_observe_through_service_notifies_report_author(self, db):
        inst, author, director, report = self._setup()

        ProgressService.submit(report, author)
        ProgressService.accept_review(report, director)
        ProgressService.observe(report, director, review_text="Needs fixes")

        notification = Notification.objects.get(recipient=author)
        assert notification.event_type == "PROGRESS_OBSERVED"
        assert notification.institution == inst
        assert notification.entity_type == "progress_report"
        assert notification.entity_id == report.pk
        assert report.project.title in notification.body

    def test_approve_through_service_does_not_notify(self, db):
        inst, author, director, report = self._setup()

        ProgressService.submit(report, author)
        ProgressService.accept_review(report, director)
        ProgressService.approve(report, director)

        assert Notification.objects.count() == 0


# ──────────────────────────────────────────────
# RN-3 — SignatureService.sign → Signer + PI
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestDocumentSignEndToEnd:
    """Real SignatureService.sign drives the receiver (RN-3)."""

    def test_sign_through_service_notifies_signer_and_pi(self, db):
        inst = _make_institution()
        signer = _make_user("signer@test.edu")
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_project(inst, center=center, researcher=researcher)
        document, storage = _make_signable_document(inst, signer, project=project)

        SignatureService.sign(
            document=document,
            version_number=1,
            user=signer,
            storage=storage,
        )

        notifications = Notification.objects.filter(event_type="DOCUMENT_SIGNED")
        assert notifications.count() == 2
        recipients = set(notifications.values_list("recipient_id", flat=True))
        assert recipients == {signer.pk, pi_user.pk}
        for notification in notifications:
            assert notification.institution == inst
            assert notification.entity_type == "document"
            assert notification.entity_id == document.pk

    def test_resign_denied_creates_no_new_notification(self, db):
        inst = _make_institution()
        signer = _make_user("signer@test.edu")
        pi_user = _make_user("pi@test.edu")
        center = _make_center(inst)
        researcher = _make_researcher(inst, user=pi_user)
        project = _make_project(inst, center=center, researcher=researcher)
        document, storage = _make_signable_document(inst, signer, project=project)

        SignatureService.sign(
            document=document,
            version_number=1,
            user=signer,
            storage=storage,
        )
        with pytest.raises(VersionAlreadySignedError):
            SignatureService.sign(
                document=document,
                version_number=1,
                user=signer,
                storage=storage,
            )

        assert Notification.objects.filter(event_type="DOCUMENT_SIGNED").count() == 2


# ──────────────────────────────────────────────
# RN-4 — BudgetService.add_execution → Admin
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestBudgetOverrunEndToEnd:
    """Real BudgetService.add_execution drives the receiver (RN-4)."""

    def test_unauthorized_overrun_notifies_institution_admin(self, db):
        inst = _make_institution()
        admin = _make_admin(inst)
        exec_user = _make_user("exec@test.edu")
        line = _make_line(inst, approved=Decimal("1000.00"))

        BudgetService.add_execution(
            line, Decimal("900.00"), date(2026, 4, 1), user=exec_user
        )
        with pytest.raises(ValidationError):
            BudgetService.add_execution(
                line, Decimal("200.00"), date(2026, 5, 1), user=exec_user
            )

        notification = Notification.objects.get(recipient=admin)
        assert notification.event_type == "BUDGET_OVERRUN_ATTEMPTED"
        assert notification.institution == inst
        assert notification.entity_type == "budget_line"
        assert notification.entity_id == line.pk
        assert line.name in notification.body

    def test_authorized_overrun_creates_no_notification(self, db):
        inst = _make_institution()
        _make_admin(inst)
        exec_user = _make_user("exec@test.edu")
        director = _make_user("director@test.edu")
        line = _make_line(inst, approved=Decimal("1000.00"))

        BudgetService.add_execution(
            line, Decimal("900.00"), date(2026, 4, 1), user=exec_user
        )
        BudgetService.add_execution(
            line,
            Decimal("200.00"),
            date(2026, 5, 1),
            user=exec_user,
            authorized_by=director,
            authorized_at=date(2026, 5, 1),
        )

        assert Notification.objects.count() == 0


# ──────────────────────────────────────────────
# API flows over real service-created notifications
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestReadAndUnreadEndToEnd:
    """Mark-read and unread_count against rows created by real flows."""

    def test_mark_read_sets_is_read(self, db):
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)
        ProjectService.submit(project, pi_user)
        notification = Notification.objects.get(recipient=director)

        client = Client()
        _login(client, director, inst)
        response = client.post(
            reverse("notifications:notification-read", args=[notification.pk])
        )

        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None

    def test_unread_count_reflects_read_actions(self, db):
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)
        ProjectService.submit(project, pi_user)
        second = _make_project(inst, center=project.center)
        ProjectService.submit(second, pi_user)

        client = Client()
        _login(client, director, inst)

        unread = client.get(reverse("notifications:notification-unread-count"))
        assert unread.status_code == 200
        assert unread.json() == {"count": 2}

        first = Notification.objects.filter(
            recipient=director, event_type="PROJECT_SUBMITTED"
        ).order_by("created_at").first()
        client.post(reverse("notifications:notification-read", args=[first.pk]))

        unread = client.get(reverse("notifications:notification-unread-count"))
        assert unread.json() == {"count": 1}


# ──────────────────────────────────────────────
# transaction.on_commit — email dispatch gating
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestEmailEnqueueEndToEnd:
    """Real submit flow enqueues dispatch once per CREATED row (Channel Semantics)."""

    def test_disabled_email_preference_enqueues_no_task(self, db):
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)
        UserPreference.objects.create(user=director, channel="email", enabled=False)

        with mock.patch(
            "apps.notifications.receivers.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ), mock.patch(
            "apps.notifications.receivers.dispatch_notification.delay"
        ) as delay:
            ProjectService.submit(project, pi_user)

        delay.assert_not_called()
        # NOTE: no global on_commit call-count assertion here — the search
        # module also registers on_commit callbacks during saves (its own
        # receivers are tested in apps/search/tests/test_signals.py).
        # In-app delivery is unaffected by the email opt-out.
        assert Notification.objects.filter(recipient=director).count() == 1

    def test_enabled_email_enqueues_one_task_on_commit(self, db):
        inst = _make_institution()
        director, pi_user, project = _make_director_and_project(inst)

        with mock.patch(
            "apps.notifications.receivers.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ), mock.patch(
            "apps.notifications.receivers.dispatch_notification.delay"
        ) as delay:
            ProjectService.submit(project, pi_user)

        notification = Notification.objects.get(recipient=director)
        # NOTE: on_commit is called by other apps too (search receivers
        # register on every indexed save) — assert the notifications
        # dispatch was enqueued exactly once, which is the contract here.
        delay.assert_called_once_with(str(notification.pk))
