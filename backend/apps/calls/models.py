"""
Calls — Convocatorias module (SIGPI §6.8).

Implements the data model defined in design.md and spec.md:
- Call: 6-state FSM, institution-scoped, 4 nullable dates
- CallDocument: metadata-only document records
- CallProject: project association with UniqueConstraint
- CallStateLog: domain audit log for FSM transitions

Design reference: openspec/changes/calls/design.md
Spec reference:   openspec/changes/calls/spec.md

GREEN PHASE: Full model implementation — tests must pass.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django_fsm import FSMField, transition

# ──────────────────────────────────────────────
# Choice Enums
# ──────────────────────────────────────────────


class CallStatus(models.TextChoices):
    """FSM states for the Call lifecycle (6 states)."""

    BORRADOR = "borrador", "Borrador"
    ABIERTA = "abierta", "Abierta"
    CERRADA = "cerrada", "Cerrada"
    EN_EVALUACION = "en_evaluacion", "En Evaluación"
    RESULTADOS_PUBLICADOS = "resultados_publicados", "Resultados Publicados"
    ARCHIVADA = "archivada", "Archivada"


class CallType(models.TextChoices):
    """Call scope choices."""

    INTERNAL = "internal", "Internal"
    EXTERNAL = "external", "External"


class CallDocumentType(models.TextChoices):
    """Document type choices for CallDocument."""

    CONVOCATORIA = "convocatoria", "Convocatoria"
    ANEXO = "anexo", "Anexo"
    REGLAMENTO = "reglamento", "Reglamento"
    RESULTADO = "resultado", "Resultado"
    OTRO = "otro", "Otro"


# Terminal states — no outbound transitions allowed.
TERMINAL_STATES = {
    CallStatus.ARCHIVADA,
}


# ──────────────────────────────────────────────
# Call
# ──────────────────────────────────────────────


class Call(models.Model):
    """Funding call with 6-state FSM lifecycle.

    Institution-scoped (no center/group/line hierarchy).
    Carries denormalized institution_id for RLS.

    Field-level constraints:
      - RF-067: type/entity rules validated in clean() + DB CHECK.
      - RF-067: date ordering validated in clean() + DB CHECK.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="calls",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    call_type = models.CharField(max_length=20, choices=CallType.choices)
    external_entity = models.CharField(max_length=255, blank=True, default="")
    submission_start = models.DateField(null=True, blank=True)
    submission_end = models.DateField(null=True, blank=True)
    evaluation_start = models.DateField(null=True, blank=True)
    evaluation_end = models.DateField(null=True, blank=True)
    status = FSMField(default=CallStatus.BORRADOR, protected=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calls_call"
        verbose_name = "Call"
        verbose_name_plural = "Calls"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(call_type=CallType.INTERNAL) & models.Q(external_entity="")
                )
                | ~models.Q(call_type=CallType.INTERNAL),
                name="check_internal_no_entity",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(call_type=CallType.EXTERNAL) & ~models.Q(external_entity="")
                )
                | ~models.Q(call_type=CallType.EXTERNAL),
                name="check_external_has_entity",
            ),
            models.CheckConstraint(
                condition=models.Q(submission_end__isnull=True)
                | models.Q(submission_start__isnull=True)
                | models.Q(submission_end__gte=models.F("submission_start")),
                name="check_submission_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(evaluation_end__isnull=True)
                | models.Q(evaluation_start__isnull=True)
                | models.Q(evaluation_end__gte=models.F("evaluation_start")),
                name="check_evaluation_dates",
            ),
        ]
        indexes = [
            models.Index(
                fields=["institution", "status"],
                name="idx_call_inst_status",
            ),
            models.Index(
                fields=["call_type"],
                name="idx_call_type",
            ),
            models.Index(
                fields=["submission_start"],
                name="idx_call_submission_start",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        errors = {}

        # RF-067: type/entity rules.
        if self.call_type == CallType.INTERNAL and self.external_entity:
            errors.setdefault("external_entity", []).append(
                "Internal calls must not have an external entity."
            )
        if self.call_type == CallType.EXTERNAL and not self.external_entity:
            errors.setdefault("external_entity", []).append(
                "External entity is required for external calls."
            )

        # RF-067: date validation.
        if self.submission_start and self.submission_end:
            if self.submission_end < self.submission_start:
                errors.setdefault("submission_end", []).append(
                    "Submission end must be on or after submission start."
                )
        if self.evaluation_start and self.evaluation_end:
            if self.evaluation_end < self.evaluation_start:
                errors.setdefault("evaluation_end", []).append(
                    "Evaluation end must be on or after evaluation start."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ── FSM Transitions (5 total) ──────────────────────

    @transition(field=status, source=CallStatus.BORRADOR, target=CallStatus.ABIERTA)
    def open_call(self):
        """borrador → abierta."""

    @transition(field=status, source=CallStatus.ABIERTA, target=CallStatus.CERRADA)
    def close_call(self):
        """abierta → cerrada."""

    @transition(field=status, source=CallStatus.CERRADA, target=CallStatus.EN_EVALUACION)
    def start_evaluation(self):
        """cerrada → en_evaluacion."""

    @transition(
        field=status,
        source=CallStatus.EN_EVALUACION,
        target=CallStatus.RESULTADOS_PUBLICADOS,
    )
    def publish_results(self):
        """en_evaluacion → resultados_publicados."""

    @transition(
        field=status,
        source=[CallStatus.CERRADA, CallStatus.RESULTADOS_PUBLICADOS],
        target=CallStatus.ARCHIVADA,
    )
    def archive(self):
        """cerrada | resultados_publicados → archivada (terminal)."""


# ──────────────────────────────────────────────
# CallDocument
# ──────────────────────────────────────────────


class CallDocument(models.Model):
    """Metadata-only document record for a Call.

    Stores name, type, and external URL. No file upload in MVP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=20, choices=CallDocumentType.choices)
    external_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calls_calldocument"
        verbose_name = "Call Document"
        verbose_name_plural = "Call Documents"
        ordering = ["call", "-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_doc_type_display()})"


# ──────────────────────────────────────────────
# CallProject
# ──────────────────────────────────────────────


class CallProject(models.Model):
    """Project association through-model with UniqueConstraint.

    Enforces one call per project at the database level.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="call_projects",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="call_associations",
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calls_callproject"
        verbose_name = "Call Project"
        verbose_name_plural = "Call Projects"
        ordering = ["call", "linked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                name="unique_call_per_project",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.call} — {self.project}"


# ──────────────────────────────────────────────
# CallStateLog
# ──────────────────────────────────────────────


class CallStateLog(models.Model):
    """Domain audit log for FSM transitions.

    Dedicated per-call log for queryable state history.
    Each transition is also mirrored to AuditEvent for
    cross-module audit consistency.

    triggered_by is nullable (SET_NULL on user deletion).
    Append-only — no update/delete endpoints exposed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="state_logs",
    )
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    triggered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_state_logs",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calls_callstatelog"
        verbose_name = "Call State Log"
        verbose_name_plural = "Call State Logs"
        ordering = ["call", "-created_at"]
        indexes = [
            models.Index(
                fields=["call", "-created_at"],
                name="idx_call_statelog_time",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} → {self.to_state}"
