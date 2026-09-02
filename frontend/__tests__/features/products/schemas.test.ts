/**
 * Products zod schemas — create form validation mirroring the DRF serializer.
 *
 * Spec (products-ui business rules):
 *   - title required; type ∈ the 11 codes; publication_year int 1900..current_year+1.
 *   - Nested author/attachment schemas back the PR2 managers.
 */

import {
  MAX_PUBLICATION_YEAR,
  MIN_PUBLICATION_YEAR,
  buildProductPayload,
  productAttachmentSchema,
  productAuthorSchema,
  productFormSchema,
} from "@/features/products/schemas";

const currentYear = new Date().getFullYear();

const validProduct = {
  project: "p3",
  title: "Artículo de IA",
  description: "Investigación aplicada.",
  type: "articulo",
  publication_year: 2024,
};

describe("productFormSchema", () => {
  it("accepts a valid product payload", () => {
    expect(productFormSchema.safeParse(validProduct).success).toBe(true);
  });

  it("rejects a missing title with a Spanish message", () => {
    const result = productFormSchema.safeParse({ ...validProduct, title: "" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("title");
      expect(result.error.issues[0]?.message).toMatch(/obligatorio/i);
    }
  });

  it("rejects a type outside the 11 codes", () => {
    const result = productFormSchema.safeParse({ ...validProduct, type: "tesis" });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("type");
    }
  });

  it("rejects a publication_year below 1900", () => {
    const result = productFormSchema.safeParse({ ...validProduct, publication_year: 1899 });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("publication_year");
    }
  });

  it("rejects a publication_year beyond current_year + 1", () => {
    const result = productFormSchema.safeParse({
      ...validProduct,
      publication_year: currentYear + 2,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("publication_year");
    }
  });

  it("accepts the boundary years 1900 and current_year + 1", () => {
    expect(
      productFormSchema.safeParse({
        ...validProduct,
        publication_year: MIN_PUBLICATION_YEAR,
      }).success,
    ).toBe(true);
    expect(
      productFormSchema.safeParse({
        ...validProduct,
        publication_year: MAX_PUBLICATION_YEAR,
      }).success,
    ).toBe(true);
  });

  it("rejects a non-integer publication_year", () => {
    const result = productFormSchema.safeParse({ ...validProduct, publication_year: 2024.5 });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("publication_year");
    }
  });
});

describe("buildProductPayload", () => {
  it("projects form values onto the writable API payload", () => {
    expect(
      buildProductPayload({
        project: "p3",
        title: "Artículo",
        description: "Descripción.",
        type: "software",
        publication_year: 2024,
      }),
    ).toEqual({
      project: "p3",
      title: "Artículo",
      description: "Descripción.",
      type: "software",
      publication_year: 2024,
    });
  });
});

describe("productAuthorSchema", () => {
  it("accepts a valid author row with researcher, principal flag and order", () => {
    expect(
      productAuthorSchema.safeParse({ researcher: "r1", is_principal: true, order: 0 }).success,
    ).toBe(true);
  });

  it("rejects an author without a researcher", () => {
    const result = productAuthorSchema.safeParse({
      researcher: "",
      is_principal: false,
      order: 0,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("researcher");
    }
  });
});

describe("productAttachmentSchema", () => {
  it("accepts metadata-only attachment with a valid URL", () => {
    expect(
      productAttachmentSchema.safeParse({
        name: "Bases",
        doc_type: "PDF",
        external_url: "https://example.com/bases.pdf",
      }).success,
    ).toBe(true);
  });

  it("rejects a malformed external_url", () => {
    const result = productAttachmentSchema.safeParse({
      name: "Bases",
      doc_type: "PDF",
      external_url: "not-a-url",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("external_url");
    }
  });

  it("rejects a doc_type longer than 50 characters", () => {
    const result = productAttachmentSchema.safeParse({
      name: "Bases",
      doc_type: "x".repeat(51),
      external_url: "https://example.com/bases.pdf",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("doc_type");
    }
  });
});
