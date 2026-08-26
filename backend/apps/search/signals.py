"""Signal receivers for the search module — Meilisearch index/delete.

Receivers translate ORM save/delete events into Celery enqueues
(design.md — Data Flow / Async boundary):

- ORM only: receivers never touch the network; they only register a
  ``transaction.on_commit`` callback (< 50 ms, no I/O)
- Commit gating: the enqueue runs after the sender transaction commits,
  so uncommitted data is never indexed and rolled-back writes enqueue
  nothing
- Resilient: enqueue errors are logged and swallowed so a broker
  failure never breaks the sender's committed transaction
- Filtered per model: each receiver reacts only to its own entity
  (``post_save``/``post_delete``, ``sender=<model>``, ``dispatch_uid``)

Signals are connected in apps.search.apps.ready() (dispatch_uid keeps
them idempotent across reloads).
"""

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.calls.models import Call
from apps.products.models import ResearchProduct
from apps.progress.models import ProgressReport
from apps.projects.models import Project
from apps.researchers.models import Researcher
from apps.search.tasks import delete_document, index_document

logger = logging.getLogger(__name__)


def _enqueue(index_name, object_id, task):
    """Register a Celery enqueue to run once the sender transaction commits.

    The callback swallows and logs enqueue errors: the sender's
    committed transaction must never fail because of search indexing.
    """

    def _on_commit():
        try:
            task.delay(index_name, str(object_id))
        except Exception:
            logger.exception(
                "Failed to enqueue %s for %s %s", task.name, index_name, object_id
            )

    transaction.on_commit(_on_commit)


# ──────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────


@receiver(post_save, sender=Project, dispatch_uid="search.on_project_post_save")
def on_project_post_save(sender, instance, **kwargs):
    """Enqueue project indexing after the sender transaction commits."""
    _enqueue("projects", instance.pk, index_document)


@receiver(post_delete, sender=Project, dispatch_uid="search.on_project_post_delete")
def on_project_post_delete(sender, instance, **kwargs):
    """Enqueue project document removal after the sender transaction commits."""
    _enqueue("projects", instance.pk, delete_document)


# ──────────────────────────────────────────────
# Researchers
# ──────────────────────────────────────────────


@receiver(post_save, sender=Researcher, dispatch_uid="search.on_researcher_post_save")
def on_researcher_post_save(sender, instance, **kwargs):
    """Enqueue researcher indexing after the sender transaction commits."""
    _enqueue("researchers", instance.pk, index_document)


@receiver(post_delete, sender=Researcher, dispatch_uid="search.on_researcher_post_delete")
def on_researcher_post_delete(sender, instance, **kwargs):
    """Enqueue researcher document removal after the sender transaction commits."""
    _enqueue("researchers", instance.pk, delete_document)


# ──────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────


@receiver(post_save, sender=ResearchProduct, dispatch_uid="search.on_product_post_save")
def on_product_post_save(sender, instance, **kwargs):
    """Enqueue product indexing after the sender transaction commits."""
    _enqueue("products", instance.pk, index_document)


@receiver(post_delete, sender=ResearchProduct, dispatch_uid="search.on_product_post_delete")
def on_product_post_delete(sender, instance, **kwargs):
    """Enqueue product document removal after the sender transaction commits."""
    _enqueue("products", instance.pk, delete_document)


# ──────────────────────────────────────────────
# Calls
# ──────────────────────────────────────────────


@receiver(post_save, sender=Call, dispatch_uid="search.on_call_post_save")
def on_call_post_save(sender, instance, **kwargs):
    """Enqueue call indexing after the sender transaction commits."""
    _enqueue("calls", instance.pk, index_document)


@receiver(post_delete, sender=Call, dispatch_uid="search.on_call_post_delete")
def on_call_post_delete(sender, instance, **kwargs):
    """Enqueue call document removal after the sender transaction commits."""
    _enqueue("calls", instance.pk, delete_document)


# ──────────────────────────────────────────────
# Advances (ProgressReport)
# ──────────────────────────────────────────────


@receiver(post_save, sender=ProgressReport, dispatch_uid="search.on_advance_post_save")
def on_advance_post_save(sender, instance, **kwargs):
    """Enqueue advance indexing after the sender transaction commits."""
    _enqueue("advances", instance.pk, index_document)


@receiver(post_delete, sender=ProgressReport, dispatch_uid="search.on_advance_post_delete")
def on_advance_post_delete(sender, instance, **kwargs):
    """Enqueue advance document removal after the sender transaction commits."""
    _enqueue("advances", instance.pk, delete_document)
