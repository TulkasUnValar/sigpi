"""
DRF ViewSets for the progress (advances) module.

Implements 4 ViewSets per design.md:
- ProgressViewSet: CRUD + 9 FSM actions, institution-scoped queryset,
  action-specific serializers and permissions.
- ProgressDocumentViewSet: nested under progress report, CRUD with
  borrador guard.
- ProgressReviewViewSet: read-only list (RN-P05).
- ProgressStateLogViewSet: read-only list.

Permission model (spec §Security):
- list/retrieve: any authenticated user in the institution
- create: researcher+ who is a project member (IsProgressCreatorOrProjectMember)
- update/delete: creator or project member; only borrador
- FSM actions: per-action permission classes matching the spec matrix

Design reference: openspec/sdd/advances/design.md — ViewSets & Permissions
Spec reference:   openspec/sdd/advances/spec.md — API Contract, Security
"""
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from django_fsm import TransitionNotAllowed
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.progress.filters import ProgressReportFilter
from apps.progress.models import (
    ProgressDocument,
    ProgressReport,
    ProgressReview,
    ProgressStateLog,
)
from apps.progress.permissions import (
    CanReturnToDraft,
    IsCenterDirectorForProject,
    IsProgressCreatorOrProjectMember,
)
from apps.progress.serializers import (
    ProgressDocumentSerializer,
    ProgressReportCreateSerializer,
    ProgressReportListSerializer,
    ProgressReportSerializer,
    ProgressReviewSerializer,
    ProgressStateLogSerializer,
)
from apps.progress.services import ProgressDocumentService, ProgressService

# ──────────────────────────────────────────────────────────
# ProgressViewSet
# ──────────────────────────────────────────────────────────


class ProgressViewSet(viewsets.ModelViewSet):
    """CRUD + 9 FSM actions for ProgressReport. Institution-scoped.

    - list: any authenticated user, lightweight serializer
    - create: researcher+ who is project member (IsProgressCreatorOrProjectMember)
    - retrieve: any authenticated user, full detail + nested
    - update: creator/member; only borrador (guard in service)
    - destroy: creator/member; only borrador (guard in service)
    - 9 FSM actions: per-action permission classes
    """

    queryset = ProgressReport.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProgressReportFilter
    search_fields = ["description", "activities", "difficulties"]
    ordering_fields = ["period_start", "period_end", "created_at", "status"]

    # ── Serializer resolution ─────────────────────────────

    def get_serializer_class(self):
        """Return the appropriate serializer per action.

        - list: ProgressReportListSerializer (7-field summary)
        - create/update: ProgressReportCreateSerializer (writable fields)
        - retrieve/FSM actions: ProgressReportSerializer (full detail + nested)
        """
        if self.action == "list":
            return ProgressReportListSerializer
        if self.action in ("create", "partial_update", "update"):
            return ProgressReportCreateSerializer
        return ProgressReportSerializer

    # ── Permission resolution ─────────────────────────────

    def get_permissions(self):
        """Assign permission classes per action per spec matrix.

        - create: IsProgressCreatorOrProjectMember
        - list/retrieve: authenticated only
        - update/destroy: IsProgressCreatorOrProjectMember
        - FSM submit/resubmit: IsProgressCreatorOrProjectMember
        - FSM director actions: IsCenterDirectorForProject
        - FSM return_to_draft (rechazado): IsProgressCreatorOrProjectMember
        """
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]

        # Director-only FSM actions
        director_actions = {
            "accept_review", "approve", "observe", "reject",
        }
        if self.action in director_actions:
            return [IsAuthenticated(), IsCenterDirectorForProject()]

        # return_to_draft — depends on source state:
        # en_revision/observado → director; rechazado → creator
        # Resolved at object level via CanReturnToDraft.has_object_permission
        if self.action == "return_to_draft":
            return [IsAuthenticated(), CanReturnToDraft()]

        # create, update, destroy, submit, resubmit
        return [IsAuthenticated(), IsProgressCreatorOrProjectMember()]

    # ── Queryset scoping ──────────────────────────────────

    def get_queryset(self) -> QuerySet:
        """Filter reports by the user's active institution.

        Superadmin sees all; regular users see only their active
        institution's reports.

        When project_pk is present in kwargs (nested shortcut),
        additionally filter by project_id.
        """
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            qs = ProgressReport.objects.all()
        else:
            membership = getattr(self.request, "active_membership", None)
            if membership is None:
                return ProgressReport.objects.none()
            qs = ProgressReport.objects.filter(
                institution=membership.institution
            )

        # Nested shortcut: /projects/{project_pk}/progress/
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            qs = qs.filter(project_id=project_pk)

        return qs

    # ── CRUD lifecycle hooks ──────────────────────────────

    def perform_create(self, serializer):
        """Inject institution + created_by from request, delegate to service."""
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        validated = serializer.validated_data
        project = validated.get("project")

        data = {
            k: v for k, v in validated.items()
            if k not in ("institution", "project", "created_by")
        }

        try:
            report = ProgressService.create(
                project=project,
                user=self.request.user,
                **data,
            )
            serializer.instance = report
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Delegate update to ProgressService (handles borrador guard)."""
        report = self.get_object()
        validated = serializer.validated_data
        data = {
            k: v for k, v in validated.items()
            if k not in ("institution", "created_by", "status", "project")
        }

        try:
            updated = ProgressService.update(report, **data)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Delete progress report — only borrador, via service."""
        try:
            ProgressService.delete(instance)
        except ValidationError as e:
            raise PermissionDenied(
                detail=e.message if hasattr(e, "message") else str(e)
            )

    # ── FSM Action Endpoints (9 total) ───────────────────
    # Each calls the corresponding ProgressService method.
    # Guards (invalid source state, permissions) handled by
    # service + permission classes.

    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk=None, **kwargs) -> Response:
        """borrador → enviado."""
        return self._fsm_transition(ProgressService.submit, request)

    @action(detail=True, methods=["post"])
    def accept_review(self, request: Request, pk=None, **kwargs) -> Response:
        """enviado → en_revision."""
        return self._fsm_transition(ProgressService.accept_review, request)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → aprobado (terminal)."""
        return self._fsm_transition(ProgressService.approve, request)

    @action(detail=True, methods=["post"])
    def observe(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → observado + create ProgressReview."""
        report = self.get_object()
        review_text = request.data.get("review_text", "")
        try:
            updated = ProgressService.observe(report, request.user, review_text)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → rechazado + create ProgressReview."""
        report = self.get_object()
        review_text = request.data.get("review_text", "")
        try:
            updated = ProgressService.reject(report, request.user, review_text)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def return_to_draft(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision | observado | rechazado → borrador."""
        report = self.get_object()
        reason = request.data.get("reason", "")
        try:
            updated = ProgressService.return_to_draft(
                report, request.user, reason=reason
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def resubmit(self, request: Request, pk=None, **kwargs) -> Response:
        """observado → enviado."""
        return self._fsm_transition(ProgressService.resubmit, request)

    # ── FSM helpers ───────────────────────────────────────

    @staticmethod
    def _extract_error(e: ValidationError | TransitionNotAllowed) -> str | dict:
        """Extract a consistent error detail from ValidationError or TransitionNotAllowed."""
        if hasattr(e, "message_dict") and e.message_dict:
            return e.message_dict
        if hasattr(e, "messages") and e.messages:
            msg = e.messages[0] if isinstance(e.messages, list) else str(e.messages)
            return msg
        return str(e)

    def _fsm_transition(self, service_method, request: Request) -> Response:
        """Generic FSM transition handler for actions without extra params."""
        report = self.get_object()
        try:
            updated = service_method(report, request.user)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))
        except TransitionNotAllowed as e:
            raise DRFValidationError(str(e))


# ──────────────────────────────────────────────────────────
# ProgressDocumentViewSet — nested under /progress/{pk}/documents/
# ──────────────────────────────────────────────────────────


class ProgressDocumentViewSet(viewsets.ModelViewSet):
    """Nested CRUD for ProgressDocument.

    - list: any authenticated user
    - create/update/destroy: creator or project member
    - Borrador guard: mutations rejected if parent report not borrador.
    """

    serializer_class = ProgressDocumentSerializer
    permission_classes = [IsAuthenticated, IsProgressCreatorOrProjectMember]

    def get_queryset(self) -> QuerySet:
        """Filter documents by parent progress report from URL."""
        progress_pk = self.kwargs.get("progressreport_pk")
        if progress_pk:
            return ProgressDocument.objects.filter(
                progress_report_id=progress_pk
            )
        return ProgressDocument.objects.none()

    def _get_parent_report(self) -> ProgressReport:
        """Resolve and return the parent progress report from URL kwargs."""
        progress_pk = self.kwargs.get("progressreport_pk")
        if not progress_pk:
            raise Http404("Progress report not found.")
        try:
            return ProgressReport.objects.get(pk=progress_pk)
        except ProgressReport.DoesNotExist:
            raise Http404("Progress report not found.")

    def check_object_permissions(self, request, obj):
        """Redirect object permission to parent progress report for child entities."""
        report = getattr(obj, "progress_report", None)
        if report is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, report):
                    self.permission_denied(
                        request,
                        message=getattr(permission, "message", None),
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        """Add document via ProgressDocumentService (handles borrador guard)."""
        report = self._get_parent_report()
        name = serializer.validated_data["name"]
        doc_type = serializer.validated_data["doc_type"]
        external_url = serializer.validated_data.get("external_url", "")
        try:
            doc = ProgressDocumentService.add(report, name, doc_type, external_url)
            serializer.instance = doc
        except ValidationError as e:
            raise PermissionDenied(
                detail=e.message if hasattr(e, "message") else str(e)
            )

    def perform_update(self, serializer):
        """Update document via service (handles borrador guard)."""
        document = self.get_object()
        try:
            updated = ProgressDocumentService.update(
                document, **serializer.validated_data
            )
            serializer.instance = updated
        except ValidationError as e:
            raise PermissionDenied(
                detail=e.message if hasattr(e, "message") else str(e)
            )

    def perform_destroy(self, instance):
        """Remove document via service (handles borrador guard)."""
        try:
            ProgressDocumentService.remove(instance)
        except ValidationError as e:
            raise PermissionDenied(
                detail=e.message if hasattr(e, "message") else str(e)
            )


# ──────────────────────────────────────────────────────────
# ProgressReviewViewSet — read-only (RN-P05)
# ──────────────────────────────────────────────────────────


class ProgressReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of ProgressReview (RN-P05).

    Reviews are append-only — created by the observe()/reject()
    transitions in ProgressService. No create/update/delete.
    """

    serializer_class = ProgressReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter reviews by parent progress report from URL."""
        progress_pk = self.kwargs.get("progressreport_pk")
        if progress_pk:
            return ProgressReview.objects.filter(
                progress_report_id=progress_pk
            )
        return ProgressReview.objects.none()


# ──────────────────────────────────────────────────────────
# ProgressStateLogViewSet — read-only
# ──────────────────────────────────────────────────────────


class ProgressStateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of ProgressStateLog.

    State logs are append-only — created by _log_transition()
    in ProgressService. No create/update/delete.
    """

    serializer_class = ProgressStateLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter state logs by parent progress report from URL."""
        progress_pk = self.kwargs.get("progressreport_pk")
        if progress_pk:
            return ProgressStateLog.objects.filter(
                progress_report_id=progress_pk
            )
        return ProgressStateLog.objects.none()
