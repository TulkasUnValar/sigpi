"use client";

/**
 * Products mutations — create.
 *
 * Spec (products-ui server state):
 *   - createProduct POSTs /api/products/ with the active institution scope.
 *   - Every success invalidates the products root so list/detail keys
 *     refetch; failures leave the cache intact and surface via the caller.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import type {
  CreateProductAttachmentPayload,
  CreateProductAuthorPayload,
  CreateProductPayload,
  ResearchProduct,
} from "@/features/products/types";

function useInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Create a product — POST /api/products/. */
export function useCreateProduct() {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateProductPayload) =>
      api.post<ResearchProduct>("/api/products/", payload, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Update a product — PATCH /api/products/{id}/. */
export function useUpdateProduct(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: Partial<CreateProductPayload>) =>
      api.patch<ResearchProduct>(`/api/products/${id}/`, payload, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Delete a product — DELETE /api/products/{id}/. */
export function useDeleteProduct(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: () => api.delete(`/api/products/${id}/`, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

// ──────────────────────────────────────────────────────────
// Nested mutations — authors and attachments.
//
// The product id comes from the URL; every call passes the active
// institutionId and invalidates `products.all` only on success so the
// nested lists refetch.
// ──────────────────────────────────────────────────────────

/** Create an author — POST /api/products/{id}/authors/. */
export function useCreateProductAuthor(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateProductAuthorPayload) =>
      api.post(`/api/products/${id}/authors/`, payload, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Update an author — PATCH /api/products/{id}/authors/{pk}/. */
export function useUpdateProductAuthor(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: ({
      authorId,
      payload,
    }: {
      authorId: string;
      payload: Partial<CreateProductAuthorPayload>;
    }) => api.patch(`/api/products/${id}/authors/${authorId}/`, payload, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Delete an author — DELETE /api/products/{id}/authors/{pk}/. */
export function useDeleteProductAuthor(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (authorId: string) =>
      api.delete(`/api/products/${id}/authors/${authorId}/`, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Create an attachment (metadata only) — POST /api/products/{id}/attachments/. */
export function useCreateProductAttachment(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateProductAttachmentPayload) =>
      api.post(`/api/products/${id}/attachments/`, payload, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Update an attachment — PATCH /api/products/{id}/attachments/{pk}/. */
export function useUpdateProductAttachment(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: ({
      attachmentId,
      payload,
    }: {
      attachmentId: string;
      payload: Partial<CreateProductAttachmentPayload>;
    }) =>
      api.patch(`/api/products/${id}/attachments/${attachmentId}/`, payload, {
        institutionId,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

/** Delete an attachment — DELETE /api/products/{id}/attachments/{pk}/. */
export function useDeleteProductAttachment(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (attachmentId: string) =>
      api.delete(`/api/products/${id}/attachments/${attachmentId}/`, { institutionId }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
