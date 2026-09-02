/**
 * Products feature types — mirror the DRF serializers (apps/products).
 *
 * - ProductList: lightweight row from GET /api/products/.
 * - ResearchProduct: full detail serializer (read + write).
 * - ProductAuthor / ProductAttachment: nested resources (PR2 managers).
 * - Page<T>: DRF paginated envelope.
 * - ProductFilter: the 9 backend filters (django-filter).
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** The 11 hardcoded product type codes (ProductType choices). */
export type ProductType =
  | "articulo"
  | "libro"
  | "capitulo"
  | "software"
  | "prototipo"
  | "evento"
  | "consultoria"
  | "diseno_industrial"
  | "innovacion_proceso"
  | "innovacion_gestion"
  | "carta";

/** Lightweight product row from GET /api/products/ (list serializer). */
export interface ProductList {
  id: string;
  title: string;
  type: string;
  publication_year: number;
  project: string;
  created_at: string;
}

/** Full product detail (ResearchProductSerializer). */
export interface ResearchProduct {
  id: string;
  institution: string;
  project: string;
  title: string;
  description: string;
  type: string;
  publication_year: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

/** Author junction row (ProductAuthorSerializer). */
export interface ProductAuthor {
  id: string;
  product: string;
  researcher: string;
  is_principal: boolean;
  order: number;
}

/** Metadata-only attachment row (ProductAttachmentSerializer). */
export interface ProductAttachment {
  id: string;
  product: string;
  name: string;
  doc_type: string;
  external_url: string;
  created_at: string;
}

/**
 * List filters supported by ResearchProductFilter: type, year (exact),
 * year__gte/year__lte (range), and project/researcher/center/group/line.
 */
export interface ProductFilter {
  type?: string;
  year?: string;
  year__gte?: string;
  year__lte?: string;
  project?: string;
  researcher?: string;
  center?: string;
  group?: string;
  line?: string;
}

/** Writable payload for POST /api/products/ (read-only fields omitted). */
export interface CreateProductPayload {
  project: string;
  title: string;
  description: string;
  type: ProductType;
  publication_year: number;
}

/** Writable payload for creating a product author (nested POST). */
export interface CreateProductAuthorPayload {
  researcher: string;
  is_principal: boolean;
  order: number;
}

/** Writable payload for creating a product attachment (nested POST). */
export interface CreateProductAttachmentPayload {
  name: string;
  doc_type: string;
  external_url: string;
}
