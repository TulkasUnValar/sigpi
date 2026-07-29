"""
Unit tests for calls FilterSet (Phase 3.11).

Covers CallFilter:
- status (ChoiceFilter)
- call_type (ChoiceFilter)
- submission_start_after / submission_start_before (DateFilter)
- evaluation_start_after / evaluation_start_before (DateFilter)
- title (CharFilter icontains)

Strict TDD: this file is written BEFORE filters.py exists.
Expected failure: ImportError (filters.py not created yet).
"""

import datetime

import pytest

from apps.calls.models import Call

# ──────────────────────────────────────────────────────────
# CallFilter
# ──────────────────────────────────────────────────────────


class TestCallFilter:
    """CallFilter: status, type, date ranges, title search."""

    @pytest.mark.django_db
    def test_filter_by_status(self):
        """Filtering by status must return only matching calls."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_abierta = CallFactory(status="abierta")
        CallFactory(status="borrador")

        qs = CallFilter(data={"status": "abierta"}, queryset=Call.objects.all()).qs
        assert qs.count() == 1
        assert call_abierta in qs

    @pytest.mark.django_db
    def test_filter_by_call_type(self):
        """Filtering by call_type must return only matching calls."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_external = CallFactory(call_type="external", external_entity="Entity")
        CallFactory(call_type="internal")

        qs = CallFilter(data={"call_type": "external"}, queryset=Call.objects.all()).qs
        assert qs.count() == 1
        assert call_external in qs

    @pytest.mark.django_db
    def test_filter_by_title_contains(self):
        """Filtering by title must use icontains."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_alpha = CallFactory(title="Alpha Call")
        CallFactory(title="Beta Call")

        qs = CallFilter(data={"title": "alpha"}, queryset=Call.objects.all()).qs
        assert qs.count() == 1
        assert call_alpha in qs

    @pytest.mark.django_db
    def test_filter_by_submission_start_after(self):
        """submission_start_after must filter gte."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_later = CallFactory(submission_start=datetime.date(2026, 6, 1))
        CallFactory(submission_start=datetime.date(2026, 1, 1))

        qs = CallFilter(
            data={"submission_start_after": "2026-05-01"},
            queryset=Call.objects.all(),
        ).qs
        assert qs.count() == 1
        assert call_later in qs

    @pytest.mark.django_db
    def test_filter_by_submission_start_before(self):
        """submission_start_before must filter lte."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_earlier = CallFactory(submission_start=datetime.date(2026, 1, 1))
        CallFactory(submission_start=datetime.date(2026, 6, 1))

        qs = CallFilter(
            data={"submission_start_before": "2026-05-01"},
            queryset=Call.objects.all(),
        ).qs
        assert qs.count() == 1
        assert call_earlier in qs

    @pytest.mark.django_db
    def test_filter_by_evaluation_start_range(self):
        """evaluation_start_after + evaluation_start_before must filter range."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        call_mid = CallFactory(evaluation_start=datetime.date(2026, 4, 15))
        CallFactory(evaluation_start=datetime.date(2026, 1, 1))
        CallFactory(evaluation_start=datetime.date(2026, 8, 1))

        qs = CallFilter(
            data={
                "evaluation_start_after": "2026-03-01",
                "evaluation_start_before": "2026-06-01",
            },
            queryset=Call.objects.all(),
        ).qs
        assert qs.count() == 1
        assert call_mid in qs

    @pytest.mark.django_db
    def test_no_filter_returns_all(self):
        """Empty filter data must return all calls."""
        from apps.calls.filters import CallFilter
        from apps.calls.tests.conftest import CallFactory

        CallFactory()
        CallFactory()

        qs = CallFilter(data={}, queryset=Call.objects.all()).qs
        assert qs.count() == 2
