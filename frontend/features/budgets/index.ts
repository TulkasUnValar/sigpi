/**
 * Budgets feature — public API.
 *
 * Re-exports components, hooks, types, and utilities for the budgets module.
 * Follows the same pattern as calls, projects, researchers.
 */

// Components
export { BudgetList } from "./BudgetList";
export { BudgetForm } from "./BudgetForm";
export { BudgetDetail } from "./BudgetDetail";
export { BudgetSummary } from "./BudgetSummary";

// Hooks - Queries
export {
  useBudgets,
  useBudget,
  useBudgetLines,
  useBudgetExecutions,
  useFundingSources,
  useBudgetAttachments,
  useBudgetSummary,
} from "./queries";

// Hooks - Mutations
export {
  useCreateBudget,
  useUpdateBudget,
  useDeleteBudget,
  useCreateBudgetLine,
  useUpdateBudgetLine,
  useDeleteBudgetLine,
  useCreateFundingSource,
  useUpdateFundingSource,
  useDeleteFundingSource,
  useCreateBudgetExecution,
  useCreateBudgetAttachment,
  useUpdateBudgetAttachment,
  useDeleteBudgetAttachment,
} from "./mutations";

// Permissions
export { useBudgetPermissions, canManageBudget, canAuthorizeExecution } from "./permissions";

// Constants
export {
  BUDGET_STATUS_LABELS,
  BUDGET_STATUS_VARIANTS,
  BUDGET_DOC_TYPE_LABELS,
  BUDGET_DOC_TYPE_OPTIONS,
  BUDGET_STATUS_OPTIONS,
  formatCurrency,
  parseDecimal,
} from "./constants";

// Schemas
export {
  budgetFormSchema,
  budgetLineFormSchema,
  fundingSourceFormSchema,
  budgetExecutionFormSchema,
  budgetAttachmentFormSchema,
  buildCreateBudgetPayload,
  buildUpdateBudgetPayload,
  buildCreateBudgetLinePayload,
  buildUpdateBudgetLinePayload,
  buildCreateFundingSourcePayload,
  buildUpdateFundingSourcePayload,
  buildCreateBudgetExecutionPayload,
  buildCreateBudgetAttachmentPayload,
} from "./schemas";
export type {
  BudgetFormValues,
  BudgetLineFormValues,
  FundingSourceFormValues,
  BudgetExecutionFormValues,
  BudgetAttachmentFormValues,
} from "./schemas";

// Types
export type {
  Budget,
  BudgetListItem,
  BudgetLine,
  FundingSource,
  BudgetExecution,
  BudgetAttachment,
  BudgetSummary as BudgetSummaryType,
  BudgetFilter,
  BudgetStatus,
  BudgetDocType,
  CreateBudgetPayload,
  UpdateBudgetPayload,
  CreateBudgetLinePayload,
  UpdateBudgetLinePayload,
  CreateFundingSourcePayload,
  UpdateFundingSourcePayload,
  CreateBudgetExecutionPayload,
  CreateBudgetAttachmentPayload,
  UpdateBudgetAttachmentPayload,
  Page,
} from "./types";
