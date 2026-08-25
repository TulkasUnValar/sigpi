"""
Audit signal-layer tests — STRICT TDD.

Tests verify the PR 2 signal layer (apps/audit/signals.py):
- CREATE event emitted on model creation.
- UPDATE event emitted on save with actual changes (with old/new diff).
- DELETE event emitted on model deletion.
- No event emitted on save without changes.
- Raw saves are ignored.
- Missing institution context is ignored.
- AuditEvent itself is not tracked.

Design reference: openspec/changes/audit/design.md
Spec reference: openspec/changes/audit/specs/audit/spec.md (RA-1, RA-2)
"""

import uuid
from datetime import date

import pytest

from apps.accounts.audit import AuditEvent, AuditEventType
from apps.accounts.models import User
from apps.audit.context import audit_context, reset_audit_context
from apps.budgets.models import Budget
from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import Project
from apps.researchers.models import Researcher


@pytest.fixture(autouse=True)
def _clear_context():
    """Ensure the request-scoped audit context never leaks between tests."""
    reset_audit_context()
    yield
    reset_audit_context()


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name="Universidad Test", code="UTEST")


@pytest.fixture
def center(db, institution) -> ResearchCenter:
    return ResearchCenter.objects.create(institution=institution, name="AI Lab", code="AI")


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(email="audit@test.com", auth_source="local", password="pass")


@pytest.fixture
def researcher(db, institution) -> Researcher:
    return _make_researcher(institution, first_name="Ana")


def _make_researcher(institution, **overrides):
    """Create a Researcher with minimal required fields."""
    defaults = {
        "institution": institution,
        "first_name": "Ana",
        "last_name": "Lopez",
        "document_type": "CC",
        "document_number": f"DN-{uuid.uuid4().hex[:8]}",
        "primary_email": f"ana.{uuid.uuid4().hex[:4]}@test.edu",
    }
    defaults.update(overrides)
    return Researcher.objects.create(**defaults)


def _make_project(institution, center, researcher, **overrides):
    defaults = {
        "institution": institution,
        "center": center,
        "principal_investigator": researcher,
        "title": "Test Project",
        "abstract": "An abstract",
        "objectives": "Objectives",
        "methodology": "Methodology",
        "expected_results": "Results",
        "keywords": "test",
        "start_date": date(2026, 1, 1),
        "estimated_end_date": date(2026, 12, 31),
    }
    defaults.update(overrides)
    return Project.objects.create(**defaults)


# ──────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────


class TestCreateSignal:
    """CREATE events are emitted on model creation."""

    def test_create_researcher_emits_event(self, db, institution, user):
        with audit_context(user=user, institution_id=institution.id, ip_address="10.0.0.1"):
            _make_researcher(institution, first_name="Ana")

        events = AuditEvent.objects.filter(event_type="CREATE")
        assert events.count() == 1
        event = events.first()
        assert event.entity_type == "researcher"
        assert event.entity_id is not None
        assert event.action == "CREATE"
        assert event.user == user
        assert event.institution_id == institution.id
        assert event.new_values.get("first_name") == "Ana"

    def test_create_project_derives_project_id(self, db, institution, center, researcher, user):
        with audit_context(user=user, institution_id=institution.id):
            project = _make_project(institution, center, researcher)

        event = AuditEvent.objects.get(event_type="CREATE", entity_type="project")
        assert event.entity_id == project.pk
        assert event.project_id == project.pk

    def test_create_budget_derives_project_id_via_relation(
        self, db, institution, center, researcher, user
    ):
        with audit_context(user=user, institution_id=institution.id):
            project = _make_project(institution, center, researcher)
            budget = Budget.objects.create(
                project=project,
                institution=institution,
                name="Budget 1",
                approved_amount=1000,
            )

        event = AuditEvent.objects.get(event_type="CREATE", entity_type="budget")
        assert event.entity_id == budget.pk
        assert event.project_id == project.pk


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────


class TestUpdateSignal:
    """UPDATE events are emitted on save with changes, with old/new diff."""

    def test_update_emits_event_with_diff(self, db, institution, user):
        with audit_context(user=user, institution_id=institution.id):
            researcher = _make_researcher(institution, first_name="Ana")
        AuditEvent.objects.all().delete()

        with audit_context(user=user, institution_id=institution.id):
            researcher.first_name = "Ana Maria"
            researcher.save()

        events = AuditEvent.objects.filter(event_type="UPDATE")
        assert events.count() == 1
        event = events.first()
        assert event.entity_type == "researcher"
        assert event.action == "UPDATE"
        assert event.old_values.get("first_name") == "Ana"
        assert event.new_values.get("first_name") == "Ana Maria"

    def test_no_event_on_save_without_changes(self, db, institution, user):
        with audit_context(user=user, institution_id=institution.id):
            researcher = _make_researcher(institution, first_name="Ana")
        AuditEvent.objects.all().delete()

        with audit_context(user=user, institution_id=institution.id):
            researcher.save()

        assert AuditEvent.objects.count() == 0


# ──────────────────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────────────────


class TestDeleteSignal:
    """DELETE events are emitted on model deletion."""

    def test_delete_emits_event(self, db, institution, user):
        with audit_context(user=user, institution_id=institution.id):
            researcher = _make_researcher(institution, first_name="Ana")
        AuditEvent.objects.all().delete()

        with audit_context(user=user, institution_id=institution.id):
            researcher.delete()

        events = AuditEvent.objects.filter(event_type="DELETE")
        assert events.count() == 1
        event = events.first()
        assert event.entity_type == "researcher"
        assert event.action == "DELETE"
        assert event.old_values.get("first_name") == "Ana"


# ──────────────────────────────────────────────────────────
# Ignored cases
# ──────────────────────────────────────────────────────────


class TestIgnoredCases:
    """Raw saves, missing institution, and AuditEvent itself are ignored."""

    def test_raw_save_is_ignored(self, db, institution, user, researcher):
        with audit_context(user=user, institution_id=institution.id):
            researcher.first_name = "Changed"
            # raw saves (e.g. fixture loading) must not emit events.
            from apps.audit import signals

            signals.pre_save_handler(sender=Researcher, instance=researcher, raw=True)
            signals.post_save_handler(
                sender=Researcher, instance=researcher, created=False, raw=True
            )

        assert AuditEvent.objects.count() == 0

    def test_missing_institution_context_is_ignored(self, db):
        # No audit context set -> institution_id is None -> signals skip.
        inst = Institution.objects.create(name="No Context U", code="NCU")
        _make_researcher(inst)
        assert AuditEvent.objects.count() == 0

    def test_audit_event_itself_not_tracked(self, db, institution, user):
        with audit_context(user=user, institution_id=institution.id):
            AuditEvent.objects.create(event_type=AuditEventType.LOGIN, user=user)

        assert AuditEvent.objects.filter(event_type="CREATE").count() == 0
        assert AuditEvent.objects.filter(event_type="UPDATE").count() == 0
