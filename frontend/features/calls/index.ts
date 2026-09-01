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
export {
  useCallsList,
  useCallDetail,
  useCallDocuments,
  useCallProjects,
  useCallStateHistory,
} from "@/features/calls/queries";
export {
  useCreateCall,
  useUpdateCall,
  useDeleteCall,
  useCallTransition,
} from "@/features/calls/mutations";
export { getCallActions, isDestructiveCallAction } from "@/features/calls/fsm";
export type { CallAction } from "@/features/calls/fsm";
export { canManageCall, MANAGER_ROLES } from "@/features/calls/permissions";
export {
  getCallTypeLabel,
  getCallStatusLabel,
  CALL_STATUS_LABELS,
  CALL_TYPE_LABELS,
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
  Page,
} from "@/features/calls/types";