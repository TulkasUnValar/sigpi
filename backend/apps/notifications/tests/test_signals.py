"""
Signal definition and emission tests — STRICT TDD (RED phase).

Covers the three semantic signals added for the notifications module
(spec deltas in openspec/changes/notifications/spec.md):

- progress_state_changed (RN-2): emitted once per successful FSM
  transition from ProgressService._log_transition; payload
  progress_report / from_state / to_state / triggered_by
- document_signed (RN-3): emitted after a successful
  SignatureService.sign; payload document / version / signer / sha256
- budget_overrun_attempted (RN-4): emitted when add_execution rejects an
  unauthorized overrun; payload budget_line / attempted_amount /
  requested_by / institution

Compatibility aliases required by the apply contract (instance /
old_status / new_status / user on progress; instance on document and
budget signals) are asserted alongside the spec payload.
"""

import hashlib
import io
import uuid
from datetime import date
from decimal import Decimal

import django.dispatch
import pytest
from django.core.exceptions import ValidationError
from django_fsm import TransitionNotAllowed

from apps.budgets.models import Budget, BudgetLine
from apps.budgets.services import BudgetService
from apps.documents.models import Document, DocumentType, DocumentVersion
from apps.documents.services import (
    IntegrityCheckError,
    SignatureService,
    VersionAlreadySignedError,
)
from apps.progress.services import ProgressService
from apps.projects.models import Project, ProjectStatus

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


class _SignalSpy:
    """Collects (sender, kwargs) for every emission of a signal."""

    def __init__(self, signal):
        self.emissions = []
        signal.connect(self._record)

    def _record(self, sender, **kwargs):
        self.emissions.append((sender, kwargs))

    def __len__(self):
        return len(self.emissions)

    def last(self):
        return self.emissions[-1]


class FakeStorage:
    """In-memory stand-in for the MinIO storage (open interface only)."""

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


def _make_center(institution, code="C1"):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(
        institution=institution,
        code=code,
        name=f"Center {code}",
    )


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
    # Progress reports require the project to be in execution or later.
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


def _make_budget(institution, project=None):
    project = project or _make_project(institution)
    return Budget.objects.create(
        project=project,
        institution=institution,
        name="Test Budget",
        approved_amount=Decimal("5000.00"),
    )


def _make_line(institution, approved=Decimal("1000.00")):
    budget = _make_budget(institution)
    return BudgetLine.objects.create(
        budget=budget,
        name="Line item",
        approved_amount=approved,
    )


def _make_signable_document(institution, user, tampered=False):
    doc_type = DocumentType.objects.get(code="informe_final")
    document = Document.objects.create(
        institution=institution,
        doc_type=doc_type,
        title="Signed doc",
        created_by=user,
    )
    content = b"pdf-bytes"
    object_key = f"documents/{institution.pk}/{document.pk}/v1/file.pdf"
    storage = FakeStorage(content)
    DocumentVersion.objects.create(
        document=document,
        version=1,
        object_key=object_key,
        sha256=("0" * 64) if tampered else hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        mime_type="application/pdf",
        uploaded_by=user,
    )
    return document, storage


# ──────────────────────────────────────────────
# Signal definitions
# ──────────────────────────────────────────────


class TestSignalDefinitions:
    """The three semantic signals exist and are django.dispatch.Signal."""

    def test_progress_state_changed_defined(self):
        from apps.progress.signals import progress_state_changed

        assert isinstance(progress_state_changed, django.dispatch.Signal)

    def test_document_signed_defined(self):
        from apps.documents.signals import document_signed

        assert isinstance(document_signed, django.dispatch.Signal)

    def test_budget_overrun_attempted_defined(self):
        from apps.budgets.signals import budget_overrun_attempted

        assert isinstance(budget_overrun_attempted, django.dispatch.Signal)


# ──────────────────────────────────────────────
# progress_state_changed emission
# ──────────────────────────────────────────────


class TestProgressStateChangedSignal:
    """RN-2 delta: emitted once per successful FSM transition."""

    def test_observe_emits_signal_with_payload(self, db):
        from apps.progress.signals import progress_state_changed

        spy = _SignalSpy(progress_state_changed)
        try:
            inst = _make_institution()
            author = _make_user("author@test.edu")
            director = _make_user("director@test.edu")
            project = _make_project(inst)
            report = _make_report(project, author)

            ProgressService.submit(report, author)
            ProgressService.accept_review(report, director)
            ProgressService.observe(report, director, review_text="Needs fixes")

            _, kwargs = spy.last()
            assert kwargs["progress_report"] == report
            assert kwargs["from_state"] == "en_revision"
            assert kwargs["to_state"] == "observado"
            assert kwargs["triggered_by"] == director
            # Compatibility aliases (apply contract).
            assert kwargs["instance"] == report
            assert kwargs["old_status"] == "en_revision"
            assert kwargs["new_status"] == "observado"
            assert kwargs["user"] == director
        finally:
            progress_state_changed.disconnect(spy._record)

    def test_each_transition_emits_once(self, db):
        from apps.progress.signals import progress_state_changed

        spy = _SignalSpy(progress_state_changed)
        try:
            inst = _make_institution()
            author = _make_user("author@test.edu")
            director = _make_user("director@test.edu")
            project = _make_project(inst)
            report = _make_report(project, author)

            ProgressService.submit(report, author)
            ProgressService.accept_review(report, director)
            ProgressService.observe(report, director, review_text="Fix")

            assert len(spy) == 3
            assert [kw["to_state"] for _, kw in spy.emissions] == [
                "enviado",
                "en_revision",
                "observado",
            ]
        finally:
            progress_state_changed.disconnect(spy._record)

    def test_failed_transition_does_not_emit(self, db):
        from apps.progress.signals import progress_state_changed

        spy = _SignalSpy(progress_state_changed)
        try:
            inst = _make_institution()
            author = _make_user("author@test.edu")
            project = _make_project(inst)
            report = _make_report(project, author)

            # observe() is only valid from en_revision — invalid from borrador.
            with pytest.raises(TransitionNotAllowed):
                ProgressService.observe(report, author, review_text="Nope")

            assert len(spy) == 0
        finally:
            progress_state_changed.disconnect(spy._record)


# ──────────────────────────────────────────────
# document_signed emission
# ──────────────────────────────────────────────


class TestDocumentSignedSignal:
    """RN-3 delta: emitted only after a successful sign."""

    def test_sign_emits_signal_with_payload(self, db):
        from apps.documents.signals import document_signed

        spy = _SignalSpy(document_signed)
        try:
            inst = _make_institution()
            signer = _make_user("signer@test.edu")
            doc, storage = _make_signable_document(inst, signer)

            signature = SignatureService.sign(
                document=doc,
                version_number=1,
                user=signer,
                storage=storage,
            )

            assert signature is not None
            _, kwargs = spy.last()
            assert kwargs["document"] == doc
            assert kwargs["version"] == 1
            assert kwargs["signer"] == signer
            assert kwargs["sha256"] == hashlib.sha256(b"pdf-bytes").hexdigest()
            assert kwargs["instance"] == doc
        finally:
            document_signed.disconnect(spy._record)

    def test_resign_does_not_emit(self, db):
        from apps.documents.signals import document_signed

        spy = _SignalSpy(document_signed)
        try:
            inst = _make_institution()
            signer = _make_user("signer@test.edu")
            doc, storage = _make_signable_document(inst, signer)

            SignatureService.sign(
                document=doc,
                version_number=1,
                user=signer,
                storage=storage,
            )
            with pytest.raises(VersionAlreadySignedError):
                SignatureService.sign(
                    document=doc,
                    version_number=1,
                    user=signer,
                    storage=storage,
                )

            assert len(spy) == 1
        finally:
            document_signed.disconnect(spy._record)

    def test_hash_mismatch_does_not_emit(self, db):
        from apps.documents.signals import document_signed

        spy = _SignalSpy(document_signed)
        try:
            inst = _make_institution()
            signer = _make_user("signer@test.edu")
            doc, storage = _make_signable_document(inst, signer, tampered=True)

            with pytest.raises(IntegrityCheckError):
                SignatureService.sign(
                    document=doc,
                    version_number=1,
                    user=signer,
                    storage=storage,
                )

            assert len(spy) == 0
        finally:
            document_signed.disconnect(spy._record)


# ──────────────────────────────────────────────
# budget_overrun_attempted emission
# ──────────────────────────────────────────────


class TestBudgetOverrunAttemptedSignal:
    """RN-4 delta: emitted only when an unauthorized overrun is rejected."""

    def test_unauthorized_overrun_emits_signal(self, db):
        from apps.budgets.signals import budget_overrun_attempted

        spy = _SignalSpy(budget_overrun_attempted)
        try:
            inst = _make_institution()
            user = _make_user("exec@test.edu")
            line = _make_line(inst, approved=Decimal("1000.00"))
            BudgetService.add_execution(
                line, Decimal("900.00"), date(2026, 4, 1), user=user
            )

            with pytest.raises(ValidationError):
                BudgetService.add_execution(
                    line, Decimal("200.00"), date(2026, 5, 1), user=user
                )

            assert len(spy) == 1
            _, kwargs = spy.last()
            assert kwargs["budget_line"] == line
            assert kwargs["attempted_amount"] == Decimal("200.00")
            assert kwargs["approved_amount"] == Decimal("1000.00")
            assert kwargs["requested_by"] == user
            assert kwargs["institution"] == inst
            assert kwargs["instance"] == line
        finally:
            budget_overrun_attempted.disconnect(spy._record)

    def test_authorized_overrun_does_not_emit(self, db):
        from apps.budgets.signals import budget_overrun_attempted

        spy = _SignalSpy(budget_overrun_attempted)
        try:
            inst = _make_institution()
            user = _make_user("exec@test.edu")
            director = _make_user("director@test.edu")
            line = _make_line(inst, approved=Decimal("1000.00"))
            BudgetService.add_execution(
                line, Decimal("900.00"), date(2026, 4, 1), user=user
            )

            execution = BudgetService.add_execution(
                line,
                Decimal("200.00"),
                date(2026, 5, 1),
                user=user,
                authorized_by=director,
                authorized_at=date(2026, 5, 1),
            )

            assert execution is not None
            assert len(spy) == 0
        finally:
            budget_overrun_attempted.disconnect(spy._record)

    def test_within_budget_does_not_emit(self, db):
        from apps.budgets.signals import budget_overrun_attempted

        spy = _SignalSpy(budget_overrun_attempted)
        try:
            inst = _make_institution()
            user = _make_user("exec@test.edu")
            line = _make_line(inst, approved=Decimal("1000.00"))

            BudgetService.add_execution(
                line, Decimal("400.00"), date(2026, 5, 1), user=user
            )

            assert len(spy) == 0
        finally:
            budget_overrun_attempted.disconnect(spy._record)
