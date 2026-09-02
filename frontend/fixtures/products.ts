/**
 * Seed fixtures — products dataset.
 *
 * Mirrors the DRF ResearchProduct list serializer (rows) and full
 * serializer (details). filterProductRows applies the backend query
 * params so the MSW list handler behaves like DRF when filters are active.
 */

/** Product row matching the DRF list serializer. */
export interface FixtureProduct {
  id: string;
  title: string;
  type: string;
  publication_year: number;
  project: string;
  created_at: string;
  /** Author researcher ids — enables the researcher filter (DRF join). */
  researcher_ids?: string[];
  /** Project center/group/line ids — enable the related-entity filters. */
  center?: string;
  group?: string;
  line?: string;
}

/** Full product detail matching the DRF ResearchProductSerializer. */
export interface FixtureProductDetail {
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

/** Non-empty product set spanning several types and years 2023–2025. */
export const fixtureProducts: FixtureProduct[] = [
  {
    id: "prod-1",
    title: "Artículo IA 2025",
    type: "articulo",
    publication_year: 2025,
    project: "p4",
    researcher_ids: ["r-1", "r-2"],
    center: "center-1",
    group: "group-1",
    line: "line-1",
    created_at: "2026-01-10T09:00:00Z",
  },
  {
    id: "prod-2",
    title: "Libro Biotecnología",
    type: "libro",
    publication_year: 2024,
    project: "p3",
    researcher_ids: ["r-2"],
    center: "center-2",
    created_at: "2026-01-20T09:00:00Z",
  },
  {
    id: "prod-3",
    title: "Software de Monitoreo",
    type: "software",
    publication_year: 2023,
    project: "p4",
    researcher_ids: ["r-1"],
    center: "center-1",
    group: "group-2",
    created_at: "2025-12-01T09:00:00Z",
  },
  {
    id: "prod-4",
    title: "Capítulo de Energías",
    type: "capitulo",
    publication_year: 2025,
    project: "p3",
    researcher_ids: ["r-3"],
    center: "center-2",
    line: "line-2",
    created_at: "2025-11-15T09:00:00Z",
  },
  {
    id: "prod-5",
    title: "Prototipo Agro",
    type: "prototipo",
    publication_year: 2024,
    project: "p4",
    researcher_ids: ["r-1", "r-3"],
    center: "center-1",
    created_at: "2025-10-05T09:00:00Z",
  },
];

/** Full detail rows keyed by product id. */
export const fixtureProductDetails: Record<string, FixtureProductDetail> = {
  "prod-1": {
    id: "prod-1",
    institution: "inst-1",
    project: "p4",
    title: "Artículo IA 2025",
    description: "Aplicaciones de inteligencia artificial en agricultura.",
    type: "articulo",
    publication_year: 2025,
    created_at: "2026-01-10T09:00:00Z",
    updated_at: "2026-01-10T09:00:00Z",
    created_by: "u1",
    updated_by: null,
  },
  "prod-2": {
    id: "prod-2",
    institution: "inst-1",
    project: "p3",
    title: "Libro Biotecnología",
    description: "Compendio de avances en biotecnología aplicada.",
    type: "libro",
    publication_year: 2024,
    created_at: "2026-01-20T09:00:00Z",
    updated_at: "2026-01-20T09:00:00Z",
    created_by: "u1",
    updated_by: null,
  },
  "prod-3": {
    id: "prod-3",
    institution: "inst-1",
    project: "p4",
    title: "Software de Monitoreo",
    description: "Plataforma de monitoreo ambiental en tiempo real.",
    type: "software",
    publication_year: 2023,
    created_at: "2025-12-01T09:00:00Z",
    updated_at: "2025-12-01T09:00:00Z",
    created_by: "u2",
    updated_by: "u1",
  },
  "prod-4": {
    id: "prod-4",
    institution: "inst-1",
    project: "p3",
    title: "Capítulo de Energías",
    description: "Capítulo sobre transición energética en la región.",
    type: "capitulo",
    publication_year: 2025,
    created_at: "2025-11-15T09:00:00Z",
    updated_at: "2025-11-15T09:00:00Z",
    created_by: "u2",
    updated_by: null,
  },
  "prod-5": {
    id: "prod-5",
    institution: "inst-1",
    project: "p4",
    title: "Prototipo Agro",
    description: "Prototipo de sensor para cultivos de altura.",
    type: "prototipo",
    publication_year: 2024,
    created_at: "2025-10-05T09:00:00Z",
    updated_at: "2025-10-05T09:00:00Z",
    created_by: "u1",
    updated_by: null,
  },
};

/** Params accepted by the MSW list handler (mirrors ResearchProductFilter). */
export interface ProductFilterParams {
  type?: string | null;
  year?: string | null;
  year__gte?: string | null;
  year__lte?: string | null;
  project?: string | null;
  researcher?: string | null;
  center?: string | null;
  group?: string | null;
  line?: string | null;
}

/**
 * Filter list rows by the DRF query params — used by the MSW list handler
 * so dev/tests behave like the backend when filters are active.
 */
export function filterProductRows(
  rows: FixtureProduct[],
  params: ProductFilterParams = {},
): FixtureProduct[] {
  return rows.filter((row) => {
    if (params.type && row.type !== params.type) return false;
    if (params.year && row.publication_year !== Number(params.year)) return false;
    if (params.year__gte && row.publication_year < Number(params.year__gte)) return false;
    if (params.year__lte && row.publication_year > Number(params.year__lte)) return false;
    if (params.project && row.project !== params.project) return false;
    if (params.researcher && !row.researcher_ids?.includes(params.researcher)) return false;
    if (params.center && row.center !== params.center) return false;
    if (params.group && row.group !== params.group) return false;
    if (params.line && row.line !== params.line) return false;
    return true;
  });
}

// ──────────────────────────────────────────────────────────
// Nested fixtures — authors and attachments (PR2).
// Researcher ids use the researchers fixture ids (r-1/r-2/r-3) so the
// AuthorsManager id → full_name mapping resolves in dev.
// ──────────────────────────────────────────────────────────

/** Author junction row matching ProductAuthorSerializer. */
export interface FixtureProductAuthor {
  id: string;
  product: string;
  researcher: string;
  is_principal: boolean;
  order: number;
}

/** Metadata-only attachment row matching ProductAttachmentSerializer. */
export interface FixtureProductAttachment {
  id: string;
  product: string;
  name: string;
  doc_type: string;
  external_url: string;
  created_at: string;
}

const TS_NESTED = {
  created_at: "2026-02-01T09:00:00Z",
};

/** Authors keyed by product id — exactly one principal per product. */
export const fixtureProductAuthors: Record<string, FixtureProductAuthor[]> = {
  "prod-1": [
    { id: "pa-1", product: "prod-1", researcher: "r-1", is_principal: true, order: 0 },
    { id: "pa-2", product: "prod-1", researcher: "r-2", is_principal: false, order: 1 },
  ],
  "prod-2": [{ id: "pa-3", product: "prod-2", researcher: "r-2", is_principal: true, order: 0 }],
  "prod-3": [{ id: "pa-4", product: "prod-3", researcher: "r-1", is_principal: true, order: 0 }],
  "prod-4": [{ id: "pa-5", product: "prod-4", researcher: "r-3", is_principal: true, order: 0 }],
  "prod-5": [
    { id: "pa-6", product: "prod-5", researcher: "r-1", is_principal: true, order: 0 },
    { id: "pa-7", product: "prod-5", researcher: "r-3", is_principal: false, order: 1 },
  ],
};

/** Attachments keyed by product id — metadata only, valid URLs. */
export const fixtureProductAttachments: Record<string, FixtureProductAttachment[]> = {
  "prod-1": [
    {
      id: "pt-1",
      product: "prod-1",
      name: "Acta de aprobación",
      doc_type: "Acta",
      external_url: "https://example.com/acta-prod1.pdf",
      created_at: TS_NESTED.created_at,
    },
    {
      id: "pt-2",
      product: "prod-1",
      name: "Certificado de software",
      doc_type: "Certificado",
      external_url: "https://example.com/certificado-prod1.pdf",
      created_at: TS_NESTED.created_at,
    },
  ],
  "prod-2": [
    {
      id: "pt-3",
      product: "prod-2",
      name: "Carátula del libro",
      doc_type: "Imagen",
      external_url: "https://example.com/caratula-prod2.png",
      created_at: TS_NESTED.created_at,
    },
  ],
  "prod-3": [],
  "prod-4": [],
  "prod-5": [],
};

/** Writable author payload (nested POST/PATCH). */
export interface ProductAuthorPayload {
  researcher: string;
  is_principal: boolean;
  order: number;
}

/** Field errors for author validation (400 body keys). */
export type ProductAuthorFieldErrors = Partial<Record<"researcher" | "is_principal", string>>;

/** Validation result: ok, or the 400 field errors to return. */
export type AuthorValidationResult = { ok: true } | { ok: false; errors: ProductAuthorFieldErrors };

const DUPLICATE_RESEARCHER_FIXTURE_MSG = "Este investigador ya es autor del producto.";
const PRINCIPAL_EXISTS_FIXTURE_MSG = "Ya existe un autor principal en este producto.";

/**
 * Validate an author create against the product invariants: a researcher
 * must not repeat and at most one principal may exist. Mirrors the DRF
 * ProductAuthorSerializer guards (400 {researcher} / 400 {is_principal}).
 */
export function validateProductAuthorCreate(
  existing: FixtureProductAuthor[],
  payload: ProductAuthorPayload,
): AuthorValidationResult {
  const errors: ProductAuthorFieldErrors = {};
  if (existing.some((a) => a.researcher === payload.researcher)) {
    errors.researcher = DUPLICATE_RESEARCHER_FIXTURE_MSG;
  }
  if (payload.is_principal && existing.some((a) => a.is_principal)) {
    errors.is_principal = PRINCIPAL_EXISTS_FIXTURE_MSG;
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true };
}

/**
 * Validate an author PATCH: a researcher reassignment must not duplicate
 * another author and setting is_principal while another author is still
 * principal is rejected (the two-step switch must unset first).
 */
export function validateProductAuthorUpdate(
  existing: FixtureProductAuthor[],
  authorId: string,
  payload: Partial<ProductAuthorPayload>,
): AuthorValidationResult {
  const errors: ProductAuthorFieldErrors = {};
  const others = existing.filter((a) => a.id !== authorId);
  if (payload.researcher !== undefined && others.some((a) => a.researcher === payload.researcher)) {
    errors.researcher = DUPLICATE_RESEARCHER_FIXTURE_MSG;
  }
  if (payload.is_principal === true && others.some((a) => a.is_principal)) {
    errors.is_principal = PRINCIPAL_EXISTS_FIXTURE_MSG;
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true };
}

/** True when the value is an http(s) URL (mirrors zod .url()). */
export function isValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/** Field errors for attachment validation (400 body keys). */
export type ProductAttachmentFieldErrors = Partial<
  Record<"name" | "doc_type" | "external_url", string>
>;

/** Validation result for an attachment payload. */
export type AttachmentValidationResult =
  | { ok: true }
  | { ok: false; errors: ProductAttachmentFieldErrors };

/**
 * Validate metadata-only attachment payload: name required, doc_type
 * free text non-empty ≤ 50 chars, external_url a valid URL.
 */
export function validateProductAttachmentPayload(payload: {
  name: string;
  doc_type: string;
  external_url: string;
}): AttachmentValidationResult {
  const errors: ProductAttachmentFieldErrors = {};
  if (!payload.name.trim()) errors.name = "El nombre es obligatorio.";
  if (!payload.doc_type.trim()) {
    errors.doc_type = "El tipo de documento es obligatorio.";
  } else if (payload.doc_type.length > 50) {
    errors.doc_type = "El tipo de documento no puede superar 50 caracteres.";
  }
  if (!isValidHttpUrl(payload.external_url)) {
    errors.external_url = "La URL externa debe ser válida.";
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  return { ok: true };
}
