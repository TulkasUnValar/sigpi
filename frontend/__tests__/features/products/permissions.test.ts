/**
 * Products permissions — flat all-authenticated policy.
 *
 * Spec (products-ui): the backend enforces IsAuthenticated only, so every
 * authenticated role may render CRUD affordances — no RoleGuard exists.
 */

import { canManageProducts } from "@/features/products/permissions";

describe("canManageProducts — flat all-authenticated policy", () => {
  it("allows every known authenticated role to manage products", () => {
    expect(canManageProducts(["researcher"])).toBe(true);
    expect(canManageProducts(["director"])).toBe(true);
    expect(canManageProducts(["director_centro"])).toBe(true);
    expect(canManageProducts(["admin"])).toBe(true);
    expect(canManageProducts(["superadmin"])).toBe(true);
  });

  it("returns true for any role outside the known vocabulary", () => {
    expect(canManageProducts(["externo"])).toBe(true);
  });
});
