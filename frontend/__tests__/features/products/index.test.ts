/**
 * Products feature barrel — public API surface.
 *
 * Spec (products-ui): the feature index re-exports the constants, schemas,
 * authorization helper, hooks, mutations and components. This test
 * exercises the barrel so the re-export statements are covered and the
 * public surface stays stable.
 */

import {
  ALLOWED_PROJECT_STATES,
  PRODUCT_TYPES,
  PRODUCT_TYPE_OPTIONS,
  ProductForm,
  ProductList,
  buildProductPayload,
  canManageProducts,
  getProductTypeLabel,
  productFormSchema,
  useCreateProduct,
  useProductDetail,
  useProductsList,
} from "@/features/products";

describe("products feature barrel", () => {
  it("re-exports the constants", () => {
    expect(Object.keys(PRODUCT_TYPES)).toHaveLength(11);
    expect(PRODUCT_TYPE_OPTIONS).toHaveLength(11);
    expect(ALLOWED_PROJECT_STATES).toContain("aprobado");
    expect(getProductTypeLabel("libro")).toBe("Libro");
  });

  it("re-exports the schema helpers and permission policy", () => {
    expect(productFormSchema).toBeDefined();
    expect(typeof buildProductPayload).toBe("function");
    expect(canManageProducts(["researcher"])).toBe(true);
  });

  it("re-exports the query/mutation hooks and components", () => {
    expect(typeof useProductsList).toBe("function");
    expect(typeof useProductDetail).toBe("function");
    expect(typeof useCreateProduct).toBe("function");
    expect(typeof ProductList).toBe("function");
    expect(typeof ProductForm).toBe("function");
  });
});
