/**
 * Projects feature barrel — public API of the module.
 *
 * Pages, the shell, and tests import from here; internals stay private to
 * the feature directory (calls/products/advances pattern).
 */

export { ProjectList } from "@/features/projects/ProjectList";
export { ProjectDetail } from "@/features/projects/ProjectDetail";
export { ProjectWizard } from "@/features/projects/ProjectWizard";
export { ProjectForm } from "@/features/projects/ProjectForm";
export { FsmActionBar } from "@/features/projects/FsmActionBar";
export {
  useActiveInstitutionId,
  useProjectsList,
  useProjectDetail,
  useProjectObservations,
  useProjectStateHistory,
  useCenters,
  useGroups,
  useLines,
  useResearchers,
} from "@/features/projects/queries";
export {
  useCreateProject,
  useProjectTransition,
  useUpdateProject,
} from "@/features/projects/mutations";
export { getProjectActions, isDestructiveAction, canEditProject } from "@/features/projects/fsm";
export type { ProjectAction } from "@/features/projects/fsm";
export {
  basicStepSchema,
  classificationStepSchema,
  teamStepSchema,
  documentsStepSchema,
  projectFormSchema,
  buildUpdatePayload,
} from "@/features/projects/schemas";
export type { ProjectDraft, DocumentDraft, ProjectFormValues } from "@/features/projects/schemas";
export type {
  Page,
  ProjectList as ProjectListRow,
  ProjectMember,
  ProjectDocument,
  ProjectObservation,
  ProjectStateLog,
  ProjectDetail as ProjectDetailModel,
  HierarchyNode,
  ResearcherOption,
  TeamMemberDraft,
  CreateProjectPayload,
  UpdateProjectPayload,
} from "@/features/projects/types";
