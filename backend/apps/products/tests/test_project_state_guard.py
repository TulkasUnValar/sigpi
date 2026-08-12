"""
Project-state guard tests for products module — STRICT TDD (RED phase).

Tests define expected behavior of the project-state guard in
ResearchProductViewSet.perform_create():
- Rejects projects in pre-approval states (borrador, enviado, en_revision, observado)
- Allows projects in approved or active states (aprobado, en_ejecucion, suspendido, finalizado, en_cierre)

Spec reference:  openspec/changes/cross-module-integration/spec.md — FR-003, BR-002
Design reference: openspec/changes/cross-module-integration/design.md — IP-3
"""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter
from apps.projects.models import Project
from apps.researchers.models import Researcher

# ── Helpers ────────────────────────────────────────────


def _login(client, user, institution):
    """Login and set active institution in session."""
    client.force_login(user)
    session = client.session
    session["institution_id"] = str(institution.pk)
    session.save()


def _make_researcher(institution, **kwargs):
    defaults = {
        "first_name": "Test",
        "last_name": "Researcher",
        "document_type": "CC",
        "document_number": f"RES-{uuid.uuid4().hex[:8]}",
        "primary_email": f"res-{uuid.uuid4().hex[:4]}@test.edu",
    }
    defaults.update(kwargs)
    return Researcher.objects.create(institution=institution, **defaults)


def _make_project(institution, center, pi, status="borrador"):
    from datetime import date, timedelta

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
        start_date=date.today(),
        estimated_end_date=date.today() + timedelta(days=365),
        status=status,
    )


# ──────────────────────────────────────────────
# Products state guard (IP-3)
# ──────────────────────────────────────────────


class TestProductsProjectStateGuard:
    """ResearchProductViewSet.perform_create() guarded by project approval state."""

    @pytest.fixture
    def api_client(self):
        return Client()

    @pytest.fixture
    def institution(self, db):
        return Institution.objects.create(name="Guard Inst", code="GI001")

    @pytest.fixture
    def center(self, db, institution):
        return ResearchCenter.objects.create(institution=institution, name="Lab", code="LAB")

    @pytest.fixture
    def admin_user(self, db, institution):
        role = Role.objects.get(name="Admin Institucional")
        user = User.objects.create_user(email="admin@test.edu", auth_source="local", password="p")
        InstitutionMembership.objects.create(
            user=user, institution=institution, role=role, is_active=True
        )
        return user

    @pytest.fixture
    def pi(self, db, institution):
        return _make_researcher(institution)

    # ── Blocked states ───────────────────────────

    @pytest.mark.parametrize(
        "blocked_status",
        ["borrador", "enviado", "en_revision", "observado"],
    )
    def test_create_rejects_pre_approval_project(self, db, api_client, institution, center, admin_user, pi, blocked_status):
        """perform_create raises PermissionDenied for pre-approval projects."""
        project = _make_project(institution, center, pi, status=blocked_status)
        _login(api_client, admin_user, institution)

        url = reverse("products:product-list")
        data = {
            "title": "New Product",
            "description": "Desc",
            "type": "articulo",
            "publication_year": 2025,
            "project": str(project.id),
        }
        response = api_client.post(url, data, content_type="application/json")

        assert response.status_code == 403
        body = response.json()
        assert "detail" in body
        assert "approved or active projects" in body["detail"]

    # ── Allowed states ───────────────────────────

    @pytest.mark.parametrize(
        "allowed_status",
        ["aprobado", "en_ejecucion", "suspendido", "finalizado", "en_cierre"],
    )
    def test_create_allows_approved_and_active(self, db, api_client, institution, center, admin_user, pi, allowed_status):
        """perform_create succeeds for approved-or-active projects."""
        project = _make_project(institution, center, pi, status=allowed_status)
        _login(api_client, admin_user, institution)

        url = reverse("products:product-list")
        data = {
            "title": "New Product",
            "description": "Desc",
            "type": "articulo",
            "publication_year": 2025,
            "project": str(project.id),
        }
        response = api_client.post(url, data, content_type="application/json")

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["title"] == "New Product"
