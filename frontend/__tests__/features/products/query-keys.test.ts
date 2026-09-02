/**
 * Products query-key factory — institution-scoped keys.
 *
 * Spec (products-ui server state): products keys cover list, detail, and the
 * nested authors/attachments resources, all scoped by the active institution.
 */

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys.products factory", () => {
  it("shapes the all/lists/details roots", () => {
    expect(queryKeys.products.all).toEqual(["products"]);
    expect(queryKeys.products.lists()).toEqual(["products", "list"]);
    expect(queryKeys.products.details()).toEqual(["products", "detail"]);
  });

  it("scopes the list key by institution and params", () => {
    expect(queryKeys.products.list("inst-1", { type: "articulo", page: 2 })).toEqual([
      "products",
      "list",
      "inst-1",
      { type: "articulo", page: 2 },
    ]);
  });

  it("scopes the detail key by institution and product id", () => {
    expect(queryKeys.products.detail("inst-1", "prod-1")).toEqual([
      "products",
      "detail",
      "inst-1",
      "prod-1",
    ]);
  });

  it("derives nested author and attachment keys from the detail key", () => {
    expect(queryKeys.products.authors("inst-1", "prod-1")).toEqual([
      "products",
      "detail",
      "inst-1",
      "prod-1",
      "authors",
    ]);
    expect(queryKeys.products.attachments("inst-1", "prod-1")).toEqual([
      "products",
      "detail",
      "inst-1",
      "prod-1",
      "attachments",
    ]);
  });
});
