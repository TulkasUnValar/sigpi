/**
 * Documents feature constants — labels, limits, and shared reference data.
 *
 * - DOCUMENT_ENTITY_TYPES: the polymorphic entity kinds a document can attach to.
 * - MAX_FILE_SIZE: hard upload cap enforced client-side (backend enforces its own).
 *
 * Design (server-state): kept here so forms and filters share a single source.
 */

/** Entity kinds accepted by the documents API (polymorphic relation). */
export const DOCUMENT_ENTITY_TYPES = [
  { value: "project", label: "Proyecto" },
  { value: "advance", label: "Avance" },
  { value: "report", label: "Informe" },
  { value: "product", label: "Producto" },
  { value: "call", label: "Convocatoria" },
] as const;

/** Maximum allowed upload size (100 MB). Backend enforces independently. */
export const MAX_FILE_SIZE = 100 * 1024 * 1024;
