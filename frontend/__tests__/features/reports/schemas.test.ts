/**
 * Reports schemas — zod validation of the generator selection.
 *
 * Spec (frontend-reports 1.3): the selection is `{type, entityId}` and
 * `advances` maps to the project entity selector (advances reports target
 * a project entity — backend `advances` entities are project-scoped).
 */

import {
  parseReportSelection,
  reportSelectionSchema,
  resolveSelectorKind,
} from "@/features/reports/schemas";

describe("reportSelectionSchema", () => {
  it("accepts a valid selection for every report type", () => {
    expect(reportSelectionSchema.parse({ type: "project", entityId: "p1" })).toEqual({
      type: "project",
      entityId: "p1",
    });
    expect(reportSelectionSchema.parse({ type: "researcher", entityId: "r1" }).type).toBe(
      "researcher",
    );
    expect(reportSelectionSchema.parse({ type: "center", entityId: "c1" }).type).toBe("center");
    expect(reportSelectionSchema.parse({ type: "advances", entityId: "p3" }).type).toBe(
      "advances",
    );
  });

  it("rejects an unknown report type", () => {
    expect(reportSelectionSchema.safeParse({ type: "budget", entityId: "x" }).success).toBe(
      false,
    );
  });

  it("rejects a selection without an entity id", () => {
    const result = reportSelectionSchema.safeParse({ type: "project", entityId: "" });
    expect(result.success).toBe(false);
  });
});

describe("resolveSelectorKind", () => {
  it("maps advances to the project selector", () => {
    expect(resolveSelectorKind("advances")).toBe("project");
  });

  it("keeps the other report types as their own selector kind", () => {
    expect(resolveSelectorKind("project")).toBe("project");
    expect(resolveSelectorKind("researcher")).toBe("researcher");
    expect(resolveSelectorKind("center")).toBe("center");
  });
});

describe("parseReportSelection", () => {
  it("returns the validated selection for valid input", () => {
    expect(parseReportSelection({ type: "center", entityId: "c2" })).toEqual({
      type: "center",
      entityId: "c2",
    });
  });

  it("returns null for invalid input", () => {
    expect(parseReportSelection({ type: "project" })).toBeNull();
    expect(parseReportSelection(null)).toBeNull();
    expect(parseReportSelection({ type: "advances", entityId: "" })).toBeNull();
  });
});
