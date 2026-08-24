"""
Admin tests for budgets app — STRICT TDD (RED phase).

Tests verify that all 5 budget models are properly registered in Django
admin with list_display, search_fields, list_filter, and raw_id_fields.

RED PHASE: Tests fail because admin.py does not exist.

Design reference: openspec/changes/budgets/design.md — Admin
"""

import pytest
from django.contrib.admin.sites import site as admin_site

from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    FundingSource,
)


class TestAdminRegistration:
    """All 5 models must be registered in admin site."""

    @pytest.mark.parametrize(
        "model",
        [Budget, BudgetLine, FundingSource, BudgetExecution, BudgetAttachment],
    )
    def test_model_is_registered(self, db, model):
        assert model in admin_site._registry, f"{model.__name__} is not registered in admin site"


class TestBudgetAdmin:
    def test_list_display(self, db):
        admin_class = admin_site._registry[Budget]
        expected = ["name", "status", "project", "institution", "approved_amount", "created_at"]
        for field in expected:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        admin_class = admin_site._registry[Budget]
        assert "name" in admin_class.search_fields

    def test_list_filter(self, db):
        admin_class = admin_site._registry[Budget]
        assert "status" in admin_class.list_filter
        assert "institution" in admin_class.list_filter

    def test_raw_id_fields(self, db):
        admin_class = admin_site._registry[Budget]
        assert "project" in admin_class.raw_id_fields
        assert "institution" in admin_class.raw_id_fields


class TestBudgetLineAdmin:
    def test_list_display(self, db):
        admin_class = admin_site._registry[BudgetLine]
        expected = ["budget", "name", "approved_amount"]
        for field in expected:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        admin_class = admin_site._registry[BudgetLine]
        assert "name" in admin_class.search_fields

    def test_raw_id_fields(self, db):
        admin_class = admin_site._registry[BudgetLine]
        assert "budget" in admin_class.raw_id_fields


class TestFundingSourceAdmin:
    def test_list_display(self, db):
        admin_class = admin_site._registry[FundingSource]
        expected = ["project", "name", "amount"]
        for field in expected:
            assert field in admin_class.list_display

    def test_raw_id_fields(self, db):
        admin_class = admin_site._registry[FundingSource]
        assert "project" in admin_class.raw_id_fields


class TestBudgetExecutionAdmin:
    def test_list_display(self, db):
        admin_class = admin_site._registry[BudgetExecution]
        expected = ["line", "amount", "executed_at", "authorized_by", "authorized_at"]
        for field in expected:
            assert field in admin_class.list_display

    def test_list_filter(self, db):
        admin_class = admin_site._registry[BudgetExecution]
        assert "executed_at" in admin_class.list_filter

    def test_raw_id_fields(self, db):
        admin_class = admin_site._registry[BudgetExecution]
        assert "line" in admin_class.raw_id_fields
        assert "authorized_by" in admin_class.raw_id_fields


class TestBudgetAttachmentAdmin:
    def test_list_display(self, db):
        admin_class = admin_site._registry[BudgetAttachment]
        expected = ["budget", "name", "doc_type", "external_url", "created_at"]
        for field in expected:
            assert field in admin_class.list_display

    def test_search_fields(self, db):
        admin_class = admin_site._registry[BudgetAttachment]
        assert "name" in admin_class.search_fields

    def test_list_filter(self, db):
        admin_class = admin_site._registry[BudgetAttachment]
        assert "doc_type" in admin_class.list_filter

    def test_raw_id_fields(self, db):
        admin_class = admin_site._registry[BudgetAttachment]
        assert "budget" in admin_class.raw_id_fields
