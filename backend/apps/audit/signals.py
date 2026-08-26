"""
Signal layer for generic CRUD audit capture.

Receivers listen to the tracked models and emit CREATE / UPDATE / DELETE
AuditEvents through the canonical ``AuditEventEmitter``. They deliberately
do NOT emit STATE_CHANGE (that stays with the FSM services) and never call
``save()`` on the source model, which prevents recursion.

Guarantees:
- Raw saves are ignored.
- Events are only written when an institution audit context is present.
- ``AuditEvent`` itself is excluded from receivers.
- Receivers are connected with ``dispatch_uid`` to prevent duplicates.
- ``old_values`` / ``new_values`` use safe scalar serialization.

Design reference: openspec/changes/audit/design.md
Spec reference: openspec/changes/audit/specs/audit/spec.md (RA-1, RA-2)
"""

import datetime
import decimal
import logging
import uuid

from django.db.models.signals import post_delete, post_save, pre_save

from apps.accounts.audit import AuditEvent, AuditEventEmitter, AuditEventType
from apps.audit.context import get_audit_context

logger = logging.getLogger(__name__)

# Attributes used to carry state between pre_save and post_save.
_OLD_VALUES_ATTR = "_audit_old_values"
_NEW_VALUES_ATTR = "_audit_new_values"
_CHANGED_ATTR = "_audit_changed_fields"


def _serialize_value(value):
    """Serialize a single field value to a JSON-safe scalar.

    Handles UUIDs, decimals, dates/datetimes, and model instances
    (foreign keys). Everything else falls back to a string.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if hasattr(value, "pk"):
        return str(value.pk)
    return str(value)


def _tracked_field_attnames(model):
    """Concrete column attribute names to compare for diffs.

    Excludes the primary key and auto-managed timestamp fields
    (auto_now / auto_now_add) so that a no-op save does not produce an
    event just because ``updated_at`` was refreshed.
    """
    names = []
    for field in model._meta.fields:
        if field.primary_key:
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        names.append(field.attname)
    return names


def _serialize_instance(instance, attnames):
    """Serialize a set of field attribute names to a JSON-safe dict."""
    result = {}
    for name in attnames:
        try:
            result[name] = _serialize_value(getattr(instance, name))
        except Exception:  # pragma: no cover - defensive
            result[name] = None
    return result


def _resolve_project_id(instance):
    """Derive the project_id from an instance or its project relation."""
    if instance._meta.model_name == "project":
        return instance.pk
    if hasattr(instance, "project_id"):
        return instance.project_id
    if hasattr(instance, "project"):
        try:
            return instance.project_id
        except Exception:
            return None
    return None


def _emit(sender, instance, event_type, old_values=None, new_values=None):
    """Emit an audit event for a tracked model using the active context."""
    ctx = get_audit_context()
    emitter = AuditEventEmitter()
    emitter.emit(
        event_type=event_type,
        user=ctx.user,
        ip_address=ctx.ip_address,
        institution_id=ctx.institution_id,
        entity_type=sender._meta.model_name,
        entity_id=instance.pk,
        action=event_type,
        old_values=old_values,
        new_values=new_values,
        project_id=_resolve_project_id(instance),
    )


# ──────────────────────────────────────────────────────────
# Receivers
# ──────────────────────────────────────────────────────────


def pre_save_handler(sender, instance, raw, **kwargs):
    """Load the prior row and compute the changed-field diff.

    The diff is stashed on the instance so ``post_save_handler`` can emit
    an UPDATE event without re-querying.
    """
    if raw or sender is AuditEvent:
        return
    attnames = _tracked_field_attnames(sender)

    if instance.pk is None:
        # CREATE: capture the full new state.
        setattr(instance, _NEW_VALUES_ATTR, _serialize_instance(instance, attnames))
        setattr(instance, _CHANGED_ATTR, set(attnames))
        return

    # UPDATE: compare against the persisted prior row.
    try:
        prior = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_values = {}
    new_values = {}
    changed = set()
    for name in attnames:
        old_val = getattr(prior, name)
        new_val = getattr(instance, name)
        if old_val != new_val:
            changed.add(name)
            old_values[name] = _serialize_value(old_val)
            new_values[name] = _serialize_value(new_val)

    setattr(instance, _OLD_VALUES_ATTR, old_values)
    setattr(instance, _NEW_VALUES_ATTR, new_values)
    setattr(instance, _CHANGED_ATTR, changed)


def post_save_handler(sender, instance, created, raw, **kwargs):
    """Emit CREATE or UPDATE after a tracked model is saved."""
    if raw or sender is AuditEvent:
        return
    ctx = get_audit_context()
    if not ctx.institution_id:
        return

    if created:
        new_values = getattr(instance, _NEW_VALUES_ATTR, None) or _serialize_instance(
            instance, _tracked_field_attnames(sender)
        )
        _emit(sender, instance, AuditEventType.CREATE, new_values=new_values)
        return

    changed = getattr(instance, _CHANGED_ATTR, set())
    if not changed:
        return
    _emit(
        sender,
        instance,
        AuditEventType.UPDATE,
        old_values=getattr(instance, _OLD_VALUES_ATTR, {}),
        new_values=getattr(instance, _NEW_VALUES_ATTR, {}),
    )


def post_delete_handler(sender, instance, **kwargs):
    """Emit DELETE after a tracked model is deleted."""
    if sender is AuditEvent:
        return
    ctx = get_audit_context()
    if not ctx.institution_id:
        return

    old_values = _serialize_instance(instance, _tracked_field_attnames(sender))
    _emit(sender, instance, AuditEventType.DELETE, old_values=old_values)


# ──────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────


def _tracked_models():
    """Import and return the models tracked by the signal layer."""
    from apps.budgets.models import Budget
    from apps.documents.models import Document
    from apps.progress.models import ProgressReport
    from apps.projects.models import Project
    from apps.researchers.models import Researcher

    return [Project, ProgressReport, Researcher, Budget, Document]


def connect_signals() -> None:
    """Connect receivers to the tracked models using dispatch_uid.

    Safe to call multiple times: dispatch_uid prevents duplicate
    connections. Invoked from ``AuditConfig.ready()``.
    """
    for model in _tracked_models():
        label = model._meta.label_lower
        pre_save.connect(pre_save_handler, sender=model, dispatch_uid=f"audit_pre_save_{label}")
        post_save.connect(
            post_save_handler, sender=model, dispatch_uid=f"audit_post_save_{label}"
        )
        post_delete.connect(
            post_delete_handler, sender=model, dispatch_uid=f"audit_post_delete_{label}"
        )
