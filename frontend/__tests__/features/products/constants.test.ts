/**
 * Products constants — PRODUCT_TYPE_CODES and i18n-based label resolution.
 *
 * Spec (products-ui business rules):
 *   - type is one of the 11 codes, displayed with translated labels.
 *   - the project select is restricted to ALLOWED_PROJECT_STATES (6 states).
 */

import {
  ALLOWED_PROJECT_STATES,
  PRODUCT_TYPE_CODES,
  getProductTypeLabel,
  getProductTypeOptions,
} from "@/features/products/constants";

// Mock translation function that returns the key as-is for testing
const mockT = (key: string) => key;

// Mock translation function that returns Spanish labels (simulating real i18n)
const spanishT = (key: string) => {
  const labels: Record<string, string> = {
    "types.articulo": "Artículo",
    "types.libro": "Libro",
    "types.capitulo": "Capítulo",
    "types.software": "Software",
    "types.prototipo": "Prototipo",
    "types.evento": "Evento",
    "types.consultoria": "Consultoría",
    "types.diseno_industrial": "Diseño Industrial",
    "types.innovacion_proceso": "Innovación de Proceso",
    "types.innovacion_gestion": "Innovación de Gestión",
    "types.carta": "Carta",
  };
  return labels[key] ?? key;
};

describe("PRODUCT_TYPE_CODES", () => {
  it("contains all 11 product type codes", () => {
    expect(PRODUCT_TYPE_CODES).toHaveLength(11);
    expect(PRODUCT_TYPE_CODES).toContain("articulo");
    expect(PRODUCT_TYPE_CODES).toContain("libro");
    expect(PRODUCT_TYPE_CODES).toContain("capitulo");
    expect(PRODUCT_TYPE_CODES).toContain("software");
    expect(PRODUCT_TYPE_CODES).toContain("prototipo");
    expect(PRODUCT_TYPE_CODES).toContain("evento");
    expect(PRODUCT_TYPE_CODES).toContain("consultoria");
    expect(PRODUCT_TYPE_CODES).toContain("diseno_industrial");
    expect(PRODUCT_TYPE_CODES).toContain("innovacion_proceso");
    expect(PRODUCT_TYPE_CODES).toContain("innovacion_gestion");
    expect(PRODUCT_TYPE_CODES).toContain("carta");
  });
});

describe("getProductTypeOptions", () => {
  it("returns 11 options with value/label pairs using the translation function", () => {
    const options = getProductTypeOptions(spanishT);
    expect(options).toHaveLength(11);
    expect(options[0]).toEqual({ value: "articulo", label: "Artículo" });
    expect(options[10]).toEqual({ value: "carta", label: "Carta" });
  });

  it("uses the translation function for labels", () => {
    const options = getProductTypeOptions(mockT);
    expect(options[0]).toEqual({ value: "articulo", label: "types.articulo" });
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
  it("resolves a known code to its translated label", () => {
    expect(getProductTypeLabel(spanishT, "software")).toBe("Software");
    expect(getProductTypeLabel(spanishT, "carta")).toBe("Carta");
  });

  it("falls back to the raw value for unknown codes", () => {
    expect(getProductTypeLabel(spanishT, "tesis")).toBe("tesis");
  });

  it("uses the translation function for labels", () => {
    expect(getProductTypeLabel(mockT, "articulo")).toBe("types.articulo");
  });
});
