"""MinIO/S3 storage backend for the documents module.

Files never transit Django (spec RF-D01): the backend issues presigned
URLs against MinIO via the S3 API and clients upload/download directly.
This module provides the storage backend and the canonical object-key
scheme used by the documents spec.

Spec: openspec/changes/attachments/specs/documents/spec.md — MinIO/S3 Contract:
- Object keys follow documents/{institution_id}/{document_id}/v{version}/{filename}.
- Presigned PUT URLs expire within 30 minutes; GET within 15 minutes.
"""

from typing import Any

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

DOCUMENTS_PREFIX = "documents"


class MinIOStorage(S3Boto3Storage):
    """Private MinIO bucket with presigned PUT/GET URL helpers."""

    # Attributes injected by django-storages from STORAGES OPTIONS at
    # instantiation; declared here for the type checker.
    bucket_name: str
    endpoint_url: str | None
    querystring_auth: bool
    querystring_expire: int

    def _s3_client(self) -> Any:
        """Return the boto3 S3 client used to sign URLs."""
        return self.connection.meta.client  # type: ignore[reportOptionalMemberAccess]

    def build_object_key(self, institution_id, document_id, version, filename):
        """Return the canonical object key for a document version.

        Scheme: documents/{institution_id}/{document_id}/v{version}/{filename}
        """
        return f"{DOCUMENTS_PREFIX}/{institution_id}/{document_id}/v{version}/{filename}"

    def presign_put(self, object_key, expires=None):
        """Return a presigned PUT URL for direct client upload.

        Default expiry is 30 minutes (settings.MINIO_PRESIGN_PUT_EXPIRY).
        """
        if expires is None:
            expires = settings.MINIO_PRESIGN_PUT_EXPIRY
        return self._s3_client().generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expires,
        )

    def presign_get(self, object_key, expires=None):
        """Return a presigned GET URL for direct client download.

        Default expiry is 15 minutes (settings.MINIO_PRESIGN_GET_EXPIRY).
        """
        if expires is None:
            expires = settings.MINIO_PRESIGN_GET_EXPIRY
        return self._s3_client().generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expires,
        )
