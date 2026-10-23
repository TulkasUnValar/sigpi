/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Budgets mutations tests — TanStack Query hooks for budget CRUD operations.
 *
 * Tests mutation calls, cache invalidation, and error handling.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import {
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
} from "@/features/budgets/mutations";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api";
import type {
  Budget,
  BudgetLine,
  BudgetExecution,
  FundingSource,
  BudgetAttachment,
} from "@/features/budgets/types";

jest.mock("@/lib/api");
jest.mock("@/store/auth");

const mockApi = api as jest.Mocked<typeof api>;
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useCreateBudget", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("creates a budget", async () => {
    const mockBudget: Budget = {
      id: "budget-new",
      project: "project-1",
      institution: "inst-1",
      name: "Budget 2026",
      approved_amount: "10000.00",
      status: "draft",
      lines: [],
      attachments: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockBudget);

    const { result } = renderHook(() => useCreateBudget(), { wrapper: createWrapper() });

    result.current.mutate({
      project: "project-1",
      name: "Budget 2026",
      approved_amount: "10000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith("/api/budgets/", {
      project: "project-1",
      name: "Budget 2026",
      approved_amount: "10000.00",
    });
  });

  it("handles creation error", async () => {
    mockApi.post.mockRejectedValue(new Error("Duplicate budget"));

    const { result } = renderHook(() => useCreateBudget(), { wrapper: createWrapper() });

    result.current.mutate({
      project: "project-1",
      name: "Budget 2026",
      approved_amount: "10000.00",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
  });
});

describe("useUpdateBudget", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("updates a budget", async () => {
    const mockBudget: Budget = {
      id: "budget-1",
      project: "project-1",
      institution: "inst-1",
      name: "Budget 2026 v2",
      approved_amount: "15000.00",
      status: "draft",
      lines: [],
      attachments: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockApi.patch.mockResolvedValue(mockBudget);

    const { result } = renderHook(() => useUpdateBudget("budget-1"), { wrapper: createWrapper() });

    result.current.mutate({
      name: "Budget 2026 v2",
      approved_amount: "15000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.patch).toHaveBeenCalledWith("/api/budgets/budget-1/", {
      name: "Budget 2026 v2",
      approved_amount: "15000.00",
    });
  });
});

describe("useDeleteBudget", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("deletes a budget", async () => {
    mockApi.delete.mockResolvedValue({});

    const { result } = renderHook(() => useDeleteBudget("budget-1"), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.delete).toHaveBeenCalledWith("/api/budgets/budget-1/");
  });
});

describe("useCreateBudgetLine", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("creates a budget line", async () => {
    const mockLine: BudgetLine = {
      id: "line-new",
      budget: "budget-1",
      name: "Personal",
      approved_amount: "5000.00",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockLine);

    const { result } = renderHook(() => useCreateBudgetLine("budget-1"), { wrapper: createWrapper() });

    result.current.mutate({
      name: "Personal",
      approved_amount: "5000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith("/api/budgets/budget-1/lines/", {
      name: "Personal",
      approved_amount: "5000.00",
    });
  });
});

describe("useCreateBudgetExecution", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("creates a budget execution within approved amount", async () => {
    const mockExecution: BudgetExecution = {
      id: "exec-new",
      line: "line-1",
      amount: "1000.00",
      executed_at: "2026-03-15",
      authorized_by: null,
      authorized_at: null,
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockExecution);

    const { result } = renderHook(
      () => useCreateBudgetExecution("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      amount: "1000.00",
      executed_at: "2026-03-15",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith(
      "/api/budgets/budget-1/lines/line-1/executions/",
      {
        amount: "1000.00",
        executed_at: "2026-03-15",
      },
    );
  });

  it("creates an authorized over-execution", async () => {
    const mockExecution: BudgetExecution = {
      id: "exec-new",
      line: "line-1",
      amount: "15000.00",
      executed_at: "2026-03-15",
      authorized_by: "user-1",
      authorized_at: "2026-03-15T10:00:00Z",
      created_at: "2026-03-15T00:00:00Z",
      updated_at: "2026-03-15T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockExecution);

    const { result } = renderHook(
      () => useCreateBudgetExecution("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      amount: "15000.00",
      executed_at: "2026-03-15",
      authorized_by: "user-1",
      authorized_at: "2026-03-15T10:00:00Z",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith(
      "/api/budgets/budget-1/lines/line-1/executions/",
      {
        amount: "15000.00",
        executed_at: "2026-03-15",
        authorized_by: "user-1",
        authorized_at: "2026-03-15T10:00:00Z",
      },
    );
  });

  it("handles over-execution error without authorization (RN-020)", async () => {
    const error = new Error("Execution exceeds approved budget");
    (error as any).status = 400;
    mockApi.post.mockRejectedValue(error);

    const { result } = renderHook(
      () => useCreateBudgetExecution("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      amount: "15000.00",
      executed_at: "2026-03-15",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateBudgetLine", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("updates a budget line", async () => {
    const mockLine: BudgetLine = {
      id: "line-1",
      budget: "budget-1",
      name: "Personal Actualizado",
      approved_amount: "6000.00",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockApi.patch.mockResolvedValue(mockLine);

    const { result } = renderHook(
      () => useUpdateBudgetLine("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "Personal Actualizado",
      approved_amount: "6000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.patch).toHaveBeenCalledWith("/api/budgets/budget-1/lines/line-1/", {
      name: "Personal Actualizado",
      approved_amount: "6000.00",
    });
  });

  it("handles update error", async () => {
    mockApi.patch.mockRejectedValue(new Error("Update failed"));

    const { result } = renderHook(
      () => useUpdateBudgetLine("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "Personal Actualizado",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useDeleteBudgetLine", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("deletes a budget line", async () => {
    mockApi.delete.mockResolvedValue({});

    const { result } = renderHook(
      () => useDeleteBudgetLine("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.delete).toHaveBeenCalledWith("/api/budgets/budget-1/lines/line-1/");
  });

  it("handles delete error when line has executions (409)", async () => {
    const error = new Error("Cannot delete line with executions");
    (error as any).status = 409;
    mockApi.delete.mockRejectedValue(error);

    const { result } = renderHook(
      () => useDeleteBudgetLine("budget-1", "line-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateFundingSource", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("creates a funding source", async () => {
    const mockSource: FundingSource = {
      id: "source-new",
      project: "project-1",
      name: "MinCiencias",
      amount: "8000.00",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockSource);

    const { result } = renderHook(
      () => useCreateFundingSource("project-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "MinCiencias",
      amount: "8000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith("/api/projects/project-1/funding-sources/", {
      name: "MinCiencias",
      amount: "8000.00",
    });
  });

  it("handles creation error", async () => {
    mockApi.post.mockRejectedValue(new Error("Creation failed"));

    const { result } = renderHook(
      () => useCreateFundingSource("project-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "MinCiencias",
      amount: "8000.00",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateFundingSource", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("updates a funding source", async () => {
    const mockSource: FundingSource = {
      id: "source-1",
      project: "project-1",
      name: "MinCiencias Actualizado",
      amount: "9000.00",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    };
    mockApi.patch.mockResolvedValue(mockSource);

    const { result } = renderHook(
      () => useUpdateFundingSource("project-1", "source-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "MinCiencias Actualizado",
      amount: "9000.00",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.patch).toHaveBeenCalledWith(
      "/api/projects/project-1/funding-sources/source-1/",
      {
        name: "MinCiencias Actualizado",
        amount: "9000.00",
      },
    );
  });
});

describe("useDeleteFundingSource", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("deletes a funding source", async () => {
    mockApi.delete.mockResolvedValue({});

    const { result } = renderHook(
      () => useDeleteFundingSource("project-1", "source-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.delete).toHaveBeenCalledWith(
      "/api/projects/project-1/funding-sources/source-1/",
    );
  });
});

describe("useCreateBudgetAttachment", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("creates a budget attachment", async () => {
    const mockAttachment: BudgetAttachment = {
      id: "att-new",
      budget: "budget-1",
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "https://example.com/doc.pdf",
      created_at: "2026-01-01T00:00:00Z",
    };
    mockApi.post.mockResolvedValue(mockAttachment);

    const { result } = renderHook(
      () => useCreateBudgetAttachment("budget-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "https://example.com/doc.pdf",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.post).toHaveBeenCalledWith("/api/budgets/budget-1/attachments/", {
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "https://example.com/doc.pdf",
    });
  });

  it("handles creation error when external_url is missing (RF-B05)", async () => {
    const error = new Error("external_url is required");
    (error as any).status = 400;
    mockApi.post.mockRejectedValue(error);

    const { result } = renderHook(
      () => useCreateBudgetAttachment("budget-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "",
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateBudgetAttachment", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("updates a budget attachment", async () => {
    const mockAttachment: BudgetAttachment = {
      id: "att-1",
      budget: "budget-1",
      name: "Formulación Actualizada",
      doc_type: "formulacion",
      external_url: "https://example.com/doc-v2.pdf",
      created_at: "2026-01-01T00:00:00Z",
    };
    mockApi.patch.mockResolvedValue(mockAttachment);

    const { result } = renderHook(
      () => useUpdateBudgetAttachment("budget-1", "att-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate({
      name: "Formulación Actualizada",
      external_url: "https://example.com/doc-v2.pdf",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.patch).toHaveBeenCalledWith(
      "/api/budgets/budget-1/attachments/att-1/",
      {
        name: "Formulación Actualizada",
        external_url: "https://example.com/doc-v2.pdf",
      },
    );
  });
});

describe("useDeleteBudgetAttachment", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthStore.mockReturnValue({
      activeInstitution: { id: "inst-1", name: "Test Institution" },
    } as any);
  });

  it("deletes a budget attachment", async () => {
    mockApi.delete.mockResolvedValue({});

    const { result } = renderHook(
      () => useDeleteBudgetAttachment("budget-1", "att-1"),
      { wrapper: createWrapper() },
    );

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApi.delete).toHaveBeenCalledWith("/api/budgets/budget-1/attachments/att-1/");
  });
});
