/**
 * Advances feature barrel — public API of the module.
 *
 * Pages and the shell import from here; internals stay private to the
 * feature directory.
 */

export { FsmActionBar } from "@/features/advances/FsmActionBar";
export { DocumentsManager } from "@/features/advances/DocumentsManager";
export { AdvanceForm } from "@/features/advances/AdvanceForm";
export {
  useActiveInstitutionId,
  useAdvancesList,
  useAdvanceDetail,
  useAdvanceDocuments,
} from "@/features/advances/queries";
export {
  useCreateAdvance,
  useAdvanceTransition,
  useCreateAdvanceDocument,
  useUpdateAdvanceDocument,
  useDeleteAdvanceDocument,
  useUpdateAdvance,
  useDeleteAdvance,
} from "@/features/advances/mutations";
export type { AdvanceTransitionPayload } from "@/features/advances/mutations";
export {
  getAdvanceActions,
  isDestructiveAdvanceAction,
  needsReviewText,
} from "@/features/advances/fsm";
export type { AdvanceAction } from "@/features/advances/fsm";
export {
  getAdvanceStatusLabel,
  getAdvanceDocTypeLabel,
  ADVANCE_STATUS_LABELS,
  ADVANCE_STATUS_OPTIONS,
  ADVANCE_DOC_TYPE_LABELS,
  ADVANCE_DOC_TYPE_OPTIONS,
} from "@/features/advances/constants";
export {
  advanceCreateSchema,
  advanceEditSchema,
  advanceFormSchema,
} from "@/features/advances/schemas";
export type { AdvanceDraft, AdvanceFormValues } from "@/features/advances/schemas";
export type {
  AdvanceList,
  AdvanceDetail,
  AdvanceReview,
  AdvanceStateLog,
  AdvanceDocument,
  AdvanceDocumentPayload,
  AdvanceWritableFields,
  AdvanceEditPayload,
  CreateAdvancePayload,
  Page,
} from "@/features/advances/types";
