"""
DRF ModelSerializers for the project_workflow module.

Provides 6 serializers implementing the API contract from spec.md:
- WorkflowTemplateListSerializer — lightweight list (5 fields)
- WorkflowTemplateSerializer — full detail with nested steps (read/write)
- WorkflowStepSerializer — nested step representation
- WorkflowInstanceListSerializer — lightweight list with is_overdue
- WorkflowInstanceSerializer — full detail with nested actions
- WorkflowActionSerializer — create-only, read-only FKs

Design decisions (from design.md):
- Nested steps on WorkflowTemplateSerializer are read/write
- Nested actions on WorkflowInstanceSerializer are read-only
- project_id (UUIDField) is exposed as `project` in instance serializers
- is_overdue is computed as SerializerMethodField

Spec reference: openspec/changes/project_workflow/spec.md — API Contract
Design reference: openspec/changes/project_workflow/design.md — Serializers
"""
from django.utils import timezone
from rest_framework import serializers

from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowStep,
    WorkflowTemplate,
)

# ──────────────────────────────────────────────────────────
# WorkflowStepSerializer
# ──────────────────────────────────────────────────────────


class WorkflowStepSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowStep — nested in template.

    Fields: id, order, name, role_required, deadline_days.
    """

    class Meta:
        model = WorkflowStep
        fields = [
            "id",
            "order",
            "name",
            "role_required",
            "deadline_days",
        ]


# ──────────────────────────────────────────────────────────
# WorkflowTemplateListSerializer
# ──────────────────────────────────────────────────────────


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template list views.

    Exposes: id, name, center, is_active, step_count.
    """

    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "name",
            "center",
            "is_active",
            "step_count",
        ]

    def get_step_count(self, obj: WorkflowTemplate) -> int:
        return obj.steps.count()


# ──────────────────────────────────────────────────────────
# WorkflowTemplateSerializer
# ──────────────────────────────────────────────────────────


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Full-detail serializer with nested steps (read/write).

    Nested steps are writable on create and update.
    institution is writable (set by view from active membership if omitted).
    """

    steps = WorkflowStepSerializer(many=True, required=False)

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "institution",
            "center",
            "name",
            "description",
            "is_active",
            "steps",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        template = WorkflowTemplate.objects.create(**validated_data)
        for step_data in steps_data:
            WorkflowStep.objects.create(template=template, **step_data)
        return template

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", None)
        instance = super().update(instance, validated_data)
        if steps_data is not None:
            instance.steps.all().delete()
            for step_data in steps_data:
                WorkflowStep.objects.create(template=instance, **step_data)
        return instance


# ──────────────────────────────────────────────────────────
# WorkflowActionSerializer
# ──────────────────────────────────────────────────────────


class WorkflowActionSerializer(serializers.ModelSerializer):
    """Create-only serializer for WorkflowAction.

    instance, step, and acted_by are read-only — set by the view.
    action and observation_text are writable.
    """

    class Meta:
        model = WorkflowAction
        fields = [
            "id",
            "instance",
            "step",
            "action",
            "acted_by",
            "observation_text",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "instance",
            "step",
            "acted_by",
            "created_at",
        ]


# ──────────────────────────────────────────────────────────
# WorkflowInstanceListSerializer
# ──────────────────────────────────────────────────────────


class WorkflowInstanceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for instance list views.

    Exposes: id, project (UUID), status, deadline_date, is_overdue, current_step.
    """

    project = serializers.UUIDField(source="project_id")
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "project",
            "status",
            "deadline_date",
            "is_overdue",
            "current_step",
        ]

    def get_is_overdue(self, obj: WorkflowInstance) -> bool:
        if obj.deadline_date is None:
            return False
        if obj.status != WorkflowInstanceStatus.PENDING:
            return False
        return obj.deadline_date < timezone.now()


# ──────────────────────────────────────────────────────────
# WorkflowInstanceSerializer (full detail)
# ──────────────────────────────────────────────────────────


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Full-detail serializer with nested actions and is_overdue.

    Nested actions are read-only — created via service layer or action endpoints.
    project_id is exposed as `project` (UUID).
    """

    project = serializers.UUIDField(source="project_id")
    is_overdue = serializers.SerializerMethodField()
    actions = WorkflowActionSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "project",
            "institution",
            "template",
            "current_step",
            "status",
            "deadline_date",
            "completed_at",
            "is_overdue",
            "actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "institution",
            "template",
            "current_step",
            "status",
            "deadline_date",
            "completed_at",
            "is_overdue",
            "actions",
            "created_at",
            "updated_at",
        ]

    def get_is_overdue(self, obj: WorkflowInstance) -> bool:
        if obj.deadline_date is None:
            return False
        if obj.status != WorkflowInstanceStatus.PENDING:
            return False
        return obj.deadline_date < timezone.now()
