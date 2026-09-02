/**
 * Products fixtures — dev dataset + DRF-mirroring filter helper.
 *
 * Spec (products-ui MSW): fixture rows mirror the list serializer and
 * filterProductRows applies the backend query params so dev/tests behave
 * like DRF when filters are active.
 */

import { filterProductRows, fixtureProductDetails, fixtureProducts } from "@/fixtures/products";

describe("fixtureProducts", () => {
  it("spans multiple product types and publication years", () => {
    expect(fixtureProducts.length).toBeGreaterThanOrEqual(4);
    const types = new Set(fixtureProducts.map((p) => p.type));
    expect(types.size).toBeGreaterThanOrEqual(3);
    const years = fixtureProducts.map((p) => p.publication_year);
    expect(years).toContain(2023);
    expect(years).toContain(2025);
  });

  it("keys a detail row for every list row", () => {
    for (const row of fixtureProducts) {
      const detail = fixtureProductDetails[row.id];
      expect(detail).toBeDefined();
      expect(detail?.title).toBe(row.title);
    }
  });
});

describe("filterProductRows", () => {
  it("filters by exact type", () => {
    const rows = filterProductRows(fixtureProducts, { type: "articulo" });
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.type === "articulo")).toBe(true);
  });

  it("filters by year range", () => {
    const rows = filterProductRows(fixtureProducts, { year__gte: "2024", year__lte: "2025" });
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.publication_year >= 2024 && r.publication_year <= 2025)).toBe(true);
  });

  it("combines type and exact-year filters", () => {
    const rows = filterProductRows(fixtureProducts, { type: "libro", year: "2024" });
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.type === "libro" && r.publication_year === 2024)).toBe(true);
  });

  it("filters by project and researcher ids", () => {
    const byProject = filterProductRows(fixtureProducts, { project: "p3" });
    expect(byProject.length).toBeGreaterThan(0);
    expect(byProject.every((r) => r.project === "p3")).toBe(true);

    const byResearcher = filterProductRows(fixtureProducts, { researcher: "r-2" });
    expect(byResearcher.length).toBeGreaterThan(0);
    expect(byResearcher.every((r) => r.researcher_ids?.includes("r-2"))).toBe(true);
  });

  it("filters by the hierarchy ids served to the center/group/line selects", () => {
    const byCenter = filterProductRows(fixtureProducts, { center: "center-1" });
    expect(byCenter.length).toBeGreaterThan(0);
    expect(byCenter.every((r) => r.center === "center-1")).toBe(true);

    const byGroup = filterProductRows(fixtureProducts, { group: "group-1" });
    expect(byGroup.length).toBeGreaterThan(0);
    expect(byGroup.every((r) => r.group === "group-1")).toBe(true);

    const byLine = filterProductRows(fixtureProducts, { line: "line-1" });
    expect(byLine.length).toBeGreaterThan(0);
    expect(byLine.every((r) => r.line === "line-1")).toBe(true);
  });

  it("returns an empty array when no rows match the filters", () => {
    expect(filterProductRows(fixtureProducts, { type: "carta", year: "1900" })).toEqual([]);
  });
});
