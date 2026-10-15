/**
 * Documents feature schemas — zod validation for upload metadata.
 *
 * The upload flow is a two-step process: validate the metadata first
 * (this schema), then run the presign/upload/confirm pipeline. The
 * file itself is validated separately (size + type) at the UI layer.
 *
 * Design (server-state): zod schemas catch invalid input before the
 * network round-trip, matching the backend serializer constraints.
 */

import { z } from "zod";

/**
 * Metadata required to create a document record before upload.
 * Mirrors the backend DocumentCreateSerializer field constraints.
 */
export const uploadMetadataSchema = z.object({
  filename: z.string().min(1, "El nombre del archivo es requerido"),
  doc_type: z.string().min(1, "El tipo de documento es requerido"),
  entity_type: z.string().optional(),
  entity_id: z.string().optional(),
});

/** Inferred type from the upload metadata zod schema. */
export type UploadMetadata = z.infer<typeof uploadMetadataSchema>;
