"""
DRF ViewSets for the project_workflow module — Phase 3.

Implements 3 ViewSets per design.md:
- WorkflowTemplateViewSet: ModelViewSet (CRUD), admin+ only
- WorkflowInstanceViewSet: list, retrieve + @action approve/observe/reject
- WorkflowActionViewSet: create+list+retrieve, no update/delete (405)

Permission model (spec §Security):
- Template CRUD: admin+ (level ≤ 2)
- Instance list/retrieve: authenticated + institution scoping
- Approve/Observe/Reject: IsWorkflowStepApprover (center director)
- Actions: append-only — no update/delete permitted

Design reference: openspec/changes/project_workflow/design.md — ViewSets & Permissions
Spec reference: openspec/changes/project_workflow/spec.md — API Contract, Security
"""
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.permissions import IsInstitutionAdmin
from apps.project_workflow.filters import WorkflowInstanceFilter
from apps.project_workflow.models import (
    WorkflowAction,
    WorkflowInstance,
    WorkflowTemplate,
)
from apps.project_workflow.permissions import IsWorkflowStepApprover
from apps.project_workflow.serializers import (
    WorkflowActionSerializer,
    WorkflowInstanceListSerializer,
    WorkflowInstanceSerializer,
    WorkflowTemplateListSerializer,
    WorkflowTemplateSerializer,
)
from apps.project_workflow.services import WorkflowService

# ──────────────────────────────────────────────────────────
# WorkflowTemplateViewSet
# ──────────────────────────────────────────────────────────


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for WorkflowTemplate — admin+ only.

    - list/retrieve: any admin+ user, institution-scoped
    - create/update/destroy: admin+ (level ≤ 2)
    - Nested steps are read/write via WorkflowTemplateSerializer
    """

    queryset = WorkflowTemplate.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return WorkflowTemplateListSerializer
        return WorkflowTemplateSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsInstitutionAdmin()]

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return WorkflowTemplate.objects.all()

        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            return WorkflowTemplate.objects.none()

        return WorkflowTemplate.objects.filter(institution=membership.institution)

    def perform_create(self, serializer):
        """Inject institution from active membership if not provided."""
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        institution = serializer.validated_data.get("institution")
        if institution is None:
            serializer.validated_data["institution"] = membership.institution

        serializer.save()


# ──────────────────────────────────────────────────────────
# WorkflowInstanceViewSet
# ──────────────────────────────────────────────────────────


class WorkflowInstanceViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
):
    """list, retrieve + 3 action endpoints for WorkflowInstance.

    No create — instances are signal-driven (created when Project is submitted).
    No update/delete — instance lifecycle is managed by actions + signals.
    """

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = WorkflowInstanceFilter
    ordering_fields = ["created_at", "deadline_date", "status"]

    def get_serializer_class(self):
        if self.action == "list":
            return WorkflowInstanceListSerializer
        return WorkflowInstanceSerializer

    def get_permissions(self):
        if self.action in ("approve", "observe", "reject"):
            return [IsAuthenticated(), IsWorkflowStepApprover()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            qs = WorkflowInstance.objects.all()
        else:
            membership = getattr(self.request, "active_membership", None)
            if membership is None:
                qs = WorkflowInstance.objects.none()
            else:
                qs = WorkflowInstance.objects.filter(institution=membership.institution)

        return WorkflowService.annotate_overdue(qs)

    # ── Action Endpoints ──────────────────────────────────

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk=None, **kwargs) -> Response:
        """Approve the workflow instance (advance step or complete)."""
        instance = self.get_object()
        try:
            updated = WorkflowService.advance_step(instance.id, triggered_by=request.user)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def observe(self, request: Request, pk=None, **kwargs) -> Response:
        """Observe the workflow instance with optional observation text."""
        instance = self.get_object()
        observation_text = request.data.get("observation_text", "")
        try:
            updated = WorkflowService.observe(
                instance.id,
                user=request.user,
                observation_text=observation_text,
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk=None, **kwargs) -> Response:
        """Reject the workflow instance with optional reason."""
        instance = self.get_object()
        reason = request.data.get("reason", "")
        try:
            updated = WorkflowService.reject(instance.id, user=request.user, reason=reason)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))

    @staticmethod
    def _extract_error(e: ValidationError) -> str | dict:
        if hasattr(e, "message_dict") and e.message_dict:
            return e.message_dict
        if hasattr(e, "messages") and e.messages:
            return e.messages[0] if isinstance(e.messages, list) else str(e.messages)
        return str(e)


# ──────────────────────────────────────────────────────────
# WorkflowActionViewSet
# ──────────────────────────────────────────────────────────


class WorkflowActionViewSet(viewsets.ModelViewSet):
    """Append-only audit records for a WorkflowInstance.

    - list: actions for a specific instance
    - create: new action (instance + step injected by view)
    - retrieve: single action (read-only)
    - update/delete: 405 Method Not Allowed (WF-006)

    Nested under /instances/{instance_pk}/actions/.
    """

    serializer_class = WorkflowActionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> QuerySet:
        """Filter actions by parent instance from URL."""
        instance_pk = self.kwargs.get("instance_pk")
        if instance_pk:
            return WorkflowAction.objects.filter(instance_id=instance_pk)
        return WorkflowAction.objects.none()

    def perform_create(self, serializer):
        """Inject instance and current step from URL/context."""
        instance_pk = self.kwargs.get("instance_pk")
        if instance_pk is None:
            raise DRFValidationError("Instance ID required.")

        try:
            instance = WorkflowInstance.objects.get(pk=instance_pk)
        except WorkflowInstance.DoesNotExist:
            raise DRFValidationError("Instance not found.")

        serializer.save(
            instance=instance,
            step=instance.current_step,
            acted_by=self.request.user,
        )
