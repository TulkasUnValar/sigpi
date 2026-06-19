"""
InstitutionLifecycleService — FSM transition orchestrator.

Enforces business rule: cannot deactivate/archive a parent entity
if it has active children. Uses the child resolution map from the
design to query the appropriate related models.

Design reference: openspec/changes/institutions/design.md — LifecycleService contract
Spec reference: openspec/changes/institutions/spec.md — RF-008

Child Resolution Map:
  Institution → Sede, Facultad, ResearchCenter (direct FK)
  Sede        → Facultad, ResearchCenter (where sede=self)
  Facultad    → ResearchCenter (where facultad=self)
  ResearchCenter → ResearchGroup (where center=self)
  ResearchGroup  → ResearchLine (where group=self)
  ResearchLine   → NONE (leaf)
"""

from django.core.exceptions import ValidationError

from apps.institutions.models import (
    Institution,
    Sede,
    Facultad,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
)


class InstitutionLifecycleService:
    """Centralized FSM transition orchestrator with child-active guards.

    All transition methods enforce:
    1. deactivate/archive: no active children (ValidationError if blocked)
    2. activate: transitions deactivated → active
    3. archive: transitions active|deactivated → archived (TERMINAL)

    The guard traverses the child resolution map to find all direct
    child entities and checks if any have status='active'.
    """

    @staticmethod
    def _get_child_querysets(instance):
        """Return a list of (label, queryset) for direct children of the entity.

        Each queryset is filtered to children of this instance and
        further filtered to status='active'.
        """
        if isinstance(instance, Institution):
            return [
                ("sedes", Sede.objects.filter(institution=instance)),
                ("facultades", Facultad.objects.filter(institution=instance)),
                ("centers", ResearchCenter.objects.filter(institution=instance)),
            ]
        if isinstance(instance, Sede):
            return [
                ("facultades", Facultad.objects.filter(sede=instance)),
                ("centers", ResearchCenter.objects.filter(sede=instance)),
            ]
        if isinstance(instance, Facultad):
            return [
                ("centers", ResearchCenter.objects.filter(facultad=instance)),
            ]
        if isinstance(instance, ResearchCenter):
            return [
                ("groups", ResearchGroup.objects.filter(center=instance)),
            ]
        if isinstance(instance, ResearchGroup):
            return [
                ("lines", ResearchLine.objects.filter(group=instance)),
            ]
        if isinstance(instance, ResearchLine):
            return []  # leaf — no children
        # Fallback for unknown types
        return []

    @staticmethod
    def _has_active_children(instance) -> bool:
        """Check if the instance has any direct children with status='active'."""
        for _label, qs in InstitutionLifecycleService._get_child_querysets(instance):
            if qs.filter(status="active").exists():
                return True
        return False

    # ── Public transition methods ──────────────

    @staticmethod
    def activate(instance):
        """Transition deactivated → active.

        No guard needed — any entity can be reactivated from deactivated.
        Archived is terminal — django-fsm blocks this at the transition level.
        """
        instance.activate()
        instance.is_active = True
        instance.save()
        return instance

    @staticmethod
    def deactivate(instance):
        """Transition active → deactivated.

        Guard: reject if any direct child entity has status='active'.
        Raises ValidationError with 409-style message if blocked.
        """
        if InstitutionLifecycleService._has_active_children(instance):
            raise ValidationError(
                "Deactivate or archive children first."
            )
        instance.deactivate()
        instance.is_active = False
        instance.save()
        return instance

    @staticmethod
    def archive(instance):
        """Transition active|deactivated → archived (TERMINAL).

        Guard: reject if any direct child entity has status='active'.
        Raises ValidationError with 409-style message if blocked.
        """
        if InstitutionLifecycleService._has_active_children(instance):
            raise ValidationError(
                "Deactivate or archive children first."
            )
        instance.archive()
        instance.is_active = False
        instance.save()
        return instance
