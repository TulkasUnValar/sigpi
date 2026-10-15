/**
 * Documents feature mutations — React Query hooks for writing document data.
 *
 * The upload flow is a 4-step pipeline (RN-035 / RN-036):
 *   1. POST /api/documents/         → create metadata record
 *   2. POST /api/documents/{id}/presign/ → get presigned PUT URL
 *   3. PUT <presigned_url>          → upload file directly to MinIO
 *   4. POST /api/documents/{id}/confirm/ → tell backend to verify + mark uploaded
 *
 * On success, the documents query keys are invalidated so the list and
 * detail views refetch. Re-upload uses the same presign/confirm pair but
 * skips the metadata creation (the record already exists).
 *
 * Design (server-state): mutations invalidate via the centralized query
 * key factories so cache stays consistent without manual refetch logic.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { presignUpload } from "@/lib/storage-upload";
import type { Document, PresignResponse } from "./types";
import type { UploadMetadata } from "./schemas";

/** Create a new document via the full presign/upload/confirm pipeline. */
export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ metadata, file }: { metadata: UploadMetadata; file: File }) => {
      // 1. Create document metadata record in the backend.
      const document = await api.post<Document>("/api/documents/", metadata);

      // 2. Request a presigned PUT URL for the new document id.
      const presign = await api.post<PresignResponse>(
        `/api/documents/${document.id}/presign/`,
      );

      // 3. Upload the file directly to MinIO (no auth headers).
      await presignUpload(presign.upload_url, file);

      // 4. Confirm the upload so the backend verifies + marks as uploaded.
      await api.post(`/api/documents/${document.id}/confirm/`, { key: presign.key });

      return document;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
}

/** Re-upload a document (creates a new version) via presign/confirm. */
export function useReuploadDocument(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      // 1. Get presigned PUT URL for a new version of the existing record.
      const presign = await api.post<PresignResponse>(`/api/documents/${id}/presign/`);

      // 2. Upload the file directly to MinIO (no auth headers).
      await presignUpload(presign.upload_url, file);

      // 3. Confirm — backend bumps the version number.
      await api.post(`/api/documents/${id}/confirm/`, { key: presign.key });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(id) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(id) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
}
