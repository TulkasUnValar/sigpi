/**
 * Budgets fixtures — MSW test data for budget entities.
 */

import type {
  Budget,
  BudgetAttachment,
  BudgetExecution,
  BudgetLine,
  BudgetListItem,
  BudgetSummary,
  FundingSource,
} from "@/features/budgets/types";

export const mockBudgetLine: BudgetLine = {
  id: "line-1",
  budget: "budget-1",
  name: "Personal",
  approved_amount: "5000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockBudgetLine2: BudgetLine = {
  id: "line-2",
  budget: "budget-1",
  name: "Equipos",
  approved_amount: "3000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockBudgetAttachment: BudgetAttachment = {
  id: "attachment-1",
  budget: "budget-1",
  name: "Formulación del proyecto",
  doc_type: "formulacion",
  external_url: "https://example.com/document.pdf",
  created_at: "2026-01-01T00:00:00Z",
};

export const mockBudget: Budget = {
  id: "budget-1",
  project: "project-1",
  institution: "inst-1",
  name: "Presupuesto 2026",
  approved_amount: "10000.00",
  status: "draft",
  lines: [mockBudgetLine, mockBudgetLine2],
  attachments: [mockBudgetAttachment],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockBudgetListItem: BudgetListItem = {
  id: "budget-1",
  project: "project-1",
  project_name: "Proyecto IA",
  name: "Presupuesto 2026",
  approved_amount: "10000.00",
  status: "draft",
  created_at: "2026-01-01T00:00:00Z",
};

export const mockBudgetListItem2: BudgetListItem = {
  id: "budget-2",
  project: "project-2",
  project_name: "Proyecto Biotech",
  name: "Presupuesto 2026",
  approved_amount: "25000.00",
  status: "approved",
  created_at: "2026-01-02T00:00:00Z",
};

export const mockFundingSource: FundingSource = {
  id: "source-1",
  project: "project-1",
  name: "MinCiencias",
  amount: "8000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockFundingSource2: FundingSource = {
  id: "source-2",
  project: "project-1",
  name: "Recursos propios",
  amount: "2000.00",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const mockBudgetExecution: BudgetExecution = {
  id: "execution-1",
  line: "line-1",
  amount: "1500.00",
  executed_at: "2026-03-15",
  authorized_by: null,
  authorized_at: null,
  created_at: "2026-03-15T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
};

export const mockBudgetExecutionAuthorized: BudgetExecution = {
  id: "execution-2",
  line: "line-1",
  amount: "4000.00",
  executed_at: "2026-04-20",
  authorized_by: "user-1",
  authorized_at: "2026-04-20T00:00:00Z",
  created_at: "2026-04-20T00:00:00Z",
  updated_at: "2026-04-20T00:00:00Z",
};

export const mockBudgetSummary: BudgetSummary = {
  approved: "10000.00",
  executed: "5500.00",
  balance: "4500.00",
};
