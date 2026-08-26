"""Signal receiver tests for PR 3 — Tasks + Signals (STRICT TDD, RED).

Covers the ten receiver paths (design.md — Data Flow; 5 entities ×
post_save / post_delete):

- ``post_save`` on each indexed model registers a ``transaction.on_commit``
  callback that enqueues ``index_document.delay(index_name, str(pk))``
- ``post_delete`` on each indexed model registers a ``transaction.on_commit``
  callback that enqueues ``delete_document.delay(index_name, str(pk))``
- the enqueue is deferred until commit (never runs inside the sender)
- enqueue errors are swallowed so the sender transaction always commits

Receivers are connected in ``apps.search.apps.ready()`` with
``dispatch_uid`` (ORM-only, no I/O inside receivers).

Spec reference:   meilisearch-module spec — RF-086..RF-089 / Advances
Design reference: meilisearch-module design — Data Flow / Async boundary
"""

from unittest import mock

from apps.calls.tests.conftest import CallFactory
from apps.products.tests.conftest import ProductFactory
from apps.progress.tests.conftest import ProgressReportFactory
from apps.projects.models import Project
from apps.projects.tests.conftest import ProjectFactory
from apps.researchers.tests.conftest import ResearcherFactory


def _run_on_commit(fn):
    """Inline on_commit: run registered callbacks immediately."""
    return fn()


class TestProjectSignals:
    def test_post_save_enqueues_index_document_on_commit(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.index_document.delay"
        ) as delay:
            project = ProjectFactory()

        on_commit.assert_called()
        delay.assert_any_call("projects", str(project.pk))

    def test_post_delete_enqueues_delete_document_on_commit(self, db):
        project = ProjectFactory()
        project_pk = str(project.pk)  # Django nulls pk after post_delete

        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.delete_document.delay"
        ) as delay:
            project.delete()

        on_commit.assert_called()
        delay.assert_any_call("projects", project_pk)

    def test_index_enqueue_deferred_until_commit(self, db):
        # on_commit is NOT mocked: the callback is registered but must not
        # run inside the sender transaction (rollback discards it).
        with mock.patch("apps.search.signals.index_document.delay") as delay:
            ProjectFactory()

        delay.assert_not_called()

    def test_enqueue_error_swallowed_so_sender_commits(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ), mock.patch(
            "apps.search.signals.index_document.delay",
            side_effect=RuntimeError("broker down"),
        ):
            project = ProjectFactory()  # must not raise

        assert Project.objects.filter(pk=project.pk).exists()


class TestResearcherSignals:
    def test_post_save_enqueues_index_document_on_commit(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.index_document.delay"
        ) as delay:
            researcher = ResearcherFactory()

        on_commit.assert_called()
        delay.assert_any_call("researchers", str(researcher.pk))

    def test_post_delete_enqueues_delete_document_on_commit(self, db):
        researcher = ResearcherFactory()
        researcher_pk = str(researcher.pk)  # Django nulls pk after post_delete

        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.delete_document.delay"
        ) as delay:
            researcher.delete()

        on_commit.assert_called()
        delay.assert_any_call("researchers", researcher_pk)


class TestProductSignals:
    def test_post_save_enqueues_index_document_on_commit(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.index_document.delay"
        ) as delay:
            product = ProductFactory()

        on_commit.assert_called()
        delay.assert_any_call("products", str(product.pk))

    def test_post_delete_enqueues_delete_document_on_commit(self, db):
        product = ProductFactory()
        product_pk = str(product.pk)  # Django nulls pk after post_delete

        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.delete_document.delay"
        ) as delay:
            product.delete()

        on_commit.assert_called()
        delay.assert_any_call("products", product_pk)


class TestCallSignals:
    def test_post_save_enqueues_index_document_on_commit(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.index_document.delay"
        ) as delay:
            call = CallFactory()

        on_commit.assert_called()
        delay.assert_any_call("calls", str(call.pk))

    def test_post_delete_enqueues_delete_document_on_commit(self, db):
        call = CallFactory()
        call_pk = str(call.pk)  # Django nulls pk after post_delete

        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.delete_document.delay"
        ) as delay:
            call.delete()

        on_commit.assert_called()
        delay.assert_any_call("calls", call_pk)


class TestAdvanceSignals:
    def test_post_save_enqueues_index_document_on_commit(self, db):
        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.index_document.delay"
        ) as delay:
            report = ProgressReportFactory()

        on_commit.assert_called()
        delay.assert_any_call("advances", str(report.pk))

    def test_post_delete_enqueues_delete_document_on_commit(self, db):
        report = ProgressReportFactory()
        report_pk = str(report.pk)  # Django nulls pk after post_delete

        with mock.patch(
            "apps.search.signals.transaction.on_commit", side_effect=_run_on_commit
        ) as on_commit, mock.patch(
            "apps.search.signals.delete_document.delay"
        ) as delay:
            report.delete()

        on_commit.assert_called()
        delay.assert_any_call("advances", report_pk)
