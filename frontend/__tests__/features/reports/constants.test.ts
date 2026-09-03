/**
 * Reports constants — Spanish labels, option lists, endpoint builders.
 *
 * Spec (frontend-reports 1.2): REPORT_TYPES maps the four report codes to
 * Spanish labels; builders produce the preview/pdf/approve endpoint paths
 * and the `{type}_report.pdf` filename (backend FileResponse contract).
 */

import {
  REPORT_STATUS_LABELS,
  REPORT_TYPES,
  REPORT_TYPE_OPTIONS,
  buildApproveUrl,
  buildPdfFilename,
  buildPdfUrl,
  buildPreviewUrl,
  getReportStatusLabel,
  getReportTypeLabel,
} from "@/features/reports/constants";

describe("REPORT_TYPES", () => {
  it("maps the four report codes to Spanish labels", () => {
    expect(REPORT_TYPES).toEqual({
      project: "Proyecto",
      researcher: "Investigador",
      center: "Centro",
      advances: "Avances",
    });
  });

  it("exposes exactly four value+label options in backend order", () => {
    expect(REPORT_TYPE_OPTIONS).toHaveLength(4);
    expect(REPORT_TYPE_OPTIONS[0]).toEqual({ value: "project", label: "Proyecto" });
    expect(REPORT_TYPE_OPTIONS.map((o) => o.value)).toEqual([
      "project",
      "researcher",
      "center",
      "advances",
    ]);
  });
});

describe("REPORT_STATUS_LABELS", () => {
  it("maps the three status codes to Spanish labels", () => {
    expect(REPORT_STATUS_LABELS).toEqual({
      not_generated: "No generado",
      generated: "Generado",
      approved: "Aprobado",
    });
  });
});

describe("label helpers", () => {
  it("resolves a known type into its Spanish label", () => {
    expect(getReportTypeLabel("project")).toBe("Proyecto");
    expect(getReportTypeLabel("advances")).toBe("Avances");
  });

  it("falls back to the raw value for unknown types", () => {
    expect(getReportTypeLabel("bogus")).toBe("bogus");
  });

  it("resolves every status code into its Spanish label", () => {
    expect(getReportStatusLabel("not_generated")).toBe("No generado");
    expect(getReportStatusLabel("generated")).toBe("Generado");
    expect(getReportStatusLabel("approved")).toBe("Aprobado");
  });
});

describe("endpoint builders", () => {
  it("builds the preview URL for any report type", () => {
    expect(buildPreviewUrl("project", "p1")).toBe("/api/reports/project/p1/preview/");
    expect(buildPreviewUrl("advances", "p3")).toBe("/api/reports/advances/p3/preview/");
  });

  it("builds the pdf URL", () => {
    expect(buildPdfUrl("researcher", "r1")).toBe("/api/reports/researcher/r1/pdf/");
  });

  it("builds the approve URL", () => {
    expect(buildApproveUrl("center", "c1")).toBe("/api/reports/center/c1/approve/");
  });

  it("builds the {type}_report.pdf filename for the FileResponse", () => {
    expect(buildPdfFilename("project")).toBe("project_report.pdf");
    expect(buildPdfFilename("advances")).toBe("advances_report.pdf");
  });
});
