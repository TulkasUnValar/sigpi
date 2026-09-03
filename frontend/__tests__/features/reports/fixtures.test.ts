/**
 * Reports fixtures — preview HTML, PDF bytes, approval payloads.
 *
 * Spec (frontend-reports 1.14): the fixtures mirror the archived
 * apps.reports contracts so the MSW handlers serve realistic
 * preview/pdf/approve responses — including the verbatim RN-017 409.
 */

import {
  RN_017_MESSAGE,
  fixtureReportApproveConflict,
  fixtureReportApproveForbidden,
  fixtureReportApproveSuccess,
  fixtureReportPdfBytes,
  fixtureReportPreviewHtml,
} from "@/fixtures";

describe("reports fixtures", () => {
  it("exports preview HTML that renders a report body", () => {
    expect(fixtureReportPreviewHtml).toContain("<html");
    expect(fixtureReportPreviewHtml).toContain("Informe de proyecto");
  });

  it("exports PDF bytes starting with the %PDF magic header", () => {
    const head = String.fromCharCode(...fixtureReportPdfBytes.slice(0, 5));
    expect(head).toBe("%PDF-");
  });

  it("exports the approve success payload with status approved", () => {
    expect(fixtureReportApproveSuccess).toEqual({
      status: "approved",
      report_id: "rep-1",
      approval_id: "appr-1",
    });
  });

  it("exports the 403 director-only payload (RN-016)", () => {
    expect(fixtureReportApproveForbidden).toEqual({
      error: "You must be a center director to approve reports.",
    });
  });

  it("exports the 409 RN-017 payload with the verbatim message", () => {
    expect(RN_017_MESSAGE).toBe("Pending progress reports must be reviewed");
    expect(fixtureReportApproveConflict).toEqual({ error: RN_017_MESSAGE });
  });
});
