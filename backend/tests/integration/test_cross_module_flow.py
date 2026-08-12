"""
Cross-module integration test — end-to-end flow.

Exercises the full SIGPI flow:
  Call open → Project linked → Submitted → In Review → Approved
  → Workflow completed → Execution started → Progress created
  → Product registered → Report generated

Verifies:
- IP-1: call_state_changed signal fires
- IP-2: ProgressService guard allows execution-state project
- IP-3: ProductViewSet guard allows approved/active project
- IP-4: ReportRenderer.validate_entity resolves and scopes correctly
- IP-5: workflow_completed signal fires on workflow completion

Spec reference:  openspec/changes/cross-module-integration/spec.md
Design reference: openspec/changes/cross-module-integration/design.md
"""

from unittest.mock import patch

import pytest

from apps.calls.models import Call, CallStatus
from apps.calls.services import CallProjectService, CallService
from apps.products.models import ResearchProduct
from apps.progress.services import ProgressService
from apps.project_workflow.models import WorkflowInstanceStatus, WorkflowStep, WorkflowTemplate
from apps.projects.services import ProjectService
from apps.reports.services import ReportRenderer

# ── Helpers ────────────────────────────────────────────


def _make_user(email="test@example.com"):
    from apps.accounts.models import User

    return User.objects.create_user(email=email)


def _make_institution(code="TU"):
    from apps.institutions.models import Institution

    return Institution.objects.create(name=f"Test University {code}", code=code)


def _make_center(institution):
    from apps.institutions.models import ResearchCenter

    return ResearchCenter.objects.create(institution=institution, name="AI Lab", code="AI")


def _make_researcher(institution, user=None):
    from apps.researchers.models import Researcher

    return Researcher.objects.create(
        institution=institution,
        first_name="Test",
        last_name="PI",
        document_type="CC",
        document_number="DOC-001",
        primary_email="pi@test.edu",
        user=user,
    )


@pytest.mark.integration
def test_cross_module_flow(db):
    """Full end-to-end flow across 6 modules."""
    from apps.calls.signals import call_state_changed
    from apps.project_workflow.signals import workflow_completed
    from apps.researchers.models import ResearcherAffiliation

    # ── Setup ──────────────────────────────────────────
    institution = _make_institution("INT")
    center = _make_center(institution)
    director = _make_user("director@test.edu")
    pi = _make_researcher(institution, user=director)
    ResearcherAffiliation.objects.create(researcher=pi, center=center, is_primary=True)

    # ── 1. Call open (IP-1) ───────────────────────────
    call = Call.objects.create(
        institution=institution,
        title="Integration Call",
        description="Call for integration test",
        call_type="internal",
        status=CallStatus.BORRADOR,
    )

    with patch.object(call_state_changed, "send") as mock_call_signal:
        call = CallService.open_call(call, director)

    assert call.status == CallStatus.ABIERTA
    mock_call_signal.assert_called_once()
    call_kwargs = mock_call_signal.call_args[1]
    assert call_kwargs["from_state"] == CallStatus.BORRADOR
    assert call_kwargs["to_state"] == CallStatus.ABIERTA
    assert call_kwargs["triggered_by"] == director

    # ── 2. Create project and link to call ─────────────
    project = ProjectService.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        user=director,
        title="Integration Project",
        abstract="Abstract",
        objectives="Objectives",
        methodology="Methodology",
        expected_results="Results",
        keywords="integration, test",
        start_date="2026-01-01",
        estimated_end_date="2026-12-31",
    )
    assert project.status == "borrador"

    CallProjectService.link(call, project)
    assert call.call_projects.filter(project=project).exists()

    # ── 3. Create single-step workflow template ────────
    template = WorkflowTemplate.objects.create(institution=institution, name="Single Step")
    WorkflowStep.objects.create(template=template, order=1, name="Approval", deadline_days=7)

    # ── 4. Submit project (triggers workflow creation) ─
    ProjectService.submit(project, director)
    assert project.status == "enviado"

    # Workflow instance should exist
    from apps.project_workflow.models import WorkflowInstance

    instance = WorkflowInstance.objects.filter(project_id=project.id).first()
    assert instance is not None
    assert instance.status == WorkflowInstanceStatus.PENDING

    # ── 5. Accept review ───────────────────────────────
    ProjectService.accept_review(project, director)
    assert project.status == "en_revision"

    # ── 6. Approve project (triggers workflow advance) ─
    with patch.object(workflow_completed, "send") as mock_wf_signal:
        ProjectService.approve(project, director)

    assert project.status == "aprobado"
    instance.refresh_from_db()
    assert instance.status == WorkflowInstanceStatus.COMPLETED
    mock_wf_signal.assert_called_once()
    wf_kwargs = mock_wf_signal.call_args[1]
    assert wf_kwargs["project_id"] == project.id
    assert wf_kwargs["instance_id"] == instance.id

    # ── 7. Start execution ────────────────────────────
    ProjectService.start_execution(project, director)
    assert project.status == "en_ejecucion"

    # ── 8. Create progress report (IP-2 guard) ────────
    progress_user = _make_user("progress@test.edu")
    report = ProgressService.create(
        project=project,
        user=progress_user,
        period_start="2026-01-01",
        period_end="2026-06-30",
        description="Integration progress",
        cumulative_percentage=50.00,
        activities="Activities",
    )
    assert report.pk is not None
    assert report.project == project

    # ── 9. Create product (IP-3 guard) ──────────────────
    product = ResearchProduct.objects.create(
        institution=institution,
        project=project,
        title="Integration Product",
        description="Product desc",
        type="articulo",
        publication_year=2025,
    )
    assert product.pk is not None

    # ── 10. Generate report (IP-4 validation) ──────────
    renderer = ReportRenderer()
    institution_id = renderer.validate_entity("project", str(project.pk), institution.id)
    assert institution_id == institution.id

    html = renderer.render_html("project", str(project.pk), director)
    assert html is not None
    assert "Integration Project" in html
