"""
DRF ViewSets for the institutions module — Phase 4.

Implements the 6-entity hierarchy REST API with:
- Institution: superadmin-only writes (IsSuperAdmin)
- Sede/Facultad/Center: institution-admin writes (IsInstitutionAdminOrReadOnly)
- Group/Line: center-director writes (IsCenterDirectorOrReadOnly)
- Lifecycle actions: activate/deactivate/archive via @action POST
- Nested routes: parent FK injection from URL kwargs via perform_create

Design reference: openspec/changes/institutions/design.md
Spec reference: openspec/changes/institutions/spec.md
"""

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.institutions.models import (
    Facultad,
    Institution,
    ResearchCenter,
    ResearchGroup,
    ResearchLine,
    Sede,
)
from apps.institutions.permissions import (
    IsCenterDirectorOrReadOnly,
    IsInstitutionAdminOrReadOnly,
    IsSuperAdmin,
)
from apps.institutions.serializers import (
    FacultadSerializer,
    InstitutionSerializer,
    ResearchCenterSerializer,
    ResearchGroupSerializer,
    ResearchLineSerializer,
    SedeSerializer,
)
from apps.institutions.services import InstitutionLifecycleService

# ──────────────────────────────────────────────────────────
# Helper: lifecycle action response
# ──────────────────────────────────────────────────────────


def _lifecycle_response(transition_fn, instance, request):
    """Call a lifecycle service method and return a 200 JSON response."""
    try:
        updated = transition_fn(instance)
        serializer = None
        # Dynamically pick serializer based on instance type
        for cls, ser in _SERIALIZER_MAP.items():
            if isinstance(updated, cls):
                serializer = ser(updated, context={"request": request})
                break
        if serializer:
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"status": updated.status}, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {"detail": str(e.messages[0]) if hasattr(e, "messages") else str(e)},
            status=status.HTTP_409_CONFLICT,
        )


# Used by _lifecycle_response to pick the correct serializer
_SERIALIZER_MAP = {
    Institution: InstitutionSerializer,
    Sede: SedeSerializer,
    Facultad: FacultadSerializer,
    ResearchCenter: ResearchCenterSerializer,
    ResearchGroup: ResearchGroupSerializer,
    ResearchLine: ResearchLineSerializer,
}


# ──────────────────────────────────────────────────────────
# InstitutionViewSet
# ──────────────────────────────────────────────────────────


class InstitutionViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for Institution. Superadmin-only writes."""

    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self) -> QuerySet:
        """All authenticated users can list/retrieve institutions.
        Superadmins see all; regular users see all (no RLS on root table)."""
        return Institution.objects.all()

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)


# ──────────────────────────────────────────────────────────
# SedeViewSet
# ──────────────────────────────────────────────────────────


class SedeViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for Sede. Institution-admin writes."""

    serializer_class = SedeSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]

    def get_queryset(self) -> QuerySet:
        """Filter Sedes by the institution_pk URL kwarg."""
        institution_pk = self.kwargs.get("institution_pk")
        if institution_pk:
            return Sede.objects.filter(institution_id=institution_pk)
        return Sede.objects.none()

    def perform_create(self, serializer):
        """Inject institution from URL kwarg."""
        institution_pk = self.kwargs.get("institution_pk")
        institution = Institution.objects.get(pk=institution_pk)
        serializer.save(institution=institution)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)


# ──────────────────────────────────────────────────────────
# FacultadViewSet
# ──────────────────────────────────────────────────────────


class FacultadViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for Facultad. Institution-admin writes."""

    serializer_class = FacultadSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]

    def get_queryset(self) -> QuerySet:
        institution_pk = self.kwargs.get("institution_pk")
        if institution_pk:
            return Facultad.objects.filter(institution_id=institution_pk)
        return Facultad.objects.none()

    def perform_create(self, serializer):
        institution_pk = self.kwargs.get("institution_pk")
        institution = Institution.objects.get(pk=institution_pk)
        serializer.save(institution=institution)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)


# ──────────────────────────────────────────────────────────
# ResearchCenterViewSet
# ──────────────────────────────────────────────────────────


class ResearchCenterViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for ResearchCenter. Institution-admin writes."""

    serializer_class = ResearchCenterSerializer
    permission_classes = [IsInstitutionAdminOrReadOnly]

    def get_queryset(self) -> QuerySet:
        institution_pk = self.kwargs.get("institution_pk")
        if institution_pk:
            return ResearchCenter.objects.filter(institution_id=institution_pk)
        return ResearchCenter.objects.none()

    def perform_create(self, serializer):
        institution_pk = self.kwargs.get("institution_pk")
        institution = Institution.objects.get(pk=institution_pk)
        serializer.save(institution=institution)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)


# ──────────────────────────────────────────────────────────
# ResearchGroupViewSet
# ──────────────────────────────────────────────────────────


class ResearchGroupViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for ResearchGroup. Center-director writes."""

    serializer_class = ResearchGroupSerializer
    permission_classes = [IsCenterDirectorOrReadOnly]

    def get_queryset(self) -> QuerySet:
        center_pk = self.kwargs.get("center_pk")
        if center_pk:
            return ResearchGroup.objects.filter(center_id=center_pk)
        return ResearchGroup.objects.none()

    def perform_create(self, serializer):
        center_pk = self.kwargs.get("center_pk")
        center = ResearchCenter.objects.select_related("institution").get(pk=center_pk)
        serializer.save(institution=center.institution, center=center)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)


# ──────────────────────────────────────────────────────────
# ResearchLineViewSet
# ──────────────────────────────────────────────────────────


class ResearchLineViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle for ResearchLine. Center-director writes."""

    serializer_class = ResearchLineSerializer
    permission_classes = [IsCenterDirectorOrReadOnly]

    def get_queryset(self) -> QuerySet:
        group_pk = self.kwargs.get("group_pk")
        if group_pk:
            return ResearchLine.objects.filter(group_id=group_pk)
        return ResearchLine.objects.none()

    def perform_create(self, serializer):
        group_pk = self.kwargs.get("group_pk")
        group = ResearchGroup.objects.select_related("institution").get(pk=group_pk)
        serializer.save(institution=group.institution, group=group)

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.activate, instance, request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.deactivate, instance, request)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk=None, **kwargs) -> Response:
        instance = self.get_object()
        return _lifecycle_response(InstitutionLifecycleService.archive, instance, request)
