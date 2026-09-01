/**
 * Calls feature barrel — public API of the module.
 *
 * Pages and the shell import from here; internals stay private to the
 * feature directory.
 */

export { CallList } from "@/features/calls/CallList";
export { CallForm } from "@/features/calls/CallForm";
export { CallDetail } from "@/features/calls/CallDetail";
export { FsmActionBar } from "@/features/calls/FsmActionBar";
export { DocumentsManager } from "@/features/calls/DocumentsManager";
export { ProjectsManager } from "@/features/calls/ProjectsManager";
export { StateHistoryManager } from "@/features/calls/StateHistoryManager";
export { DeleteCallButton } from "@/features/calls/DeleteCallButton";
export {
  useCallsList,
  useCallDetail,
  useCallDocuments,
  useCallProjects,
  useCallStateHistory,
  useProjectOptions,
} from "@/features/calls/queries";
export {
  useCreateCall,
  useUpdateCall,
  useDeleteCall,
  useCallTransition,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useLinkProject,
  useUnlinkProject,
} from "@/features/calls/mutations";
export type { DocumentPayload } from "@/features/calls/mutations";
export { getCallActions, isDestructiveCallAction } from "@/features/calls/fsm";
export type { CallAction } from "@/features/calls/fsm";
export { canManageCall, MANAGER_ROLES } from "@/features/calls/permissions";
export {
  getCallTypeLabel,
  getCallStatusLabel,
  CALL_STATUS_LABELS,
  CALL_TYPE_LABELS,
  CALL_DOC_TYPE_LABELS,
  CALL_DOC_TYPE_OPTIONS,
} from "@/features/calls/constants";
export { buildCallPayload, callFormSchema } from "@/features/calls/schemas";
export type { CallFormValues } from "@/features/calls/schemas";
export type {
  Call as CallDetailModel,
  CallList as CallListRow,
  CallDocument,
  CallProject,
  CallStateLog,
  CallFilter,
  CallStatus,
  CallType,
  CreateCallPayload,
  ProjectOption,
  Page,
} from "@/features/calls/types";
