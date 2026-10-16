/**
 * Documents feature types — mirror the backend documents module contracts.
 *
 * - DocumentType: reference data for document classification (Acta, Informe, etc.).
 * - Document: the main document entity with metadata and MinIO storage info.
 * - DocumentVersion: immutable snapshot of a document at a given version number.
 * - DocumentFilters: query params for the list endpoint.
 * - PresignResponse: the backend response for a presign request (URL + key).
 *
 * Design (server-state): these types match the DRF serializer outputs 1:1
 * so queries can be typed without mapping layers.
 */

/** Reference data: kind of document (e.g. Acta, Informe, Producto). */
export interface DocumentType {
  id: string;
  code: string;
  name: string;
  description: string;
}

/** A stored document with metadata, ownership, and MinIO storage info. */
export interface Document {
  id: string;
  title: string;
  institution: string;
  project: string | null;
  entity_type: string | null;
  entity_id: string | null;
  doc_type: DocumentType;
  is_signed: boolean;
  current_version: number;
  signature: {
    signer: string | null;
    signed_at: string;
    sha256: string;
  } | null;
  created_by: {
    id: string;
    full_name: string;
  };
  created_at: string;
  updated_at: string;
}

/** Immutable snapshot of a document at a given version. */
export interface DocumentVersion {
  id: string;
  document: string;
  version: number;
  object_key: string;
  sha256: string;
  size_bytes: number;
  mime_type: string;
  uploaded_by: {
    id: string;
    full_name: string;
  };
  uploaded_at: string;
  /** Presigned GET URL — only populated when explicitly requested. */
  download_url?: string;
}

/** Query params accepted by GET /api/documents/. */
export interface DocumentFilters {
  doc_type?: string;
  entity_type?: string;
  is_signed?: boolean;
  search?: string;
  page?: number;
}

/** Body of POST /api/documents/{id}/presign/ on success. */
export interface PresignResponse {
  upload_url: string;
  key: string;
}
