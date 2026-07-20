"""
DRF ViewSets for the projects module — Phase 4.

Implements 5 ViewSets per design.md:
- ProjectViewSet: CRUD + 16 FSM actions, institution-scoped queryset,
  action-specific serializers and permissions.
- ProjectMemberViewSet: nested under project, CRUD with parent validation.
- ProjectDocumentViewSet: nested under project, CRUD with parent validation.
- ProjectObservationViewSet: read-only list (RN-014).
- ProjectStateLogViewSet: read-only list.

Permission model (spec §Security):
- list/retrieve: any authenticated user in the institution
- create: researcher-level + affiliation with target center (RN-009)
- update/delete: PI, co-investigator, admin+; delete only borrador
- FSM actions: per-action permission classes matching the spec matrix

Design reference: openspec/changes/projects/design.md — ViewSets & Permissions
Spec reference: openspec/changes/projects/spec.md — API Contract, Security
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

from apps.accounts.permissions import HasRoleLevelOrHigher, IsInstitutionAdmin
from apps.projects.filters import ProjectFilter
from apps.projects.models import (
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectObservation,
    ProjectStateLog,
)
from apps.projects.permissions import (
    CanCreateProjectInCenter,
    IsCenterDirectorForProject,
    IsProjectOwnerOrCoInvestigator,
)
from apps.projects.serializers import (
    ProjectCreateSerializer,
    ProjectDocumentSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
    ProjectObservationSerializer,
    ProjectSerializer,
    ProjectStateLogSerializer,
)
from apps.projects.services import (
    ProjectDocumentService,
    ProjectMemberService,
    ProjectService,
)

# ──────────────────────────────────────────────────────────
# ProjectViewSet
# ──────────────────────────────────────────────────────────


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD + 16 FSM actions for Project. Institution-scoped.

    - list: any authenticated user, lightweight serializer
    - create: researcher+ with affiliation (RN-009)
    - retrieve: any authenticated user, full detail + nested
    - update: PI, co-investigator, admin+; terminal guard
    - destroy: PI if borrador, admin+ any state
    - 16 FSM actions: per-action permission classes
    """

    queryset = Project.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ["title", "abstract", "keywords"]
    ordering_fields = ["title", "start_date", "created_at", "status"]

    # ── Serializer resolution ─────────────────────────────

    def get_serializer_class(self):
        """Return the appropriate serializer per action.

        - list: ProjectListSerializer (7-field summary)
        - create/update: ProjectCreateSerializer (writable fields)
        - retrieve/FSM actions: ProjectSerializer (full detail + nested)
        """
        if self.action == "list":
            return ProjectListSerializer
        if self.action in ("create", "partial_update", "update"):
            return ProjectCreateSerializer
        return ProjectSerializer

    # ── Permission resolution ─────────────────────────────

    def get_permissions(self):
        """Assign permission classes per action per spec matrix.

        - create: CanCreateProjectInCenter (RN-009)
        - list/retrieve: authenticated only (institution scoping via queryset)
        - update/destroy: IsProjectOwnerOrCoInvestigator
        - FSM PI actions: submit, resubmit, finalize
        - FSM director actions: accept_review, approve, observe,
          return_to_draft, reject, start_execution, suspend, resume,
          initiate_closure, close
        - FSM admin actions: cancel
        """
        if self.action == "create":
            return [IsAuthenticated(), CanCreateProjectInCenter()]
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]

        # FSM — director actions
        director_actions = {
            "accept_review", "approve", "observe", "return_to_draft",
            "reject", "start_execution", "suspend", "resume",
            "initiate_closure", "close",
        }
        if self.action in director_actions:
            return [IsAuthenticated(), IsCenterDirectorForProject()]

        # FSM — PI actions
        if self.action in ("submit", "resubmit", "finalize"):
            return [IsAuthenticated(), IsProjectOwnerOrCoInvestigator()]

        # FSM — admin action
        if self.action == "cancel":
            return [IsAuthenticated(), IsInstitutionAdmin()]

        # CRUD mutations
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsProjectOwnerOrCoInvestigator()]

        return [IsAuthenticated()]

    # ── Queryset scoping ──────────────────────────────────

    def get_queryset(self) -> QuerySet:
        """Filter projects by the user's active institution.

        Superadmin (Django superuser) sees all; regular users see
        only their active institution's projects.
        """
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return Project.objects.all()

        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            return Project.objects.none()

        return Project.objects.filter(institution=membership.institution)

    # ── CRUD lifecycle hooks ──────────────────────────────

    def perform_create(self, serializer):
        """Inject institution from active membership, delegate to ProjectService."""
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        institution = membership.institution
        validated = serializer.validated_data
        center = validated.get("center")
        principal_investigator = validated.get("principal_investigator")

        data = {
            k: v for k, v in validated.items()
            if k not in ("institution", "center", "principal_investigator")
        }

        try:
            project = ProjectService.create(
                institution=institution,
                center=center,
                principal_investigator=principal_investigator,
                user=self.request.user,
                **data,
            )
            serializer.instance = project
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Delegate update to ProjectService (handles terminal guard)."""
        project = self.get_object()
        validated = serializer.validated_data
        data = {k: v for k, v in validated.items() if k != "institution"}

        try:
            updated = ProjectService.update(project, **data)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Delete project — only borrador for non-admin users."""
        if instance.status != "borrador":
            # Admin+ (level ≤ 2) can delete any project
            if not HasRoleLevelOrHigher.has_level(self.request, 2):
                raise DRFValidationError(
                    "Only projects in borrador state can be deleted."
                )
        instance.delete()

    # ── FSM Action Endpoints (16 total) ───────────────────
    # Each calls the corresponding ProjectService method.
    # Guards (invalid source state, permissions) handled by
    # service + permission classes.

    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk=None, **kwargs) -> Response:
        """borrador → enviado."""
        return self._fsm_transition(ProjectService.submit, request)

    @action(detail=True, methods=["post"])
    def accept_review(self, request: Request, pk=None, **kwargs) -> Response:
        """enviado → en_revision."""
        return self._fsm_transition(ProjectService.accept_review, request)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → aprobado."""
        return self._fsm_transition(ProjectService.approve, request)

    @action(detail=True, methods=["post"])
    def observe(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → observado + create ProjectObservation."""
        project = self.get_object()
        observation_text = request.data.get("observation_text", "")
        try:
            updated = ProjectService.observe(project, request.user, observation_text)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def return_to_draft(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision | observado → borrador."""
        return self._fsm_transition(ProjectService.return_to_draft, request)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk=None, **kwargs) -> Response:
        """en_revision → rechazado (terminal)."""
        return self._fsm_transition(ProjectService.reject, request)

    @action(detail=True, methods=["post"])
    def resubmit(self, request: Request, pk=None, **kwargs) -> Response:
        """observado → enviado."""
        return self._fsm_transition(ProjectService.resubmit, request)

    @action(detail=True, methods=["post"])
    def start_execution(self, request: Request, pk=None, **kwargs) -> Response:
        """aprobado → en_ejecucion."""
        return self._fsm_transition(ProjectService.start_execution, request)

    @action(detail=True, methods=["post"])
    def suspend(self, request: Request, pk=None, **kwargs) -> Response:
        """en_ejecucion → suspendido."""
        project = self.get_object()
        reason = request.data.get("reason", "")
        try:
            updated = ProjectService.suspend(project, request.user, reason)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def resume(self, request: Request, pk=None, **kwargs) -> Response:
        """suspendido → en_ejecucion."""
        return self._fsm_transition(ProjectService.resume, request)

    @action(detail=True, methods=["post"])
    def finalize(self, request: Request, pk=None, **kwargs) -> Response:
        """en_ejecucion → finalizado with actual_end_date."""
        project = self.get_object()
        actual_end_date = request.data.get("actual_end_date")
        try:
            updated = ProjectService.finalize(
                project, request.user, actual_end_date
            )
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

    @action(detail=True, methods=["post"])
    def initiate_closure(self, request: Request, pk=None, **kwargs) -> Response:
        """finalizado → en_cierre."""
        return self._fsm_transition(ProjectService.initiate_closure, request)

    @action(detail=True, methods=["post"])
    def close(self, request: Request, pk=None, **kwargs) -> Response:
        """en_cierre → cerrado (terminal)."""
        return self._fsm_transition(ProjectService.close, request)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk=None, **kwargs) -> Response:
        """Any non-terminal → cancelado (terminal)."""
        project = self.get_object()
        reason = request.data.get("reason", "")
        try:
            updated = ProjectService.cancel(project, request.user, reason)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (ValidationError, TransitionNotAllowed) as e:
            raise DRFValidationError(self._extract_error(e))

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
        project = self.get_object()
        try:
            updated = service_method(project, request.user)
            serializer = self.get_serializer(updated)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(self._extract_error(e))
        except TransitionNotAllowed as e:
            raise DRFValidationError(str(e))


# ──────────────────────────────────────────────────────────
# ProjectMemberViewSet — nested under /projects/{pk}/members/
# ──────────────────────────────────────────────────────────


class ProjectMemberViewSet(viewsets.ModelViewSet):
    """Nested CRUD for ProjectMember.

    - list: any authenticated user
    - create/update/destroy: PI or co-investigator
    - Terminal projects reject mutations (enforced by service layer).
    """

    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrCoInvestigator]

    def get_queryset(self) -> QuerySet:
        """Filter members by parent project from URL."""
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            return ProjectMember.objects.filter(project_id=project_pk)
        return ProjectMember.objects.none()

    def _get_parent_project(self) -> Project:
        """Resolve and return the parent project from URL kwargs."""
        project_pk = self.kwargs.get("project_pk")
        if not project_pk:
            raise Http404("Project not found.")
        try:
            return Project.objects.get(pk=project_pk)
        except Project.DoesNotExist:
            raise Http404("Project not found.")

    def check_object_permissions(self, request, obj):
        """Redirect object permission to parent project for child entities."""
        project = getattr(obj, "project", None)
        if project is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, project):
                    self.permission_denied(
                        request,
                        message=getattr(permission, "message", None),
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        """Add member via ProjectMemberService (handles terminal + unique)."""
        project = self._get_parent_project()
        researcher = serializer.validated_data["researcher"]
        role = serializer.validated_data["role"]
        try:
            member = ProjectMemberService.add(project, researcher, role)
            serializer.instance = member
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Update member role via service (handles terminal guard)."""
        member = self.get_object()
        role = serializer.validated_data.get("role")
        try:
            updated = ProjectMemberService.update(member, role)
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Remove member via service (handles terminal guard)."""
        try:
            ProjectMemberService.remove(instance)
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )


# ──────────────────────────────────────────────────────────
# ProjectDocumentViewSet — nested under /projects/{pk}/documents/
# ──────────────────────────────────────────────────────────


class ProjectDocumentViewSet(viewsets.ModelViewSet):
    """Nested CRUD for ProjectDocument.

    - list: any authenticated user
    - create/update/destroy: PI or co-investigator
    - Terminal projects reject mutations (enforced by service layer).
    """

    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrCoInvestigator]

    def get_queryset(self) -> QuerySet:
        """Filter documents by parent project from URL."""
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            return ProjectDocument.objects.filter(project_id=project_pk)
        return ProjectDocument.objects.none()

    def _get_parent_project(self) -> Project:
        """Resolve and return the parent project from URL kwargs."""
        project_pk = self.kwargs.get("project_pk")
        if not project_pk:
            raise Http404("Project not found.")
        try:
            return Project.objects.get(pk=project_pk)
        except Project.DoesNotExist:
            raise Http404("Project not found.")

    def check_object_permissions(self, request, obj):
        """Redirect object permission to parent project for child entities."""
        project = getattr(obj, "project", None)
        if project is not None:
            for permission in self.get_permissions():
                if not permission.has_object_permission(request, self, project):
                    self.permission_denied(
                        request,
                        message=getattr(permission, "message", None),
                    )
            return
        super().check_object_permissions(request, obj)

    def perform_create(self, serializer):
        """Add document via ProjectDocumentService (handles terminal guard)."""
        project = self._get_parent_project()
        name = serializer.validated_data["name"]
        doc_type = serializer.validated_data["doc_type"]
        external_url = serializer.validated_data["external_url"]
        try:
            doc = ProjectDocumentService.add(project, name, doc_type, external_url)
            serializer.instance = doc
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_update(self, serializer):
        """Update document via service (handles terminal guard)."""
        document = self.get_object()
        try:
            updated = ProjectDocumentService.update(
                document, **serializer.validated_data
            )
            serializer.instance = updated
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    def perform_destroy(self, instance):
        """Remove document via service (handles terminal guard)."""
        try:
            ProjectDocumentService.remove(instance)
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )


# ──────────────────────────────────────────────────────────
# ProjectObservationViewSet — read-only (RN-014)
# ──────────────────────────────────────────────────────────


class ProjectObservationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of ProjectObservation (RN-014).

    Observations are append-only — created by the observe()
    transition in ProjectService. No create/update/delete.
    """

    serializer_class = ProjectObservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter observations by parent project from URL."""
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            return ProjectObservation.objects.filter(project_id=project_pk)
        return ProjectObservation.objects.none()


# ──────────────────────────────────────────────────────────
# ProjectStateLogViewSet — read-only (RN-012)
# ──────────────────────────────────────────────────────────


class ProjectStateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of ProjectStateLog (RN-012).

    State logs are append-only — created by _log_transition()
    in ProjectService. No create/update/delete.
    """

    serializer_class = ProjectStateLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        """Filter state logs by parent project from URL."""
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            return ProjectStateLog.objects.filter(project_id=project_pk)
        return ProjectStateLog.objects.none()
