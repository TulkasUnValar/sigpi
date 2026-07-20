"""
Institutions & Research Structure — 6-entity hierarchy with FSM lifecycle.

Implementa el modelo de datos definido en design.md y spec.md:
- Institution → Sede → Facultad → ResearchCenter → ResearchGroup → ResearchLine
- Flexible parenting: facultad puede saltar sede; centro puede colgarse de cualquier nivel
- denormalized institution_id en todas las entidades para RLS O(1)
- FSMField con estados: active, deactivated, archived (archived es terminal)

Design reference: openspec/changes/institutions/design.md
Spec reference: openspec/changes/institutions/spec.md
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField, transition

# ──────────────────────────────────────────────
# Abstract base for institution-scoped entities
# ──────────────────────────────────────────────


class InstitutionScopedModel(models.Model):
    """Patrón compartido para las 5 entidades subordinadas a Institution.

    No incluye a Institution en sí. Provee institution FK, code, name,
    description, status FSMField, y la restricción (institution, code) unique.
    """

    institution = models.ForeignKey(
        "Institution",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = FSMField(default="active", protected=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    # — FSM transitions (shared by all sub-entities) —

    @transition(field=status, source="deactivated", target="active")
    def activate(self):
        """Transition: deactivated → active."""

    @transition(field=status, source="active", target="deactivated")
    def deactivate(self):
        """Transition: active → deactivated."""

    @transition(field=status, source=["active", "deactivated"], target="archived")
    def archive(self):
        """Transition: active|deactivated → archived (terminal)."""


# ──────────────────────────────────────────────
# Institution
# ──────────────────────────────────────────────


class Institution(models.Model):
    """Research institution in the SIGPI network.

    Expands the original stub with description, contact fields, logo,
    and FSM lifecycle. Institution has no institution_id column — it IS
    the root of the hierarchy. RLS does NOT filter this table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True, max_length=254)
    contact_phone = models.CharField(max_length=30, blank=True)
    logo_url = models.URLField(blank=True, max_length=500)
    status = FSMField(default="active", protected=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "institutions_institution"
        verbose_name = "Institution"
        verbose_name_plural = "Institutions"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    # — FSM transitions —

    @transition(field=status, source="deactivated", target="active")
    def activate(self):
        """Transition: deactivated → active."""

    @transition(field=status, source="active", target="deactivated")
    def deactivate(self):
        """Transition: active → deactivated."""

    @transition(field=status, source=["active", "deactivated"], target="archived")
    def archive(self):
        """Transition: active|deactivated → archived (terminal)."""


# ──────────────────────────────────────────────
# Sede
# ──────────────────────────────────────────────


class Sede(InstitutionScopedModel):
    """Campus or physical location of an Institution.

    Spec: (institution, code) unique. Sede is the second level
    of the hierarchy, below Institution directly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        db_table = "institutions_sede"
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        ordering = ["institution", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_sede_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.institution.code})"


# ──────────────────────────────────────────────
# Facultad
# ──────────────────────────────────────────────


class Facultad(InstitutionScopedModel):
    """Faculty or school within an Institution, optionally under a Sede.

    Flexible hierarchy: facultad can link directly to institution
    (sede is nullable). clean() validates that sede belongs to the
    same institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facultades",
    )

    class Meta:
        db_table = "institutions_facultad"
        verbose_name = "Facultad"
        verbose_name_plural = "Facultades"
        ordering = ["institution", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_facultad_code_per_institution",
            ),
        ]

    def clean(self):
        super().clean()
        if self.sede and self.sede.institution_id != self.institution_id:
            raise ValidationError({"sede": "Sede belongs to a different institution."})

    def __str__(self) -> str:
        return f"{self.name} ({self.institution.code})"


# ──────────────────────────────────────────────
# ResearchCenter
# ──────────────────────────────────────────────


class ResearchCenter(InstitutionScopedModel):
    """Research center — expande el stub original con campos FSM y FK opcionales.

    Flexible parenting: center can attach to institution directly,
    to a sede, or to a facultad (or both). clean() validates that
    any FK targets belong to the same institution.

    Changes from stub:
    - code: now required (blank=False)
    - name: no longer unique globally → (institution, code) unique
    - Added: description, contact_email, contact_phone, status, sede, facultad
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="centers",
    )
    contact_email = models.EmailField(blank=True, max_length=254)
    contact_phone = models.CharField(max_length=30, blank=True)
    sede = models.ForeignKey(
        Sede,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centers",
    )
    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centers",
    )

    class Meta:
        db_table = "institutions_researchcenter"
        verbose_name = "Research Center"
        verbose_name_plural = "Research Centers"
        ordering = ["institution", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_center_code_per_institution",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.sede and self.sede.institution_id != self.institution_id:
            errors["sede"] = "Sede belongs to a different institution."
        if self.facultad and self.facultad.institution_id != self.institution_id:
            errors["facultad"] = "Facultad belongs to a different institution."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.name} ({self.institution.code})"


# ──────────────────────────────────────────────
# ResearchGroup
# ──────────────────────────────────────────────


class ResearchGroup(InstitutionScopedModel):
    """Research group — belongs to a ResearchCenter.

    Spec: (institution, code) unique. Group is the second-to-last
    level of the hierarchy. clean() validates that center belongs
    to the same institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    center = models.ForeignKey(
        ResearchCenter,
        on_delete=models.CASCADE,
        related_name="groups",
    )

    class Meta:
        db_table = "institutions_researchgroup"
        verbose_name = "Research Group"
        verbose_name_plural = "Research Groups"
        ordering = ["institution", "center", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_group_code_per_institution",
            ),
        ]

    def clean(self):
        super().clean()
        if self.center.institution_id != self.institution_id:
            raise ValidationError({"center": "Center belongs to a different institution."})

    def __str__(self) -> str:
        return f"{self.name} ({self.institution.code})"


# ──────────────────────────────────────────────
# ResearchLine
# ──────────────────────────────────────────────


class ResearchLine(InstitutionScopedModel):
    """Research line — belongs to a ResearchGroup. Leaf of the hierarchy.

    Spec: (institution, code) unique. Line is the terminal leaf —
    no children exist below it. clean() validates that group belongs
    to the same institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ResearchGroup,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    class Meta:
        db_table = "institutions_researchline"
        verbose_name = "Research Line"
        verbose_name_plural = "Research Lines"
        ordering = ["institution", "group", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_line_code_per_institution",
            ),
        ]

    def clean(self):
        super().clean()
        if self.group.institution_id != self.institution_id:
            raise ValidationError({"group": "Group belongs to a different institution."})

    def __str__(self) -> str:
        return f"{self.name} ({self.institution.code})"
