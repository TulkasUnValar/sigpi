"""
Project-state guard tests for progress (advances) module — STRICT TDD (RED phase).

Tests define expected behavior of `_validate_project_state_for_progress`:
- Rejects projects in pre-execution states (borrador, enviado, en_revision, observado)
- Allows projects in execution or later states (en_ejecucion, suspendido, finalizado, en_cierre, cerrado)

Spec reference:  openspec/changes/cross-module-integration/spec.md — FR-002, BR-001
Design reference: openspec/changes/cross-module-integration/design.md — IP-2
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.projects.models import Project

# ── Helpers ────────────────────────────────────────────


def _make_user():
    from apps.accounts.models import User

    return User.objects.create_user(email=f"user_{User.objects.count()}@test.edu")


def _make_project(institution, center, pi, status="borrador"):
    return Project.objects.create(
        institution=institution,
        center=center,
        principal_investigator=pi,
        title="Guard Test Project",
        abstract="Test abstract",
        objectives="Test objectives",
        methodology="Test methodology",
        expected_results="Test results",
        keywords="test, guard",
        start_date="2026-01-01",
        estimated_end_date="2026-12-31",
        status=status,
    )


# ──────────────────────────────────────────────
# Progress state guard (IP-2)
# ──────────────────────────────────────────────


class TestProgressProjectStateGuard:
    """ProgressService.create() guarded by project execution-state check."""

    def _setup(self):
        from apps.institutions.models import Institution, ResearchCenter
        from apps.researchers.models import Researcher

        institution = Institution.objects.create(name="Guard Inst", code="GI001")
        center = ResearchCenter.objects.create(institution=institution, name="Lab", code="LAB")
        user = _make_user()
        pi = Researcher.objects.create(user=user, institution=institution, first_name="PI", last_name="Test")
        return institution, center, pi

    # ── Blocked states ───────────────────────────

    @pytest.mark.parametrize(
        "blocked_status",
        ["borrador", "enviado", "en_revision", "observado"],
    )
    def test_create_rejects_pre_execution_project(self, db, blocked_status):
        """ProgressService.create() raises ValidationError for pre-execution projects."""
        from apps.progress.services import ProgressService

        institution, center, pi = self._setup()
        project = _make_project(institution, center, pi, status=blocked_status)
        user = _make_user()

        with pytest.raises(ValidationError, match="execution or later states"):
            ProgressService.create(
                project=project,
                user=user,
                period_start="2026-01-01",
                period_end="2026-06-30",
                description="Test",
                cumulative_percentage=Decimal("50"),
                activities="Test",
            )

    # ── Allowed states ───────────────────────────

    @pytest.mark.parametrize(
        "allowed_status",
        ["en_ejecucion", "suspendido", "finalizado", "en_cierre", "cerrado"],
    )
    def test_create_allows_execution_and_later(self, db, allowed_status):
        """ProgressService.create() succeeds for execution-or-later projects."""
        from apps.progress.services import ProgressService

        institution, center, pi = self._setup()
        project = _make_project(institution, center, pi, status=allowed_status)
        user = _make_user()

        report = ProgressService.create(
            project=project,
            user=user,
            period_start="2026-01-01",
            period_end="2026-06-30",
            description="Test",
            cumulative_percentage=Decimal("50"),
            activities="Test",
        )
        assert report.pk is not None
        assert report.project == project
        assert report.status == "borrador"
