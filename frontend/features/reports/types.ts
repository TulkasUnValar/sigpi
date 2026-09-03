/**
 * Reports feature types — mirror the archived apps.reports contracts.
 *
 * - ReportType: the four report codes served by the backend (RF-050–RF-053).
 * - ReportStatus: UI projection of a report's lifecycle. The backend exposes
 *   only preview/pdf/approve actions (no registry), so the UI derives the
 *   status from successful operations: not_generated → generated (PDF) →
 *   approved (approve).
 * - ReportTarget: a selected reportable entity (type + id + display name).
 * - ReportPreview: the `{"html": "..."}` body of the preview endpoint.
 * - ReportApprovalResponse: the 200 body of POST .../approve/.
 */

/** The four report codes (backend ReportType choices). */
export type ReportType = "project" | "researcher" | "center" | "advances";

/** UI-projected report lifecycle status. */
export type ReportStatus = "not_generated" | "generated" | "approved";

/**
 * Selector kind fed by the entity hooks. `advances` deliberately maps to
 * projects — advances reports target a project entity (RB-004).
 */
export type ReportSelectorKind = "project" | "researcher" | "center";

/** A selected reportable entity. */
export interface ReportTarget {
  type: ReportType;
  entityId: string;
  entityName: string;
}

/** Body of GET /api/reports/{type}/{id}/preview/ (PreviewSerializer). */
export interface ReportPreview {
  html: string;
}

/** Body of POST /api/reports/{type}/{id}/approve/ on success. */
export interface ReportApprovalResponse {
  status: "approved";
  report_id: string;
  approval_id: string;
}

/** DRF paginated envelope (entity lists). */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
