"""Real-PostgreSQL proof that ``index_document`` needs its tenant context.

These tests run as the least-privilege ``sigpi_app`` role (via the
``postgres_app_role`` fixture), so row-level security actually applies to the
model read the task performs. They prove the context is load-bearing:

- with the institution passed the task finds its Project and projects the
  Meilisearch document
- with no context (or the wrong institution) the same protected read finds
  nothing — the non-vacuity control that stops the positive case from passing
  even if the context did nothing

The task is exercised by calling it directly (no broker); the Meilisearch
client boundary is mocked, as in the mock-level task tests.
"""

import uuid
from unittest import mock

import pytest

from apps.projects.models import Project
from apps.projects.tests.conftest import ProjectFactory
from apps.search.tasks import index_document
from config import tenant_context

TENANT_GUC = "sigpi.institution_id"
BYPASS_GUC = "sigpi.bypass_rls"


def _set_rls(conn, institution_id, bypass):
    """Write both RLS GUCs at connection scope, exactly like production does."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [TENANT_GUC, "" if institution_id is None else str(institution_id)],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [BYPASS_GUC, "true" if bypass else "false"],
        )


class TestIndexDocumentTenantContext:
    """The passed institution is what makes the task's protected read visible."""

    def test_context_is_what_makes_the_read_visible(self, postgres_app_role):
        conn = postgres_app_role

        _set_rls(conn, None, bypass=True)
        project = ProjectFactory()
        tenant_context.clear(conn)

        # Non-vacuity control: the same protected read the task performs finds
        # nothing with no context. If the row were visible here, the positive
        # assertion below would prove nothing about the context.
        with pytest.raises(Project.DoesNotExist):
            Project.objects.get(pk=project.pk)

        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = index_document("projects", str(project.pk), str(project.institution_id))

        assert result == {"status": "indexed", "index": "projects", "id": str(project.pk)}
        (document,) = get_client.return_value.index.return_value.add_documents.call_args.args[0]
        assert document["id"] == str(project.pk)
        assert document["institution_id"] == str(project.institution_id)

    def test_wrong_institution_cannot_see_the_row(self, postgres_app_role):
        conn = postgres_app_role

        _set_rls(conn, None, bypass=True)
        project = ProjectFactory()
        tenant_context.clear(conn)

        # A context for another institution is as good as no context.
        with mock.patch("apps.search.tasks.get_client") as get_client:
            result = index_document("projects", str(project.pk), str(uuid.uuid4()))

        assert result is None
        get_client.return_value.index.assert_not_called()
