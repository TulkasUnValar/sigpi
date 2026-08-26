"""Celery task tests for PR 3 — Tasks + Signals (STRICT TDD, RED).

Covers the task contract from design.md (Interfaces / Contracts):

- ``index_document(index_name, object_id)`` performs a fresh DB lookup
  and projects the row into Meilisearch via the sync client
- a missing object is harmless for index tasks (no client call, no raise)
- ``delete_document(index_name, object_id)`` removes the document by
  string ID and does not require the row to exist
- Meilisearch/client exceptions retry with exponential backoff
  (countdown ``60 * 2**retries``) up to ``max_retries``

The sync SDK transport is ``httpx2`` (a fork of httpx), which the
``responses`` library cannot intercept; per the design's testing
strategy the client boundary is mocked instead (mocked SDK/client).

Spec reference:   meilisearch-module spec — RF-086..RF-089 / Advances
Design reference: meilisearch-module design — Interfaces / Contracts
"""

import uuid
from unittest import mock

import pytest

from apps.projects.tests.conftest import ProjectFactory
from apps.search.tasks import delete_document, index_document


class TestIndexDocumentTask:
    """index_document projects a fresh DB row; missing rows are harmless."""

    def test_index_document_looks_up_fresh_row_and_adds_document(self, db):
        project = ProjectFactory(title="Biotecnología aplicada")

        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = index_document("projects", str(project.pk))

        index = get_client.return_value.index
        index.assert_called_once_with("projects")
        index.return_value.add_documents.assert_called_once()
        (document,) = index.return_value.add_documents.call_args.args[0]
        assert document["id"] == str(project.pk)
        assert document["title"] == "Biotecnología aplicada"
        assert document["institution_id"] == str(project.institution_id)
        assert result == {"status": "indexed", "index": "projects", "id": str(project.pk)}

    def test_index_document_missing_object_is_harmless(self, db):
        missing_id = str(uuid.uuid4())

        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = index_document("projects", missing_id)

        assert result is None
        get_client.return_value.index.assert_not_called()

    def test_index_document_client_error_retries_with_exponential_countdown(self, db):
        project = ProjectFactory()
        error = RuntimeError("meili down")

        with mock.patch("apps.search.tasks.get_client") as get_client:
            get_client.return_value.index.return_value.add_documents.side_effect = error
            with mock.patch.object(
                index_document, "retry", side_effect=error
            ) as retry_mock:
                with pytest.raises(RuntimeError):
                    index_document("projects", str(project.pk))

        retry_mock.assert_called_once()
        kwargs = retry_mock.call_args.kwargs
        assert kwargs["countdown"] == 60 * (2**0)  # first attempt: 60×2^0
        assert isinstance(kwargs["exc"], RuntimeError)

    def test_index_document_retry_countdown_doubles_per_retry(self, db):
        project = ProjectFactory()
        error = RuntimeError("still down")

        with mock.patch("apps.search.tasks.get_client") as get_client:
            get_client.return_value.index.return_value.add_documents.side_effect = error
            with mock.patch.object(
                index_document, "retry", side_effect=error
            ) as retry_mock:
                # Second attempt (retries=1): countdown must be 60×2^1.
                # apply() runs eagerly and captures the failure (it does not
                # propagate — task_eager_propagates is False in tests).
                result = index_document.apply(
                    args=["projects", str(project.pk)], retries=1
                )

        assert result.state == "FAILURE"
        assert retry_mock.call_args.kwargs["countdown"] == 60 * (2**1)


class TestDeleteDocumentTask:
    """delete_document removes by string ID; no DB row required."""

    def test_delete_document_removes_by_string_id(self, db):
        project = ProjectFactory()

        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = delete_document("projects", str(project.pk))

        index = get_client.return_value.index
        index.assert_called_once_with("projects")
        index.return_value.delete_document.assert_called_once_with(str(project.pk))
        assert result == {"status": "deleted", "index": "projects", "id": str(project.pk)}

    def test_delete_document_does_not_require_existing_row(self):
        missing_id = str(uuid.uuid4())

        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = delete_document("calls", missing_id)

        get_client.return_value.index.return_value.delete_document.assert_called_once_with(
            missing_id
        )
        assert result["id"] == missing_id

    def test_delete_document_client_error_retries_with_exponential_countdown(self):
        error = RuntimeError("delete failed")

        with mock.patch("apps.search.tasks.get_client") as get_client:
            get_client.return_value.index.return_value.delete_document.side_effect = error
            with mock.patch.object(
                delete_document, "retry", side_effect=error
            ) as retry_mock:
                with pytest.raises(RuntimeError):
                    delete_document("products", str(uuid.uuid4()))

        kwargs = retry_mock.call_args.kwargs
        assert kwargs["countdown"] == 60 * (2**0)
        assert isinstance(kwargs["exc"], RuntimeError)


class TestTaskRetryContract:
    """Retry contract shared by both tasks (spec NFR / design)."""

    def test_index_task_allows_up_to_three_retries(self):
        assert index_document.max_retries == 3

    def test_delete_task_allows_up_to_three_retries(self):
        assert delete_document.max_retries == 3
