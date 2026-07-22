"""
Factory-boy factories for the reports (informes) module.

Provides ergonomic test data generation for Report and ReportApproval.

Spec reference:   sdd/reports/spec
Design reference: openspec/changes/reports/design.md

RED PHASE: Factories reference model fields that don't exist yet.
"""

import factory
from factory.django import DjangoModelFactory

# ═══════════════════════════════════════════════════
# User factory (inline — decoupled from accounts tests)
# ═══════════════════════════════════════════════════


class UserFactory(DjangoModelFactory):
    """Minimal User factory for reports tests."""

    email = factory.Sequence(lambda n: f"report-user-{n}@test.edu")
    is_active = True

    class Meta:
        model = "accounts.User"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        return user_model.objects.create_user(*args, **kwargs)


class ReportFactory(DjangoModelFactory):
    """Factory for Report — generic report with type + entity_id."""

    report_type = "project"
    entity_id = factory.Faker("uuid4")
    institution = factory.SubFactory("apps.institutions.tests.conftest.InstitutionFactory")
    created_by = factory.SubFactory(UserFactory)
    status = "generated"
    version = 1

    class Meta:
        model = "reports.Report"


class ReportApprovalFactory(DjangoModelFactory):
    """Factory for ReportApproval — approval with metadata."""

    report = factory.SubFactory(ReportFactory)
    approved_by = factory.SubFactory(UserFactory)
    report_version = 1

    class Meta:
        model = "reports.ReportApproval"
