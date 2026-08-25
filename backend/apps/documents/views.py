"""
DRF ViewSets for the documents module — Phase 5 (views, URLs & integration).

Implements the API Contract from spec.md:
- DocumentViewSet: CRUD + actions — types, presign, confirm, versions
  (list + re-upload), version detail + presigned GET, sign, download.
- DigitalSignatureViewSet: read-only signature records per document (RF-D05).
- MinutesViewSet: CRUD for actas (RF-D07).

Error contract (spec.md Error Handling), mapped from service exceptions:
- 400  ValidationError (invalid entity/type/filename, unknown doc_type)
- 403  cross-institution entity on presign / minutes; Auditor writes
- 404  nonexistent document or version
- 409  ObjectKeyMismatch, SignedDocumentImmutable, VersionAlreadySigned,
       IntegrityCheck
- 503  StorageUnavailable

Document.save() runs full_clean() (model immutability guard RF-066), so
serializer-driven updates of signed documents surface Django ValidationError
which the views map to 409.

Design reference: openspec/changes/attachments/design.md — Interfaces/Contracts
Spec reference:   openspec/changes/attachments/specs/documents/spec.md — API Contract
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
)
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.audit import AuditEventEmitter, AuditEventType
from apps.audit.context import get_audit_context
from apps.documents.filters import DocumentFilter, MinutesFilter
from apps.documents.models import (
    DigitalSignature,
    Document,
    DocumentType,
    DocumentVersion,
    Minutes,
)
from apps.documents.permissions import CanWriteDocuments, IsSameInstitution
from apps.documents.serializers import (
    DigitalSignatureSerializer,
    DocumentSerializer,
    DocumentTypeSerializer,
    DocumentVersionSerializer,
    MinutesSerializer,
)
from apps.documents.services import (
    DocumentService,
    IntegrityCheckError,
    MinutesService,
    ObjectKeyMismatchError,
    SignatureService,
    SignedDocumentImmutableError,
    StorageUnavailableError,
    VersionAlreadySignedError,
    VersionNotFoundError,
    _get_storage,
    _is_signed,
)

# Service ValidationError subclasses that mark HTTP conflicts (spec → 409).
CONFLICT_ERRORS = (
    ObjectKeyMismatchError,
    SignedDocumentImmutableError,
    VersionAlreadySignedError,
    IntegrityCheckError,
)

IMMUTABLE_MESSAGE = "Signed documents are immutable"


class Conflict(APIException):
    """HTTP 409 Conflict — spec Error Handling (immutable / key / hash cases)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "conflict"


class ServiceUnavailable(APIException):
    """HTTP 503 — MinIO unreachable (spec Error Handling)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Storage unavailable."
    default_code = "service_unavailable"


# ──────────────────────────────────────────────
# Error mapping helpers
# ──────────────────────────────────────────────


def _extract_error(e: DjangoValidationError) -> str | dict:
    """Extract a consistent error detail from a Django ValidationError."""
    if hasattr(e, "message_dict") and e.message_dict:
        return e.message_dict
    if hasattr(e, "messages") and e.messages:
        msg = e.messages[0] if isinstance(e.messages, list) else str(e.messages)
        return msg
    return str(e)


def _error_text(e: DjangoValidationError) -> str:
    """Flatten a ValidationError into searchable text."""
    if hasattr(e, "message_dict") and e.message_dict:
        return " ".join(str(m) for msgs in e.message_dict.values() for m in msgs)
    if hasattr(e, "messages") and e.messages:
        return " ".join(str(m) for m in e.messages)
    return str(e)


def _is_cross_institution_error(e: DjangoValidationError) -> bool:
    """Service raised 'Entity belongs to a different institution.' (→ 403)."""
    return "different institution" in _error_text(e)


def _map_service_error(e: DjangoValidationError) -> APIException:
    """Map a service/model ValidationError to the spec HTTP exception."""
    if isinstance(e, CONFLICT_ERRORS):
        return Conflict(_extract_error(e))
    if _is_cross_institution_error(e):
        return PermissionDenied(_extract_error(e))
    if IMMUTABLE_MESSAGE in _error_text(e):
        return Conflict(IMMUTABLE_MESSAGE)
    return DRFValidationError(_extract_error(e))


def _emit_document_download(document, version: int) -> None:
    """Emit a DOCUMENT_DOWNLOADED audit event (RF-106 / RF-D09).

    Called immediately after a presigned GET URL is issued (download /
    version_detail) and before the response is built. Uses the request-scoped
    audit context (user, IP, institution) populated by TenantMiddleware.
    Storage failures return 503 before this helper runs, so no event is written.
    """
    ctx = get_audit_context()
    AuditEventEmitter().emit(
        event_type=AuditEventType.DOCUMENT_DOWNLOADED,
        user=ctx.user,
        ip_address=ctx.ip_address,
        institution_id=ctx.institution_id or document.institution_id,
        entity_type="document",
        entity_id=document.id,
        action="DOWNLOAD",
        project_id=document.project_id,
        details={"document_id": str(document.id), "version": version},
    )


# ──────────────────────────────────────────────
# Institution scoping (superadmin bypass)
# ──────────────────────────────────────────────


def _scoped_documents(request: Request) -> QuerySet:
    """Documents visible to the request user (superuser bypasses)."""
    user = request.user
    if user.is_authenticated and user.is_superuser:
        return Document.objects.all()
    membership = getattr(request, "active_membership", None)
    if membership is None:
        return Document.objects.none()
    return Document.objects.filter(institution=membership.institution)


def _scoped_minutes(request: Request) -> QuerySet:
    """Minutes visible to the request user (superuser bypasses)."""
    user = request.user
    if user.is_authenticated and user.is_superuser:
        return Minutes.objects.all()
    membership = getattr(request, "active_membership", None)
    if membership is None:
        return Minutes.objects.none()
    return Minutes.objects.filter(institution=membership.institution)


# ──────────────────────────────────────────────
# DocumentViewSet
# ──────────────────────────────────────────────


class DocumentViewSet(viewsets.ModelViewSet):
    """CRUD + presign/confirm/versions/sign/download actions for documents.

    - reads: any authenticated member of the institution
    - writes (presign, confirm, sign, versions, metadata update): role ≤ 6
    - signed documents are immutable → 409 (service + model guards)
    """

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DocumentFilter
    search_fields = ["title"]
    ordering_fields = ["title", "created_at"]
    permission_classes = [IsAuthenticated, CanWriteDocuments, IsSameInstitution]
    lookup_value_regex = r"[0-9a-f-]{36}"

    def get_queryset(self) -> QuerySet:
        return _scoped_documents(self.request)

    # ── Lifecycle hooks ─────────────────────────

    def create(self, request: Request, *args, **kwargs) -> Response:
        """POST /documents/ starts the presign flow (spec API Contract note)."""
        return self.presign(request)

    def perform_update(self, serializer):
        """Metadata update — signed documents raise model clean() → 409."""
        try:
            serializer.save()
        except DjangoValidationError as e:
            raise _map_service_error(e)

    def perform_destroy(self, instance):
        if _is_signed(instance):
            raise Conflict(IMMUTABLE_MESSAGE)
        instance.delete()

    # ── Actions ─────────────────────────────────

    @action(detail=False, methods=["get"])
    def types(self, request: Request) -> Response:
        """List the 12 authoritative document types (RF-D08)."""
        serializer = DocumentTypeSerializer(DocumentType.objects.all(), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def presign(self, request: Request) -> Response:
        """Issue a presigned PUT URL for a NEW document (RF-D01)."""
        membership = getattr(request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")
        try:
            result = DocumentService.presign(
                institution=membership.institution,
                user=request.user,
                doc_type=request.data.get("doc_type"),
                filename=request.data.get("filename"),
                content_type=request.data.get("content_type"),
                entity_type=request.data.get("entity_type"),
                entity_id=request.data.get("entity_id"),
            )
        except DjangoValidationError as e:
            raise _map_service_error(e)
        except StorageUnavailableError as e:
            raise ServiceUnavailable(str(e))
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk=None) -> Response:
        """Record a DocumentVersion after the client uploaded the object (RF-D01)."""
        document = self.get_object()
        data = request.data
        try:
            version = DocumentService.confirm(
                document=document,
                object_key=data.get("object_key"),
                user=request.user,
                size_bytes=data.get("size_bytes"),
                mime_type=data.get("mime_type"),
                sha256=data.get("sha256"),
            )
        except DjangoValidationError as e:
            raise _map_service_error(e)
        except StorageUnavailableError as e:
            raise ServiceUnavailable(str(e))
        serializer = DocumentVersionSerializer(version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def versions(self, request: Request, pk=None) -> Response:
        """GET: versions descending; POST: presign the next version (RF-D03)."""
        document = self.get_object()
        if request.method == "GET":
            qs = document.versions.select_related("uploaded_by").order_by("-version")
            serializer = DocumentVersionSerializer(qs, many=True)
            return Response(serializer.data)
        try:
            result = DocumentService.presign_next_version(
                document=document,
                user=request.user,
                filename=request.data.get("filename"),
                content_type=request.data.get("content_type"),
            )
        except DjangoValidationError as e:
            raise _map_service_error(e)
        except StorageUnavailableError as e:
            raise ServiceUnavailable(str(e))
        return Response(result)

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version>[0-9]+)")
    def version_detail(self, request: Request, pk=None, version=None) -> Response:
        """Version detail + presigned GET download (+ signature when signed)."""
        document = self.get_object()
        try:
            version_obj = document.versions.get(version=int(version))
        except DocumentVersion.DoesNotExist:
            raise NotFound("Version not found")
        signature = version_obj.signatures.select_related("signer").first()
        try:
            download_url = _get_storage().presign_get(version_obj.object_key)
        except Exception as exc:
            raise ServiceUnavailable("Storage unavailable") from exc
        _emit_document_download(document, version_obj.version)
        data = DocumentVersionSerializer(version_obj).data
        data["download_url"] = download_url
        data["signature"] = DigitalSignatureSerializer(signature).data if signature else None
        return Response(data)

    @action(detail=True, methods=["post"], url_path=r"versions/(?P<version>[0-9]+)/sign")
    def sign(self, request: Request, pk=None, version=None) -> Response:
        """Sign a version: GET bytes → SHA-256 → signature → lock (RF-D04)."""
        document = self.get_object()
        try:
            signature = SignatureService.sign(
                document=document,
                version_number=int(version),
                user=request.user,
            )
        except VersionNotFoundError as e:
            raise NotFound(str(e))
        except DjangoValidationError as e:
            raise _map_service_error(e)
        except StorageUnavailableError as e:
            raise ServiceUnavailable(str(e))
        serializer = DigitalSignatureSerializer(signature)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request: Request, pk=None) -> Response:
        """Presigned GET URL for the latest version (spec API Contract)."""
        document = self.get_object()
        version_obj = document.versions.order_by("-version").first()
        if version_obj is None:
            raise NotFound("No versions available")
        try:
            download_url = _get_storage().presign_get(version_obj.object_key)
        except Exception as exc:
            raise ServiceUnavailable("Storage unavailable") from exc
        _emit_document_download(document, version_obj.version)
        return Response(
            {
                "download_url": download_url,
                "object_key": version_obj.object_key,
                "version": version_obj.version,
            }
        )


# ──────────────────────────────────────────────
# DigitalSignatureViewSet
# ──────────────────────────────────────────────


class DigitalSignatureViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only signature records for a document (RF-D05)."""

    serializer_class = DigitalSignatureSerializer
    permission_classes = [IsAuthenticated, CanWriteDocuments]
    lookup_url_kwarg = "signature_pk"

    def get_queryset(self) -> QuerySet:
        document_pk = self.kwargs.get("pk")
        qs = DigitalSignature.objects.select_related("document_version", "signer")
        if document_pk:
            qs = qs.filter(document_version__document_id=document_pk)
        return qs.filter(document_version__document__in=_scoped_documents(self.request))


# ──────────────────────────────────────────────
# MinutesViewSet
# ──────────────────────────────────────────────


class MinutesViewSet(viewsets.ModelViewSet):
    """CRUD for Minutes (actas) — RF-D07. Signed actas are immutable (→ 409)."""

    queryset = Minutes.objects.all()
    serializer_class = MinutesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MinutesFilter
    permission_classes = [IsAuthenticated, CanWriteDocuments, IsSameInstitution]

    def get_queryset(self) -> QuerySet:
        return _scoped_minutes(self.request)

    def perform_create(self, serializer):
        membership = getattr(self.request, "active_membership", None)
        if membership is None:
            raise DRFValidationError("No active institution membership.")
        data = serializer.validated_data
        try:
            minutes = MinutesService.create(
                institution=membership.institution,
                user=self.request.user,
                acta_type=data["acta_type"],
                document=data["document"],
                project=data.get("project"),
            )
            serializer.instance = minutes
        except DjangoValidationError as e:
            raise _map_service_error(e)

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as e:
            raise _map_service_error(e)

    def perform_destroy(self, instance):
        if instance.document.versions.filter(signatures__isnull=False).exists():
            raise Conflict(IMMUTABLE_MESSAGE)
        instance.delete()
