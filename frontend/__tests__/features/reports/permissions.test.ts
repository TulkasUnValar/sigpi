/**
 * Reports permissions — role gating per RB-001.
 *
 * RB-001: preview/PDF require CanGenerateReport (role ≤ 4; admin level ≤ 2
 * bypass). Approve requires center director (role ≤ 3 + center membership;
 * superuser bypass). Non-directors MUST NOT see or fire the approve action.
 */

import {
  canApproveReport,
  canGenerateReport,
  isDirector,
  roleLevel,
} from "@/features/reports/permissions";

describe("roleLevel", () => {
  it("assigns levels matching the backend role hierarchy", () => {
    expect(roleLevel("superadmin")).toBe(1);
    expect(roleLevel("admin")).toBe(2);
    expect(roleLevel("director")).toBe(3);
    expect(roleLevel("director_centro")).toBe(4);
    expect(roleLevel("researcher")).toBe(5);
  });

  it("treats unknown roles as never-privileged", () => {
    expect(roleLevel("auditor")).toBeGreaterThan(4);
  });
});

describe("canGenerateReport (RB-001: role ≤ 4; admin level ≤ 2 bypass)", () => {
  it("always allows admin-level roles (level ≤ 2 bypass)", () => {
    expect(canGenerateReport(["admin"])).toBe(true);
    expect(canGenerateReport(["superadmin"])).toBe(true);
  });

  it("allows roles at level ≤ 4", () => {
    expect(canGenerateReport(["director"])).toBe(true);
    expect(canGenerateReport(["director_centro"])).toBe(true);
  });

  it("denies researcher and unknown roles", () => {
    expect(canGenerateReport(["researcher"])).toBe(false);
    expect(canGenerateReport([])).toBe(false);
    expect(canGenerateReport(["auditor"])).toBe(false);
  });
});

describe("canApproveReport (RB-001: director ≤ 3 + center membership; superuser bypass)", () => {
  it("lets a superadmin approve without membership checks", () => {
    expect(canApproveReport(["superadmin"])).toBe(true);
    expect(canApproveReport(["superadmin"], [], "c1")).toBe(true);
  });

  it("lets a director approve an entity in their own center", () => {
    expect(canApproveReport(["director"], [{ id: "c1", name: "Centro A" }], "c1")).toBe(true);
  });

  it("denies a director outside their center membership", () => {
    expect(canApproveReport(["director"], [{ id: "c1", name: "Centro A" }], "c2")).toBe(false);
  });

  it("denies non-director roles even with a center membership", () => {
    expect(canApproveReport(["researcher"], [{ id: "c1", name: "Centro A" }], "c1")).toBe(false);
    expect(canApproveReport(["director_centro"], [{ id: "c1", name: "Centro A" }], "c1")).toBe(
      false,
    );
  });

  it("treats a missing entity center as a level-only check", () => {
    expect(canApproveReport(["director"])).toBe(true);
    expect(canApproveReport(["admin"])).toBe(true);
  });
});

describe("isDirector", () => {
  it("is true for director-level roles (≤ 3)", () => {
    expect(isDirector(["director"])).toBe(true);
    expect(isDirector(["admin"])).toBe(true);
    expect(isDirector(["superadmin"])).toBe(true);
  });

  it("is false for researcher and director_centro", () => {
    expect(isDirector(["researcher"])).toBe(false);
    expect(isDirector(["director_centro"])).toBe(false);
    expect(isDirector([])).toBe(false);
  });
});
