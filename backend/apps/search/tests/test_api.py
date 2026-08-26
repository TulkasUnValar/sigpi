"""Search API tests for PR 4 — API Layer (STRICT TDD, RED).

Covers the PR 4 API contract from the meilisearch-module spec:

- RF-090 Full-Text Search: ``GET /api/search/?q=&index=`` returns ranked
  matches; no matches → 200 with empty ``hits``.
- RF-091 Filtered Search: ``filters`` must be valid JSON and only the
  index's declared layout keys are accepted; malformed JSON, unknown
  index, and unsupported keys return 400.
- Tenant Isolation: a forged ``institution_id`` filter is never honored —
  the view injects ``institution_id == request.institution_id`` so the
  outgoing Meilisearch filter contains only the server-owned scope.
  Missing tenant context → 400 (middleware). Superusers may omit the
  scope.

Test pattern: ``django.test.Client`` + ``force_login`` + session
``institution_id`` (full middleware stack, matches audit test_api.py).
The Meilisearch client boundary is mocked
(``get_client().index().search()``) because the sync SDK transports over
``httpx2``, which the ``responses`` library cannot intercept (PR 3 note).
The mock returns a real ``SearchResults`` so the response serialization
(``processingTimeMs``, pagination metadata) is verified end-to-end.

Spec reference:   meilisearch-module spec — RF-090 / RF-091 / Tenant Isolation
Design reference: meilisearch-module design — Interfaces / Contracts
"""

import json
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse
from meilisearch_python_sdk.models.search import SearchResults

from apps.accounts.models import User
from apps.institutions.tests.conftest import InstitutionFactory


def _make_user(email: str, **extra) -> User:
    return User.objects.create_user(
        email=email, auth_source="local", password="pass", **extra
    )


def _login(client: Client, user: User, institution=None) -> None:
    client.force_login(user)
    session = client.session
    if institution is not None:
        session["institution_id"] = str(institution.pk)
    session.save()


def _search_url() -> str:
    return reverse("search:search")


def _search_results(hits, query, *, total=1, time_ms=1):
    """Real SDK SearchResults instance returned by the mocked client."""
    return SearchResults(
        hits=hits,
        query=query,
        processing_time_ms=time_ms,
        offset=0,
        limit=20,
        estimated_total_hits=total,
        total_hits=total,
    )


def _mock_search(get_client, results):
    """Return a real SearchResults from the mocked client boundary.

    The mocked ``search()`` MUST return a real ``SearchResults``: a bare
    MagicMock flows into DRF's JSON encoder, whose ``default()`` hits the
    ``hasattr(obj, 'tolist')`` branch and hands the C encoder a fresh
    MagicMock forever — an infinite C-level loop (never a RecursionError).
    """
    get_client.return_value.index.return_value.search.return_value = results
    return get_client.return_value.index.return_value.search


@pytest.mark.django_db
class TestSearchApiTenantIsolation:
    """Tenant scope is server-owned: injected, never client-forged."""

    def test_missing_tenant_returns_400(self):
        client = Client()
        _login(client, _make_user("tenantless@test.edu"))

        response = client.get(_search_url(), {"q": "biotecnología", "index": "projects"})

        assert response.status_code == 400
        assert response.json() == {"detail": "Active institution required."}

    def test_forged_institution_id_uses_server_scope_only(self):
        client = Client()
        institution_b = InstitutionFactory()
        _login(client, _make_user("tenant-b@test.edu"), institution_b)
        forged_a = InstitutionFactory()

        with mock.patch("apps.search.views.get_client") as get_client:
            search_mock = _mock_search(
                get_client, _search_results([], "biotecnología", total=0)
            )
            response = client.get(
                _search_url(),
                {
                    "q": "biotecnología",
                    "index": "projects",
                    "filters": json.dumps(
                        {"institution_id": str(forged_a.pk), "status": "aprobado"}
                    ),
                },
            )

        assert response.status_code == 200
        search_mock.assert_called_once()
        kwargs = search_mock.call_args.kwargs
        # Outgoing filter contains ONLY the server-owned tenant scope.
        assert kwargs["filter"] == [
            f"institution_id = '{institution_b.pk}'",
            "status = 'aprobado'",
        ]
        assert str(forged_a.pk) not in json.dumps(kwargs)

    def test_tenant_scope_injected_without_client_filters(self):
        client = Client()
        institution = InstitutionFactory()
        _login(client, _make_user("tenant-c@test.edu"), institution)

        with mock.patch("apps.search.views.get_client") as get_client:
            search_mock = _mock_search(get_client, _search_results([], "x", total=0))
            response = client.get(
                _search_url(), {"q": "x", "index": "researchers"}
            )

        assert response.status_code == 200
        kwargs = search_mock.call_args.kwargs
        assert kwargs["filter"] == [f"institution_id = '{institution.pk}'"]

    def test_superuser_may_omit_tenant_scope(self):
        client = Client()
        _login(
            client,
            User.objects.create_superuser(email="root@test.edu", password="pass"),
        )

        with mock.patch("apps.search.views.get_client") as get_client:
            search_mock = _mock_search(get_client, _search_results([], "x", total=0))
            response = client.get(_search_url(), {"q": "x", "index": "projects"})

        assert response.status_code == 200
        kwargs = search_mock.call_args.kwargs
        assert kwargs["filter"] is None


@pytest.mark.django_db
class TestSearchApiValidation:
    """index/filters validation — 400 on unknown index or bad filters."""

    def _logged_in(self):
        client = Client()
        institution = InstitutionFactory()
        _login(client, _make_user("valid@test.edu"), institution)
        return client, institution

    def test_missing_index_returns_400(self):
        client, _ = self._logged_in()

        response = client.get(_search_url(), {"q": "x"})

        assert response.status_code == 400
        assert "index" in response.json()["detail"].lower()

    def test_unknown_index_returns_400(self):
        client, _ = self._logged_in()

        response = client.get(_search_url(), {"q": "x", "index": "documents"})

        assert response.status_code == 400
        assert "documents" in response.json()["detail"]

    def test_malformed_filters_json_returns_400(self):
        client, _ = self._logged_in()

        response = client.get(
            _search_url(), {"q": "x", "index": "projects", "filters": "{not json"}
        )

        assert response.status_code == 400

    def test_non_object_filters_returns_400(self):
        client, _ = self._logged_in()

        response = client.get(
            _search_url(), {"q": "x", "index": "projects", "filters": "[1, 2]"}
        )

        assert response.status_code == 400

    def test_unsupported_filter_key_returns_400(self):
        client, _ = self._logged_in()

        # `line` is not a declared filter key for the calls index.
        response = client.get(
            _search_url(),
            {"q": "x", "index": "calls", "filters": json.dumps({"line": "X"})},
        )

        assert response.status_code == 400
        assert "line" in response.json()["detail"]

    def test_layout_filter_keys_accepted_and_combined(self):
        client, institution = self._logged_in()

        with mock.patch("apps.search.views.get_client") as get_client:
            search_mock = _mock_search(get_client, _search_results([], "x", total=0))
            response = client.get(
                _search_url(),
                {
                    "q": "x",
                    "index": "projects",
                    "filters": json.dumps({"status": "aprobado", "year": 2026}),
                },
            )

        assert response.status_code == 200
        kwargs = search_mock.call_args.kwargs
        assert kwargs["filter"] == [
            f"institution_id = '{institution.pk}'",
            "status = 'aprobado'",
            "year = 2026",
        ]


@pytest.mark.django_db
class TestSearchApiResults:
    """Ranked pass-through of the Meilisearch response."""

    def _search(self, *, query="biotecnología", results, institution=None):
        client = Client()
        _login(client, _make_user("results@test.edu"), institution or InstitutionFactory())
        with mock.patch("apps.search.views.get_client") as get_client:
            get_client.return_value.index.return_value.search.return_value = results
            return client.get(
                _search_url(), {"q": query, "index": "projects"}
            ), get_client.return_value.index.return_value.search

    def test_ranked_matches_passed_through(self):
        hits = [
            {"id": "1", "title": "Biotecnología aplicada", "_rankingScore": 0.91},
            {"id": "2", "title": "Taller de biotecnología", "_rankingScore": 0.62},
        ]
        results = _search_results(hits, "biotecnología", total=2, time_ms=3)

        response, search_mock = self._search(results=results)

        assert response.status_code == 200
        data = response.json()
        # Ranked matches preserved in Meilisearch order.
        assert data["hits"] == hits
        assert data["query"] == "biotecnología"
        assert data["processingTimeMs"] == 3
        assert data["estimatedTotalHits"] == 2
        assert data["offset"] == 0
        assert data["limit"] == 20
        search_mock.assert_called_once()
        assert search_mock.call_args.args[0] == "biotecnología"
        assert search_mock.call_args.kwargs["offset"] == 0
        assert search_mock.call_args.kwargs["limit"] == 20

    def test_no_matches_returns_200_empty(self):
        results = _search_results([], "xyzzy", total=0)

        response, _ = self._search(query="xyzzy", results=results)

        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == []
        assert data["estimatedTotalHits"] == 0
