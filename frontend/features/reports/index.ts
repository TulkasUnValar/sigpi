/**
 * Reports feature barrel — public API of the module.
 *
 * Pages and the shell import from here; internals stay private to the
 * feature directory.
 */

export { ReportHub } from "@/features/reports/ReportHub";
export { ReportGeneratorForm } from "@/features/reports/ReportGeneratorForm";
export { useReportPreview, useReportEntityOptions } from "@/features/reports/queries";
export { useApproveReport } from "@/features/reports/mutations";
export {
  canGenerateReport,
  canApproveReport,
  isDirector,
  isAdminPlus,
  roleLevel,
} from "@/features/reports/permissions";
export {
  REPORT_TYPES,
  REPORT_TYPE_OPTIONS,
  REPORT_STATUS_LABELS,
  getReportTypeLabel,
  getReportStatusLabel,
  buildPreviewUrl,
  buildPdfUrl,
  buildApproveUrl,
  buildPdfFilename,
} from "@/features/reports/constants";
export { reportSelectionSchema, resolveSelectorKind, parseReportSelection } from "@/features/reports/schemas";
export type { ReportSelection } from "@/features/reports/schemas";
export type {
  Page,
  ReportApprovalResponse,
  ReportPreview,
  ReportSelectorKind,
  ReportStatus,
  ReportTarget,
  ReportType,
} from "@/features/reports/types";
