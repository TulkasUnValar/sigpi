"""
Service layer for the documents module — business rules + audit.

DocumentService: issues presigned PUT keys, confirms uploads (key match →
409), allocates the next version, validates the entity's institution, and
emits DOCUMENT_UPLOADED. SignatureService: fetches object bytes, computes
SHA-256 server-side, creates the signature atomically, locks the document
via update() (bypassing the model save() immutability guard), and emits
DOCUMENT_SIGNED. MinutesService: validates acta type and project/
institution consistency, creates the row, and emits MINUTES_CREATED.

Error contract (spec.md): ValidationError subclasses mark HTTP conflict
(409) cases for the view layer; StorageUnavailableError maps to 503.

Design reference: openspec/changes/attachments/design.md — Data Flow
Spec reference:   openspec/changes/attachments/specs/documents/spec.md
"""

import hashlib

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max

from apps.accounts.audit import AuditEventEmitter
from apps.documents.models import DigitalSignature, Document, DocumentType, DocumentVersion, Minutes
from apps.documents.signals import document_signed
from apps.documents.storage import DOCUMENTS_PREFIX

# ──────────────────────────────────────────────
# Service exceptions (mapped to HTTP status by views)
# ──────────────────────────────────────────────


class ObjectKeyMismatchError(ValidationError):
    """Confirm with an object_key not issued for this document (RF-D01 → 409)."""


class SignedDocumentImmutableError(ValidationError):
    """Mutation/version bump of a signed document (RF-066 → 409)."""


class VersionAlreadySignedError(ValidationError):
    """Re-sign of an already-signed version (RF-D04 → 409)."""


class IntegrityCheckError(ValidationError):
    """Server-computed hash differs from the confirmed hash (RF-D04 → 409)."""


class VersionNotFoundError(ValidationError):
    """Sign target version does not exist (→ 404)."""


class StorageUnavailableError(Exception):
    """MinIO unreachable or errored (error contract → 503)."""


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────


def _get_storage(storage=None):
    """Return the injected storage backend or the configured default."""
    return storage if storage is not None else default_storage


def _validate_filename(filename):
    """Reject empty and path-traversal filenames (→ 400)."""
    if not filename or not isinstance(filename, str):
        raise ValidationError({"filename": "filename is required."})
    if "/" in filename or "\\" in filename or filename in (".", ".."):
        raise ValidationError({"filename": "filename must be a plain file name."})


def _resolve_entity(institution, entity_type, entity_id):
    """Resolve the explicit entity FK and verify its institution.

    Returns a {field_name: entity} dict for Document creation, or {} when
    the document is standalone (no entity binding).
    """
    if entity_type is None and entity_id is None:
        return {}
    if entity_type is None or entity_id is None:
        raise ValidationError(
            {"entity_type": "entity_type and entity_id must be provided together."}
        )
    if entity_type not in Document.ENTITY_FIELDS:
        raise ValidationError({"entity_type": f"Unknown entity type: {entity_type}"})

    field = Document.ENTITY_FIELDS[entity_type]
    model = Document._meta.get_field(field).remote_field.model
    try:
        entity = model.objects.get(pk=entity_id)
    except model.DoesNotExist:
        raise ValidationError({"entity_id": f"{entity_type} entity not found."})

    if entity.institution_id != institution.id:
        raise ValidationError({"entity_id": "Entity belongs to a different institution."})
    return {field: entity}


def _next_version(document):
    """Return the next version number for a document (max + 1, starting at 1)."""
    return (document.versions.aggregate(max_version=Max("version"))["max_version"] or 0) + 1


def _is_signed(document):
    """DB-level signed check — robust against stale in-memory instances.

    The signing service flips is_signed via update(); a document object
    loaded before signing may still carry the old False flag.
    """
    return Document.objects.filter(pk=document.pk, is_signed=True).exists()


# ──────────────────────────────────────────────
# DocumentService
# ──────────────────────────────────────────────


class DocumentService:
    """Owns the presign → confirm lifecycle of document versions."""

    @staticmethod
    def presign(
        institution,
        user,
        doc_type,
        filename,
        content_type,
        entity_type=None,
        entity_id=None,
        storage=None,
    ):
        """Issue a presigned PUT URL for a NEW document (v1).

        Creates the Document metadata row (RF-D02), validates the entity's
        institution (cross-institution → 403 in views), and returns
        {upload_url, object_key, document_id}.
        """
        try:
            doc_type_obj = DocumentType.objects.get(code=doc_type)
        except DocumentType.DoesNotExist:
            raise ValidationError({"doc_type": f"Unknown document type: {doc_type}"})
        _validate_filename(filename)
        entity_kwargs = _resolve_entity(institution, entity_type, entity_id)

        with transaction.atomic():
            document = Document.objects.create(
                institution=institution,
                doc_type=doc_type_obj,
                title=filename,
                entity_type=entity_type,
                created_by=user,
                **entity_kwargs,
            )

        storage = _get_storage(storage)
        object_key = storage.build_object_key(institution.id, document.id, 1, filename)
        try:
            upload_url = storage.presign_put(object_key)
        except Exception as exc:
            raise StorageUnavailableError("Storage unavailable") from exc
        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "document_id": str(document.pk),
        }

    @staticmethod
    def presign_next_version(document, user, filename, content_type, storage=None):
        """Issue a presigned PUT URL for the next version (RF-D03).

        Rejects signed documents (RF-066 version bump → 409). Returns
        {upload_url, object_key, version}.
        """
        if _is_signed(document):
            raise SignedDocumentImmutableError("Signed documents are immutable")
        _validate_filename(filename)

        next_version = _next_version(document)
        storage = _get_storage(storage)
        object_key = storage.build_object_key(
            document.institution_id, document.id, next_version, filename
        )
        try:
            upload_url = storage.presign_put(object_key)
        except Exception as exc:
            raise StorageUnavailableError("Storage unavailable") from exc
        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "version": next_version,
        }

    @staticmethod
    def confirm(document, object_key, user, size_bytes, mime_type, sha256, storage=None):
        """Record a DocumentVersion after the client uploaded the object (RF-D01).

        Verifies the object_key matches the canonical scheme for this
        document at the next version (mismatch → 409 ObjectKeyMismatchError),
        verifies the object exists in storage, and emits DOCUMENT_UPLOADED.
        sha256 is the client-claimed expected hash — re-verified server-side
        at sign time (frontend hashes are never trusted for the signature).
        """
        if _is_signed(document):
            raise SignedDocumentImmutableError("Signed documents are immutable")

        next_version = _next_version(document)
        expected_prefix = (
            f"{DOCUMENTS_PREFIX}/{document.institution_id}/{document.pk}/v{next_version}/"
        )
        if not object_key.startswith(expected_prefix):
            raise ObjectKeyMismatchError("Object key mismatch")

        storage = _get_storage(storage)
        try:
            exists = storage.exists(object_key)
        except Exception as exc:
            raise StorageUnavailableError("Storage unavailable") from exc
        if not exists:
            raise ValidationError({"object_key": "Object not found in storage."})

        with transaction.atomic():
            version = DocumentVersion.objects.create(
                document=document,
                version=next_version,
                object_key=object_key,
                sha256=sha256,
                size_bytes=size_bytes,
                mime_type=mime_type,
                uploaded_by=user,
            )

        AuditEventEmitter().emit(
            event_type="DOCUMENT_UPLOADED",
            user=user,
            institution_id=document.institution_id,
            details={
                "document_id": str(document.pk),
                "version": version.version,
            },
        )
        return version


# ──────────────────────────────────────────────
# SignatureService
# ──────────────────────────────────────────────


class SignatureService:
    """Signs a document version: GET bytes → SHA-256 → sign → lock (RF-D04)."""

    @staticmethod
    def sign(document, version_number, user, storage=None, metadata=None):
        """Fetch the object, verify the hash, create the signature, lock.

        - version missing → VersionNotFoundError (404)
        - version already signed → VersionAlreadySignedError (409)
        - any other version signed → SignedDocumentImmutableError (409)
        - server-computed hash != version.sha256 → IntegrityCheckError (409)
        - storage error → StorageUnavailableError (503)

        The document is locked with a QuerySet update() because
        Document.save() runs clean() and raises on signed documents
        (RF-066 model guard).
        """
        try:
            version = document.versions.get(version=version_number)
        except DocumentVersion.DoesNotExist:
            raise VersionNotFoundError("Version not found")

        if version.signatures.exists():
            raise VersionAlreadySignedError("Version already signed")
        if _is_signed(document):
            raise SignedDocumentImmutableError("Signed documents are immutable")

        storage = _get_storage(storage)
        try:
            with storage.open(version.object_key, "rb") as obj_file:
                digest = hashlib.sha256()
                for chunk in iter(lambda: obj_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            computed = digest.hexdigest()
        except Exception as exc:
            raise StorageUnavailableError("Storage unavailable") from exc

        if computed != version.sha256:
            raise IntegrityCheckError("Integrity check failed")

        with transaction.atomic():
            signature = DigitalSignature.objects.create(
                document_version=version,
                signer=user,
                sha256=computed,
                signer_metadata=metadata or {},
            )
            # Bypass the model save() immutability guard on purpose.
            Document.objects.filter(pk=document.pk).update(is_signed=True)

        AuditEventEmitter().emit(
            event_type="DOCUMENT_SIGNED",
            user=user,
            institution_id=document.institution_id,
            details={
                "document_id": str(document.pk),
                "version": version.version,
                "sha256": computed,
            },
        )
        # Semantic signal for the notifications module (spec delta RN-3).
        # Emitted after the atomic write so the in-app Notification row
        # persists with the signing transaction.
        document_signed.send(
            sender=DigitalSignature,
            instance=document,
            document=document,
            version=version.version,
            signer=user,
            sha256=computed,
        )
        return signature


# ──────────────────────────────────────────────
# MinutesService
# ──────────────────────────────────────────────


class MinutesService:
    """Creates Minutes rows (RF-D07) with acta validation and audit."""

    @staticmethod
    def create(institution, user, acta_type, document, project=None):
        """Create a Minutes row and emit MINUTES_CREATED.

        Validates the acta_type (4 values), that the backing document is
        of an acta_* type, and that document/project belong to the same
        institution as the Minutes row.
        """
        if acta_type not in Minutes.ActaType.values:
            raise ValidationError({"acta_type": f"Invalid acta type: {acta_type}"})
        if not document.doc_type.code.startswith("acta_"):
            raise ValidationError({"document": "Minutes must be backed by an acta document."})
        if document.institution_id != institution.id:
            raise ValidationError({"document": "Document belongs to a different institution."})
        if project is not None and project.institution_id != institution.id:
            raise ValidationError({"project": "Project belongs to a different institution."})

        with transaction.atomic():
            minutes = Minutes.objects.create(
                acta_type=acta_type,
                project=project,
                institution=institution,
                document=document,
                created_by=user,
            )

        AuditEventEmitter().emit(
            event_type="MINUTES_CREATED",
            user=user,
            institution_id=institution.id,
            details={
                "minutes_id": str(minutes.pk),
                "acta_type": acta_type,
            },
        )
        return minutes
