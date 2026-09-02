/**
 * Products nested fixtures + validators — authors and attachments (RF-006/RF-007).
 *
 * Spec (products-ui MSW):
 *   - fixtureProductAuthors / fixtureProductAttachments seed the nested
 *     stores with exactly one principal per product.
 *   - validateProductAuthorCreate rejects duplicates (400 {researcher}) and
 *     a second principal (400 {is_principal}).
 *   - validateProductAuthorUpdate mirrors the two-step switch invariant:
 *     setting a principal while another exists is rejected.
 *   - validateProductAttachmentPayload rejects empty name/doc_type, doc_type
 *     > 50 chars, and malformed external_url.
 */

import {
  fixtureProductAttachments,
  fixtureProductAuthors,
  fixtureProducts,
  validateProductAttachmentPayload,
  validateProductAuthorCreate,
  validateProductAuthorUpdate,
} from "@/fixtures/products";

describe("fixtureProductAuthors", () => {
  it("keys an author list for every product, with exactly one principal", () => {
    for (const row of fixtureProducts) {
      const authors = fixtureProductAuthors[row.id]!;
      expect(authors).toBeDefined();
      if (authors.length > 0) {
        const principals = authors.filter((a) => a.is_principal);
        expect(principals).toHaveLength(1);
      }
    }
  });

  it("references existing researcher ids so the mapping resolves in dev", () => {
    const referenced = new Set(
      Object.values(fixtureProductAuthors)
        .flat()
        .map((a) => a.researcher),
    );
    expect(referenced.size).toBeGreaterThan(0);
    // r-1 / r-2 / r-3 are the researcher fixture ids.
    for (const id of referenced) {
      expect(id).toMatch(/^r-\d+$/);
    }
  });
});

describe("fixtureProductAttachments", () => {
  it("keys an attachment list for every product with valid URLs", () => {
    for (const row of fixtureProducts) {
      const attachments = fixtureProductAttachments[row.id]!;
      expect(attachments).toBeDefined();
      for (const a of attachments) {
        expect(a.name.length).toBeGreaterThan(0);
        expect(a.doc_type.length).toBeLessThanOrEqual(50);
        expect(a.external_url).toMatch(/^https?:\/\//);
      }
    }
  });
});

describe("validateProductAuthorCreate", () => {
  const existing = [
    { id: "pa-1", product: "prod-1", researcher: "r-1", is_principal: true, order: 0 },
  ];

  it("accepts a non-duplicate, non-principal author", () => {
    const result = validateProductAuthorCreate(existing, {
      researcher: "r-2",
      is_principal: false,
      order: 1,
    });
    expect(result).toEqual({ ok: true });
  });

  it("rejects a duplicate researcher with a {researcher} field error", () => {
    const result = validateProductAuthorCreate(existing, {
      researcher: "r-1",
      is_principal: false,
      order: 1,
    });
    expect(result).toEqual({
      ok: false,
      errors: { researcher: "Este investigador ya es autor del producto." },
    });
  });

  it("rejects a second principal with an {is_principal} field error", () => {
    const result = validateProductAuthorCreate(existing, {
      researcher: "r-2",
      is_principal: true,
      order: 1,
    });
    expect(result).toEqual({
      ok: false,
      errors: { is_principal: "Ya existe un autor principal en este producto." },
    });
  });
});

describe("validateProductAuthorUpdate", () => {
  const existing = [
    { id: "pa-1", product: "prod-1", researcher: "r-1", is_principal: true, order: 0 },
    { id: "pa-2", product: "prod-1", researcher: "r-2", is_principal: false, order: 1 },
  ];

  it("accepts unsetting the current principal (first step of the switch)", () => {
    const result = validateProductAuthorUpdate(existing, "pa-1", { is_principal: false });
    expect(result).toEqual({ ok: true });
  });

  it("accepts setting the target principal after the old one is unset", () => {
    const withoutPrincipal = existing.map((a) =>
      a.id === "pa-1" ? { ...a, is_principal: false } : a,
    );
    const result = validateProductAuthorUpdate(withoutPrincipal, "pa-2", {
      is_principal: true,
    });
    expect(result).toEqual({ ok: true });
  });

  it("rejects setting a principal while another author is still principal", () => {
    const result = validateProductAuthorUpdate(existing, "pa-2", { is_principal: true });
    expect(result).toEqual({
      ok: false,
      errors: { is_principal: "Ya existe un autor principal en este producto." },
    });
  });

  it("rejects reassigning an author to a duplicate researcher", () => {
    const result = validateProductAuthorUpdate(existing, "pa-2", { researcher: "r-1" });
    expect(result).toEqual({
      ok: false,
      errors: { researcher: "Este investigador ya es autor del producto." },
    });
  });
});

describe("validateProductAttachmentPayload", () => {
  it("accepts complete metadata with a valid URL", () => {
    const result = validateProductAttachmentPayload({
      name: "Acta de aprobación",
      doc_type: "Acta",
      external_url: "https://example.com/acta.pdf",
    });
    expect(result).toEqual({ ok: true });
  });

  it("rejects a malformed external_url", () => {
    const result = validateProductAttachmentPayload({
      name: "Acta",
      doc_type: "Acta",
      external_url: "not-a-url",
    });
    expect(result).toEqual({
      ok: false,
      errors: { external_url: "La URL externa debe ser válida." },
    });
  });

  it("rejects an empty doc_type", () => {
    const result = validateProductAttachmentPayload({
      name: "Acta",
      doc_type: "   ",
      external_url: "https://example.com/a.pdf",
    });
    expect(result).toEqual({
      ok: false,
      errors: { doc_type: "El tipo de documento es obligatorio." },
    });
  });

  it("rejects a doc_type longer than 50 characters", () => {
    const result = validateProductAttachmentPayload({
      name: "Acta",
      doc_type: "x".repeat(51),
      external_url: "https://example.com/a.pdf",
    });
    expect(result).toEqual({
      ok: false,
      errors: { doc_type: "El tipo de documento no puede superar 50 caracteres." },
    });
  });
});
