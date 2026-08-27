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
  CreateInstitutionPayload,
  UpdateInstitutionPayload,
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
  type InstitutionFormValues,
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
} from "@/features/institutions/queries";

// Mutations
export {
  useCreateInstitution,
  useUpdateInstitution,
  useDeleteInstitution,
  useInstitutionTransition,
} from "@/features/institutions/mutations";

// Components
export { EntityForm } from "@/features/institutions/EntityForm";
export { FsmActionBar } from "@/features/institutions/FsmActionBar";
export { EntityDetail } from "@/features/institutions/EntityDetail";
export {
  InstitutionTree,
  flattenVisibleNodes,
  findParentId,
} from "@/features/institutions/InstitutionTree";
