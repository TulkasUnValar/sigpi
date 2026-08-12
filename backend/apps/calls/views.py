"""
DRF ViewSets for the calls module — Phase 3.

Implements 4 ViewSets per design.md:
- CallViewSet: CRUD + 5 FSM actions, institution-scoped queryset,
  action-specific serializers and permissions.
- CallDocumentViewSet: nested under call, CRUD with parent validation.
- CallProjectViewSet: nested under call, CRUD with state guard.
- CallStateLogViewSet: read-only list.

Permission model (spec §Security):
- list/retrieve: any authenticated user in the institution
- create/update/delete/FSM: director_centro (level <= 3) + institution match
- Documents/projects: same as call mutations
- State logs: read-only for any authenticated user

Design reference: openspec/changes/calls/design.md — ViewSets & Permissions
Spec reference: openspec/changes/calls/spec.md — API Contract, Security
"""

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from django_fsm import TransitionNotAllowed
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.calls.filters import CallFilter
from apps.calls.models import Call, CallDocument, CallProject, CallStateLog
from apps.calls.permissions import CanManageCall
from apps.calls.serializers import (
    CallDocumentSerializer,
    CallListSerializer,
    CallProjectCreateSerializer,
    CallProjectSerializer,
    CallSerializer,
    CallStateLogSerializer,
)
from apps.calls.services import (
    CallDocumentService,
    CallProjectService,
    CallService,
)

# ──────────────────────────────────────────────────────────
# CallViewSet
# ──────────────────────────────────────────────────────────


class CallViewSet(viewsets.ModelViewSet):
    """CRUD + 5 FSM actions for Call. Institution-scoped.

    - list: any authenticated user, lightweight serializer
    - create: director_centro+ with institution match
    - retrieve: any authenticated user, full detail
    - update/delete: director_centro+ with institution match
    - 5 FSM actions: per-action permission classes
    """

    queryset = Call.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CallFilter
    search_fields = ["title", "description"]
    ordering_fields = ["title", "created_at", "status", "call_type"]

    # ── Serializer resolution ─────────────────────────────

    def get_serializer_class(self):
        """Return the appropriate serializer per action.

        - list: CallListSerializer (5-field summary)
        - create/update: CallSerializer (writable fields + validation)
        - retrieve/FSM actions: CallSerializer (full detail)
        """
        if self.action == "list":
            return CallListSerializer
        return CallSerializer

    # ── Permission resolution ─────────────────────────────

    def get_permissions(self):
        """Assign permission classes per action per spec matrix.

        - create/update/destroy/FSM: CanManageCall (director+ + institution)
        - list/retrieve: authenticated only (institution scoping via queryset)
        """
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action in (
            "create",
            "update",
            "partial_update",
            "destroy",
            "open_call",
            "close_call",
            "start_evaluation",
            "publish_results",
            "archive",
        ):
            return [IsAuthenticated(), CanManageCall()]
        return [IsAuthenticated()]

    # ── Queryset scoping ──────────────────────────────────

    def get_queryset(self) -> QuerySet:
        """Filter calls by the user's active institution.

        Superadmin (Django superuser) sees all; regular users see
        only their active institution's calls.
        """
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return Call.objects.all()

        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            return Call.objects.none()

        return Call.objects.filter(institution=membership.institution)

    # ── CRUD lifecycle hooks ──────────────────────────────

    def perform_create(self, serializer):
        """Inject institution from active membership, delegate to CallService."""
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        institution = membership.institution
        validated = serializer.validated_data
        data = {k: v for k, v in validated.items() if k != "institution"}

        try:
            call = CallService.create(
                institution=institution,
                user=self.request.user,
                **data,
            )
            serializer.instance = call
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Delegate update to CallService (handles terminal guard)."""
        call = self.get_object()
        validated = serializer.validated_data
        data = {k: v for k, v in validated.items() if k != "institution"}

        try:
            updated = CallService.update(call, **data)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Delete call — only borrador for non-admin users (enforced by service)."""
        try:
            CallService.delete(instance)
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    # ── FSM Action Endpoints (5 total) ────────────────────

    @action(detail=True, methods=["post"])
    def open_call(self, request: Request, pk=None, **kwargs) -> Response:
        """borrador → abierta."""
        return self._fsm_transition(CallService.open_call, request)

    @action(detail=True, methods=["post"])
    def close_call(self, request: Request, pk=None, **kwargs) -> Response:
        """abierta → cerrada."""
        return self._fsm_transition(CallService.close_call, request)

    @action(detail=True, methods=["post"])
    def start_evaluation(self, request: Request, pk=None, **kwargs) -> Response:
        """cerrada → en_evaluacion."""
        return self._fsm_transition(CallService.start_evaluation, request)

    @action(detail=True, methods=["post"])
    def publish_results(self, request: Request, pk=None, **kwargs) -> Response:
        """en_evaluacion → resultados_publicados."""
        return self._fsm_transition(CallService.publish_results, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        """cerrada | resultados_publicados → archivada (terminal)."""
        return self._fsm_transition(CallService.archive, request)

    # ── FSM helpers ───────────────────────────────────────

    @staticmethod
    def _extract_error(e: ValidationError | TransitionNotAllowed) -> str | dict:
        """Extract a consistent error detail from a ValidationError or TransitionNotAllowed."""
        if hasattr(e, "message_dict") and e.message_dict:
            return e.message_dict
        if hasattr(e, "messages") and e.messages:
            msg = e.messages[0] if isinstance(e.messages, list) else str(e.messages)
            return msg
        return str(e)

    def _fsm_transition(self, service_method, request: Request) -> Response:
        """Generic FSM transition handler for actions without extra params."""
        call = self.get_object()
        try:
            updated = service_method(call, request.user)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))
        except TransitionNotAllowed as e:
            raise DRFValidationError(str(e))


# ──────────────────────────────────────────────────────────
# CallDocumentViewSet — nested under /calls/{call_pk}/documents/
# ──────────────────────────────────────────────────────────


class CallDocumentViewSet(viewsets.ModelViewSet):
    """Nested CRUD for CallDocument.

    - list/retrieve: any authenticated user
    - create/update/destroy: director_centro+ (CanManageCall)
    - Terminal calls reject mutations (enforced by service layer).
    """

    serializer_class = CallDocumentSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), CanManageCall()]

    def get_queryset(self) -> QuerySet:
        """Filter documents by parent call from URL."""
        call_pk = self.kwargs.get("call_pk")
        if call_pk:
            return CallDocument.objects.filter(call_id=call_pk)
        return CallDocument.objects.none()

    def _get_parent_call(self) -> Call:
        """Resolve and return the parent call from URL kwargs."""
        call_pk = self.kwargs.get("call_pk")
        if not call_pk:
            raise Http404("Call not found.")
        try:
            return Call.objects.get(pk=call_pk)
        except Call.DoesNotExist:
            raise Http404("Call not found.")

    def check_object_permissions(self, request, obj):
        """Redirect object permission to parent call for child entities."""
        call = getattr(obj, "call", None)
        if call is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, call):
                    self.permission_denied(
                        request,
                        message=getattr(permission, "message", None),
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        """Add document via CallDocumentService (handles terminal guard)."""
        call = self._get_parent_call()
        name = serializer.validated_data["name"]
        doc_type = serializer.validated_data["doc_type"]
        external_url = serializer.validated_data["external_url"]
        try:
            doc = CallDocumentService.add(call, name, doc_type, external_url)
            serializer.instance = doc
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Update document via service (handles terminal guard)."""
        document = self.get_object()
        try:
            updated = CallDocumentService.update(document, **serializer.validated_data)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Remove document via service (handles terminal guard)."""
        try:
            CallDocumentService.remove(instance)
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )


# ──────────────────────────────────────────────────────────
# CallProjectViewSet — nested under /calls/{call_pk}/projects/
# ──────────────────────────────────────────────────────────


class CallProjectViewSet(viewsets.ModelViewSet):
    """Nested CRUD for CallProject.

    - list/retrieve: any authenticated user
    - create: director_centro+ with state guard (abierta only)
    - destroy: director_centro+
    """

    def get_serializer_class(self):
        if self.action == "create":
            return CallProjectCreateSerializer
        return CallProjectSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), CanManageCall()]

    def get_queryset(self) -> QuerySet:
        """Filter projects by parent call from URL."""
        call_pk = self.kwargs.get("call_pk")
        if call_pk:
            return CallProject.objects.filter(call_id=call_pk)
        return CallProject.objects.none()

    def _get_parent_call(self) -> Call:
        """Resolve and return the parent call from URL kwargs."""
        call_pk = self.kwargs.get("call_pk")
        if not call_pk:
            raise Http404("Call not found.")
        try:
            return Call.objects.get(pk=call_pk)
        except Call.DoesNotExist:
            raise Http404("Call not found.")

    def check_object_permissions(self, request, obj):
        """Redirect object permission to parent call for child entities."""
        call = getattr(obj, "call", None)
        if call is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, call):
                    self.permission_denied(
                        request,
                        message=getattr(permission, "message", None),
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        """Link project via CallProjectService (handles state + unique guard)."""
        call = self._get_parent_call()
        project = serializer.validated_data["project"]
        try:
            cp = CallProjectService.link(call, project)
            serializer.instance = cp
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Unlink project via service."""
        try:
            CallProjectService.unlink(instance)
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )


# ──────────────────────────────────────────────────────────
# CallStateLogViewSet — read-only
# ──────────────────────────────────────────────────────────


class CallStateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of CallStateLog.

    State logs are append-only — created by _log_transition()
    in CallService. No create/update/delete.
    """

    serializer_class = CallStateLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter state logs by parent call from URL."""
        call_pk = self.kwargs.get("call_pk")
        if call_pk:
            return CallStateLog.objects.filter(call_id=call_pk)
        return CallStateLog.objects.none()
