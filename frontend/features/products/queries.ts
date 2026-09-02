"use client";

/**
 * Products TanStack Query hooks — list and detail.
 *
 * Spec (products-ui list / RF-001):
 *   - useProductsList serializes the 9 backend filters (type, year,
 *     year__gte, year__lte, project, researcher, center, group, line)
 *     plus page and ordering via buildQueryString; empty ("Todos")
 *     values are omitted and page 1 is not serialized.
 *   - All hooks pass the active institutionId to `api` so the
 *     X-Institution-ID header is sent.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type {
  Page,
  ProductAttachment,
  ProductAuthor,
  ProductFilter,
  ProductList,
  ResearchProduct,
} from "@/features/products/types";

/** Active institution id from the auth store (drives X-Institution-ID). */
export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** List query options (filters + pagination + ordering). */
export interface ProductsListParams extends ProductFilter {
  page?: number;
  ordering?: string;
}

/** Serialize list params into a DRF query string. */
export function buildQueryString(params: ProductsListParams): string {
  const sp = new URLSearchParams();
  if (params.page && params.page > 1) sp.set("page", String(params.page));
  if (params.type) sp.set("type", params.type);
  if (params.year) sp.set("year", params.year);
  if (params.year__gte) sp.set("year__gte", params.year__gte);
  if (params.year__lte) sp.set("year__lte", params.year__lte);
  if (params.project) sp.set("project", params.project);
  if (params.researcher) sp.set("researcher", params.researcher);
  if (params.center) sp.set("center", params.center);
  if (params.group) sp.set("group", params.group);
  if (params.line) sp.set("line", params.line);
  if (params.ordering) sp.set("ordering", params.ordering);
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

/** Fetch the paginated product list (25/page) with filters. */
export function useProductsList(params: ProductsListParams = {}) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.products.list(institutionId, params),
    queryFn: () =>
      api.get<Page<ProductList>>(`/api/products/${buildQueryString(params)}`, {
        institutionId,
      }),
  });
}

/** Fetch a single product's full detail. */
export function useProductDetail(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.products.detail(institutionId, id),
    queryFn: () => api.get<ResearchProduct>(`/api/products/${id}/`, { institutionId }),
    enabled: Boolean(id),
  });
}

/** Fetch the authors of a product (nested list). */
export function useProductAuthors(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.products.authors(institutionId, id),
    queryFn: () => api.get<Page<ProductAuthor>>(`/api/products/${id}/authors/`, { institutionId }),
    enabled: Boolean(id),
  });
}

/** Fetch the attachments of a product (nested list). */
export function useProductAttachments(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.products.attachments(institutionId, id),
    queryFn: () =>
      api.get<Page<ProductAttachment>>(`/api/products/${id}/attachments/`, {
        institutionId,
      }),
    enabled: Boolean(id),
  });
}
