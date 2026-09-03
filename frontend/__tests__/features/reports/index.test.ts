/**
 * Reports feature barrel — public API surface.
 *
 * Design (frontend-reports): the feature index re-exports types,
 * constants, schemas, authorization helpers, hooks, mutations and
 * components. This test exercises the barrel so the re-export statements
 * are covered and the public surface stays stable.
 */

import {
  REPORT_STATUS_LABELS,
  REPORT_TYPES,
  ReportGeneratorForm,
  ReportHub,
  buildApproveUrl,
  buildPdfFilename,
  buildPdfUrl,
  buildPreviewUrl,
  canApproveReport,
  canGenerateReport,
  getReportStatusLabel,
  getReportTypeLabel,
  isAdminPlus,
  isDirector,
  parseReportSelection,
  reportSelectionSchema,
  resolveSelectorKind,
  roleLevel,
  useApproveReport,
  useReportEntityOptions,
  useReportPreview,
} from "@/features/reports";

describe("reports feature barrel", () => {
  it("re-exports the report type and status label maps", () => {
    expect(REPORT_TYPES.project).toBe("Proyecto");
    expect(REPORT_STATUS_LABELS.not_generated).toBe("No generado");
    expect(getReportTypeLabel("advances")).toBe("Avances");
    expect(getReportStatusLabel("approved")).toBe("Aprobado");
  });

  it("re-exports the endpoint and filename builders", () => {
    expect(buildPreviewUrl("project", "p1")).toBe("/api/reports/project/p1/preview/");
    expect(buildPdfUrl("researcher", "r1")).toBe("/api/reports/researcher/r1/pdf/");
    expect(buildApproveUrl("center", "c1")).toBe("/api/reports/center/c1/approve/");
    expect(buildPdfFilename("project")).toBe("project_report.pdf");
  });

  it("re-exports the validation schema and selector mapping", () => {
    expect(reportSelectionSchema.parse({ type: "project", entityId: "p1" })).toEqual({
      type: "project",
      entityId: "p1",
    });
    expect(resolveSelectorKind("advances")).toBe("project");
    expect(parseReportSelection({ type: "center", entityId: "c1" })).toEqual({
      type: "center",
      entityId: "c1",
    });
  });

  it("re-exports the authorization helpers", () => {
    expect(canGenerateReport(["director"])).toBe(true);
    expect(canGenerateReport(["researcher"])).toBe(false);
    expect(canApproveReport(["director"], [{ id: "c1" }], "c1")).toBe(true);
    expect(isDirector(["admin"])).toBe(true);
    expect(isAdminPlus(["admin"])).toBe(true);
    expect(roleLevel("superadmin")).toBe(1);
  });

  it("re-exports the hooks and components", () => {
    expect(typeof useReportPreview).toBe("function");
    expect(typeof useReportEntityOptions).toBe("function");
    expect(typeof useApproveReport).toBe("function");
    expect(typeof ReportHub).toBe("function");
    expect(typeof ReportGeneratorForm).toBe("function");
  });
});
