"""
DRF ViewSets for the researchers module — Phase 4.

Implements 4 ViewSets per design.md:
- ResearcherViewSet: CRUD + deactivate action, role-gated permissions
- ResearcherAffiliationViewSet: nested affiliations + set_primary action
- ExternalProfileViewSet: nested external profiles
- ResearcherAttachmentViewSet: nested attachments

Permission model (spec §Security):
- list/retrieve: any authenticated user in the institution
- create: director (level ≤ 3) or higher
- update: self (owning researcher, level ≤ 4) or admin+ (level ≤ 2)
- delete: superadmin only (level ≤ 1)
- deactivate: admin+ (level ≤ 2)

Design reference: openspec/changes/researchers/design.md — ViewSets & Permissions
Spec reference: openspec/changes/researchers/spec.md — API Contract, Security
"""
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.permissions import HasRoleLevelOrHigher, IsSuperAdmin
from apps.researchers.models import (
    ExternalProfile,
    Researcher,
    ResearcherAffiliation,
    ResearcherAttachment,
)
from apps.researchers.permissions import IsResearcherOrReadOnly
from apps.researchers.serializers import (
    ExternalProfileSerializer,
    ResearcherAffiliationSerializer,
    ResearcherAttachmentSerializer,
    ResearcherCreateSerializer,
    ResearcherListSerializer,
    ResearcherSerializer,
)
from apps.researchers.services import (
    ResearcherAffiliationService,
    ResearcherProfileService,
)

# ──────────────────────────────────────────────────────────
# IsDirectorOrHigher — create permission for researchers
# ──────────────────────────────────────────────────────────


class IsDirectorOrHigher(BasePermission):
    """Create access: director (level ≤ 3) or higher.

    Used to gate researcher creation — researchers (level 4)
    can manage their own profiles but cannot create new ones.
    Per spec: Center Director can create, Researcher cannot.
    """

    def has_permission(self, request: Request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return HasRoleLevelOrHigher.has_level(request, 3)


# ──────────────────────────────────────────────────────────
# ResearcherViewSet
# ──────────────────────────────────────────────────────────


class ResearcherViewSet(viewsets.ModelViewSet):
    """CRUD + deactivate for Researcher. Role-gated permissions.

    - list: any authenticated user
    - create: researcher+ (level ≤ 4)
    - retrieve: any authenticated user
    - update: self (owning researcher) or admin+ (level ≤ 2)
    - delete: superadmin only (level ≤ 1)
    - deactivate: admin+ (level ≤ 2)
    """

    queryset = Researcher.objects.all()

    def get_permissions(self):
        """Assign permission classes per action.

        - destroy: only superadmin (level 1)
        - create: director+ (level ≤ 3) per spec — researchers cannot create
        - all others: IsResearcherOrReadOnly (self/level≤4 for writes)
        """
        if self.action == "destroy":
            return [IsAuthenticated(), IsSuperAdmin()]
        if self.action == "create":
            return [IsAuthenticated(), IsDirectorOrHigher()]
        return [IsAuthenticated(), IsResearcherOrReadOnly()]

    def get_serializer_class(self):
        """Return the appropriate serializer per action.

        - list: ResearcherListSerializer (lightweight summary)
        - create: ResearcherCreateSerializer (writable fields only)
        - retrieve/update: ResearcherSerializer (full detail + nested)
        """
        if self.action == "list":
            return ResearcherListSerializer
        if self.action in ("create", "partial_update", "update"):
            return ResearcherCreateSerializer
        return ResearcherSerializer

    def get_queryset(self) -> QuerySet:
        """Filter researchers by the user's active institution.

        Superadmins see all; regular users see only their institution.
        """
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return Researcher.objects.all()

        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            return Researcher.objects.none()

        return Researcher.objects.filter(institution=membership.institution)

    def perform_create(self, serializer):
        """Inject institution from active membership and delegate to service."""
        membership = self.request.active_membership
        if membership is None:
            raise DRFValidationError("No active institution membership.")

        institution = membership.institution
        validated_data = {k: v for k, v in serializer.validated_data.items()
                          if k != "institution"}

        try:
            researcher = ResearcherProfileService.create(
                institution=institution,
                user=None,
                **validated_data,
            )
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )
        # Set instance so DRF can serialize the response
        serializer.instance = researcher

    def perform_update(self, serializer):
        """Delegate update to service layer for business logic."""
        researcher = self.get_object()
        validated_data = {k: v for k, v in serializer.validated_data.items()
                          if k != "institution"}
        updated = ResearcherProfileService.update(researcher, **validated_data)
        serializer.instance = updated

    def perform_destroy(self, instance):
        """Delete a researcher. Superadmin-only (enforced by permissions)."""
        instance.delete()

    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk=None, **kwargs) -> Response:
        """Deactivate a researcher profile. Admin+ only.

        Returns 200 on success, 403 on permission denied, 404 on not found.
        """
        researcher = self.get_object()
        try:
            updated = ResearcherProfileService.deactivate(researcher)
            serializer = ResearcherSerializer(
                updated, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"detail": str(e.messages[0]) if hasattr(e, "messages") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ──────────────────────────────────────────────────────────
# ResearcherAffiliationViewSet
# ──────────────────────────────────────────────────────────


class ResearcherAffiliationViewSet(viewsets.ModelViewSet):
    """Nested affiliation CRUD under /researchers/{researcher_pk}/affiliations/.

    - list: any authenticated user
    - create: researcher+ (level ≤ 4) — self or admin
    - retrieve/update/delete: researcher+ (self or admin)
    - set_primary: researcher+ (self or admin)
    """

    serializer_class = ResearcherAffiliationSerializer
    permission_classes = [IsAuthenticated, IsResearcherOrReadOnly]

    def get_queryset(self) -> QuerySet:
        """Filter affiliations by researcher from URL."""
        researcher_pk = self.kwargs.get("researcher_pk")
        if researcher_pk:
            return ResearcherAffiliation.objects.filter(
                researcher_id=researcher_pk
            )
        return ResearcherAffiliation.objects.none()

    def perform_create(self, serializer):
        """Inject researcher from URL and delegate to service."""
        researcher_pk = self.kwargs.get("researcher_pk")
        try:
            researcher = Researcher.objects.get(pk=researcher_pk)
        except Researcher.DoesNotExist:
            raise Http404("Researcher not found.")

        center = serializer.validated_data.get("center")
        group = serializer.validated_data.get("group")
        line = serializer.validated_data.get("line")
        is_primary = serializer.validated_data.get("is_primary", False)

        try:
            affiliation = ResearcherAffiliationService.add(
                researcher=researcher,
                center=center,
                group=group,
                line=line,
                is_primary=is_primary,
            )
            serializer.instance = affiliation
        except ValidationError as e:
            raise DRFValidationError(
                detail=e.message_dict if hasattr(e, "message_dict") else e.messages
            )

    @action(detail=True, methods=["post"])
    def set_primary(self, request: Request, researcher_pk=None, pk=None, **kwargs) -> Response:
        """Set an affiliation as the primary one for the researcher.

        Atomically unsets current primary and sets the target.
        Returns 200 on success, 400 if already primary or invalid.
        """
        affiliation = self.get_object()
        try:
            updated = ResearcherAffiliationService.set_primary(affiliation)
            serializer = ResearcherAffiliationSerializer(
                updated, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"detail": str(e.messages[0]) if hasattr(e, "messages") else str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ──────────────────────────────────────────────────────────
# ExternalProfileViewSet
# ──────────────────────────────────────────────────────────


class ExternalProfileViewSet(viewsets.ModelViewSet):
    """Nested external profile CRUD under /researchers/{researcher_pk}/profiles/.

    - list: any authenticated user
    - create: researcher+ (level ≤ 4) — self or admin
    - retrieve/update/delete: researcher+ (self or admin)
    """

    serializer_class = ExternalProfileSerializer
    permission_classes = [IsAuthenticated, IsResearcherOrReadOnly]

    def get_queryset(self) -> QuerySet:
        """Filter profiles by researcher from URL."""
        researcher_pk = self.kwargs.get("researcher_pk")
        if researcher_pk:
            return ExternalProfile.objects.filter(
                researcher_id=researcher_pk
            )
        return ExternalProfile.objects.none()

    def perform_create(self, serializer):
        """Inject researcher FK from URL."""
        researcher_pk = self.kwargs.get("researcher_pk")
        try:
            researcher = Researcher.objects.get(pk=researcher_pk)
        except Researcher.DoesNotExist:
            raise Http404("Researcher not found.")
        serializer.save(researcher=researcher)


# ──────────────────────────────────────────────────────────
# ResearcherAttachmentViewSet
# ──────────────────────────────────────────────────────────


class ResearcherAttachmentViewSet(viewsets.ModelViewSet):
    """Nested attachment CRUD under /researchers/{researcher_pk}/attachments/.

    - list: any authenticated user
    - create: researcher+ (level ≤ 4) — self or admin
    - retrieve/update/delete: researcher+ (self or admin)
    """

    serializer_class = ResearcherAttachmentSerializer
    permission_classes = [IsAuthenticated, IsResearcherOrReadOnly]

    def get_queryset(self) -> QuerySet:
        """Filter attachments by researcher from URL."""
        researcher_pk = self.kwargs.get("researcher_pk")
        if researcher_pk:
            return ResearcherAttachment.objects.filter(
                researcher_id=researcher_pk
            )
        return ResearcherAttachment.objects.none()

    def perform_create(self, serializer):
        """Inject researcher FK from URL."""
        researcher_pk = self.kwargs.get("researcher_pk")
        try:
            researcher = Researcher.objects.get(pk=researcher_pk)
        except Researcher.DoesNotExist:
            raise Http404("Researcher not found.")
        serializer.save(researcher=researcher)
