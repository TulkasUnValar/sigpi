"""Reindex all Meilisearch indexes (SIGPI §6.11).

Creates indexes, applies settings (searchable/filterable attributes), and
backfills existing data. Designed to be idempotent and safe to run multiple
times.

Usage:
    python manage.py reindex_search
    python manage.py reindex_search --index projects
    python manage.py reindex_search --recreate

The ``--index`` flag targets a single index (projects|researchers|products|
calls|advances). The ``--recreate`` flag deletes and recreates indexes instead
of just updating settings.

RLS handling: queries run inside ``tenant_context`` per institution because the
indexed tables are row-level security protected and a management command has no
request context. The command iterates all institutions and indexes each
tenant's data separately.
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.institutions.models import Institution
from apps.search.client import get_client
from apps.search.indexers import INDEX_CONFIG, to_document
from apps.search.tasks import INDEX_MODELS
from config.tenant_context import tenant_context

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reindex Meilisearch indexes: create, apply settings, backfill data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--index",
            type=str,
            choices=list(INDEX_CONFIG.keys()),
            help="Reindex only the specified index (default: all).",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Delete and recreate indexes instead of updating settings.",
        )

    def handle(self, *args, **options):
        target_index = options.get("index")
        recreate = options.get("recreate")

        indexes_to_process = (
            {target_index: INDEX_CONFIG[target_index]} if target_index else INDEX_CONFIG
        )

        try:
            client = get_client()
        except Exception as exc:
            raise CommandError(f"Failed to connect to Meilisearch: {exc}") from exc

        self.stdout.write(f"Processing {len(indexes_to_process)} index(es)...")

        for index_name, config in indexes_to_process.items():
            self._reindex_index(client, index_name, config, recreate)

        self.stdout.write(self.style.SUCCESS("Reindexing complete."))

    def _reindex_index(self, client, index_name, config, recreate):
        """Create/update a single index and backfill its documents."""
        self.stdout.write(f"\n[{index_name}] Starting reindex...")

        # Step 1: Create or recreate the index
        index = client.index(index_name)
        if recreate:
            self.stdout.write("  Deleting existing index...")
            try:
                client.delete_index(index_name)
            except Exception as exc:
                # Index may not exist yet; log but continue
                self.stdout.write(f"  Delete skipped (index may not exist): {exc}")

        self.stdout.write("  Creating index...")
        try:
            client.create_index(index_name, primary_key="id")
        except Exception as exc:
            # Index already exists; that's fine for idempotency
            if "already_exists" not in str(exc).lower():
                raise CommandError(f"Failed to create index {index_name}: {exc}") from exc
            self.stdout.write("  Index already exists, continuing...")

        # Step 2: Apply settings
        self.stdout.write("  Applying settings...")
        try:
            index.update_searchable_attributes(config["searchable"])
            index.update_filterable_attributes(config["filterable"])
        except Exception as exc:
            raise CommandError(f"Failed to apply settings for {index_name}: {exc}") from exc

        # Step 3: Backfill documents per institution (RLS requires tenant context)
        model = INDEX_MODELS[index_name]
        institutions = Institution.objects.all()
        total_indexed = 0

        for institution in institutions:
            with tenant_context(connection, institution.id):
                documents = []
                for instance in model.objects.all().iterator():
                    documents.append(to_document(index_name, instance))

                if documents:
                    try:
                        index.add_documents(documents)
                        total_indexed += len(documents)
                    except Exception as exc:
                        raise CommandError(
                            f"Failed to index documents for {index_name} "
                            f"(institution {institution.id}): {exc}"
                        ) from exc

        self.stdout.write(self.style.SUCCESS(f"  ✓ Indexed {total_indexed} document(s)"))
