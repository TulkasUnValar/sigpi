/**
 * Products constants — PRODUCT_TYPES label map and ALLOWED_PROJECT_STATES.
 *
 * Spec (products-ui business rules):
 *   - type is one of the 11 codes, displayed with Spanish labels.
 *   - the project select is restricted to ALLOWED_PROJECT_STATES (6 states).
 */

import {
  ALLOWED_PROJECT_STATES,
  PRODUCT_TYPE_OPTIONS,
  PRODUCT_TYPES,
  getProductTypeLabel,
} from "@/features/products/constants";

describe("PRODUCT_TYPES", () => {
  it("maps the 11 product type codes to Spanish labels", () => {
    expect(Object.keys(PRODUCT_TYPES)).toHaveLength(11);
    expect(PRODUCT_TYPES.articulo).toBe("Artículo");
    expect(PRODUCT_TYPES.libro).toBe("Libro");
    expect(PRODUCT_TYPES.capitulo).toBe("Capítulo");
    expect(PRODUCT_TYPES.software).toBe("Software");
    expect(PRODUCT_TYPES.prototipo).toBe("Prototipo");
    expect(PRODUCT_TYPES.evento).toBe("Evento");
    expect(PRODUCT_TYPES.consultoria).toBe("Consultoría");
    expect(PRODUCT_TYPES.diseno_industrial).toBe("Diseño Industrial");
    expect(PRODUCT_TYPES.innovacion_proceso).toBe("Innovación de Proceso");
    expect(PRODUCT_TYPES.innovacion_gestion).toBe("Innovación de Gestión");
    expect(PRODUCT_TYPES.carta).toBe("Carta");
  });

  it("exposes PRODUCT_TYPE_OPTIONS for selects with value/label pairs", () => {
    expect(PRODUCT_TYPE_OPTIONS).toHaveLength(11);
    expect(PRODUCT_TYPE_OPTIONS[0]).toEqual({ value: "articulo", label: "Artículo" });
    expect(PRODUCT_TYPE_OPTIONS[10]).toEqual({ value: "carta", label: "Carta" });
  });
});

describe("ALLOWED_PROJECT_STATES", () => {
  it("contains exactly the 6 project states allowed for products", () => {
    expect(ALLOWED_PROJECT_STATES).toEqual([
      "aprobado",
      "en_ejecucion",
      "suspendido",
      "finalizado",
      "en_cierre",
      "cerrado",
    ]);
  });

  it("excludes non-allowed states such as borrador and en_revision", () => {
    expect(ALLOWED_PROJECT_STATES).not.toContain("borrador");
    expect(ALLOWED_PROJECT_STATES).not.toContain("en_revision");
  });
});

describe("getProductTypeLabel", () => {
  it("resolves a known code to its Spanish label", () => {
    expect(getProductTypeLabel("software")).toBe("Software");
    expect(getProductTypeLabel("carta")).toBe("Carta");
  });

  it("falls back to the raw value for unknown codes", () => {
    expect(getProductTypeLabel("tesis")).toBe("tesis");
  });
});
