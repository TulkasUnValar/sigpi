/**
 * Child entity configs — sedeConfig / facultadConfig / centerConfig.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - Child entity writes require admin or superadmin (not just superadmin).
 *   - Center parent_type supports institution | sede | facultad.
 *   - Configs drive EntityForm field rendering and labels.
 */

import {
  sedeConfig,
  facultadConfig,
  centerConfig,
  institutionConfig,
} from "@/features/institutions/schemas";

describe("child entity configs", () => {
  it("sedeConfig drives Spanish labels, endpoints and the admin write threshold", () => {
    expect(sedeConfig.kind).toBe("sede");
    expect(sedeConfig.label).toBe("Sede");
    expect(sedeConfig.pluralLabel).toBe("Sedes");
    expect(sedeConfig.minRoles).toEqual(["admin", "superadmin"]);
    expect(sedeConfig.fields.map((f) => f.name)).toEqual(["code", "name", "description"]);
    expect(sedeConfig.schema.safeParse({ code: "S1", name: "Sede Bogotá" }).success).toBe(true);
  });

  it("facultadConfig exposes an optional sede reference field", () => {
    expect(facultadConfig.kind).toBe("facultad");
    expect(facultadConfig.minRoles).toEqual(["admin", "superadmin"]);
    const names = facultadConfig.fields.map((f) => f.name);
    expect(names).toContain("sede");
    expect(
      facultadConfig.schema.safeParse({ sede: "sede-1", code: "F1", name: "Facultad" }).success,
    ).toBe(true);
  });

  it("centerConfig exposes sede + facultad references (parent_type nesting)", () => {
    expect(centerConfig.kind).toBe("center");
    expect(centerConfig.minRoles).toEqual(["admin", "superadmin"]);
    const names = centerConfig.fields.map((f) => f.name);
    expect(names).toContain("sede");
    expect(names).toContain("facultad");
    const ok = centerConfig.schema.safeParse({
      sede: "sede-1",
      facultad: "fac-1",
      code: "C1",
      name: "Centro IA",
    });
    expect(ok.success).toBe(true);
  });

  it("keeps the institution config superadmin-only", () => {
    expect(institutionConfig.minRoles).toEqual(["superadmin"]);
  });

  it("exposes endpoint builders per kind (detail + FSM paths)", () => {
    expect(sedeConfig.detailPath("sede-1")).toBe("/api/sedes/sede-1/");
    expect(sedeConfig.fsmPath("sede-1", "deactivate")).toBe("/api/sedes/sede-1/deactivate/");
    expect(facultadConfig.detailPath("fac-1")).toBe("/api/facultades/fac-1/");
    expect(facultadConfig.fsmPath("fac-1", "archive")).toBe("/api/facultades/fac-1/archive/");
    expect(centerConfig.detailPath("center-1")).toBe("/api/centers/center-1/");
    expect(centerConfig.fsmPath("center-1", "activate")).toBe("/api/centers/center-1/activate/");
    expect(institutionConfig.detailPath("inst-1")).toBe("/api/institutions/inst-1/");
  });
});
