/**
 * Institutions feature — public API.
 *
 * Exports the contracts, FSM config, query/mutation hooks and the
 * shared UI components consumed by the app routes and tests.
 */

// Types
export type {
  Institution,
  Sede,
  Facultad,
  ResearchCenter,
  ResearchGroup,
  ResearchLine,
  Page,
  EntityKind,
  EntityStatus,
  InstitutionTreeNode,
  FsmAction,
  EntityConfig,
  EntityField,
  EntityFieldOption,
  CreateInstitutionPayload,
  UpdateInstitutionPayload,
  CreateSedePayload,
  UpdateSedePayload,
  CreateFacultadPayload,
  UpdateFacultadPayload,
  CreateCenterPayload,
  UpdateCenterPayload,
} from "@/features/institutions/types";

// Schemas
export {
  institutionSchema,
  sedeSchema,
  facultadSchema,
  centerSchema,
  groupSchema,
  lineSchema,
  institutionConfig,
  sedeConfig,
  facultadConfig,
  centerConfig,
  type InstitutionFormValues,
  type SedeFormValues,
  type FacultadFormValues,
  type CenterFormValues,
} from "@/features/institutions/schemas";

// FSM
export {
  ENTITY_ACTIONS,
  getEntityActions,
  isDestructiveEntityAction,
} from "@/features/institutions/fsm";

// Queries
export {
  useActiveInstitutionId,
  fetchAllPages,
  useInstitutionsList,
  useInstitutionDetail,
  useSedes,
  useFacultades,
  useResearchCenters,
  useSedeDetail,
  useFacultadDetail,
  useCenterDetail,
} from "@/features/institutions/queries";

// Mutations
export {
  useCreateInstitution,
  useUpdateInstitution,
  useDeleteInstitution,
  useInstitutionTransition,
  useCreateSede,
  useUpdateSede,
  useDeleteSede,
  useSedeTransition,
  useCreateFacultad,
  useUpdateFacultad,
  useDeleteFacultad,
  useFacultadTransition,
  useCreateCenter,
  useUpdateCenter,
  useDeleteCenter,
  useCenterTransition,
} from "@/features/institutions/mutations";

// Components
export { EntityForm } from "@/features/institutions/EntityForm";
export { FsmActionBar, type FsmTransitionLike } from "@/features/institutions/FsmActionBar";
export { EntityDetail, type DetailField } from "@/features/institutions/EntityDetail";
export {
  InstitutionTree,
  flattenVisibleNodes,
  findParentId,
} from "@/features/institutions/InstitutionTree";
