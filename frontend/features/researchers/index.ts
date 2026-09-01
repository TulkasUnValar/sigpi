/**
 * Researchers feature — public API.
 *
 * Exports the contracts, schemas, lifecycle config, authorization
 * helpers, query/mutation hooks and the shared UI components consumed
 * by the app routes and tests.
 */

// Types
export type {
  Page,
  ResearcherList as ResearcherListItem,
  Researcher,
  ResearcherAffiliation,
  ExternalProfile,
  ResearcherAttachment,
  CreateResearcherPayload,
  UpdateResearcherPayload,
} from "@/features/researchers/types";

// Schemas
export {
  researcherCreateSchema,
  researcherEditSchema,
  DOCUMENT_TYPES,
  type ResearcherCreateFormValues,
  type ResearcherEditFormValues,
} from "@/features/researchers/schemas";

// FSM
export {
  RESEARCHER_ACTIONS,
  getResearcherActions,
  isResearcherDeactivate,
} from "@/features/researchers/fsm";

// Authorization
export {
  isAdminPlus,
  canDeactivateResearcher,
  canEditResearcher,
} from "@/features/researchers/permissions";

// Queries
export {
  useActiveInstitutionId,
  useResearchersList,
  useResearcherDetail,
  useResearcherAffiliations,
  useResearcherProfiles,
  useResearcherAttachments,
  type ResearchersListParams,
} from "@/features/researchers/queries";

// Mutations
export {
  useCreateResearcher,
  useUpdateResearcher,
  useDeactivateResearcher,
} from "@/features/researchers/mutations";

// Components
export { CompletenessBar, getCompletenessState } from "@/features/researchers/CompletenessBar";
export { ResearcherForm } from "@/features/researchers/ResearcherForm";
export { ResearcherList, researcherStatus } from "@/features/researchers/ResearcherList";
export { ResearcherDetail } from "@/features/researchers/ResearcherDetail";
export { DeactivateResearcherButton } from "@/features/researchers/DeactivateResearcherButton";
