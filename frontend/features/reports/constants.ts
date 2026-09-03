/**
 * Reports feature constants — Spanish labels, options, endpoint builders.
 *
 * REPORT_TYPES mirrors the backend report codes (apps/reports). Endpoint
 * builders produce the exact DRF paths (urls.py): preview, pdf, approve.
 * buildPdfFilename matches the FileResponse filename `{type}_report.pdf`.
 */

import type { ReportStatus, ReportType } from "@/features/reports/types";

/** Spanish labels for the four report codes. */
export const REPORT_TYPES: Record<ReportType, string> = {
  project: "Proyecto",
  researcher: "Investigador",
  center: "Centro",
  advances: "Avances",
};

/** Report type select options (same order as the backend choices). */
export const REPORT_TYPE_OPTIONS = Object.entries(REPORT_TYPES).map(([value, label]) => ({
  value: value as ReportType,
  label,
}));

/** Spanish labels for the UI-projected report lifecycle status. */
export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  not_generated: "No generado",
  generated: "Generado",
  approved: "Aprobado",
};

/** Resolve a report type code into its Spanish label (fallback: raw value). */
export function getReportTypeLabel(type: ReportType | string): string {
  return REPORT_TYPES[type as ReportType] ?? type;
}

/** Resolve a report status code into its Spanish label. */
export function getReportStatusLabel(status: ReportStatus): string {
  return REPORT_STATUS_LABELS[status];
}

/** GET /api/reports/{type}/{id}/preview/ — HTML preview (RF-056). */
export function buildPreviewUrl(type: ReportType, id: string): string {
  return `/api/reports/${type}/${id}/preview/`;
}

/** GET /api/reports/{type}/{id}/pdf/ — WeasyPrint PDF (RF-057). */
export function buildPdfUrl(type: ReportType, id: string): string {
  return `/api/reports/${type}/${id}/pdf/`;
}

/** POST /api/reports/{type}/{id}/approve/ — director approval (RN-016). */
export function buildApproveUrl(type: ReportType, id: string): string {
  return `/api/reports/${type}/${id}/approve/`;
}

/** Filename served by the PDF FileResponse: `{type}_report.pdf`. */
export function buildPdfFilename(type: ReportType): string {
  return `${type}_report.pdf`;
}
