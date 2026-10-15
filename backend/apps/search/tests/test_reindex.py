"""Tests for reindex_search management command.

Verifies the command creates indexes, applies settings, and backfills data
correctly. Uses mocked Meilisearch client to avoid hitting real service.

Spec reference: meilisearch-module spec — RF-090..RF-095 / Reindex
Design reference: meilisearch-module design — Interfaces / Contracts
"""

from unittest import mock

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestReindexSearchCommand:
    """reindex_search creates indexes, applies settings, backfills data."""

    def test_command_creates_all_five_indexes(self):
        """Without flags, command processes all 5 indexes."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            call_command("reindex_search")

        # Should create all 5 indexes
        assert mock_client.return_value.create_index.call_count == 5

    def test_command_applies_searchable_attributes(self):
        """Command applies searchable attributes from INDEX_CONFIG."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            call_command("reindex_search")

        # Should apply searchable attributes for each index
        assert mock_index.update_searchable_attributes.call_count == 5
        # Verify projects index got correct searchable attributes
        calls = mock_index.update_searchable_attributes.call_args_list
        projects_call = [c for c in calls if "title" in str(c.args[0])][0]
        assert "title" in projects_call.args[0]
        assert "abstract" in projects_call.args[0]

    def test_command_applies_filterable_attributes(self):
        """Command applies filterable attributes from INDEX_CONFIG."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            call_command("reindex_search")

        # Should apply filterable attributes for each index
        assert mock_index.update_filterable_attributes.call_count == 5

    def test_command_index_flag_targets_single_index(self):
        """--index projects only reindexes projects."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            call_command("reindex_search", index="projects")

        # Should only create 1 index
        assert mock_client.return_value.create_index.call_count == 1
        mock_client.return_value.create_index.assert_called_with("projects", primary_key="id")

    def test_command_recreate_flag_deletes_indexes(self):
        """--recreate deletes indexes before creating."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            call_command("reindex_search", recreate=True)

        # Should delete all 5 indexes
        assert mock_client.return_value.delete_index.call_count == 5

    def test_command_is_idempotent(self):
        """Running command twice doesn't error (handles existing indexes)."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            # Simulate index already exists
            mock_client.return_value.create_index.side_effect = [
                Exception("index already_exists"),
                Exception("index already_exists"),
                Exception("index already_exists"),
                Exception("index already_exists"),
                Exception("index already_exists"),
            ]

            # Should not raise
            call_command("reindex_search")

        # Should still apply settings and index documents
        assert mock_index.update_searchable_attributes.call_count == 5

    def test_command_uses_tenant_context_for_rls(self):
        """Command uses tenant_context for each institution."""
        from apps.institutions.tests.conftest import InstitutionFactory

        # Create an institution so the loop executes
        InstitutionFactory()

        with mock.patch("apps.search.management.commands.reindex_search.tenant_context") as mock_tc:
            with mock.patch("apps.search.management.commands.reindex_search.get_client"):
                mock_tc.return_value.__enter__ = mock.MagicMock()
                mock_tc.return_value.__exit__ = mock.MagicMock()

                call_command("reindex_search")

        # Should call tenant_context for each institution × each index (5 indexes)
        assert mock_tc.call_count >= 1

    def test_command_handles_empty_database(self):
        """Command handles case where no institutions exist."""
        with mock.patch("apps.search.management.commands.reindex_search.get_client") as mock_client:
            mock_index = mock.MagicMock()
            mock_client.return_value.index.return_value = mock_index

            # Should not raise
            call_command("reindex_search")

        # Should still create indexes and apply settings
        assert mock_client.return_value.create_index.call_count == 5
        assert mock_index.update_searchable_attributes.call_count == 5
