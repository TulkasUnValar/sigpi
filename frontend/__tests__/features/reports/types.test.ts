/**
 * Reports types — module contracts.
 *
 * Spec (frontend-reports): ReportType (project/researcher/center/advances),
 * ReportStatus (not_generated/generated/approved), ReportTarget, and the
 * preview `{html}` shape. Pure structural task — assertions exercise the
 * intended shape of each type.
 */

import type {
  ReportPreview,
  ReportStatus,
  ReportTarget,
  ReportType,
} from "@/features/reports/types";

describe("reports types", () => {
  it("models a report target with type, entity id and name", () => {
    const target: ReportTarget = {
      type: "project",
      entityId: "p1",
      entityName: "Proyecto Alpha",
    };
    expect(target.type).toBe("project");
    expect(target.entityId).toBe("p1");
    expect(target.entityName).toBe("Proyecto Alpha");
  });

  it("models the preview response as an html string", () => {
    const preview: ReportPreview = { html: "<h1>Informe de avances</h1>" };
    expect(preview.html).toContain("<h1>Informe de avances</h1>");
  });

  it("accepts exactly the four report type codes", () => {
    const types: ReportType[] = ["project", "researcher", "center", "advances"];
    expect(types).toHaveLength(4);
    expect(types).toContain("advances");
  });

  it("accepts exactly the three report status codes", () => {
    const statuses: ReportStatus[] = ["not_generated", "generated", "approved"];
    expect(statuses).toHaveLength(3);
    expect(statuses).toContain("not_generated");
  });
});
