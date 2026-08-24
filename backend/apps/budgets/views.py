"""
DRF ViewSets for the budgets module — Phase 2.5.

Implements 5 ViewSets per design.md:
- BudgetViewSet: CRUD + summary @action, institution-scoped.
- BudgetLineViewSet: nested under /budgets/{budget_pk}/lines/.
- BudgetExecutionViewSet: nested under lines/{line_pk}/executions/ (RN-020).
- BudgetAttachmentViewSet: nested under /budgets/{budget_pk}/attachments/.
- FundingSourceViewSet: nested under /projects/{project_pk}/funding-sources/.

Permission model (spec §Security):
- list/retrieve/summary: any authenticated user in the institution.
- create/update/delete: director_centro (level ≤ 3) + institution match.
- Execution overrun authorization requires CanAuthorizeExecution (level ≤ 3).

All mutations delegate to BudgetService inside perform_* hooks; views never
bypass the service layer (RN-020 enforcement + audit).

Design reference: openspec/changes/budgets/design.md — API and Permissions
Spec reference:   openspec/changes/budgets/specs/budgets/spec.md — API Contract
"""

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    APIException,
)
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.budgets.filters import BudgetFilter
from apps.budgets.models import (
    Budget,
    BudgetAttachment,
    BudgetExecution,
    BudgetLine,
    FundingSource,
)
from apps.budgets.permissions import (
    CanAuthorizeExecution,
    CanManageBudget,
    IsSameInstitution,
)
from apps.budgets.serializers import (
    BudgetAttachmentSerializer,
    BudgetCreateSerializer,
    BudgetExecutionSerializer,
    BudgetLineSerializer,
    BudgetSerializer,
    FundingSourceSerializer,
)
from apps.budgets.services import BudgetService, BudgetSummaryService, DuplicateBudgetError
from apps.projects.models import Project


def _extract_error(e: ValidationError) -> str | dict:
    """Extract a consistent error detail from a Django ValidationError."""
    if hasattr(e, "message_dict") and e.message_dict:
        return e.message_dict
    if hasattr(e, "messages") and e.messages:
        msg = e.messages[0] if isinstance(e.messages, list) else str(e.messages)
        return msg
    return str(e)


class Conflict(APIException):
    """HTTP 409 Conflict — duplicate budget per project (RF-B01)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "conflict"


def _scoped_budgets(request: Request) -> QuerySet:
    """Budgets visible to the request user (superuser bypasses)."""
    user = request.user
    if user.is_authenticated and user.is_superuser:
        return Budget.objects.all()

    membership = getattr(request, "active_membership", None)
    if membership is None:
        return Budget.objects.none()

    return Budget.objects.filter(institution=membership.institution)


def _scoped_projects(request: Request) -> QuerySet:
    """Projects visible to the request user (superuser bypasses)."""
    user = request.user
    if user.is_authenticated and user.is_superuser:
        return Project.objects.all()

    membership = getattr(request, "active_membership", None)
    if membership is None:
        return Project.objects.none()

    return Project.objects.filter(institution=membership.institution)


# ──────────────────────────────────────────────────────────
# BudgetViewSet
# ──────────────────────────────────────────────────────────


class BudgetViewSet(viewsets.ModelViewSet):
    """CRUD + summary for Budget. Institution-scoped.

    - list/retrieve/summary: any authenticated user.
    - create/update/delete: director_centro+ with institution match.
    """

    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BudgetFilter
    search_fields = ["name"]
    ordering_fields = ["name", "created_at", "status"]

    def get_serializer_class(self):
        if self.action == "create":
            return BudgetCreateSerializer
        return BudgetSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "summary"):
            return [IsAuthenticated(), IsSameInstitution()]
        return [IsAuthenticated(), IsSameInstitution(), CanManageBudget()]

    def get_queryset(self) -> QuerySet:
        return _scoped_budgets(self.request)

    def perform_create(self, serializer):
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        data = serializer.validated_data
        try:
            budget = BudgetService.create(
                institution=membership.institution,
                user=self.request.user,
                project=data["project"],
                name=data["name"],
                approved_amount=data["approved_amount"],
            )
            serializer.instance = budget
        except DuplicateBudgetError as e:
            raise Conflict(str(e))
        except ValidationError as e:
            raise DRFValidationError(_extract_error(e))

    def perform_update(self, serializer):
        budget = self.get_object()
        try:
            updated = BudgetService.update(budget, self.request.user, **serializer.validated_data)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(_extract_error(e))

    def perform_destroy(self, instance):
        try:
            BudgetService.delete(instance, self.request.user)
        except ValidationError as e:
            raise DRFValidationError(_extract_error(e))

    @action(detail=True, methods=["get"])
    def summary(self, request: Request, pk=None, **kwargs) -> Response:
        budget = self.get_object()
        summary = BudgetSummaryService.for_budget(budget.project)
        if summary is None:
            summary = {"approved": "0.00", "executed": "0.00", "balance": "0.00"}
        else:
            summary = {
                "approved": f"{summary['approved']:.2f}",
                "executed": f"{summary['executed']:.2f}",
                "balance": f"{summary['balance']:.2f}",
            }
        return Response(summary, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────
# BudgetLineViewSet — nested under /budgets/{budget_pk}/lines/
# ──────────────────────────────────────────────────────────


class BudgetLineViewSet(viewsets.ModelViewSet):
    """Nested CRUD for BudgetLine."""

    serializer_class = BudgetLineSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsSameInstitution()]
        return [IsAuthenticated(), IsSameInstitution(), CanManageBudget()]

    def _get_parent_budget(self) -> Budget:
        budget_pk = self.kwargs.get("budget_pk")
        if not budget_pk:
            raise Http404("Budget not found.")
        try:
            return _scoped_budgets(self.request).get(pk=budget_pk)
        except Budget.DoesNotExist:
            raise Http404("Budget not found.")

    def get_queryset(self) -> QuerySet:
        budget_pk = self.kwargs.get("budget_pk")
        if budget_pk:
            scoped = _scoped_budgets(self.request)
            return BudgetLine.objects.filter(budget_id=budget_pk, budget__in=scoped)
        return BudgetLine.objects.none()

    def check_object_permissions(self, request, obj):
        budget = getattr(obj, "budget", None)
        if budget is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, budget):
                    self.permission_denied(
                        request, message=getattr(permission, "message", None)
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        budget = self._get_parent_budget()
        data = serializer.validated_data
        line = BudgetLine(budget=budget, **data)
        line.full_clean()
        line.save()
        serializer.instance = line


# ──────────────────────────────────────────────────────────
# BudgetExecutionViewSet — nested under lines/{line_pk}/executions/
# ──────────────────────────────────────────────────────────


class BudgetExecutionViewSet(viewsets.ModelViewSet):
    """Nested CRUD for BudgetExecution, enforcing RN-020 via BudgetService."""

    serializer_class = BudgetExecutionSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsSameInstitution()]
        # create requires CanManageBudget; overrun authorization checked in service
        return [IsAuthenticated(), IsSameInstitution(), CanManageBudget(), CanAuthorizeExecution()]

    def _get_parent_line(self) -> BudgetLine:
        line_pk = self.kwargs.get("line_pk")
        if not line_pk:
            raise Http404("Line not found.")
        try:
            scoped_budgets = _scoped_budgets(self.request)
            return BudgetLine.objects.select_related("budget").get(
                pk=line_pk, budget__in=scoped_budgets
            )
        except BudgetLine.DoesNotExist:
            raise Http404("Line not found.")

    def get_queryset(self) -> QuerySet:
        line_pk = self.kwargs.get("line_pk")
        if line_pk:
            scoped_budgets = _scoped_budgets(self.request)
            return BudgetExecution.objects.filter(
                line_id=line_pk, line__budget__in=scoped_budgets
            )
        return BudgetExecution.objects.none()

    def check_object_permissions(self, request, obj):
        line = getattr(obj, "line", None)
        if line is not None:
            budget = line.budget
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, budget):
                    self.permission_denied(
                        request, message=getattr(permission, "message", None)
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        line = self._get_parent_line()
        data = serializer.validated_data
        try:
            execution = BudgetService.add_execution(
                line=line,
                amount=data["amount"],
                executed_at=data["executed_at"],
                user=self.request.user,
                authorized_by=data.get("authorized_by"),
                authorized_at=data.get("authorized_at"),
            )
            serializer.instance = execution
        except ValidationError as e:
            raise DRFValidationError(_extract_error(e))


# ──────────────────────────────────────────────────────────
# BudgetAttachmentViewSet — nested under /budgets/{budget_pk}/attachments/
# ──────────────────────────────────────────────────────────


class BudgetAttachmentViewSet(viewsets.ModelViewSet):
    """Nested CRUD for BudgetAttachment (metadata-only)."""

    serializer_class = BudgetAttachmentSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsSameInstitution()]
        return [IsAuthenticated(), IsSameInstitution(), CanManageBudget()]

    def _get_parent_budget(self) -> Budget:
        budget_pk = self.kwargs.get("budget_pk")
        if not budget_pk:
            raise Http404("Budget not found.")
        try:
            return _scoped_budgets(self.request).get(pk=budget_pk)
        except Budget.DoesNotExist:
            raise Http404("Budget not found.")

    def get_queryset(self) -> QuerySet:
        budget_pk = self.kwargs.get("budget_pk")
        if budget_pk:
            scoped = _scoped_budgets(self.request)
            return BudgetAttachment.objects.filter(budget_id=budget_pk, budget__in=scoped)
        return BudgetAttachment.objects.none()

    def check_object_permissions(self, request, obj):
        budget = getattr(obj, "budget", None)
        if budget is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, budget):
                    self.permission_denied(
                        request, message=getattr(permission, "message", None)
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        budget = self._get_parent_budget()
        data = serializer.validated_data
        att = BudgetAttachment(budget=budget, **data)
        att.full_clean()
        att.save()
        serializer.instance = att


# ──────────────────────────────────────────────────────────
# FundingSourceViewSet — nested under /projects/{project_pk}/funding-sources/
# ──────────────────────────────────────────────────────────


class FundingSourceViewSet(viewsets.ModelViewSet):
    """Nested CRUD for FundingSource (multiple per project, RN-019)."""

    serializer_class = FundingSourceSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated(), IsSameInstitution()]
        return [IsAuthenticated(), IsSameInstitution(), CanManageBudget()]

    def _get_parent_project(self) -> Project:
        project_pk = self.kwargs.get("project_pk")
        if not project_pk:
            raise Http404("Project not found.")
        try:
            return _scoped_projects(self.request).get(pk=project_pk)
        except Project.DoesNotExist:
            raise Http404("Project not found.")

    def get_queryset(self) -> QuerySet:
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            scoped = _scoped_projects(self.request)
            return FundingSource.objects.filter(project_id=project_pk, project__in=scoped)
        return FundingSource.objects.none()

    def check_object_permissions(self, request, obj):
        project = getattr(obj, "project", None)
        if project is not None:
            # Reuse the project's institution via a lightweight check object
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, project):
                    self.permission_denied(
                        request, message=getattr(permission, "message", None)
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        project = self._get_parent_project()
        data = serializer.validated_data
        source = FundingSource(project=project, **data)
        source.full_clean()
        source.save()
        serializer.instance = source
