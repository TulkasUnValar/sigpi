/**
 * Documents feature queries — React Query hooks for reading document data.
 *
 * - useDocumentTypes: reference data (small, rarely changes).
 * - useDocuments: paginated list with filters.
 * - useDocument: single document detail.
 * - useDocumentVersions: version history for a document.
 *
 * Design (server-state): query keys live in `lib/query-keys.ts` so
 * mutations can invalidate them without reaching into feature internals.
 * The `api` helper is used for every call because these endpoints live
 * on the DRF backend (not MinIO) and require session credentials.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type {
  Document,
  DocumentFilters,
  DocumentType,
  DocumentVersion,
} from "./types";

/** Fetch the catalog of document types (Acta, Informe, etc.). */
export function useDocumentTypes() {
  return useQuery({
    queryKey: ["document-types"],
    queryFn: async () => {
      const response = await api.get<{ results: DocumentType[] }>("/api/document-types/");
      return response.results;
    },
  });
}

/** Fetch a paginated, filterable list of documents. */
export function useDocuments(filters: DocumentFilters = {}) {
  return useQuery({
    queryKey: queryKeys.documents.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.doc_type) params.append("doc_type", filters.doc_type);
      if (filters.entity_type) params.append("entity_type", filters.entity_type);
      if (filters.is_signed !== undefined) params.append("is_signed", String(filters.is_signed));
      if (filters.search) params.append("search", filters.search);
      if (filters.page) params.append("page", String(filters.page));

      const response = await api.get<{ results: Document[]; count: number }>(
        `/api/documents/?${params.toString()}`,
      );
      return response;
    },
  });
}

/** Fetch a single document by id. Disabled until an id is provided. */
export function useDocument(id: string) {
  return useQuery({
    queryKey: queryKeys.documents.detail(id),
    queryFn: async () => {
      const response = await api.get<Document>(`/api/documents/${id}/`);
      return response;
    },
    enabled: !!id,
  });
}

/** Fetch the version history of a document. Disabled until an id is provided. */
export function useDocumentVersions(id: string) {
  return useQuery({
    queryKey: queryKeys.documents.versions(id),
    queryFn: async () => {
      const response = await api.get<{ results: DocumentVersion[] }>(
        `/api/documents/${id}/versions/`,
      );
      return response.results;
    },
    enabled: !!id,
  });
}
