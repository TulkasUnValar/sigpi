/**
 * Documents feature barrel — public API of the module.
 *
 * Pages and the shell import from here; internals stay private to the
 * feature directory.
 */

export type {
  Document,
  DocumentFilters,
  DocumentType,
  DocumentVersion,
  PresignResponse,
} from "./types";
export { DOCUMENT_ENTITY_TYPES, MAX_FILE_SIZE } from "./constants";
export { uploadMetadataSchema } from "./schemas";
export type { UploadMetadata } from "./schemas";
export {
  useDocumentTypes,
  useDocuments,
  useDocument,
  useDocumentVersions,
} from "./queries";
export { useCreateDocument, useReuploadDocument } from "./mutations";
export { canUploadDocuments, canViewDocuments } from "./permissions";
