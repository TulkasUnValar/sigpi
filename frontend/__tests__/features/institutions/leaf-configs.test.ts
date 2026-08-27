/**
 * Leaf entity configs — groupConfig / lineConfig.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - Group and line writes require director, admin or superadmin.
 *   - Configs drive EntityForm field rendering, labels and endpoints.
 */

import { groupConfig, lineConfig } from "@/features/institutions/schemas";

describe("leaf entity configs", () => {
  it("groupConfig drives Spanish labels, endpoints and the director write threshold", () => {
    expect(groupConfig.kind).toBe("group");
    expect(groupConfig.label).toBe("Grupo de investigación");
    expect(groupConfig.pluralLabel).toBe("Grupos de investigación");
    expect(groupConfig.minRoles).toEqual(["director", "admin", "superadmin"]);
    expect(groupConfig.fields.map((f) => f.name)).toEqual(["code", "name", "description"]);
    expect(groupConfig.detailPath("group-1")).toBe("/api/groups/group-1/");
    expect(groupConfig.fsmPath("group-1", "deactivate")).toBe("/api/groups/group-1/deactivate/");
    const ok = groupConfig.schema.safeParse({ code: "G1", name: "Grupo IA" });
    expect(ok.success).toBe(true);
  });

  it("lineConfig drives Spanish labels, endpoints and the director write threshold", () => {
    expect(lineConfig.kind).toBe("line");
    expect(lineConfig.label).toBe("Línea de investigación");
    expect(lineConfig.pluralLabel).toBe("Líneas de investigación");
    expect(lineConfig.minRoles).toEqual(["director", "admin", "superadmin"]);
    expect(lineConfig.fields.map((f) => f.name)).toEqual(["code", "name", "description"]);
    expect(lineConfig.detailPath("line-1")).toBe("/api/lines/line-1/");
    expect(lineConfig.fsmPath("line-1", "archive")).toBe("/api/lines/line-1/archive/");
    const ok = lineConfig.schema.safeParse({ code: "L1", name: "Línea DL" });
    expect(ok.success).toBe(true);
  });

  it("group schema rejects a missing required code", () => {
    const parsed = groupConfig.schema.safeParse({ name: "Grupo sin código" });
    expect(parsed.success).toBe(false);
  });

  it("line schema rejects a missing required name", () => {
    const parsed = lineConfig.schema.safeParse({ code: "L-X" });
    expect(parsed.success).toBe(false);
  });
});
