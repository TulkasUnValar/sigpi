"""Celery tasks for the search module — Meilisearch index/delete.

Task contract (design.md — Interfaces / Contracts):

- ``index_document(index_name, object_id, institution_id)`` performs a fresh DB
  lookup and projects the row via the indexers; the lookup runs inside an
  explicit tenant context because the indexed tables are RLS-protected and a
  Celery worker has no request. ``institution_id`` is passed by the enqueuing
  receiver, which still has the request/audit context; a missing value fails
  loudly instead of silently indexing nothing. A missing object is harmless
  (warning logged, no client call, no raise).
- ``delete_document(index_name, object_id)`` removes the document by
  string ID — no DB row is required.
- Meilisearch/client exceptions call ``self.retry(exc=..., countdown=60 * 2**retries)``
  up to ``max_retries`` (exponential backoff, same contract as the
  notifications dispatch task).
"""

import logging

from celery import shared_task
from django.db import connection

from apps.calls.models import Call
from apps.products.models import ResearchProduct
from apps.progress.models import ProgressReport
from apps.projects.models import Project
from apps.researchers.models import Researcher
from apps.search.client import get_client
from apps.search.indexers import to_document
from config.tenant_context import tenant_context

logger = logging.getLogger(__name__)

# Retry contract (design): up to 3 retries, exponential backoff 60×2^n.
MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 60

# Index name → model class — keys must match INDEXERS/INDEX_CONFIG.
INDEX_MODELS: dict[str, type] = {
    "projects": Project,
    "researchers": Researcher,
    "products": ResearchProduct,
    "calls": Call,
    "advances": ProgressReport,
}


@shared_task(bind=True, name="index_document", max_retries=MAX_RETRIES)
def index_document(self, index_name, object_id, institution_id=None):
    """Project a fresh DB row into the Meilisearch index.

    ``institution_id`` is a required argument in practice: it is passed by the
    enqueuing receiver, which still has the request/audit context. It has a
    default only so a missing argument reaches the explicit guard below instead
    of raising a bare ``TypeError``.

    Missing rows are harmless: the row may have been rolled back or
    deleted before the task ran, so we skip with a warning instead of
    failing the queue. Meilisearch/client errors retry with backoff.
    """
    if not institution_id:
        # Fail loudly. Without a tenant context the RLS-protected model read
        # returns nothing, the task logs "not found; skipping" and the search
        # index silently stops tracking the entity — the exact silent omission
        # this change removes. Raising surfaces it in Celery's failure state and
        # traceback; this is a programming error, not a transient fault, so it
        # must not be retried.
        raise ValueError(
            "index_document requires institution_id; the enqueuer must pass it "
            "(the task cannot discover it from a protected table)."
        )

    model = INDEX_MODELS[index_name]
    with tenant_context(connection, institution_id):
        try:
            instance = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            logger.warning("Search index: %s object %s not found; skipping", index_name, object_id)
            return None

        document = to_document(index_name, instance)
        try:
            get_client().index(index_name).add_documents([document])
        except Exception as exc:
            logger.exception("Meilisearch index failed for %s %s", index_name, object_id)
            raise self.retry(
                exc=exc,
                countdown=RETRY_BACKOFF_BASE_SECONDS * (2**self.request.retries),
            )
        return {"status": "indexed", "index": index_name, "id": str(instance.pk)}


@shared_task(bind=True, name="delete_document", max_retries=MAX_RETRIES)
def delete_document(self, index_name, object_id):
    """Remove the document by string ID (Meilisearch primary keys are strings).

    The row may already be gone from the DB — deletion removes by ID and
    does not require a fresh lookup. Client errors retry with backoff.
    """
    try:
        get_client().index(index_name).delete_document(str(object_id))
    except Exception as exc:
        logger.exception("Meilisearch delete failed for %s %s", index_name, object_id)
        raise self.retry(
            exc=exc,
            countdown=RETRY_BACKOFF_BASE_SECONDS * (2**self.request.retries),
        )
    return {"status": "deleted", "index": index_name, "id": str(object_id)}
