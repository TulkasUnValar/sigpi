/**
 * Seed fixtures — reports dataset (preview HTML, PDF bytes, approvals).
 *
 * Mirrors the archived apps.reports contracts so the MSW handlers serve
 * realistic preview/pdf/approve responses during dev/tests:
 *   - preview 200 → {"html": "..."} (PreviewSerializer)
 *   - pdf 200 → application/pdf bytes (FileResponse)
 *   - approve 200 → {"status": "approved", ...}; 409 → RN-017 verbatim.
 */

/** RN-017 exact server message (approval 409 — services.py). */
export const RN_017_MESSAGE = "Pending progress reports must be reviewed";

/** Preview HTML served by GET /api/reports/{type}/{id}/preview/ (200). */
export const fixtureReportPreviewHtml = `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <title>Informe de proyecto</title>
  </head>
  <body>
    <h1>Informe de proyecto</h1>
    <p>Resumen generado por WeasyPrint para la vista previa.</p>
  </body>
</html>`;

/** PDF bytes served by GET /api/reports/{type}/{id}/pdf/ (%PDF magic header). */
export const fixtureReportPdfBytes = new Uint8Array([
  0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, // %PDF-1.4
  0x0a, 0x25, 0xe2, 0xe3, 0xcf, 0xd3, 0x0a, // binary comment line
]);

/** Approve success payload — POST /api/reports/{type}/{id}/approve/ (200). */
export const fixtureReportApproveSuccess = {
  status: "approved",
  report_id: "rep-1",
  approval_id: "appr-1",
} as const;

/** Approve 403 payload (RN-016 — center director only). */
export const fixtureReportApproveForbidden = {
  error: "You must be a center director to approve reports.",
} as const;

/** Approve 409 payload (RN-017 — verbatim server message). */
export const fixtureReportApproveConflict = {
  error: RN_017_MESSAGE,
} as const;
