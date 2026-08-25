"""
Signal receivers for the notifications module.

Receivers translate semantic domain signals into in-app Notification
rows (spec RN-1..RN-4). Contracts (design.md — Receivers):

- ORM only: no SMTP, HTTP, or file I/O inside receivers (< 50 ms)
- Idempotent: get_or_create on the unique event tuple
- Resilient: missing templates/recipients log a warning; receiver
  errors are logged and swallowed so the sender transaction commits
- Filter: react only to the documented event state (enviado/observado)

Signals are connected in apps.notifications.apps.ready() with dispatch_uid.
"""

import functools
import logging
import re

from django.dispatch import receiver

from apps.budgets.signals import budget_overrun_attempted
from apps.documents.signals import document_signed
from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.resolvers import (
    resolve_admin,
    resolve_director,
    resolve_project_pi,
    resolve_researcher,
)
from apps.progress.signals import progress_state_changed
from apps.project_workflow.signals import project_state_changed

logger = logging.getLogger(__name__)

# Event types — codes match the seeded NotificationTemplate rows.
EVENT_PROJECT_SUBMITTED = "PROJECT_SUBMITTED"
EVENT_PROGRESS_OBSERVED = "PROGRESS_OBSERVED"
EVENT_DOCUMENT_SIGNED = "DOCUMENT_SIGNED"
EVENT_BUDGET_OVERRUN_ATTEMPTED = "BUDGET_OVERRUN_ATTEMPTED"

# Explicit entity links (no GenericForeignKey — design decision).
ENTITY_PROJECT = "project"
ENTITY_PROGRESS_REPORT = "progress_report"
ENTITY_DOCUMENT = "document"
ENTITY_BUDGET_LINE = "budget_line"

_TAG_RE = re.compile(r"{{\s*([A-Za-z0-9_.]+)\s*}}")


def _render_template(text, context):
    """Render ``{{ dotted.path }}`` tags from a serializable context dict."""

    def _resolve(match):
        value = context
        for key in match.group(1).split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = getattr(value, key, None)
            if value is None:
                return ""
        return str(value)

    return _TAG_RE.sub(_resolve, text)


def _guard(func):
    """Log and swallow receiver errors so the sender transaction commits."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Notification receiver %s failed", func.__name__)
            return None

    return wrapper


def _create_notifications(
    *,
    event_type,
    institution,
    recipients,
    entity_type,
    entity_id,
    context,
):
    """Insert one Notification per recipient (idempotent via get_or_create).

    Skips entirely when the event's template is missing or inactive.
    Missing recipients log a warning and never fail the sender.
    """
    template = NotificationTemplate.objects.filter(
        code=event_type, is_active=True
    ).first()
    if template is None:
        logger.warning(
            "NotificationTemplate %s missing or inactive; skipping", event_type
        )
        return 0

    created = 0
    for recipient in recipients:
        if recipient is None:
            continue
        try:
            _, was_created = Notification.objects.get_or_create(
                recipient=recipient,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                defaults={
                    "institution": institution,
                    "template": template,
                    "title": _render_template(template.title_template, context),
                    "body": _render_template(template.body_template, context),
                    "context": context,
                },
            )
            created += int(was_created)
        except Exception:
            logger.exception(
                "Failed to create %s notification for %s", event_type, recipient
            )
    return created


# ──────────────────────────────────────────────
# RN-1 — Project Submitted → Center Director
# ──────────────────────────────────────────────


@receiver(project_state_changed, dispatch_uid="notifications.on_project_state_changed")
@_guard
def on_project_state_changed(sender, **kwargs):
    """Notify the center director when a project is submitted (RN-1)."""
    project = kwargs.get("project")
    to_state = kwargs.get("to_state")
    if project is None or to_state != "enviado":
        return

    recipients = resolve_director(project.institution, project.center)
    if not recipients:
        logger.warning(
            "No active center director for project %s (center %s); skipping",
            project.pk,
            getattr(project, "center_id", None),
        )
        return

    _create_notifications(
        event_type=EVENT_PROJECT_SUBMITTED,
        institution=project.institution,
        recipients=recipients,
        entity_type=ENTITY_PROJECT,
        entity_id=project.pk,
        context={
            "project": {"title": project.title},
            "from_state": kwargs.get("from_state"),
            "to_state": to_state,
        },
    )


# ──────────────────────────────────────────────
# RN-2 — Observed Advance → Researcher
# ──────────────────────────────────────────────


@receiver(progress_state_changed, dispatch_uid="notifications.on_progress_state_changed")
@_guard
def on_progress_state_changed(sender, **kwargs):
    """Notify the report author when an advance is observed (RN-2)."""
    report = kwargs.get("progress_report") or kwargs.get("instance")
    to_state = kwargs.get("to_state") or kwargs.get("new_status")
    if report is None or to_state != "observado":
        return

    recipients = resolve_researcher(report)
    if not recipients:
        logger.warning(
            "No author (created_by) for progress report %s; skipping", report.pk
        )
        return

    _create_notifications(
        event_type=EVENT_PROGRESS_OBSERVED,
        institution=report.institution,
        recipients=recipients,
        entity_type=ENTITY_PROGRESS_REPORT,
        entity_id=report.pk,
        context={
            "progress": {"title": str(report)},
            "from_state": kwargs.get("from_state") or kwargs.get("old_status"),
            "to_state": to_state,
        },
    )


# ──────────────────────────────────────────────
# RN-3 — Signed Document → Signer + PI
# ──────────────────────────────────────────────


@receiver(document_signed, dispatch_uid="notifications.on_document_signed")
@_guard
def on_document_signed(sender, **kwargs):
    """Notify the signer and, when linked, the project PI (RN-3)."""
    document = kwargs.get("document") or kwargs.get("instance")
    signer = kwargs.get("signer")
    version = kwargs.get("version")
    if document is None:
        return

    recipients = []
    if signer is not None:
        recipients.append(signer)
    if document.project_id:
        recipients.extend(resolve_project_pi(document.project))

    unique = list(dict.fromkeys(r for r in recipients if r is not None))
    if not unique:
        logger.warning("No signer or PI recipient for document %s; skipping", document.pk)
        return

    _create_notifications(
        event_type=EVENT_DOCUMENT_SIGNED,
        institution=document.institution,
        recipients=unique,
        entity_type=ENTITY_DOCUMENT,
        entity_id=document.pk,
        context={
            "document": {"name": document.title},
            "version": version,
        },
    )


# ──────────────────────────────────────────────
# RN-4 — Budget Overrun Attempt → Institution Admin
# ──────────────────────────────────────────────


@receiver(budget_overrun_attempted, dispatch_uid="notifications.on_budget_overrun_attempted")
@_guard
def on_budget_overrun_attempted(sender, **kwargs):
    """Notify institutional admins when an overrun is attempted (RN-4)."""
    line = kwargs.get("budget_line") or kwargs.get("instance")
    if line is None:
        return
    institution = kwargs.get("institution")
    if institution is None:
        institution = line.budget.institution

    recipients = resolve_admin(institution)
    if not recipients:
        logger.warning("No institutional admin for %s; skipping", institution)
        return

    _create_notifications(
        event_type=EVENT_BUDGET_OVERRUN_ATTEMPTED,
        institution=institution,
        recipients=recipients,
        entity_type=ENTITY_BUDGET_LINE,
        entity_id=line.pk,
        context={
            "line": {"description": line.name},
            "amount": str(kwargs.get("attempted_amount") or ""),
        },
    )
